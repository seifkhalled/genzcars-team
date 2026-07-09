from langchain_groq import ChatGroq
from app.config import settings


def get_llm() -> ChatGroq:
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0.2,
        streaming=False,
        max_tokens=4096,
        request_timeout=120,
    )
