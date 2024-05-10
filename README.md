# Question-Generator-Evaluator-Tool

This repository is designed to process segments of documents, leveraging large language models (LLMs) to autonomously generate questions based on the content. It also provides a feature that allows users to evaluate and rate the quality of the generated questions, ensuring a continuous improvement in the relevance and accuracy of the interactions

<img src="documentation/images/main_screen.png">

## Dependencies
 - Ollama: https://ollama.com/download
 - pip install -r requirements.txt


## Add Keys to environmental variable
Add environmental variables in the .env file

## Run The Solution
To run the solution execute the following command in a terminal
`streamlit run main.py`

## Files to consider checking

`shared/shared_variables.py` for ai models to use \ 
`shared/services/model_handler_service.py` how ai models are handled \ 
`database_service.py` how vector database is managed