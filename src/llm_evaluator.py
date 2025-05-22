from langchain_community.llms import BaseLLM

class LLMEvaluator:
    def __init__(self, model: BaseLLM, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt

    def evaluate(self, input_variables: dict[str, str]) -> str:
        formatted_prompt = self.system_prompt.format(**input_variables)
        response = self.model.invoke(formatted_prompt)
        return response.content