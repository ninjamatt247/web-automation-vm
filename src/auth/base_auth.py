"""Base authentication class for web applications."""
from abc import ABC, abstractmethod
from playwright.sync_api import Page, Browser
from typing import Optional
from src.utils.logger import logger
from src.utils.config import AppConfig


class BaseAuth(ABC):
    """Base class for web application authentication."""

    def __init__(self, config: AppConfig, browser: Browser):
        """Initialize authentication handler.

        Args:
            config: Application configuration
            browser: Playwright browser instance
        """
        self.config = config
        self.browser = browser
        self.page: Optional[Page] = None

    @abstractmethod
    def login(self) -> bool:
        """Perform login to the web application.

        Returns:
            bool: True if login successful, False otherwise
        """
        pass

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Check if currently logged in.

        Returns:
            bool: True if logged in, False otherwise
        """
        pass

    def logout(self) -> bool:
        """Perform logout from the web application.

        Returns:
            bool: True if logout successful, False otherwise
        """
        try:
            if self.page:
                self.page.close()
                self.page = None
            logger.info("Logged out successfully")
            return True
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    def take_screenshot(self, name: str = "error"):
        """Take a screenshot for debugging.

        Args:
            name: Name for the screenshot file
        """
        if self.page and self.config.screenshot_on_error:
            try:
                screenshot_path = f"/app/logs/{name}_{self._get_timestamp()}.png"
                self.page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                logger.error(f"Failed to take screenshot: {e}")

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
