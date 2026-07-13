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


def get_fallback_llm() -> ChatGroq:
    api_key = settings.groq_api_key_fallback or settings.groq_api_key
    return ChatGroq(
        model=settings.groq_model_fallback,
        api_key=api_key,
        temperature=0.2,
        streaming=False,
        max_tokens=4096,
        request_timeout=120,
    )


def get_fallback_llm2() -> ChatGroq:
    api_key = settings.groq_api_key_fallback2 or settings.groq_api_key_fallback or settings.groq_api_key
    return ChatGroq(
        model=settings.groq_model_fallback,
        api_key=api_key,
        temperature=0.2,
        streaming=False,
        max_tokens=4096,
        request_timeout=120,
    )


def get_fallback_llm3() -> ChatGroq:
    api_key = settings.groq_api_key_fallback3 or settings.groq_api_key_fallback2 or settings.groq_api_key_fallback or settings.groq_api_key
    return ChatGroq(
        model=settings.groq_model_fallback,
        api_key=api_key,
        temperature=0.2,
        streaming=False,
        max_tokens=4096,
        request_timeout=120,
    )
