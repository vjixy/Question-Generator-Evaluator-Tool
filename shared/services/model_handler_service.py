from abc import ABC
from langchain.llms.ollama import Ollama
from openai import OpenAI as openAI_v2
from langchain_community.llms.openai import OpenAI as openAI_v1
import ollama
from groq import Groq
from shared.shared_variables import chat_gpt_models_list, ollama_models_list, grok_models_list, chat_gpt_models_list_v2
from langchain_community.utilities import SerpAPIWrapper
import streamlit
from shared.templates.prompts import GENERATE_ANSWER_TEMPLATE, GENERATE_ANSWER_FROM_CONTEXT_TEMPLATE, GENERATE_ANSWER_FROM_INTERNET_CONTENT_TEMPLATE, GENERATE_QUESTION_TEMPLATE, GENERATE_ANSWER_FROM_CONTEXT_AND_INTERNET_CONTENT_TEMPLATE
import json
class ModelHandlerService(ABC):
    def __init__(self):
        self.grok_client = Groq()
        self.serp_api_wrapper = SerpAPIWrapper()
        self.openai_client = openAI_v2()
    
    def _load_open_ai_model(self, model_name: str):
        return openAI_v1(model = model_name)
    
    def _load_ollama_model(self, model_name: str):
        return Ollama(model = model_name)
        
    def _download_ollama_model(self, model_name: str):
        ollama.pull(model = model_name)
        
    def _generate_ollama_response(self, prompt: str, model_name: str):
        return ollama.chat(model=model_name, messages=[
        {
            'role': 'user',
            'content': prompt,
        },
        ])['message']['content']
    
    def _generate_grok_response(self, prompt: str, model_name: str):
        return self.grok_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
                ],
                model=model_name,
            ).choices[0].message.content
        
    def _generate_gpt_response(self, prompt: str, model_name: str):
        completion = self.openai_client.chat.completions.create(
            model = model_name,
            messages = [
                {"role": "system", "content": "You are a mycobacterium professional in the medical field."},
                {"role": "user", "content": prompt},
            ]
            )
        return completion.choices[0].message.content.strip()
        
    def predict(self, model_name: str, prompt: str, model):
        if model_name in ollama_models_list:
            return self._generate_ollama_response(prompt, model_name)
        if model_name in grok_models_list:
            return self._generate_grok_response(prompt, model_name)
        if model_name in chat_gpt_models_list_v2:
            return self._generate_gpt_response(prompt, model_name)
        return model.generate([prompt]).generations[0][0].text
        
    def load_pretrained_model(self, st: streamlit, model_name: str):
        if model_name in chat_gpt_models_list:
            return self._load_open_ai_model(model_name)
        if model_name in ollama_models_list:
            try:
                return self._load_ollama_model(model_name)
            except:
                with st.spinner(f'Waiting for {model_name} response...'):
                    self._download_ollama_model(model_name)
                    return self._load_ollama_model(model_name)  
                
    def adjust_prompt_response(self, prompt: str, response_type):
        try:
            return json.loads(prompt)[response_type]
        except:
            try:
                prompt = "{"+prompt.split("{")[-1].split("}")[0]+"}"
                return json.loads(prompt)[response_type]
            except:
                return prompt
                
    def prompt_adjustment(self, response_type, context: str, question: str):
        if response_type == "question":
            return GENERATE_QUESTION_TEMPLATE.replace("__QUESTION__", question)
        if response_type == "context":
            return GENERATE_ANSWER_FROM_CONTEXT_TEMPLATE.replace("__CONTEXT__", context).replace("__QUESTION__", question)
        if response_type == "default":
            return GENERATE_ANSWER_TEMPLATE.replace("__QUESTION__", question)
        if response_type == "internet":
            search_result = self.serp_api_wrapper.run(question)
            return GENERATE_ANSWER_FROM_INTERNET_CONTENT_TEMPLATE.replace("__INTERNET__", search_result).replace("__QUESTION__", question)
        if response_type == "internet+context":
            search_result = self.serp_api_wrapper.run(question)
            return GENERATE_ANSWER_FROM_CONTEXT_AND_INTERNET_CONTENT_TEMPLATE.replace("__CONTEXT__", context).replace("__QUESTION__", question).replace("__INTERNET__", search_result)
            
    
    