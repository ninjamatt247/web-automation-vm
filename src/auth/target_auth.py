"""Authentication for target web application (Osmind EHR)."""
from playwright.sync_api import Page, Browser, TimeoutError as PlaywrightTimeout
from src.auth.base_auth import BaseAuth
from src.utils.logger import logger
from src.utils.config import AppConfig
import time


class TargetAuth(BaseAuth):
    """Authentication handler for Osmind EHR."""

    def __init__(self, config: AppConfig, browser: Browser):
        """Initialize target authentication."""
        super().__init__(config, browser)
        self.url = config.target_url
        self.username = config.target_username
        self.password = config.target_password

    def login(self) -> bool:
        """Perform login to target application.

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            logger.info(f"Logging into target application: {self.url}")

            # Create new page
            self.page = self.browser.new_page()
            self.page.set_default_timeout(self.config.browser_timeout)

            # Navigate to login page
            self.page.goto(self.url)
            logger.info("Navigated to Osmind EHR")

            time.sleep(2)

            # Find and fill username/email field
            try:
                # Try multiple possible selectors for username field
                username_selector = None
                for selector in [
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[name="username"]',
                    'input[id*="email"]',
                    'input[id*="username"]',
                    'input[placeholder*="email" i]',
                    'input[placeholder*="username" i]'
                ]:
                    try:
                        self.page.wait_for_selector(selector, timeout=3000)
                        username_selector = selector
                        break
                    except:
                        continue

                if not username_selector:
                    raise Exception("Could not find username/email input field")

                logger.info(f"Found username field: {username_selector}")
                self.page.fill(username_selector, self.username)

            except Exception as e:
                logger.error(f"Failed to fill username: {e}")
                raise

            # Find and fill password field
            try:
                password_selector = 'input[type="password"]'
                self.page.wait_for_selector(password_selector, timeout=5000)
                self.page.fill(password_selector, self.password)
                logger.info("Credentials filled")

            except Exception as e:
                logger.error(f"Failed to fill password: {e}")
                raise

            # Submit login form
            try:
                # Try multiple submit methods
                try:
                    self.page.click('button[type="submit"]', timeout=5000)
                    logger.info("Clicked submit button")
                except:
                    try:
                        self.page.click('button:has-text("Sign in"), button:has-text("Log in")', timeout=5000)
                        logger.info("Clicked login button by text")
                    except:
                        # Press Enter as fallback
                        self.page.keyboard.press('Enter')
                        logger.info("Pressed Enter to submit")

            except Exception as e:
                logger.error(f"Failed to submit form: {e}")
                raise

            # Wait for successful login
            try:
                # Wait to be redirected away from login page
                self.page.wait_for_url(lambda url: "login" not in url.lower(), timeout=15000)
                logger.info("Redirected away from login page")

                time.sleep(2)

                # Verify we're logged in by checking for common dashboard elements
                try:
                    self.page.wait_for_selector('[class*="dashboard"], [class*="home"], [role="main"], main', timeout=10000)
                    logger.info("Dashboard/main content detected")
                except:
                    logger.warning("Could not verify dashboard elements, but login redirect occurred")

            except PlaywrightTimeout:
                logger.error("Timeout waiting for login redirect")
                raise

            logger.info(f"Successfully logged into Osmind EHR - URL: {self.page.url}")
            return True

        except PlaywrightTimeout as e:
            logger.error(f"Timeout during login: {e}")
            self.take_screenshot("target_login_timeout")
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.take_screenshot("target_login_error")
            return False

    def is_logged_in(self) -> bool:
        """Check if currently logged in to target application.

        Returns:
            bool: True if logged in, False otherwise
        """
        if not self.page:
            return False

        try:
            # TODO: Customize this selector to check for logged-in state
            self.page.wait_for_selector('[data-testid="dashboard"]', timeout=3000)
            return True
        except:
            return False

    def navigate_to_input_section(self) -> bool:
        """Navigate to the section where data should be inserted.

        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # TODO: Customize navigation for your application
            logger.info("Navigating to data input section")

            # Option 1: Direct navigation
            # self.page.goto(f"{self.url}/data-input")

            # Option 2: Click navigation menu
            # self.page.click('a[href="/data-input"]')

            # Wait for input section to load
            # self.page.wait_for_selector('[data-testid="input-form"]', timeout=10000)

            logger.info("Successfully navigated to input section")
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            self.take_screenshot("target_navigation_error")
            return False
