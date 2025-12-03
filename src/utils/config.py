"""Configuration loader for the automation system."""
import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# Load environment variables
# Try Docker path first, then local path
docker_env_path = Path("/app/config/.env")
local_env_path = Path(__file__).parent.parent.parent / "config" / ".env"

if docker_env_path.exists():
    load_dotenv(docker_env_path)
elif local_env_path.exists():
    load_dotenv(local_env_path)
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

    # Osmind API Configuration
    osmind_api_base_url: str
    osmind_api_timeout: int
    osmind_batch_size: int
    osmind_rate_limit_delay: int
    osmind_max_retries: int
    osmind_default_start_date: str

    # PDF Generation Settings
    pdf_template_dir: str
    pdf_output_dir: str
    pdf_field_mappings_dir: str
    pdf_field_positions_dir: str
    pdf_batch_size: int
    pdf_retry_attempts: int

    # Microsoft OneDrive Settings
    onedrive_tenant_id: str
    onedrive_client_id: str
    onedrive_client_secret: str
    onedrive_root_folder: str
    onedrive_upload_timeout: int

    # Scheduler Settings
    pdf_scheduler_enabled: bool

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
            download_individual_files=os.getenv("DOWNLOAD_INDIVIDUAL_FILES", "true").lower() == "true",

            # Osmind API
            osmind_api_base_url=os.getenv("OSMIND_API_BASE_URL", "https://prod-app-api.osmind.org"),
            osmind_api_timeout=int(os.getenv("OSMIND_API_TIMEOUT", "30000")),
            osmind_batch_size=int(os.getenv("OSMIND_BATCH_SIZE", "50")),
            osmind_rate_limit_delay=int(os.getenv("OSMIND_RATE_LIMIT_DELAY", "1")),
            osmind_max_retries=int(os.getenv("OSMIND_MAX_RETRIES", "3")),
            osmind_default_start_date=os.getenv("OSMIND_DEFAULT_START_DATE", "2025-01-01"),

            # PDF Generation
            pdf_template_dir=os.getenv("PDF_TEMPLATE_DIR", "config/pdf_templates"),
            pdf_output_dir=os.getenv("PDF_OUTPUT_DIR", "data/pdf_output"),
            pdf_field_mappings_dir=os.getenv("PDF_FIELD_MAPPINGS_DIR", "config/field_mappings"),
            pdf_field_positions_dir=os.getenv("PDF_FIELD_POSITIONS_DIR", "config/field_positions"),
            pdf_batch_size=int(os.getenv("PDF_BATCH_SIZE", "50")),
            pdf_retry_attempts=int(os.getenv("PDF_RETRY_ATTEMPTS", "3")),

            # Microsoft OneDrive
            onedrive_tenant_id=os.getenv("ONEDRIVE_TENANT_ID", ""),
            onedrive_client_id=os.getenv("ONEDRIVE_CLIENT_ID", ""),
            onedrive_client_secret=os.getenv("ONEDRIVE_CLIENT_SECRET", ""),
            onedrive_root_folder=os.getenv("ONEDRIVE_ROOT_FOLDER", "/PDF_Forms"),
            onedrive_upload_timeout=int(os.getenv("ONEDRIVE_UPLOAD_TIMEOUT", "300")),

            # Scheduler
            pdf_scheduler_enabled=os.getenv("PDF_SCHEDULER_ENABLED", "false").lower() == "true"
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
