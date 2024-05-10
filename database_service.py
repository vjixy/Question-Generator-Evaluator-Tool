
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.document_loaders.pdf import PyPDFDirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
import numpy as np
import os
from typing import List

class DatabaseService():
    def __init__(self, database_path: str = "vectorstores/db/", data_path: str = "data/", initialize_database: bool = False):
        self.database_path = database_path
        self.data_path = data_path
        if initialize_database:
            self.create_vector_db()
        self.emender = GPT4AllEmbeddings()
        self.vector_store = self.get_vector_store()
        
    def compute_similarity(self, text1: str, text2: str):
        vec1 = self.emender.embed_query(text1)
        vec2 = self.emender.embed_query(text2)
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return similarity
        
    def get_vector_store(self):
        # Ensure the directory exists
        if not os.path.exists( self.database_path):
            raise FileNotFoundError("Vector store directory not found.")
        
        # Initialize the Chroma vector store with the specified directory
        vectorstore = Chroma(persist_directory= self.database_path, embedding_function=self.emender)
        return vectorstore
    
    def get_relevant_documents(self, text: str, calculate_similarity: bool = False):

        docs = self.vector_store.similarity_search(text)
        
        if calculate_similarity:
            for doc in docs:
                self.compute_similarity(text, doc.page_content)
        return docs
    # {'page': 62, 'source': 'data\\Chap1 - Introduction.pdf'}
    
    def available_documents(self):
        return set([u['source'] for u in self.vector_store.get()['metadatas']])
    
    def get_sections_from_document(self, document_name:str) -> List[str]:
        return [self.vector_store.get()['documents'][index] for index, metadata in enumerate(self.vector_store.get()['metadatas']) if document_name in metadata['source']]
    
    def get_documents(self):
        # articles = set([u['file_path'] for u in self.vector_store.get()['metadatas']])
        # print(f"Nombre de pdf dans la bibliothèque : {len(articles)}")
        list_of_documents = []
        data = self.vector_store.get()
        for index, metadata in enumerate(data['metadatas']):
            if metadata['source'] == 'data\\Chap1 - Introduction.pdf':
                list_of_documents.append(data['documents'][index])
                
        return list_of_documents
        return self.vector_store.get()["documents"]
        return set([u['source'] for u in self.vector_store.get()['metadatas']])
    
    def create_vector_db(self):
        loader = PyPDFDirectoryLoader(self.data_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        texts=text_splitter.split_documents(documents)
        vectorstore = Chroma.from_documents(documents=texts, embedding=GPT4AllEmbeddings(),persist_directory=self.database_path)      
        vectorstore.persist()