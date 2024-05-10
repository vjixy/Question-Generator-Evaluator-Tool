# Question-Generator-Evaluator-Tool

This repository is designed to process segments of documents, leveraging large language models (LLMs) to autonomously generate questions based on the content. It also provides a feature that allows users to evaluate and rate the quality of the generated questions, ensuring a continuous improvement in the relevance and accuracy of the interactions

<img src="documentation/images/main_screen.png">

## Dependencies
 - Ollama: https://ollama.com/download
 - pip install -r requirements.txt


## Add Keys to environmental variable
Add environmental variables in the .env file

## Run The Solution
To run the solution execute the following command in a terminal:  
`streamlit run main_question_generator.py` tool used to generate questions from a given section of a vector database. users can evaluate the generated questions from 1 to 5.  
`streamlit run main_response_generator.py` tool used to generate responses for the generated questions. users can evaluate the generated questions from 1 to 5.   
`streamlit run main_evaluate_questions_pdf_radio.py` tool used to generate questions from a given section of a given pdf file. users can evaluate the generated questions from 1 to 5.  
`streamlit run main_evaluate_questions_pdf.py` tool used to generate questions from a given section of a given pdf file. users can evaluate the generated questions using thumbs up or down.

## Files to consider checking

`shared/shared_variables.py` for ai models to use  
`shared/services/model_handler_service.py` how ai models are handled  
`database_service.py` how vector database is managed