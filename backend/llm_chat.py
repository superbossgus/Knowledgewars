"""
LLM Chat Handler
"""
import os
from typing import Optional
from pydantic import BaseModel
from anthropic import Anthropic

# claude-3-5-sonnet-20241022 se retiro el 2025-10-28. Reemplazo directo segun la
# guia de migracion de Anthropic: claude-sonnet-5.
DEFAULT_MODEL = os.getenv("CHAT_MODEL", "claude-sonnet-5")

MAX_TOKENS = 2048


class UserMessage(BaseModel):
    text: str
    role: str = "user"


class LlmChat:
    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None):
        self.model = model
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.conversation_history = []

    async def send_message(self, message: UserMessage) -> str:
        self.conversation_history.append({"role": "user", "content": message.text})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            # El pensamiento adaptativo esta encendido por omision en los modelos
            # actuales y sus tokens salen del mismo max_tokens que la respuesta.
            # Este chat devuelve texto corto, asi que lo apagamos.
            thinking={"type": "disabled"},
            messages=self.conversation_history,
        )
        assistant_message = self._text_of(response)
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    @staticmethod
    def _text_of(response) -> str:
        """
        Junta los bloques de texto de la respuesta.

        `response.content[0].text` asumia que el primer bloque es texto; en los
        modelos actuales puede ser un bloque de pensamiento y devolver vacio.
        """
        if getattr(response, "stop_reason", None) == "refusal":
            raise RuntimeError("El modelo rechazo responder (stop_reason=refusal).")

        texts = [
            block.text
            for block in getattr(response, "content", []) or []
            if getattr(block, "type", None) == "text"
        ]
        if not texts:
            raise RuntimeError(
                "La respuesta no trae ningun bloque de texto "
                f"(stop_reason={getattr(response, 'stop_reason', None)})."
            )
        return "".join(texts)

    def reset_history(self):
        self.conversation_history = []
