import os
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        API_TITLE: str = "Enterprise YouTube Downloader API Platform"
        API_VERSION: str = "1.0.0"
        API_DESCRIPTION: str = "Professional Download API Server powered by FastAPI and yt-dlp"

        # API Security Credentials
        API_KEY: str = os.getenv("API_KEY", "yt_live_9f8d7c6b5a4e3d2c1b0a")
        SECRET_KEY: str = os.getenv("SECRET_KEY", "sec_k8j7h6g5f4d3s2a1_enterprise_secret")
        WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

        # Storage & Engine Settings
        DOWNLOAD_DIR: Path = Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()
        TEMP_FILE_TTL_MINUTES: int = int(os.getenv("TEMP_FILE_TTL_MINUTES", "60"))
        MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "10"))
        DUPLICATE_CACHE_MINUTES: int = int(os.getenv("DUPLICATE_CACHE_MINUTES", "120"))

        # Security Policies
        SECURITY_ENFORCE_SIGNATURE: bool = os.getenv("SECURITY_ENFORCE_SIGNATURE", "false").lower() in ("true", "1")
        SECURITY_TIMESTAMP_WINDOW_SECONDS: int = int(os.getenv("SECURITY_TIMESTAMP_WINDOW_SECONDS", "300"))
        RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))

        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    settings = Settings()

except ImportError:
    class SettingsFallback:
        API_TITLE: str = "Enterprise YouTube Downloader API Platform"
        API_VERSION: str = "1.0.0"
        API_DESCRIPTION: str = "Professional Download API Server powered by FastAPI and yt-dlp"

        API_KEY: str = os.getenv("API_KEY", "yt_live_9f8d7c6b5a4e3d2c1b0a")
        SECRET_KEY: str = os.getenv("SECRET_KEY", "sec_k8j7h6g5f4d3s2a1_enterprise_secret")
        WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

        DOWNLOAD_DIR: Path = Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()
        TEMP_FILE_TTL_MINUTES: int = int(os.getenv("TEMP_FILE_TTL_MINUTES", "60"))
        MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "10"))
        DUPLICATE_CACHE_MINUTES: int = int(os.getenv("DUPLICATE_CACHE_MINUTES", "120"))

        SECURITY_ENFORCE_SIGNATURE: bool = os.getenv("SECURITY_ENFORCE_SIGNATURE", "false").lower() in ("true", "1")
        SECURITY_TIMESTAMP_WINDOW_SECONDS: int = int(os.getenv("SECURITY_TIMESTAMP_WINDOW_SECONDS", "300"))
        RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))

    settings = SettingsFallback()

# Ensure download directory exists
settings.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
