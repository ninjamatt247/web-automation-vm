"""Data extraction from source web application."""
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
from src.utils.logger import logger
from pathlib import Path
import json
import csv
from datetime import datetime


class DataExtractor:
    """Extract data from source web application."""

    def __init__(self, page: Page):
        """Initialize data extractor.

        Args:
            page: Playwright page instance (authenticated)
        """
        self.page = page
        self.extracted_data: List[Dict[str, Any]] = []

    def extract_table_data(self, table_selector: str = "table") -> List[Dict[str, Any]]:
        """Extract data from HTML table.

        Args:
            table_selector: CSS selector for the table

        Returns:
            List of dictionaries containing row data
        """
        try:
            logger.info(f"Extracting table data from selector: {table_selector}")

            # Wait for table to be visible
            self.page.wait_for_selector(table_selector, timeout=10000)

            # Extract table data using JavaScript
            table_data = self.page.evaluate('''(selector) => {
                const table = document.querySelector(selector);
                if (!table) return [];

                const headers = Array.from(table.querySelectorAll('thead th'))
                    .map(th => th.textContent.trim());

                const rows = Array.from(table.querySelectorAll('tbody tr'));
                return rows.map(row => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    const rowData = {};
                    cells.forEach((cell, index) => {
                        rowData[headers[index] || `column_${index}`] = cell.textContent.trim();
                    });
                    return rowData;
                });
            }''', table_selector)

            self.extracted_data.extend(table_data)
            logger.info(f"Extracted {len(table_data)} rows from table")
            return table_data

        except Exception as e:
            logger.error(f"Failed to extract table data: {e}")
            return []

    def extract_form_data(self, form_selector: str) -> Dict[str, Any]:
        """Extract data from a form.

        Args:
            form_selector: CSS selector for the form

        Returns:
            Dictionary containing form field data
        """
        try:
            logger.info(f"Extracting form data from selector: {form_selector}")

            # Extract form data using JavaScript
            form_data = self.page.evaluate('''(selector) => {
                const form = document.querySelector(selector);
                if (!form) return {};

                const formData = {};
                const inputs = form.querySelectorAll('input, textarea, select');

                inputs.forEach(input => {
                    const name = input.name || input.id;
                    if (name) {
                        if (input.type === 'checkbox') {
                            formData[name] = input.checked;
                        } else if (input.type === 'radio') {
                            if (input.checked) {
                                formData[name] = input.value;
                            }
                        } else {
                            formData[name] = input.value;
                        }
                    }
                });

                return formData;
            }''', form_selector)

            logger.info(f"Extracted {len(form_data)} fields from form")
            return form_data

        except Exception as e:
            logger.error(f"Failed to extract form data: {e}")
            return {}

    def extract_custom_data(self, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract data from custom selectors.

        Args:
            selectors: Dictionary mapping field names to CSS selectors

        Returns:
            Dictionary containing extracted data
        """
        try:
            logger.info(f"Extracting custom data with {len(selectors)} selectors")

            data = {}
            for field_name, selector in selectors.items():
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        data[field_name] = element.inner_text().strip()
                    else:
                        logger.warning(f"Selector not found for field: {field_name}")
                        data[field_name] = None
                except Exception as e:
                    logger.error(f"Error extracting field {field_name}: {e}")
                    data[field_name] = None

            logger.info(f"Extracted {len(data)} custom fields")
            return data

        except Exception as e:
            logger.error(f"Failed to extract custom data: {e}")
            return {}

    def download_file(self, download_button_selector: str, filename: Optional[str] = None) -> Optional[str]:
        """Download a file from the page.

        Args:
            download_button_selector: Selector for download button
            filename: Optional custom filename

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            logger.info(f"Initiating file download")

            # Set up download handler
            with self.page.expect_download() as download_info:
                self.page.click(download_button_selector)

            download = download_info.value

            # Generate filename if not provided
            if not filename:
                filename = download.suggested_filename

            # Save to temp directory
            download_path = Path(f"/app/data/temp/{filename}")
            download.save_as(download_path)

            logger.info(f"File downloaded successfully: {download_path}")
            return str(download_path)

        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None

    def save_to_json(self, filename: Optional[str] = None) -> str:
        """Save extracted data to JSON file.

        Args:
            filename: Optional custom filename

        Returns:
            Path to saved JSON file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extracted_data_{timestamp}.json"

        filepath = Path(f"/app/data/temp/{filename}")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.extracted_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Data saved to JSON: {filepath}")
        return str(filepath)

    def save_to_csv(self, filename: Optional[str] = None) -> str:
        """Save extracted data to CSV file.

        Args:
            filename: Optional custom filename

        Returns:
            Path to saved CSV file
        """
        if not self.extracted_data:
            logger.warning("No data to save")
            return ""

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extracted_data_{timestamp}.csv"

        filepath = Path(f"/app/data/temp/{filename}")

        # Get all unique keys from all dictionaries
        fieldnames = set()
        for item in self.extracted_data:
            fieldnames.update(item.keys())

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
            writer.writeheader()
            writer.writerows(self.extracted_data)

        logger.info(f"Data saved to CSV: {filepath}")
        return str(filepath)

    def clear_data(self):
        """Clear extracted data."""
        self.extracted_data = []
        logger.info("Extracted data cleared")
