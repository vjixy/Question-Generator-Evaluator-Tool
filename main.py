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
import ollama

# add a new user id
if "user" not in st.session_state:
    current_datetime = datetime.now()
    st.session_state.user = "User_" + current_datetime.strftime('%y%m%d%H%M%S')

# Load the database from cache
@st.cache_resource
def load_database():
    return SqlLiteService()

database_service = load_database()


user_name = st.sidebar.text_input("User", value=st.session_state.user)

if user_name:
    database_service.add_user(user_name)


selected_models = st.sidebar.multiselect("Ai models", chat_gpt_models_list + ollama_models_list)

uploaded_file = st.sidebar.file_uploader("Upload a document", type=None, accept_multiple_files=False, label_visibility="visible")


# @st.cache_resource
# def load_json_data(file_path):
#     with open(file_path, 'r') as f:
#         data = json.load(f)
#     return data


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

if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
    

    
    
if 'current_file' not in st.session_state:
    st.session_state.current_file = None
        
if uploaded_file is not None:
    file_name = uploaded_file.name
    
    if file_name not in st.session_state.uploaded_files:
        
        bytes_data = uploaded_file.getvalue()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            # Write the bytes data to the temporary file
            tmp_file.write(bytes_data)
            # Get the path of the temporary file
            tmp_file_path = tmp_file.name

        # Initialize PyPDFLoader with the path to the temporary file
        loader = PyPDFLoader(tmp_file_path)
        
        st.session_state.uploaded_files[file_name] = loader.load()
        st.session_state.current_file = file_name
        database_service.add_document(uploaded_file.name, len(st.session_state.uploaded_files[file_name]))
        # database_service.get_ratings(user_name, file_name)


# Sample array of texts
if st.session_state.current_file:
    texts = st.session_state.uploaded_files[st.session_state.current_file]
    
    if 'current_file_initialized' not in st.session_state:
        st.session_state.current_file_initialized = True
        st.session_state.feedback = {}
        st.session_state.questions = {}
        ratings = database_service.get_ratings(user_name, st.session_state.current_file)

        for rating in ratings:
            index = str(rating[0])
            if index not in st.session_state.feedback:
                st.session_state.feedback[index] = {}
                st.session_state.questions[index] = {}
            st.session_state.feedback[str(rating[0])][rating[3]] = rating[1]
            st.session_state.questions[str(rating[0])][rating[3]] = rating[2]
        
        
else:
    texts = []

# Initialize the session state for the current index and feedback if they don't exist
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

# Initialize a feedback list with None values to store user feedback for each text
if 'feedback' not in st.session_state:
    st.session_state.feedback = {}
    st.session_state.questions = {}
    


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
    text_area = st.text_area(f'Document Section: {str(st.session_state.current_index + 1)} / {len(texts)}' , texts[st.session_state.current_index].page_content, height=300)
else:
    text_area = st.text_area("Load a document first" , "", height=300)

# Display current feedback for this text if it exists
if texts:
    current_index = str(st.session_state.current_index)
    # current_feedback = st.session_state.feedback[st.session_state.current_index]

    feeds = ["👍", "👎"]

    # Create Next, Thumbs Up, Thumbs Down, and Back buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.5, 1.5, 1.5, 1.5, 1.5, 1])
    with col1:
        st.button("Back", on_click=previous_text)
    
    with col7:
        st.button("Next", on_click=next_text)
        
    
            
    for selected_model in selected_models:
        model = st.session_state[selected_model]
        if current_index not in st.session_state.questions:
            st.session_state.questions[current_index] = {}
            st.session_state.feedback[current_index] = {}
                        
        if selected_model not in st.session_state.questions[current_index]:
            st.session_state.feedback[current_index][selected_model] = None
            with st.spinner(f'Waiting for {selected_model} response...'):
                if selected_model in chat_gpt_models_list:
                    questions = model.generate([texts[st.session_state.current_index].page_content + " \n generate a useful question about the document above"]).strip()
                else:
                    questions = model.generate([texts[st.session_state.current_index].page_content + " \n generate a useful question about the document above"]).generations[0][0].text
                try:
                    st.session_state.questions[current_index][selected_model] = questions.split("?")[0] + "?"
                except:
                    st.session_state.questions[current_index][selected_model] = questions
                database_service.add_rating(user_name, st.session_state.current_file, st.session_state.current_index, None, st.session_state.questions[current_index][selected_model], selected_model)
                
        question = st.session_state.questions[current_index][selected_model]
        current_feedback = st.session_state.feedback[current_index][selected_model]
        st.caption(selected_model)
        st.write(question)
        
        def vote(current_index, selected_model, reaction):
            st.session_state.feedback[current_index][selected_model] = reaction
            database_service.update_rating(user_name, st.session_state.current_file, st.session_state.current_index, reaction, st.session_state.questions[current_index][selected_model], selected_model)
        
        # print(current_feedback)
        partial_vote_good = partial(vote, current_index, selected_model, "👍")
        partial_vote_bad = partial(vote, current_index, selected_model, "👎")
        
        if current_feedback is not None:
            if current_feedback == "👍":
                st.success(f"Your feedback: {current_feedback}")
            else:
                st.error(f"Your feedback: {current_feedback}")
        
                
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.5, 1.5, 1.5, 1.5, 1.5, 1])
        with col1:
            st.button("👍", on_click=partial_vote_good, key=f'thumbs_up_{selected_model}')
        with col2:
            st.button("👎", on_click=partial_vote_bad, key=f'thumbs_down{selected_model}')




