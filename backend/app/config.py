from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql+psycopg://devops:devops_local_only@db:5432/devops_hub'
    jwt_secret: str = 'CHANGE_ME_TO_A_LONG_RANDOM_SECRET_BEFORE_DEPLOYING'
    jwt_algorithm: str = 'HS256'
    access_token_minutes: int = 60
    cors_origins: str = 'http://localhost:8080,http://127.0.0.1:8080'

settings = Settings()
