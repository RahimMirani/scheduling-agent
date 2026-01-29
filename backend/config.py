import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google OAuth
    google_credentials_path: str = "credentials.json"

    # Gemini API
    gemini_api_key: str = ""

    # App settings
    app_host: str = "localhost"
    app_port: int = 8000
    app_secret_key: str = "change-this-in-production"

    # OAuth scopes for Gmail and Calendar
    google_scopes: list = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
