"""Data insertion into target web application."""
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
from src.utils.logger import logger
from pathlib import Path
import time


class DataInserter:
    """Insert data into target web application."""

    def __init__(self, page: Page, retry_attempts: int = 3, retry_delay: int = 5):
        """Initialize data inserter.

        Args:
            page: Playwright page instance (authenticated)
            retry_attempts: Number of retry attempts for failed insertions
            retry_delay: Delay in seconds between retries
        """
        self.page = page
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.success_count = 0
        self.failure_count = 0

    def fill_form(self, form_data: Dict[str, Any], form_selector: str = "form") -> bool:
        """Fill a form with data.

        Args:
            form_data: Dictionary mapping field names to values
            form_selector: CSS selector for the form

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Filling form with {len(form_data)} fields")

            # Wait for form to be visible
            self.page.wait_for_selector(form_selector, timeout=10000)

            # Fill each field
            for field_name, value in form_data.items():
                try:
                    # Try multiple selector strategies
                    selectors = [
                        f'input[name="{field_name}"]',
                        f'input[id="{field_name}"]',
                        f'textarea[name="{field_name}"]',
                        f'select[name="{field_name}"]',
                    ]

                    filled = False
                    for selector in selectors:
                        if self.page.query_selector(selector):
                            self.page.fill(selector, str(value))
                            filled = True
                            break

                    if not filled:
                        logger.warning(f"Field not found: {field_name}")

                except Exception as e:
                    logger.error(f"Error filling field {field_name}: {e}")

            logger.info("Form filled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to fill form: {e}")
            return False

    def submit_form(self, submit_button_selector: str = 'button[type="submit"]') -> bool:
        """Submit a form.

        Args:
            submit_button_selector: CSS selector for submit button

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Submitting form")

            # Click submit button
            self.page.click(submit_button_selector)

            # Wait for page navigation or success indicator
            time.sleep(2)  # TODO: Replace with proper wait condition

            logger.info("Form submitted successfully")
            self.success_count += 1
            return True

        except Exception as e:
            logger.error(f"Failed to submit form: {e}")
            self.failure_count += 1
            return False

    def insert_table_row(self, row_data: Dict[str, Any], add_button_selector: str) -> bool:
        """Insert a single row into a table.

        Args:
            row_data: Dictionary containing row data
            add_button_selector: Selector for "Add Row" button

        Returns:
            bool: True if successful, False otherwise
        """
        attempt = 0
        while attempt < self.retry_attempts:
            try:
                logger.info(f"Inserting table row (attempt {attempt + 1}/{self.retry_attempts})")

                # Click add row button
                self.page.click(add_button_selector)
                time.sleep(1)

                # Fill row data
                if self.fill_form(row_data):
                    if self.submit_form():
                        self.success_count += 1
                        return True

                attempt += 1
                if attempt < self.retry_attempts:
                    logger.warning(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)

            except Exception as e:
                logger.error(f"Error inserting row: {e}")
                attempt += 1

        self.failure_count += 1
        return False

    def insert_batch(self, data_list: List[Dict[str, Any]], add_button_selector: str,
                    batch_size: int = 10) -> Dict[str, int]:
        """Insert multiple rows in batches.

        Args:
            data_list: List of dictionaries containing row data
            add_button_selector: Selector for "Add Row" button
            batch_size: Number of rows to insert before pausing

        Returns:
            Dictionary with success and failure counts
        """
        logger.info(f"Starting batch insert of {len(data_list)} rows")
        self.success_count = 0
        self.failure_count = 0

        for i, row_data in enumerate(data_list):
            logger.info(f"Processing row {i + 1}/{len(data_list)}")

            self.insert_table_row(row_data, add_button_selector)

            # Pause after each batch
            if (i + 1) % batch_size == 0 and i + 1 < len(data_list):
                logger.info(f"Pausing after batch of {batch_size} rows...")
                time.sleep(3)

        results = {
            "success": self.success_count,
            "failure": self.failure_count,
            "total": len(data_list)
        }

        logger.info(f"Batch insert complete: {results}")
        return results

    def upload_file(self, file_path: str, upload_selector: str) -> bool:
        """Upload a file to the target application.

        Args:
            file_path: Path to file to upload
            upload_selector: Selector for file input element

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Uploading file: {file_path}")

            # Validate file exists
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                return False

            # Set file input
            self.page.set_input_files(upload_selector, file_path)

            # Wait for upload to process
            time.sleep(2)  # TODO: Replace with proper wait condition

            logger.info("File uploaded successfully")
            self.success_count += 1
            return True

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            self.failure_count += 1
            return False

    def click_and_fill(self, click_selector: str, field_mapping: Dict[str, tuple]) -> bool:
        """Click an element and fill fields in the resulting dialog/form.

        Args:
            click_selector: Selector to click to open form
            field_mapping: Dict mapping field names to (selector, value) tuples

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Clicking element to open form")

            # Click to open form/dialog
            self.page.click(click_selector)
            time.sleep(1)

            # Fill fields
            for field_name, (selector, value) in field_mapping.items():
                try:
                    self.page.fill(selector, str(value))
                except Exception as e:
                    logger.error(f"Error filling field {field_name}: {e}")

            logger.info("Form filled successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to click and fill: {e}")
            return False

    def get_statistics(self) -> Dict[str, int]:
        """Get insertion statistics.

        Returns:
            Dictionary with success and failure counts
        """
        return {
            "success": self.success_count,
            "failure": self.failure_count,
            "total": self.success_count + self.failure_count
        }
