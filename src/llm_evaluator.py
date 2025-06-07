from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

class LLMEvaluator:
    def __init__(self, model: ChatGoogleGenerativeAI, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt

    def evaluate(self, input_variables: dict[str, str]) -> str:
        formatted_prompt = self.system_prompt.format(**input_variables)
        response = self.model.invoke(formatted_prompt)
        return str(response.content)
    
class GenAIEvaluator:
    def __init__(self, model, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt

    def evaluate(self, input_variables: dict[str, str]) -> str:
        formatted_prompt = self.system_prompt.format(**input_variables)
        response = self.model.generate_content(formatted_prompt)
        return response.text