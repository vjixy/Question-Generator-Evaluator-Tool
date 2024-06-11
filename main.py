import streamlit as st
from shared.shared_variables import all_models_list
from functools import partial
from shared.shared_ui import SharedUi
from src.database.sql_lite_service import SqlLiteService
from database_service import DatabaseService
import os
from dotenv import load_dotenv
from shared.services.model_handler_service import ModelHandlerService
import requests
import pandas as pd
from datetime import datetime
max_feed_back_number = 5
minimum_rating = 4
response_types = ["default","context","internet","internet+context"]

# Load the database from cache
@st.cache_resource
def load_services():
    load_dotenv()
    return SqlLiteService(), None, ModelHandlerService(), SharedUi(st)

sql_service, chroma_service, model_handler_service, shared_ui = load_services()


if "website_initialized" not in st.session_state:
    shared_ui.initialize_website()

user_name = st.sidebar.text_input("User", value=st.session_state.user_name, key = "user")

selected_document = ""
if  st.session_state.old_user != user_name:
    shared_ui.refresh_user_data(selected_document)

# load single document
uploaded_file = st.sidebar.file_uploader("Upload a document", type=None, accept_multiple_files=False, label_visibility="visible")

advanced = st.sidebar.checkbox("Advanced Options", False)
if advanced:
    st.session_state.selected_models = st.sidebar.multiselect("Ai models", all_models_list, default=st.session_state.selected_models)
    st.session_state.selected_modes = st.sidebar.multiselect("Prediction Modes", response_types, default=st.session_state.selected_modes)

if uploaded_file is not None:
    selected_document = uploaded_file.name
    
    if selected_document not in st.session_state.uploaded_files:
        st.session_state.document_valid = False
        upload_directory = os.environ["UPLOAD_DIRECTORY"]
        grobid_url = os.environ["GROBID_URL"]
        is_grobid_on_external_service = os.environ["GROBID_SERVER"].lower().strip() == "on"
        if not os.path.exists(upload_directory):
            os.makedirs(upload_directory)
            
        user_documents_path = os.path.join(upload_directory, user_name)
        if not os.path.exists(user_documents_path):
            os.makedirs(user_documents_path)
            
        document_path = os.path.join(user_documents_path, selected_document.split(".")[0])
        if not os.path.exists(document_path):
            os.makedirs(document_path)
        st.session_state.document_path = document_path
            
        file_path = os.path.join(document_path, selected_document)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        tmp_file_path=file_path.replace(".pdf",".txt")
        
        if is_grobid_on_external_service:

            api_url = f"{grobid_url}/filename/{document_path}"

            # Send a GET request to the API
            response = requests.get(api_url)
            # Check for successful response
            if not response.status_code == 200:
                
                print(f"Error: {response.status_code}")
                print(response.text)
        else:
            from shared.services.grobid_service import GrobidService
            grobid_service = GrobidService()
            grobid_service.process_documents(document_path)
        st.session_state.bibtext_found = True 
        if not os.path.exists(file_path.replace(".pdf",".bibtex")):
            st.session_state.bibtext_found = False
            # st.error("DOI Not Found Insert A Document With A Valid Reference")
        else:
            with open(tmp_file_path, 'r') as file:
                # Read the file line by line
                lines = []
                for line in file:
                    line = line.strip()
                    if line:
                        lines.append(line)

            st.session_state.uploaded_files[selected_document] = lines
            st.session_state.current_file = selected_document
            
            sql_service.add_document(uploaded_file.name, len(st.session_state.uploaded_files[selected_document]))
            st.session_state.document_valid = True
else:
    st.error("Please upload a document to start")
if not st.session_state.bibtext_found:
    st.error("DOI Not Found Insert A Document With A Valid Reference")
if user_name:
    sql_service.add_user(user_name)
    
for selected_model in st.session_state.selected_models:
    if selected_model not in st.session_state.keys():
        st.session_state[selected_model] = model_handler_service.load_pretrained_model(st, selected_model)
    


shared_ui.load_document_data(sql_service, chroma_service, selected_document, load_from_db=False)

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
    
    for selected_model in st.session_state.selected_models:
        with st.expander("Question generated by: " + str(selected_model)):
            model = st.session_state[selected_model]
            if current_index not in st.session_state.questions[current_file]:
                st.session_state.questions[current_file][current_index] = {}
                st.session_state.feedback[current_file][current_index] = {}
            if selected_model not in st.session_state.questions[current_file][current_index]:
                st.session_state.feedback[current_file][current_index][selected_model] = None
                with st.spinner(f'Waiting for {selected_model} question...'):
                    prompt = model_handler_service.prompt_adjustment("question", "", st.session_state.texts[st.session_state.current_index])
                    questions = model_handler_service.adjust_prompt_response(model_handler_service.predict(selected_model ,prompt, st.session_state[selected_model]), "question")
                    
                    st.session_state.questions[current_file][current_index][selected_model] = questions

                    sql_service.add_rating(user_name, st.session_state.current_file, st.session_state.current_index, None, st.session_state.questions[current_file][current_index][selected_model], selected_model)
            question = st.session_state.questions[current_file][current_index][selected_model]
            current_feedback = st.session_state.feedback[current_file][current_index][selected_model]
            col_1, col_2 = st.columns([0.35, 1])
            
            st.write(question)
            def vote(current_index, selected_model):
                st.session_state.feedback[current_file][current_index][selected_model] = st.session_state["rating_"+selected_model]
                sql_service.update_rating(user_name, st.session_state.current_file, st.session_state.current_index, st.session_state["rating_"+selected_model], st.session_state.questions[current_file][current_index][selected_model], selected_model)
            
            if current_feedback:
                current_feedback-=1
            
            rating = st.radio("rating", [1,2,3,4,5], key=f'rating_{selected_model}', horizontal= True, index=current_feedback, on_change=partial(vote, current_index, selected_model ))

            if rating and rating>=minimum_rating:
    
                if current_index in st.session_state.questions[current_file]:
                    model_name = selected_model

                    
                    if current_index not in st.session_state.response[current_file]:
                        st.session_state.response[current_file][current_index] = {}
                            
                    if model_name not in st.session_state.response[current_file][current_index]:
                        st.session_state.response[current_file][current_index][model_name] = {}
                        
                    for selected_model in st.session_state.selected_models:
                        
                        if selected_model not in st.session_state.response[current_file][current_index][model_name]:
                            st.session_state.response[current_file][current_index][model_name][selected_model] = {}
                            
                        for response_type in st.session_state.selected_modes:
                            st.divider() 
                            if response_type not in st.session_state.response[current_file][current_index][model_name][selected_model]:
                                
                                with st.spinner(f'Waiting for {selected_model} response...'):

                                    prompt = model_handler_service.prompt_adjustment(response_type, st.session_state.texts[st.session_state.current_index], question)
                                    response = model_handler_service.adjust_prompt_response(model_handler_service.predict(selected_model ,prompt, st.session_state[selected_model]),"answer")
                                    st.session_state.response[current_file][current_index][model_name][selected_model][response_type] = response
                                    
                                    sql_service.add_response(user_name, st.session_state.current_file, st.session_state.current_index, model_name,  response, selected_model, response_type, None)
                            
                            response = st.session_state.response[current_file][current_index][model_name][selected_model][response_type]
                            try:
                                current_rating = st.session_state.rating[current_file][current_index][model_name][selected_model][response_type]
                            except:
                                current_rating = None
                            st.caption(selected_model + ", generation type: " + str(response_type))
                            st.write(response)
                            
                            def update_response_vote(current_index, model_name, selected_model, response_type):
                                if current_file not in st.session_state.rating:
                                    st.session_state.rating[current_file] = {}
                                if current_index not in st.session_state.rating[current_file]:
                                    st.session_state.rating[current_file][current_index] = {}
                                if model_name not in st.session_state.rating[current_file][current_index]:
                                    st.session_state.rating[current_file][current_index][model_name] = {}
                                if selected_model not in st.session_state.rating[current_file][current_index][model_name]:
                                    st.session_state.rating[current_file][current_index][model_name][selected_model] = {}
                                st.session_state.rating[current_file][current_index][model_name][selected_model][response_type] = st.session_state[f'rating_{model_name}_{selected_model}_{response_type}']
                                sql_service.update_response(user_name, st.session_state.current_file, st.session_state.current_index, model_name, st.session_state.response[current_file][current_index][model_name][selected_model][response_type], selected_model, response_type, int(st.session_state[f'rating_{model_name}_{selected_model}_{response_type}']))
                            
                            if current_rating:
                                current_rating-=1
                            
                            st.radio("rating", [nb for nb in range(1, max_feed_back_number+1)], key=f'rating_{model_name}_{selected_model}_{response_type}', horizontal= True, index=current_rating, on_change=partial(update_response_vote, current_index, model_name, selected_model, response_type)) 
                            
def export_data():

    file_name_list = []
    contexts_list = []
    questions_list = []
    questions_rating_list = []
    model_used_to_generate_question_list = []
    answers_list = []
    answers_rating_list = []
    response_type_list = []
    model_used_to_generate_answer_list = []
    for index in st.session_state.questions[current_file]:
        for model_name in st.session_state.questions[current_file][index]:
            question_rating = st.session_state.feedback[current_file][index][model_name]
            question_rating = question_rating if question_rating else 0
            if int(question_rating) < minimum_rating:
                file_name_list.append(current_file)
                contexts_list.append(st.session_state.texts[int(index)])
                questions_list.append(st.session_state.questions[current_file][index][model_name])
                questions_rating_list.append(question_rating)
                model_used_to_generate_question_list.append(model_name)
                answers_list.append(None)
                answers_rating_list.append(None)
                response_type_list.append(None)
                model_used_to_generate_answer_list.append(None)
                continue
            for selected_model in st.session_state.response[current_file][index][model_name]:
                for response_type in st.session_state.response[current_file][index][model_name][selected_model]:
                    response_rating = st.session_state.rating[current_file][index][model_name][selected_model][response_type]
                    file_name_list.append(current_file)
                    contexts_list.append(st.session_state.texts[int(index)])
                    questions_list.append(st.session_state.questions[current_file][index][model_name])
                    questions_rating_list.append(question_rating)
                    model_used_to_generate_question_list.append(model_name)
                    answers_list.append(st.session_state.response[current_file][index][model_name][selected_model][response_type])
                    answers_rating_list.append(response_rating)
                    response_type_list.append(response_type)
                    model_used_to_generate_answer_list.append(selected_model)
    
    # Dataset
    qa_pairs = [{ "file_name": fn, "context": c, "question": q, "question_rating": qr, "model_used_to_generate_question": mq, "answer": a, "answer_rating": ar, "answer_type": at, "model_used_to_generate_answer": ma} for fn, c, q, qr, mq, a, ar, at, ma in zip(file_name_list, contexts_list, questions_list, questions_rating_list, model_used_to_generate_question_list, answers_list, answers_rating_list, response_type_list, model_used_to_generate_answer_list)]
    df = pd.DataFrame(qa_pairs)
    # Write to csv
    download_file_name = current_file.split(".")[0]+"_data.csv"
    download_file_path = os.path.join(st.session_state.document_path, download_file_name)
    download_file_name = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ") + "_" + download_file_name
    df.to_csv(download_file_path, index=False)
    with open(download_file_path) as f:
        st.sidebar.download_button('Download CSV', f, download_file_name)
 
st.sidebar.caption("Export Data")
export = st.sidebar.button("Export", on_click=export_data)
