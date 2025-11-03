"""Configuration loader for the automation system."""
import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# Load environment variables
env_path = Path("/app/config/.env")
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Try loading from default location


@dataclass
class AppConfig:
    """Application configuration."""

    # Source Application
    source_url: str
    source_username: str
    source_password: str

    # Target Application
    target_url: str
    target_username: str
    target_password: str

    # Browser Settings
    headless: bool
    browser_timeout: int
    screenshot_on_error: bool

    # Data Transfer Settings
    batch_size: int
    retry_attempts: int
    retry_delay: int

    # Logging
    log_level: str
    log_retention_days: int

    # OpenAI API
    openai_api_key: str
    openai_model: str
    openai_max_tokens: int

    # Data Processing
    days_to_fetch: int
    download_individual_files: bool

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        return cls(
            # Source App
            source_url=os.getenv("SOURCE_APP_URL", ""),
            source_username=os.getenv("SOURCE_APP_USERNAME", ""),
            source_password=os.getenv("SOURCE_APP_PASSWORD", ""),

            # Target App
            target_url=os.getenv("TARGET_APP_URL", ""),
            target_username=os.getenv("TARGET_APP_USERNAME", ""),
            target_password=os.getenv("TARGET_APP_PASSWORD", ""),

            # Browser
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            browser_timeout=int(os.getenv("BROWSER_TIMEOUT", "30000")),
            screenshot_on_error=os.getenv("SCREENSHOT_ON_ERROR", "true").lower() == "true",

            # Data Transfer
            batch_size=int(os.getenv("BATCH_SIZE", "50")),
            retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
            retry_delay=int(os.getenv("RETRY_DELAY", "5")),

            # Logging
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_retention_days=int(os.getenv("LOG_RETENTION_DAYS", "30")),

            # OpenAI
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000")),

            # Data Processing
            days_to_fetch=int(os.getenv("DAYS_TO_FETCH", "1")),
            download_individual_files=os.getenv("DOWNLOAD_INDIVIDUAL_FILES", "true").lower() == "true"
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.source_url:
            errors.append("SOURCE_APP_URL is required")
        if not self.source_username:
            errors.append("SOURCE_APP_USERNAME is required")
        if not self.source_password:
            errors.append("SOURCE_APP_PASSWORD is required")

        if not self.target_url:
            errors.append("TARGET_APP_URL is required")
        if not self.target_username:
            errors.append("TARGET_APP_USERNAME is required")
        if not self.target_password:
            errors.append("TARGET_APP_PASSWORD is required")

        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")

        return errors


# Global config instance
config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get or create the global configuration instance."""
    global config
    if config is None:
        config = AppConfig.from_env()
    return config
