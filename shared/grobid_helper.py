import os
import subprocess
import bibtexparser
import requests
import PyPDF2
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTTextLine, LTChar
import html
import fitz
import xml.etree.ElementTree as ET

def doi_vers_bibtex_en_dict(doi, pdf_file):
    '''
    Il faut https://github.com/PauCasanova/doi2bib.git
    '''
    if 'temp' in os.listdir():
        os.system("rm temp")
    print(f'./d2b {doi} temp')
    resultat = subprocess.run(['./d2b', doi, 'temp'])
    if resultat.returncode != 0:
        return False
    resultat = open('temp').read()
    if '@' in resultat:
        bibtex_str = '@'+resultat.split("@")[1].split('\n\n')[0]
        bibtex_str = '\n'.join(segment.rstrip() for segment in bibtex_str.split('\n'))
        if len(bibtexparser.loads(bibtex_str).entries) == 0:
            return False
        bibtex_dict = bibtexparser.loads(bibtex_str).entries[0]
        if 'title' in bibtex_dict:
            bibtex_dict['title'] = normalise_texte(bibtex_dict['title'].replace('\n', ' '))
            bibtex_dict['title'] = bibtex_dict['title'].replace('<scp>', '').replace('</scp>', '')
            if 'author' in bibtex_dict:
                bibtex_dict['author'] = bibtex_dict['author'].replace('{', '').replace('}', '')
            """if 'mes_dois.pkl' in os.listdir():
                with open('mes_dois.pkl', 'rb') as f:
                    mes_dois = pickle.load(f)
            else:
                mes_dois = {}
            if doi not in mes_dois:
                mes_dois[doi] = {'title': bibtex_dict['title'],
                                 'location': pdf_file}
            else:
                print(f"{bibtex_dict['title']} ({doi}) déjà présent")
                #shutil.rmtree(pdf_file.parent.parent)
                return False
            with open('mes_dois.pkl', 'wb') as f:
                pickle.dump(mes_dois, f)                    
            """
            print("  => bibtex trouvé :")
            print(bibtex_str)
            return (bibtex_dict, bibtex_str)
        else:
            print(bibtex_dict)
            return False
        
def chercher_doi(titre_article):
    # URL de la recherche CrossRef
    url_recherche = "https://api.crossref.org/works?query="
    # Requête à l'API CrossRef avec le titre de l'article
    reponse = requests.get(url_recherche + titre_article)
    if reponse.status_code == 200:
        donnees = reponse.json()
        # Trouver le premier DOI dans les résultats
        for item in donnees['message']['items']:
            if 'DOI' in item:
                print(f"   => DOI retrouvé : {item['DOI']}")
                return item['DOI']
        return ""

def replacement(match):
    # Obtenir le mot complet (nom de l'espèce)
    complete_match = match.group(0)
    # Obtenir le texte complet et la position du motif trouvé
    full_text = match.string
    start, end = match.start(), match.end()
    # Déterminer s'il faut ajouter un espace avant
    prefix_space = ' ' if start > 0 and full_text[start-1].isalnum() else ''
    # Déterminer s'il faut ajouter un espace après
    suffix_space = ' ' if end < len(full_text) and full_text[end].isalnum() else ''
    return f"{prefix_space}{complete_match}{suffix_space}"

def normalise_texte(text):
    if text is not None:
        for possible_species in species_list:
            for species in [possible_species, possible_species.replace('Mycobacterium', 'M.')]:
                if species in text:
                    '''
                    # Expression régulière
                    species_pattern = fr"({re.escape(species)})"
                    # Substitution
                    text = re.sub(species_pattern, replacement, text)
                    '''
                    text = text.replace(species, possible_species)
        text = text.replace(' ,', ',')
        text.replace(' )', ')')
    return text

def extraire_titre_metadonnees(chemin_pdf):
    with open(chemin_pdf, 'rb') as fichier:
        lecteur_pdf = PyPDF2.PdfReader(fichier)
        info = lecteur_pdf.metadata
        return info.title if info.title else "Titre non disponible"

def extraire_titre_pdfminer(chemin_pdf):
    for page_layout in extract_pages(chemin_pdf):
        titres_potentiels = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                for text_line in element:
                    if isinstance(text_line, LTTextLine):
                        tailles_police = [char.size for char in text_line if isinstance(char, LTChar)]
                        if tailles_police:
                            taille_police_moyenne = sum(tailles_police) / len(tailles_police)
                            texte_element = ""
                            dernier_x1 = None
                            for character in text_line:
                                if isinstance(character, LTChar):
                                    if dernier_x1 is not None and character.x0 - dernier_x1 > 1:  # Seuil pour espaces
                                        texte_element += " "
                                    texte_element += character.get_text()
                                    dernier_x1 = character.x1
                            if texte_element:
                                titres_potentiels.append((taille_police_moyenne, texte_element))

        # Trier les titres potentiels par taille moyenne de police, décroissante
        titres_potentiels.sort(key=lambda x: x[0], reverse=True)
        # Parcourir les titres potentiels et sélectionner le premier qui répond aux critères
        for _, texte in titres_potentiels:
            texte_converti = html.unescape(texte)
            if len(texte_converti) >= 18:  # Condition sur la longueur du titre
                return texte_converti
        return "Titre non disponible"

def extraire_contenu_en_dict(element, contenu_dict, ns, chemin_section=''):
    for enfant in element:
        if enfant.tag.endswith('}head'):
            chemin_section = chemin_section + ' > ' + enfant.text.strip() if chemin_section else enfant.text.strip()
            contenu_dict[chemin_section] = ''
        elif enfant.tag.endswith('}p'):
            texte = ''.join(enfant.itertext()).strip()
            if chemin_section in contenu_dict:
                contenu_dict[chemin_section] += texte + "\n"
            elif "Texte hors section" not in contenu_dict:
                contenu_dict["Texte hors section"] = texte + "\n"
            else:
                contenu_dict["Texte hors section"] += texte + "\n"
        elif enfant.tag.endswith('}div'):
            extraire_contenu_en_dict(enfant, contenu_dict, ns, chemin_section)    

def extraire_et_sauvegarder_image(pdf_path, page_number, bbox_grobid, nom='', dpi=300):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number - 1)
    x, y, h, w = bbox_grobid
    bbox = [x, y, x + h, y+w]
    rect = fitz.Rect(bbox)
    # Calculer le zoom en fonction du DPI
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect)
    try:
        pix.save(nom)
    except RuntimeError as e:
        print(f"Erreur lors de la sauvegarde de l'image : {e}")
        image_path = None
    doc.close()            
            
def xml_to_text(xml_file):
    xml_data = open(xml_file).read()
    root = ET.fromstring(xml_data)

    #root = ET.fromstring(xml_data)

    # L'espace de noms TEI est spécifié via xsi:schemaLocation dans l'élément racine
    namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}  # Utiliser l'URL correcte de l'espace de noms

    # Extraire le texte des éléments <p> et <head> uniquement à l'intérieur de <teiHeader>
    textes = []

    # Recherche dans <teiHeader> sans préfixe d'espace de noms, puisque le document ne semble pas en utiliser
    for elem in root.findall('.//tei:teiHeader//tei:p', namespaces) + root.findall('.//tei:teiHeader//tei:head', namespaces):
        if elem.text:
            textes.append(elem.text.strip())

    # Concaténer les textes avec le séparateur '--'
    texte_final = '\n\n'.join(textes)

    #print(texte_final)

    # Initialisation de la liste pour stocker les textes
    textes = []

    # Fonction pour traiter récursivement chaque élément et ses enfants
    def traiter_element(elem, acc):
        if elem.tag.endswith('ref'):  # Vérifier si c'est un élément <ref>
            # Entourer le texte de l'élément <ref> de parenthèses
            if elem.text:
                acc.append(f"({elem.text.replace('(','').replace(')','')})")
        else:
            if elem.text:
                acc.append(elem.text.strip())

        # Traiter récursivement les sous-éléments
        for child in elem:
            traiter_element(child, acc)

            # Ajouter le texte suivant le sous-élément (tail) à la liste
            if child.tail:
                acc.append(child.tail.strip())

    # Parcourir <body> pour extraire les textes des balises spécifiées
    for body in root.findall('.//tei:body', namespaces):
        for elem in body.findall('.//tei:p', namespaces) + body.findall('.//tei:head', namespaces) + body.findall('.//tei:figDesc', namespaces):
            traiter_element(elem, textes)

    # Concaténer les textes avec '--' comme séparateur
    #texte_final = ''
    for texte in textes:
        if len(texte)>0:
            if texte[0] == '(':
                sep =' '
            elif texte[0] in ',.':
                sep = ''
            elif texte[0].isupper():
                sep = '\n\n'
            else:
                sep = ' '
            texte_final += sep+texte
    return normalise_texte(texte_final)         
            
species_list = open('config/especes.txt').read().split('\n')
species_list = [k for k in species_list if len(k) > 0]
# refuse = ["Journal", "Microsoft"]
# exec(open('liste_de_journaux.txt').read())