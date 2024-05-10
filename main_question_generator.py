import streamlit as st
from shared.shared_variables import ollama_models_list, chat_gpt_models_list
from langchain_community.document_loaders import PyPDFLoader
import tempfile
from langchain.llms.ollama import Ollama
from langchain.llms import OpenAI
import json
from functools import partial
from datetime import datetime
from src.database.sql_lite_service import SqlLiteService
from database_service import DatabaseService
import ollama
import os

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.old_user = ""
    st.session_state.old_file = ""
    st.session_state.uploaded_files = {}    
    st.session_state.current_file = None
    st.session_state.current_index = 0
    st.session_state.feedback = {}
    st.session_state.questions = {}
    st.session_state.responses = {}
    st.session_state.ratings = {}
    
    # add a new user id
    current_datetime = datetime.now()
    st.session_state.user_name = "User_" + current_datetime.strftime('%y%m%d%H%M%S')


# Load the database from cache
@st.cache_resource
def load_database():
    return SqlLiteService(), DatabaseService()

sql_service, chroma_service = load_database()


user_name = st.sidebar.text_input("User", value=st.session_state.user_name, key = "user")
if user_name:
    sql_service.add_user(user_name)
    
selected_models = st.sidebar.multiselect("Ai models", chat_gpt_models_list + ollama_models_list)

selected_document = st.sidebar.selectbox("Document", [os.path.basename(path) for path in chroma_service.available_documents()])

def loadPretrainedModel(model_name):
    if model_name in chat_gpt_models_list:
        return OpenAI(model = model_name)
    try:
        return Ollama(model = model_name)
    except:
        with st.spinner(f'Waiting for {selected_model} response...'):
            ollama.pull(model = selected_model)
            return Ollama(model = model_name)

for selected_model in selected_models:
    if selected_model not in st.session_state.keys():
        st.session_state[selected_model] = loadPretrainedModel(selected_model)


def new_document():
    st.session_state.current_index = 0

# for selected_document in selected_documents:
if selected_document is not None:
    if selected_document != st.session_state.current_file:
        st.session_state.current_index = 0
    file_name = selected_document
    st.session_state.current_file = file_name
    
    if file_name not in st.session_state.uploaded_files:
        
        st.session_state.uploaded_files[file_name] = chroma_service.get_sections_from_document(file_name)
        sql_service.add_document(file_name, len(st.session_state.uploaded_files[file_name]))
        # sql_service.get_ratings(user_name, file_name)

# load questions, responses, and rating
if st.session_state.current_file:
    texts = st.session_state.uploaded_files[st.session_state.current_file]
    
    if  st.session_state.old_user != user_name:
        st.session_state.current_file_initialized = True
        st.session_state.feedback = {}
        st.session_state.questions = {}
        current_file= st.session_state.current_file
        if current_file not in st.session_state.questions:
            st.session_state.questions[current_file] = {}
            st.session_state.feedback[current_file] = {}
        ratings = sql_service.get_ratings(user_name, st.session_state.current_file)

        for rating in ratings:
            index = str(rating[0])
            if index not in st.session_state.feedback[current_file]:
                st.session_state.feedback[current_file][index] = {}
                st.session_state.questions[current_file][index] = {}
            st.session_state.feedback[current_file][str(rating[0])][rating[3]] = rating[1]
            st.session_state.questions[current_file][str(rating[0])][rating[3]] = rating[2]
            
            
    if st.session_state.current_file not in st.session_state.questions:
        current_file= st.session_state.current_file
        st.session_state.questions[current_file] = {}
        st.session_state.feedback[current_file] = {}
        ratings = sql_service.get_ratings(user_name, st.session_state.current_file)

        for rating in ratings:
            index = str(rating[0])
            if index not in st.session_state.feedback[current_file]:
                st.session_state.feedback[current_file][index] = {}
                st.session_state.questions[current_file][index] = {}
            st.session_state.feedback[current_file][str(rating[0])][rating[3]] = rating[1]
            st.session_state.questions[current_file][str(rating[0])][rating[3]] = rating[2]
        
        
else:
    texts = []

st.session_state.old_user = user_name
st.session_state.old_file = st.session_state.current_file

# Function to increment the index
def next_text():
    if st.session_state.current_index < len(texts) - 1:
        st.session_state.current_index += 1

# Function to decrement the index
def previous_text():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1

# Display the current text
# st.write(texts[st.session_state.current_index])
if texts:
    text_area = st.text_area(f'Document Section: {str(st.session_state.current_index + 1)} / {len(texts)}' , texts[st.session_state.current_index], height=300)
else:
    text_area = st.text_area("Load a document first" , "", height=300)

# Display current feedback for this text if it exists
if texts:
    current_index = str(st.session_state.current_index)
    current_file = st.session_state.current_file
    # Create Next, Thumbs Up, Thumbs Down, and Back buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.5, 1.5, 1.5, 1.5, 1.5, 1])
    with col1:
        st.button("Back", on_click=previous_text)
    
    with col7:
        st.button("Next", on_click=next_text)
                
    for selected_model in selected_models:
        model = st.session_state[selected_model]
        if current_index not in st.session_state.questions[current_file]:
            st.session_state.questions[current_file][current_index] = {}
            st.session_state.feedback[current_file][current_index] = {}
                     
        if selected_model not in st.session_state.questions[current_file][current_index]:
            st.session_state.feedback[current_file][current_index][selected_model] = None
            with st.spinner(f'Waiting for {selected_model} response...'):
                
                questions = model.generate([texts[st.session_state.current_index] + " \n generate a useful question about the document above"]).generations[0][0].text
                
                try:
                    st.session_state.questions[current_file][current_index][selected_model] = questions.split("?")[0] + "?"
                except:
                    st.session_state.questions[current_file][current_index][selected_model] = questions
                sql_service.add_rating(user_name, st.session_state.current_file, st.session_state.current_index, None, st.session_state.questions[current_file][current_index][selected_model], selected_model)
                
        question = st.session_state.questions[current_file][current_index][selected_model]
        current_feedback = st.session_state.feedback[current_file][current_index][selected_model]
        st.caption(selected_model)
        st.write(question)
        
        def vote(current_index, selected_model):
            st.session_state.feedback[current_file][current_index][selected_model] = st.session_state["rating_"+selected_model]
            sql_service.update_rating(user_name, st.session_state.current_file, st.session_state.current_index, st.session_state["rating_"+selected_model], st.session_state.questions[current_file][current_index][selected_model], selected_model)
        
        if current_feedback:
            current_feedback-=1
        
        rating = st.radio("rating", [1,2,3,4,5], key=f'rating_{selected_model}', horizontal= True, index=current_feedback, on_change=partial(vote, current_index, selected_model ))
