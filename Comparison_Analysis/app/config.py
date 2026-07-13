from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    groq_api_key_fallback: str = ""
    groq_api_key_fallback2: str = ""
    groq_api_key_fallback3: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_model_fallback: str = "llama-3.1-8b-instant"

    tavily_api_key: str

    database_url: str

    openrouter_api_key: str = ""
    openrouter_api_key_fallback: str = ""
    openrouter_model: str = "google/gemma-4-26b-a4b-it:free"
    openrouter_model_fallback: str = "google/gemini-2.5-flash-preview:free"
    openrouter_vision_model: str = "google/gemma-4-26b-a4b-it:free"
    openrouter_vision_model_fallback: str = "google/gemini-2.5-flash-preview:free"

    redis_url: str = "redis://redis:6379/0"

    environment: str = "development"
    comparison_port: int = 8002

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
