from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    bot_token: str = Field(..., env="BOT_TOKEN")
    db_url: str = Field(..., env="DB_URL")
    
    class Config:
        env_file = ".env"

settings = Settings()