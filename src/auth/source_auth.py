"""Authentication for source web application."""
from playwright.sync_api import Page, Browser, TimeoutError as PlaywrightTimeout
from src.auth.base_auth import BaseAuth
from src.utils.logger import logger
from src.utils.config import AppConfig
import time


class SourceAuth(BaseAuth):
    """Authentication handler for source application."""

    def __init__(self, config: AppConfig, browser: Browser):
        """Initialize source authentication."""
        super().__init__(config, browser)
        self.url = config.source_url
        self.username = config.source_username
        self.password = config.source_password

    def login(self) -> bool:
        """Perform login to source application.

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            logger.info(f"Logging into source application: {self.url}")

            # Create new page
            self.page = self.browser.new_page()
            self.page.set_default_timeout(self.config.browser_timeout)

            # Navigate to login page
            self.page.goto(self.url)
            logger.info("Navigated to source application")

            # TODO: Customize these selectors for your source application
            # Example selectors - replace with actual selectors from your app

            # Wait for login form to load
            self.page.wait_for_selector('input[name="username"]', timeout=10000)

            # Fill in credentials
            self.page.fill('input[name="username"]', self.username)
            self.page.fill('input[name="password"]', self.password)
            logger.info("Credentials filled")

            # Submit login form
            self.page.click('button[type="submit"]')

            # Wait for successful login (adjust selector as needed)
            # This could be a dashboard element, user menu, etc.
            self.page.wait_for_selector('[data-testid="dashboard"]', timeout=15000)

            logger.info("Successfully logged into source application")
            return True

        except PlaywrightTimeout as e:
            logger.error(f"Timeout during login: {e}")
            self.take_screenshot("source_login_timeout")
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.take_screenshot("source_login_error")
            return False

    def is_logged_in(self) -> bool:
        """Check if currently logged in to source application.

        Returns:
            bool: True if logged in, False otherwise
        """
        if not self.page:
            return False

        try:
            # TODO: Customize this selector to check for logged-in state
            # Example: check for user menu, dashboard, or logout button
            self.page.wait_for_selector('[data-testid="dashboard"]', timeout=3000)
            return True
        except:
            return False

    def navigate_to_data_section(self) -> bool:
        """Navigate to the section containing data to extract.

        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # TODO: Customize navigation for your application
            # Example: clicking menu items, navigating to specific URL
            logger.info("Navigating to data section")

            # Option 1: Direct navigation
            # self.page.goto(f"{self.url}/data-section")

            # Option 2: Click navigation menu
            # self.page.click('a[href="/data-section"]')

            # Wait for data section to load
            # self.page.wait_for_selector('[data-testid="data-table"]', timeout=10000)

            logger.info("Successfully navigated to data section")
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            self.take_screenshot("source_navigation_error")
            return False
