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
import tempfile
import requests
import shutil
import pandas as pd

max_feed_back_number = 5
minimum_rating = 4
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

selected_document = ""

# load from vector store
# selected_document = st.sidebar.selectbox("Document", [os.path.basename(path) for path in chroma_service.available_documents()])

# load single document
uploaded_file = st.sidebar.file_uploader("Upload a document", type=None, accept_multiple_files=False, label_visibility="visible")

if  st.session_state.old_user != user_name:
    shared_ui.refresh_user_data(selected_document)
    
if uploaded_file is not None:
    selected_document = uploaded_file.name
    
    if selected_document not in st.session_state.uploaded_files:
        
        bytes_data = uploaded_file.getvalue()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            # Write the bytes data to the temporary file
            tmp_file.write(bytes_data)
            # Get the path of the temporary file
            tmp_file_path = tmp_file.name
        shutil.move(tmp_file_path, "temp2/"+selected_document)
        tmp_file_path = "temp2/"+selected_document
        # Replace with the actual server URL where your FastAPI app is running
        server_url = "http://localhost:8000"

        # Define the file path you want to get information for

        # Construct the complete API endpoint URL with the file path
        api_url = f"{server_url}/filename/{tmp_file_path}"

        # Send a GET request to the API
        response = requests.get(api_url)
        tmp_file_path=tmp_file_path.replace(".pdf",".txt")
        # Check for successful response
        if response.status_code == 200:
            # Convert the JSON response to a dictionary
            data = response.json()
            
            # Extract filename and directory (assuming the response structure from your app)
            directory = data.get("filename")
            
        else:
            # Handle error if the request fails
            print(f"Error: {response.status_code}")
            print(response.text)
        # Initialize PyPDFLoader with the path to the temporary file
        # loader = PyPDFLoader(tmp_file_path)
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

if user_name:
    sql_service.add_user(user_name)
    
for selected_model in selected_models:
    if selected_model not in st.session_state.keys():
        print("model loaded:", selected_model)
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
    
    for selected_model in selected_models:
        with st.expander("Question generated by: " + str(selected_model)):
            model = st.session_state[selected_model]
            if current_index not in st.session_state.questions[current_file]:
                st.session_state.questions[current_file][current_index] = {}
                st.session_state.feedback[current_file][current_index] = {}
            if selected_model not in st.session_state.questions[current_file][current_index]:
                st.session_state.feedback[current_file][current_index][selected_model] = None
                with st.spinner(f'Waiting for {selected_model} question...'):
                    prompt = st.session_state.texts[st.session_state.current_index] + " \n generate a useful question about the document above"
                    questions = model_handler_service.predict(selected_model ,prompt, st.session_state[selected_model])
                    
                    try:
                        st.session_state.questions[current_file][current_index][selected_model] = questions.split("?")[0] + "?"
                    except:
                        st.session_state.questions[current_file][current_index][selected_model] = questions
                    sql_service.add_rating(user_name, st.session_state.current_file, st.session_state.current_index, None, st.session_state.questions[current_file][current_index][selected_model], selected_model)
            question = st.session_state.questions[current_file][current_index][selected_model]
            current_feedback = st.session_state.feedback[current_file][current_index][selected_model]
            col_1, col_2 = st.columns([0.35, 1])
            
            def display_warning():
                st.toast()
                st.error("Do you really, really, wanna do this?")
                if st.button("Yes I'm ready to rumble"):
                    # run_expensive_function()
                    print("lol")
                    
            def show_confirmation():
                # st.popover("Hello there", help=None, disabled=False, use_container_width=False)
                ...
                # st.write("Are you sure?")
                # col1, col2 = st.columns(2)
                # with col1:
                #     if st.button("Yes"):
                #         st.success("Action confirmed!")
                # with col2:
                #     if st.button("Cancel"):
                #         st.warning("Action canceled!")

            # Place the button in the first column and the text in the second column
            with col_1:
                st.write("Generate new question")
            with col_2:
                if st.button("⟳", key=f'refresh_{selected_model}'):
                    show_confirmation()
                    
            
            # st.caption("Generate new question")
            # st.button("⟳", on_click=partial(next_text), key=f'refresh_{selected_model}')
            st.write(question)
            def vote(current_index, selected_model):
                st.session_state.feedback[current_file][current_index][selected_model] = st.session_state["rating_"+selected_model]
                sql_service.update_rating(user_name, st.session_state.current_file, st.session_state.current_index, st.session_state["rating_"+selected_model], st.session_state.questions[current_file][current_index][selected_model], selected_model)
            
            if current_feedback:
                current_feedback-=1
            
            rating = st.radio("rating", [1,2,3,4,5], key=f'rating_{selected_model}', horizontal= True, index=current_feedback, on_change=partial(vote, current_index, selected_model ))

            # print(rating, flush=True)
            if rating and rating>=minimum_rating:
                # st.session_state["rating_"+selected_model] = rating
    
                if current_index in st.session_state.questions[current_file]:
                    model_name = selected_model
                    # for model_name in st.session_state.questions[current_file][current_index]:
                        
                    # question = st.session_state.questions[current_file][current_index][model_name]
                    # current_feedback = st.session_state.feedback[current_file][current_index][model_name]
                    # st.caption("Generated question by: " +model_name + ", rated: " + str(current_feedback))
                    # st.write(question)
                    
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
                            st.divider() 
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
    
    data = {
        "questions":[],
        "responses":[],
    }
    questions = []
    responses = []
    contexts = []
    models = []
    for index in st.session_state.questions[current_file]:
        for model_name in st.session_state.questions[current_file][index]:
            # for selected_model in st.session_state.questions[current_file][index][selected_models]:
                # for response_type in response_types:
            question_rating = st.session_state.feedback[current_file][index][model_name]
            if question_rating and int(question_rating) >= minimum_rating:
                for selected_model in st.session_state.response[current_file][index][model_name]:
                    for response_type in st.session_state.response[current_file][index][model_name][selected_model]:
                        response_rating = st.session_state.feedback[current_file][index][model_name]
                        if response_rating and int(response_rating) >= minimum_rating:
                            contexts.append(st.session_state.texts[int(index)])
                            models.append(selected_model)
                            questions.append(st.session_state.questions[current_file][index][model_name])
                            responses.append(st.session_state.response[current_file][index][model_name][selected_model][response_type])
    
    # Dataset
    # qa_pairs = [{"question": q, "answer": a, "context": c, "model": m} for q, a, c, m in zip(questions, responses, contexts, models)]
    qa_pairs = [{"question": q, "answer": a} for q, a, in zip(questions, responses)]
    df = pd.DataFrame(qa_pairs)
    # Write to csv
    csv_path = "data.csv"
    df.to_csv(csv_path, index=False)
    with open(csv_path) as f:
        st.sidebar.download_button('Download CSV', f, csv_path)
                    
    # st.session_state.questions[current_file][current_index][selected_model]
    # st.session_state.feedback[current_file][current_index][selected_model]
    # st.session_state.rating[current_file][current_index][model_name][selected_model][response_type]
    # st.session_state.response[current_file][current_index][model_name][selected_model][response_type]
    
st.sidebar.caption("Export Data")
export = st.sidebar.button("Export", on_click=export_data)

# st.sidebar.download_button()