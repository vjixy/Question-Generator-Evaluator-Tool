import streamlit as st
from shared.shared_variables import all_models_list
from functools import partial
from shared.shared_ui import SharedUi
from src.database.sql_lite_service import SqlLiteService
from database_service import DatabaseService
import os
from langchain_community.utilities import SerpAPIWrapper
from dotenv import load_dotenv
from shared.services.model_handler_service import ModelHandlerService

max_feed_back_number = 5

# Load the database from cache
@st.cache_resource
def load_services():
    load_dotenv()
    return SqlLiteService(), DatabaseService(), ModelHandlerService(), SharedUi(st)

sql_service, chroma_service, model_handler_service, shared_ui = load_services()


if "website_initialized" not in st.session_state:
    shared_ui.initialize_website()

user_name = st.sidebar.text_input("User", value=st.session_state.user_name, key = "user")
    
selected_models = st.sidebar.multiselect("Ai models", all_models_list)

selected_document = st.sidebar.selectbox("Document", [os.path.basename(path) for path in chroma_service.available_documents()])

if user_name:
    sql_service.add_user(user_name)
    
for selected_model in selected_models:
    if selected_model not in st.session_state.keys():
        st.session_state[selected_model] = model_handler_service.load_pretrained_model(st, selected_model)
    
if  st.session_state.old_user != user_name:
    shared_ui.refresh_user_data(selected_document)

shared_ui.load_document_data(sql_service, chroma_service, selected_document)

st.session_state.old_user = user_name
    
# Function to increment the index
def next_text():
    if st.session_state.current_index < len(st.session_state.texts) - 1:
        st.session_state.current_index += 1

# Function to decrement the index
def previous_text():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1

# Display the current text
if st.session_state.texts:
    text_area = st.text_area(f'Document Section: {str(st.session_state.current_index + 1)} / {len(st.session_state.texts)}' , st.session_state.texts[st.session_state.current_index], height=300)
else:
    text_area = st.text_area("Load a document first" , "", height=300)

# Display current feedback for this text if it exists
if st.session_state.texts:
    current_index = str(st.session_state.current_index)
    current_file = st.session_state.current_file
    # Create Next, Thumbs Up, Thumbs Down, and Back buttons
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.5, 1.5, 1.5, 1.5, 1.5, 1])
    with col1:
        st.button("Back", on_click=previous_text)
    
    with col7:
        st.button("Next", on_click=next_text)
    
    if current_index in st.session_state.questions[current_file]:
        for model_name in st.session_state.questions[current_file][current_index]:
            
            question = st.session_state.questions[current_file][current_index][model_name]
            current_feedback = st.session_state.feedback[current_file][current_index][model_name]
            st.caption("Generated question by: " +model_name + ", rated: " + str(current_feedback))
            st.write(question)
            
            if current_index not in st.session_state.response[current_file]:
                st.session_state.response[current_file][current_index] = {}
                    
            if model_name not in st.session_state.response[current_file][current_index]:
                st.session_state.response[current_file][current_index][model_name] = {}
                
            # response_types = ["default","context"]
            response_types = ["default","context","internet", "internet+context"]
            
            for selected_model in selected_models:
                # model = st.session_state[selected_model]
                
                if selected_model not in st.session_state.response[current_file][current_index][model_name]:
                    st.session_state.response[current_file][current_index][model_name][selected_model] = {}
                    
                for response_type in response_types:
                            
                    if response_type not in st.session_state.response[current_file][current_index][model_name][selected_model]:
                        
                        with st.spinner(f'Waiting for {selected_model} response...'):

                            prompt = model_handler_service.prompt_adjustment(response_type, st.session_state.texts[st.session_state.current_index], question)
                            response = model_handler_service.predict(selected_model ,prompt, st.session_state[selected_model])
                            st.session_state.response[current_file][current_index][model_name][selected_model][response_type] = response
                            
                            sql_service.add_response(user_name, st.session_state.current_file, st.session_state.current_index, model_name,  response, selected_model, response_type, None)
                    
                    response = st.session_state.response[current_file][current_index][model_name][selected_model][response_type]
                    try:
                        current_rating = st.session_state.rating[current_file][current_index][model_name][selected_model][response_type]
                    except:
                        current_rating = None
                    st.caption(selected_model + ", generation type: " + str(response_type))
                    st.write(response)
                    
                    def vote(current_index, model_name, selected_model, response_type):
                        sql_service.update_response(user_name, st.session_state.current_file, st.session_state.current_index, model_name, st.session_state.response[current_file][current_index][model_name][selected_model][response_type], selected_model, response_type, int(st.session_state[f'rating_{model_name}_{selected_model}_{response_type}']))
                    
                    if current_rating:
                        current_rating-=1
                    
                    rating = st.radio("rating", [nb for nb in range(1, max_feed_back_number+1)], key=f'rating_{model_name}_{selected_model}_{response_type}', horizontal= True, index=current_rating, on_change=partial(vote, current_index, model_name, selected_model, response_type))    