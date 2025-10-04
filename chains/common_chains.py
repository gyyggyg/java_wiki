from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from interfaces.llm_interface import LLMInterface

class ChainFactory:
    """创建各种处理链的工厂"""
    
    @staticmethod
    def create_generic_chain(llm_interface: LLMInterface, prompt_template: PromptTemplate, output_parser=None):
        """创建一个通用的处理链。"""
        if output_parser is None:
            output_parser = StrOutputParser()
        return (prompt_template | llm_interface.llm | output_parser)