from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    hindsight_base_url: str = "https://api.hindsight.vectorize.io"
    hindsight_api_key: str = ""
    hindsight_bank_id: str = "nearmiss-demo"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    database_path: str = "./nearmiss.db"
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def origins(self): return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
@lru_cache
def get_settings(): return Settings()
