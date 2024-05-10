from abc import ABC
from langchain.llms.ollama import Ollama
from langchain_community.llms.openai import OpenAI
import ollama
from groq import Groq
from shared.shared_variables import chat_gpt_models_list, ollama_models_list, grok_models_list
from langchain_community.utilities import SerpAPIWrapper
import streamlit

class ModelHandlerService(ABC):
    def __init__(self):
        self.grok_client = Groq()
        self.serp_api_wrapper = SerpAPIWrapper()
    
    def _load_open_ai_model(self, model_name: str):
        return OpenAI(model = model_name)
    
    # def load_grok_model(self):
    #     return self.grok_client
    
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
        
    def predict(self, model_name: str, prompt: str, model):
        if model_name in ollama_models_list:
            return self._generate_ollama_response(prompt, model_name)
        if model_name in grok_models_list:
            return self._generate_grok_response(prompt, model_name)
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
                
    def prompt_adjustment(self, response_type, context: str, question: str):
        if response_type == "context":
            return context + " \n following the above context: "+ question
        if response_type == "default":
            return question
        if response_type == "internet":
            search_result = self.serp_api_wrapper.run(question)
            return question + "\n I researched the internet and got: " + search_result + "\n can you clarify"
        if response_type == "internet+context":
            search_result = self.serp_api_wrapper.run(question)
            return  context + " \n following the above context: " + question + "\n I researched the internet and got: " +search_result+"\n can you clarify"
            
    
    