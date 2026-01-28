"""
Configuration module for Dumu Apparels Instagram Bot.

Uses Pydantic Settings to validate and load environment variables.
All configuration values are validated at startup.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from typing import Optional
import os


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
    # Reads from DATABASE_URL env var, defaults to SQLite for local dev
    # Protocol is automatically fixed: postgres:// or postgresql:// → postgresql+asyncpg://
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dumu.db")
    )
    
    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url_protocol(cls, v: str) -> str:
        """
        Fix database URL protocol for SQLAlchemy async.
        
        Railway and many cloud providers provide URLs starting with:
        - postgres:// → needs to be postgresql+asyncpg://
        - postgresql:// → needs to be postgresql+asyncpg://
        
        Args:
            v: Database URL string
            
        Returns:
            str: Database URL with correct protocol for asyncpg
        """
        if not v:
            return v
        
        # If URL starts with postgres:// (without the +asyncpg part), fix it
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        
        # If URL starts with postgresql:// (but not postgresql+asyncpg://), fix it
        if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # If it's SQLite or already has the correct protocol, return as-is
        return v
    
    # Payment Providers - IntaSend (Primary) - Optional for now, will be added in future version
    intasend_public_key: Optional[str] = None
    intasend_secret_key: Optional[str] = None
    
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
    
    # Base URL for IPN callbacks (optional - defaults to empty, set in PesaPal dashboard)
    base_url: Optional[str] = None

    # Public URL of THIS app (used for payment callbacks)
    # Example: https://your-railway-domain.up.railway.app
    app_url: str
    
    # Instagram handle/username (for payment callback redirects)
    instagram_handle: str = "dumuapparels"

    # Payment Providers - KoPokoPo (K2) STK Push (Primary)
    kopokopo_client_id: str
    kopokopo_client_secret: str
    kopokopo_api_key: str
    kopokopo_base_url: str = "https://sandbox.kopokopo.com"
    kopokopo_till_number: str

    @field_validator("kopokopo_till_number")
    @classmethod
    def validate_kopokopo_till_number(cls, v: str) -> str:
        """
        Kopo Kopo v1 requires till numbers to start with 'K'.
        Fail fast at startup to avoid silent payment failures.
        """
        if not v:
            raise ValueError("KOPOKOPO_TILL_NUMBER is required")
        if not v.startswith("K"):
            raise ValueError("KOPOKOPO_TILL_NUMBER must start with 'K'")
        return v


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

