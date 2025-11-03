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

            # Customized selectors for Freed.ai login form

            # Wait for login form to load - try multiple possible selectors
            try:
                # Try email input first (common for modern forms)
                self.page.wait_for_selector('input[type="email"]', timeout=5000)
                email_selector = 'input[type="email"]'
            except:
                try:
                    # Fallback to username/email input by name
                    self.page.wait_for_selector('input[name="email"]', timeout=5000)
                    email_selector = 'input[name="email"]'
                except:
                    # Final fallback to any email-like input
                    self.page.wait_for_selector('input[placeholder*="email" i]', timeout=5000)
                    email_selector = 'input[placeholder*="email" i]'

            # Wait for password field
            try:
                self.page.wait_for_selector('input[type="password"]', timeout=5000)
                password_selector = 'input[type="password"]'
            except:
                # Fallback to password input by name
                self.page.wait_for_selector('input[name="password"]', timeout=5000)
                password_selector = 'input[name="password"]'

            # Fill in credentials
            self.page.fill(email_selector, self.username)
            self.page.fill(password_selector, self.password)
            logger.info("Credentials filled")

            # Submit login form - try multiple possible submit buttons
            try:
                # Try button with "Sign in" text first
                self.page.click('button:has-text("Sign in")', timeout=5000)
            except:
                try:
                    # Try button with "Login" text
                    self.page.click('button:has-text("Login")', timeout=5000)
                except:
                    try:
                        # Try submit button by type
                        self.page.click('button[type="submit"]', timeout=5000)
                    except:
                        # Final fallback - click any button that might be submit
                        self.page.click('form button:not([type="button"])', timeout=5000)

            logger.info("Form submitted, checking for OAuth redirect...")

            # ========================================
            # Handle Google OAuth Flow (Freed.ai uses Google OAuth)
            # ========================================
            try:
                # Wait for possible Google OAuth redirect
                self.page.wait_for_url(lambda url: "google.com" in url.lower(), timeout=5000)
                logger.info("Detected Google OAuth redirect, handling authentication...")

                # Wait for Google login page to load
                import time
                time.sleep(2)

                # Enter email on Google's page
                try:
                    logger.info("Entering Google email...")
                    google_email_selector = 'input[type="email"]'
                    self.page.wait_for_selector(google_email_selector, timeout=10000)
                    self.page.fill(google_email_selector, self.username)

                    # Click Next button
                    self.page.click('button:has-text("Next"), #identifierNext', timeout=5000)
                    logger.info("Email submitted")

                    # Wait for password page
                    time.sleep(2)

                    # Enter password
                    logger.info("Entering Google password...")
                    google_password_selector = 'input[type="password"]'
                    self.page.wait_for_selector(google_password_selector, timeout=10000)
                    self.page.fill(google_password_selector, self.password)

                    # Click Next button
                    self.page.click('button:has-text("Next"), #passwordNext', timeout=5000)
                    logger.info("Password submitted")

                except Exception as e:
                    logger.warning(f"Google OAuth step error (may be already authenticated): {e}")

                # Wait for redirect back to Freed.ai
                logger.info("Waiting for OAuth redirect back to application...")
                self.page.wait_for_url(lambda url: "getfreed.ai" in url.lower(), timeout=30000)
                logger.info("Successfully redirected back after OAuth")

                # Wait for dashboard to load
                time.sleep(3)

            except PlaywrightTimeout:
                # Not a Google OAuth flow, continue with normal login check
                logger.info("No Google OAuth redirect detected, checking direct login...")

            # Wait for successful login - try multiple possible success indicators
            try:
                # Try common dashboard selectors
                self.page.wait_for_selector('[data-testid*="dashboard"], .dashboard, #dashboard', timeout=15000)
            except:
                try:
                    # Try user menu or profile indicators
                    self.page.wait_for_selector('[data-testid*="user"], .user-menu, .profile, [data-testid*="menu"]', timeout=15000)
                except:
                    # Check if we're no longer on login page and on Freed.ai domain
                    try:
                        self.page.wait_for_url(lambda url: "getfreed.ai" in url.lower() and "login" not in url.lower(), timeout=15000)
                    except:
                        # Final check: just verify we're not on login page
                        self.page.wait_for_url(lambda url: "login" not in url.lower(), timeout=15000)

            logger.info(f"Successfully logged into source application - URL: {self.page.url}")
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
            # Check for logged-in state using multiple possible indicators
            # Try common dashboard or user interface elements
            self.page.wait_for_selector(
                '[data-testid*="dashboard"], .dashboard, #dashboard, '
                '[data-testid*="user"], .user-menu, .profile, '
                '[data-testid*="menu"], .main-content, '
                '.app-content, .workspace',
                timeout=3000
            )
            return True
        except:
            # If none of the above selectors are found, check if we're still on login page
            try:
                current_url = self.page.url
                return "login" not in current_url.lower()
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
