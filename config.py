from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH: str
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    
    # LinkedIn OAuth
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    LINKEDIN_REDIRECT_URI: str
    
    # Email Settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    
    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str 
    
    class Config:
        env_file = ".env"

settings = Settings()
