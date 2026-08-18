from typing import Dict, Any

class BaseAgent:
    name: str = "BaseAgent"
    description: str = ""

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent logic with input_data dict and return a dict outcome.
        """
        raise NotImplementedError
