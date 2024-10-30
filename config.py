from typing import Union
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    PEER: str
    GAME_URL: str

    RANDOM_SLEEP_BEFORE_START: bool

settings = Settings()