from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.agents.environment_agent.prompt import ENVIRONMENT_AGENT_SYSTEM_PROMPT
from app.agents.environment_agent.tools.weather import search_weather_tool
from app.core.config import settings


class EnvironmentAgentBuilder:
    """
    EnvironmentAgent构建器，用于构建EnvironmentAgent
    """

    def __init__(self):
        # 初始化deepseek模型
        self.llm = ChatOpenAI(
            model=settings.DEEPSEEK_API_MODEL, 
            base_url=settings.DEEPSEEK_API_BASE, 
            api_key=settings.DEEPSEEK_API_KEY,
            extra_body={"thinking": {"type": "disabled"}})

    def build(self):
        """
        构建EnvironmentAgent
        :return: EnvironmentAgent实例
        """
        return create_agent(
            model=self.llm,
            tools=[search_weather_tool],
            system_prompt=ENVIRONMENT_AGENT_SYSTEM_PROMPT,
            debug=True,
        )
