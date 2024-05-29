from grobid_client.grobid_client import GrobidClient
from shared.grobid_helper import doi_vers_bibtex_en_dict, chercher_doi, extraire_titre_metadonnees, normalise_texte, extraire_titre_pdfminer, extraire_et_sauvegarder_image, xml_to_text
# from grobid_client.grobid_client import GrobidClient
# from langchain_community.document_loaders.parsers import GrobidParser
import os
from lxml import etree
from Levenshtein import ratio
from abc import ABC

# docker run --rm --init --ulimit core=0 -p 8070:8070 grobid/grobid:0.8.0
# https://github.com/kermitt2/grobid_client_python

# pip install bibtexparser
# pip install grobid-client-python
# pip install PyPDF2
# pip install pdfminer.six
# pip install fitz
# pip install frontend
# pip install tools
# pip install python-Levenshtein

class GrobidService(ABC):
    def __init__(self):
        self.client = GrobidClient(config_path="./config.json")


    # process_documents(base_directory, out_put_directory)
    def process_documents(self, documents_directory: str = 'documents'):
        print(documents_directory)
        # client = GrobidClient(config_path="./config.json")
        # , output_directory: str = 'processed_documents'
        self.client.process("processFulltextDocument",
                        documents_directory, 
                        # output=output_directory,
                        tei_coordinates=True,
                        consolidate_header=True,
                        consolidate_citations=False,
                        include_raw_citations=False,
                        force=False)
        
        self.extract(documents_directory)
         
        
    def extract(self, base_directory):
        # On calcule les xml via grobid
        # base_directory = 'documents'
        # out_put_directory = 'processed_documents'
        refuse = ["Journal", "Microsoft"]
        
        # for pdf_dir in os.listdir(base_directory):
        for pdf_file in [k for k in sorted(os.listdir(base_directory)) 
                            if k.endswith('.pdf') #]:
                            and k.replace('pdf', 'bibtex') not in os.listdir(base_directory)
                            ]:
            xml_file = f'{base_directory}/'+pdf_file.replace('.pdf', '.grobid.tei.xml')
            with open(xml_file, 'r', encoding='utf-8') as file:
                tree = etree.parse(file)
            root = tree.getroot()
            # Espace de noms XML
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            doi_elem = root.find('.//tei:idno[@type="DOI"]', ns)
            doi = doi_elem.text if doi_elem is not None else ''
            if doi.endswith('.'):
                doi = doi[:-1]
            print(f"     doi : {doi}")
            #{'year': '2016', 'volume': '4', 'url': 'http://dx.doi.org/10.1128/microbiolspec.PoH-0018-2015', 'title': 'Paleogenetics and Past Infections: the Two Faces of the Coin of Human Immune Evolution', 'number': '3', 'month': '5', 'journal': 'Microbiology Spectrum', 'issn': '2165-0497', 'editor': 'Drancourt, Michel and Raoult, Didier', 'doi': '10.1128/microbiolspec.poh-0018-2015', 'author': '{Abi-Rached}, Laurent and {Raoult}, Didier', 'ENTRYTYPE': 'article', 'ID': 'AbiRached_2016'}
            titre_final = ''
            if doi != '':
                retour = doi_vers_bibtex_en_dict(doi, pdf_file)
                if retour == False:
                    continue
                elif retour is not None:
                    bibtex_dict, bibtex_str = retour
                    titre_final = bibtex_dict['title']
                    with open(f"{base_directory}/{pdf_file.replace('.pdf', '')}.bibtex", "w") as f:
                        f.write(bibtex_str)
            with open(f"{base_directory}/{pdf_file.replace('.pdf', '')}.title", "w") as f:
                if len(titre_final) > 0:
                    f.write(titre_final)        
                else:
                    titre = root.find('.//tei:titleStmt/tei:title[@type="main"]', ns)
                    if titre.text is not None: 
                        if titre.text is not None: 
                            doi = chercher_doi(titre.text)
                            if doi != '':
                                retour = doi_vers_bibtex_en_dict(doi, pdf_file)
                                if retour == False:
                                    continue
                                elif retour is not None:
                                    bibtex_dict, bibtex_str = retour
                                    titre_final = bibtex_dict['title']
                                    with open(f"{base_directory}/{pdf_file.replace('.pdf', '')}.bibtex", "w") as g:
                                        g.write(bibtex_str)
                                else:
                                    f.write(titre.text)
                                    titre_final = normalise_texte(titre.text)                         
                            else:         
                                f.write(titre.text)
                                titre_final = normalise_texte(titre.text)
                    else:
                        titre = extraire_titre_metadonnees(f'{base_directory}/{pdf_file}')
                        titre2 = extraire_titre_pdfminer(f'{base_directory}/{pdf_file}')
                        for quel_titre in (titre, titre2):
                            if (len(quel_titre) > 18
                                and all([k not in quel_titre for k in refuse])
                                and quel_titre != "Titre non disponible"
                                and not any([ratio(quel_titre, journal)>0.90 for journal in journals])):
                                titre_final = normalise_texte(quel_titre)
                                break
                        if len(titre_final) > 0:
                            doi = chercher_doi(titre_final)
                            if doi != '':
                                retour = doi_vers_bibtex_en_dict(doi, pdf_file)
                                if retour == False:
                                    continue
                                if retour is not None:
                                    bibtex_dict, bibtex_str = retour
                                    titre_final = bibtex_dict['title']
                                    with open(f"{base_directory}/{pdf_file.replace('.pdf', '')}.bibtex", "w") as g:
                                        g.write(bibtex_str)
                        f.write(titre_final)
            print(f"  => {titre_final}")
            
            # Extraction de l'abstract
            abstract = root.find('.//tei:profileDesc/tei:abstract', ns)
            abstract_text = '\n'.join(abstract.itertext()) if abstract is not None else "Abstract non trouvé"
            abstract_text = normalise_texte(abstract_text)
            #with open(f"{base_directory}/{pdf_file.replace('.pdf', '')}.abstract", "w") as f:
            #    f.write(abstract_text)
            '''
            # Extraire les informations des éléments <figure> de type "bitmap"
            figures_info = []
            for figure in root.findall('.//tei:figure', ns):
                graphic = figure.find('.//tei:graphic', ns)
                if graphic is not None and 'type' in graphic.attrib and graphic.attrib['type'] == "bitmap":
                    fig_id = figure.get('{http://www.w3.org/XML/1998/namespace}id', 'Inconnu')
                    graphic_coords = graphic.get('coords', 'Inconnu')
                    fig_desc = figure.find('.//tei:figDesc', ns)
                    fig_desc_text = normalise_texte(''.join(fig_desc.itertext()) if fig_desc is not None else 'Inconnu')
                    figures_info.append({'id': fig_id, 'coords': graphic_coords, 'description': fig_desc_text})

            for info in figures_info:
                items = info['coords'].split(',')
                page, bbox = int(items[0]), list(map(float, items[1:]))
                (dir_output / pdf_file.stem / 'fig').mkdir(exist_ok=True, parents=True)
                fig_file = dir_output / pdf_file.stem / 'fig' / f"{info['id']}.png"
                image_path = extraire_et_sauvegarder_image(pdf_file, page, bbox, nom=fig_file)
                fig_file = dir_output / pdf_file.stem / 'fig' / f"{info['id']}.legend"
                with open(fig_file, "w") as f:
                    f.write(info['description'])
                # Trouver tous les paragraphes contenant une référence à la figure cible
                paragraphes_contenant_figure = []
                for paragraphe in root.findall('.//tei:p', ns):
                    # Recherche des références dans chaque paragraphe
                    if paragraphe.find(f'.//tei:ref[@target="#'+info['id']+'"]', ns) is not None:
                        paragraphes_contenant_figure.append(normalise_texte(''.join(paragraphe.itertext())))
                fig_file = dir_output / pdf_file.stem / 'fig' / f"{info['id']}.desc"
                with open(fig_file, "w") as f:
                    f.write('\n\n'.join(paragraphes_contenant_figure))
            '''
            tableaux_info = []
            for tableau in root.findall('.//tei:figure[@type="table"]', ns):
                tableau_id = tableau.get('{http://www.w3.org/XML/1998/namespace}id', 'Inconnu')
                tableau_desc = tableau.find('.//tei:figDesc', ns)
                tableau_desc_text = normalise_texte(tableau_desc.text if tableau_desc is not None else 'Inconnu')
                tableau_coords = tableau.get('coords', 'Inconnu')
                lignes_tableau = []
                for row in tableau.findall('.//tei:row', ns):
                    cellules = row.findall('.//tei:cell', ns)
                    ligne_texte = [cell.text for cell in cellules if cell.text is not None]
                    lignes_tableau.append(';'.join(ligne_texte))
                tableau_info_texte = '\n'.join(lignes_tableau)
                tableaux_info.append({'id': tableau_id, 'description': tableau_desc_text, 
                                        'contenu': tableau_info_texte, 'coords': tableau_coords})

            for info in tableaux_info:
                items = info['coords'].split(',')
                if items[0] == "Inconnu":
                    continue
                page, bbox = int(items[0]), list(map(float, items[1:]))
                #(dir_output / pdf_file.stem / 'tab').mkdir(exist_ok=True, parents=True)
                fig_file = f"{base_directory}/{pdf_file.replace('.pdf', 'tab_' + info['id']+'.png')}"
                #fig_file = dir_output / pdf_file.stem / 'tab' / f"{info['id']}.png"
                # extraire_et_sauvegarder_image(f"{base_directory}/{pdf_file}", page, bbox, nom=fig_file)
                #fig_file = dir_output / pdf_file.stem / 'tab' / f"{info['id']}.txt"
                fig_file = f"{base_directory}/{pdf_file.replace('.pdf', 'tab_' + info['id']+'.txt')}"
                with open(fig_file, "w") as f:
                    if info['description']:
                        f.write(info['description']+'\n\n')
                    f.write(info['contenu'])
                # Trouver tous les paragraphes contenant une référence à la figure cible
                paragraphes_contenant_figure = []
                for paragraphe in root.findall('.//tei:p', ns):
                    # Recherche des références dans chaque paragraphe
                    if paragraphe.find(f'.//tei:ref[@target="#'+info['id']+'"]', ns) is not None:
                        paragraphes_contenant_figure.append(normalise_texte(''.join(paragraphe.itertext())))
                fig_file = f"{base_directory}/{pdf_file.replace('.pdf', 'tab_' + info['id']+'.desc')}"
                with open(fig_file, "w") as f:
                    f.write('\n\n'.join(paragraphes_contenant_figure))
            # On gère les tables
            if False:
                get_tables(f"{base_directory}/{pdf_file}")
            # Puis le contenu textuel
            contenu = xml_to_text(xml_file)
            '''        
            body = root.find('.//tei:body', ns)
            contenu_dict = {}
            contenu = ""
            if body is not None:        # Compter le nombre de <div> dans le <body>
            '''
            '''
                if len(body.findall('.//tei:div', ns)) > 1:
                    extraire_contenu_en_dict(body, contenu_dict, ns)    
                    #(dir_output / pdf_file.stem / 'txt').mkdir(exist_ok=True, parents=True)
                    for index, [section, texte] in enumerate(contenu_dict.items()):
                        contenu += f"{normalise_texte(section)}\n\n"
                        contenu += f"{normalise_texte(texte)}\n\n"
                        if texte != '':
                            with open(dir_output / pdf_file.stem / 'txt' / f'section_{index+1}.txt', 'w') as f:
                                f.write(f"Section: {normalise_texte(section)}\n\n{normalise_texte(texte)}")                    
                else:
            '''
            '''
                for div in body.findall('.//tei:div', ns):
                    for subdiv in div.itertext():
                        if len(subdiv) < 5:
                            jointure = ' '
                        else:
                            jointure = '\n\n'
                    contenu += normalise_texte(jointure + subdiv) #div.itertext()).strip())
            '''
            with open(f"{base_directory}/{pdf_file.replace('.pdf', '')}.txt", 'w') as f:
                f.write(normalise_texte(contenu))
                
                
                
        # client.process("processFulltextDocument",
        #                     'documents')
