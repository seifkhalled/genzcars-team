from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    tavily_api_key: str

    database_url: str

    environment: str = "development"
    comparison_port: int = 8002

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
