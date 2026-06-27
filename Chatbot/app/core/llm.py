from langchain_groq import ChatGroq
from app.config import settings


def get_llm(streaming: bool = False) -> ChatGroq:
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0 if not streaming else 0.3,
        streaming=streaming,
        max_tokens=2048,
    )
