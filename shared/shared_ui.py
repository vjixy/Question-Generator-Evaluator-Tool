import streamlit
from datetime import datetime
from abc import ABC

class SharedUi(ABC):
    def __init__(self, st: streamlit):
        self.st = st

    def refresh_document_data(self, document_name: str = None):
        self.st.session_state.current_file = document_name

        if document_name and document_name not in self.st.session_state.questions:
            self.st.session_state.current_index = 0
            self.st.session_state.questions[document_name] = {}
            self.st.session_state.feedback[document_name] = {}
            self.st.session_state.response[document_name] = {}
            self.st.session_state.rating[document_name] = {}
        
    def load_responses(self, sql_service):
        responses = sql_service.get_responses(self.st.session_state.user, self.st.session_state.current_file)
        for response in responses:
            if response[3] not in self.st.session_state.response[response[1]][str(response[2])]:
                self.st.session_state.response[response[1]][str(response[2])][response[3]] = {}
                self.st.session_state.rating[response[1]][str(response[2])][response[3]] = {}
            if response[4] not in self.st.session_state.response[response[1]][str(response[2])][response[3]]:
                self.st.session_state.response[response[1]][str(response[2])][response[3]][response[4]] = {}
                self.st.session_state.rating[response[1]][str(response[2])][response[3]][response[4]] = {}

            self.st.session_state.response[response[1]][str(response[2])][response[3]][response[4]][response[7]] = response[6]
            self.st.session_state.rating[response[1]][str(response[2])][response[3]][response[4]][response[7]] = response[5]
            
    def load_ratings(self, sql_service, document_name: str = None):
        ratings = sql_service.get_ratings(self.st.session_state.user, self.st.session_state.current_file)
            
        for rating in ratings:
            index = str(rating[0])
            if index not in self.st.session_state.feedback[document_name]:
                self.st.session_state.feedback[document_name][index] = {}
                self.st.session_state.questions[document_name][index] = {}
                self.st.session_state.response[document_name][index] = {}
                self.st.session_state.rating[document_name][index] = {}
            self.st.session_state.feedback[document_name][str(rating[0])][rating[3]] = rating[1]
            self.st.session_state.questions[document_name][str(rating[0])][rating[3]] = rating[2]

    def load_document_data(self, sql_service, chroma_service, document_name: str = None, load_from_db: bool = False):
        if self.st.session_state.document_valid and  document_name and (document_name != self.st.session_state.old_file or self.st.session_state.old_user != self.st.session_state.user):
            self.refresh_document_data(document_name)
            if load_from_db:
                self.st.session_state.uploaded_files[document_name] = chroma_service.get_sections_from_document(document_name)
                sql_service.add_document(document_name, len(self.st.session_state.uploaded_files[document_name]))
            self.st.session_state.texts = self.st.session_state.uploaded_files[document_name]
            self.load_ratings(sql_service, document_name)
            self.load_responses(sql_service)
            self.st.session_state.old_file = self.st.session_state.current_file
              

    def refresh_user_data(self, current_file: str = None):
        self.st.session_state.document_valid = False
        self.st.session_state.feedback = {}
        self.st.session_state.rating = {}
        self.st.session_state.questions = {}
        self.st.session_state.response = {}
        self.st.session_state.uploaded_files = {}
        self.refresh_document_data(current_file)
        
    def initialize_website(self):
        self.st.session_state.texts = []
        self.st.session_state.old_user = ""
        self.st.session_state.old_file = ""
        self.st.session_state.current_index = 0
        self.refresh_document_data()
        # add a new user id
        current_datetime = datetime.now()
        self.st.session_state.user_name = "User_" + current_datetime.strftime('%y%m%d%H%M%S')
        self.st.session_state.website_initialized = True