from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    groq_api_key_fallback: str = ""
    groq_api_key_fallback2: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_model_fallback: str = "gemma2-9b-it"

    tavily_api_key: str

    database_url: str

    openrouter_api_key: str = ""
    openrouter_api_key_fallback: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-exp:free"

    environment: str = "development"
    comparison_port: int = 8002

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
