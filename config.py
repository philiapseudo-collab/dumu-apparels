"""
Configuration module for Dumu Apparels Instagram Bot.

Uses Pydantic Settings to validate and load environment variables.
All configuration values are validated at startup.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are validated using Pydantic. Missing required fields
    will raise a ValidationError at startup.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Meta/Instagram Configuration
    verify_token: str
    page_access_token: str
    instagram_account_id: str
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Database Configuration
    database_url: str
    
    # Payment Providers - IntaSend (Primary)
    intasend_public_key: str
    intasend_secret_key: str
    
    # Payment Providers - PesaPal (Secondary/Fallback)
    pesapal_consumer_key: str
    pesapal_consumer_secret: str
    
    # Optional Application Settings
    app_name: str = "Dumu Apparels Instagram Bot"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Payment Link Timeout (in minutes)
    payment_link_timeout: int = 15
    
    # Currency (Kenyan Shillings)
    currency: str = "KES"


# Global settings instance
# This will be initialized when the module is imported
settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the global settings instance.
    
    Returns:
        Settings: The validated settings instance
        
    Raises:
        ValidationError: If required environment variables are missing
    """
    global settings
    if settings is None:
        settings = Settings()
    return settings

