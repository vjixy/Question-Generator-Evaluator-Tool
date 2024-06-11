GENERATE_QUESTION_TEMPLATE = """
You are a mycobacterium professional in the medical field.

Generate a question based on the following context, the question should be creative and aligns with the context. 

__CONTEXT__


Respond only with the generated question as a json format like follow:
    
    {
        "question": "What is the question?"
    }

"""

GENERATE_ANSWER_TEMPLATE = """
You are a mycobacterium professional in the medical field.

Answer the following question: 

__QUESTION__


Respond only with the generated answer as a json format like follow:
    
    {
        "answer": "What is the answer?"
    }
"""

GENERATE_ANSWER_FROM_CONTEXT_TEMPLATE = """
You are a mycobacterium professional in the medical field.
You will be given a context and question, you will use the context to answer the question,

Context:

__CONTEXT__


Question: 

__QUESTION__


Answer the question by only using content from the context only do not use knowledge outside of the context, if you do not know say I don't know. 
keep the answer short and concise.
Respond only with the generated answer as a json format like follow:
    
    {
        "answer": "What is the answer?"
    }
"""

GENERATE_ANSWER_FROM_INTERNET_CONTENT_TEMPLATE = """
You are a mycobacterium professional in the medical field.
You will be given a context from  and question, you will use the context to answer the question,

Internet context:

__INTERNET__


Question: 

__QUESTION__


Answer the question based on the internet context only do not use knowledge outside of the context, if you do not know say I don't know. 
keep the answer short and concise.
Respond only with the generated answer as a json format like follow:
    
    {
        "answer": "What is the answer?"
    }
"""

GENERATE_ANSWER_FROM_CONTEXT_AND_INTERNET_CONTENT_TEMPLATE = """
You are a mycobacterium professional in the medical field.
You will be given internet context, document context and a question, you will use the contexts to answer the question,

Internet context:

__INTERNET__

Document context:

__CONTEXT__


Question: 

__QUESTION__


Answer the question based on the internet context and document context only do not use knowledge outside of the context, if you do not know say I don't know. 
keep the answer short and concise.
Respond only with the generated answer as a json format like follow:
    
    {
        "answer": "What is the answer?"
    }
"""