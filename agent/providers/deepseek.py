import os

from agent.providers.openai_compatible import OpenAICompatibleJSONPlannerProvider


class DeepSeekJSONPlannerProvider(OpenAICompatibleJSONPlannerProvider):
    def __init__(self):
        super().__init__(
            api_key=os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("AGENT_LLM_API_KEY"),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            model=os.environ.get("DEEPSEEK_PLANNER_MODEL", "deepseek-chat"),
        )
