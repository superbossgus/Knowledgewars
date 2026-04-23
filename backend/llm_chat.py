"""
LLM Chat Handler
"""
from typing import Optional
from pydantic import BaseModel
from anthropic import Anthropic

class UserMessage(BaseModel):
    text: str
    role: str = "user"

class LlmChat:
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.model = model
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.conversation_history = []
    
    async def send_message(self, message: UserMessage) -> str:
        self.conversation_history.append({"role": "user", "content": message.text})
        response = self.client.messages.create(model=self.model, max_tokens=2048, messages=self.conversation_history)
        assistant_message = response.content[0].text
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        return assistant_message
    
    def reset_history(self):
        self.conversation_history = []
