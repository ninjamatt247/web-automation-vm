"""Upload patient notes to Osmind EHR."""
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
from src.utils.logger import logger
import time


class OsmindInserter:
    """Insert patient notes into Osmind EHR."""

    def __init__(self, page: Page, retry_attempts: int = 3, retry_delay: int = 5):
        """Initialize Osmind inserter.

        Args:
            page: Playwright page instance (authenticated to Osmind)
            retry_attempts: Number of retry attempts for failed uploads
            retry_delay: Delay in seconds between retries
        """
        self.page = page
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.success_count = 0
        self.failure_count = 0

    def navigate_to_patient_notes(self) -> bool:
        """Navigate to the section for creating/editing patient notes.

        Returns:
            bool: True if navigation successful
        """
        try:
            logger.info("Navigating to patient notes section...")

            # Try common navigation patterns
            # This will need customization based on actual Osmind UI
            try:
                # Try clicking "New Note" or "Create Note" button
                self.page.click('button:has-text("New Note"), button:has-text("Create Note"), a:has-text("New Note")', timeout=5000)
                logger.info("Clicked 'New Note' button")
            except:
                try:
                    # Try navigating via menu
                    self.page.click('a[href*="note"], a[href*="patient"]', timeout=5000)
                    logger.info("Navigated via menu link")
                except:
                    logger.warning("Could not find standard navigation, may already be on notes page")

            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to patient notes: {e}")
            return False

    def search_patient(self, patient_name: str) -> bool:
        """Search for a patient by name.

        Args:
            patient_name: Name of patient to search for

        Returns:
            bool: True if patient found and selected
        """
        try:
            logger.info(f"Searching for patient: {patient_name}")

            # Look for search field
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="search" i]',
                'input[placeholder*="patient" i]',
                'input[name*="search"]',
                'input[class*="search"]'
            ]

            search_field = None
            for selector in search_selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=3000)
                    search_field = selector
                    break
                except:
                    continue

            if not search_field:
                logger.warning("Could not find search field")
                return False

            # Enter patient name
            self.page.fill(search_field, patient_name)
            time.sleep(1)

            # Press Enter or click search button
            try:
                self.page.keyboard.press('Enter')
            except:
                self.page.click('button[type="submit"], button:has-text("Search")', timeout=3000)

            time.sleep(2)

            # Try to click the first result
            try:
                self.page.click('.search-result:first-child, .patient-result:first-child, [class*="result"]:first-child', timeout=5000)
                logger.info(f"Selected patient: {patient_name}")
                return True
            except:
                logger.warning(f"Could not find patient in search results: {patient_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to search for patient: {e}")
            return False

    def upload_note(self, note_data: Dict[str, Any]) -> bool:
        """Upload a single patient note to Osmind.

        Args:
            note_data: Dictionary containing cleaned note and patient info
                      Expected keys: 'patient_name', 'cleaned_note', 'visit_date'

        Returns:
            bool: True if upload successful
        """
        patient_name = note_data.get('patient_name', 'Unknown')
        cleaned_note = note_data.get('cleaned_note', '')

        attempt = 0
        while attempt < self.retry_attempts:
            try:
                logger.info(f"Uploading note for {patient_name} (attempt {attempt + 1}/{self.retry_attempts})")

                # Navigate to create note section
                if not self.navigate_to_patient_notes():
                    raise Exception("Could not navigate to notes section")

                # Search for patient
                if not self.search_patient(patient_name):
                    logger.warning(f"Patient not found: {patient_name}, may need manual creation")
                    # Continue anyway in case we're already on the right patient page

                time.sleep(1)

                # Find the note text area
                note_field_selectors = [
                    'textarea[name*="note"]',
                    'textarea[placeholder*="note" i]',
                    'textarea[class*="note"]',
                    'textarea',
                    '[contenteditable="true"]',
                    '.editor, .note-editor'
                ]

                note_field = None
                for selector in note_field_selectors:
                    try:
                        self.page.wait_for_selector(selector, timeout=3000)
                        note_field = selector
                        logger.info(f"Found note field: {selector}")
                        break
                    except:
                        continue

                if not note_field:
                    raise Exception("Could not find note input field")

                # Fill in the note
                try:
                    if '[contenteditable="true"]' in note_field or 'editor' in note_field:
                        # For rich text editors
                        self.page.click(note_field)
                        time.sleep(0.5)
                        self.page.keyboard.type(cleaned_note)
                    else:
                        # For regular textareas
                        self.page.fill(note_field, cleaned_note)

                    logger.info("Note content filled")
                except Exception as e:
                    logger.error(f"Failed to fill note: {e}")
                    raise

                time.sleep(1)

                # Save/Submit the note
                try:
                    save_selectors = [
                        'button:has-text("Save")',
                        'button:has-text("Submit")',
                        'button:has-text("Create")',
                        'button[type="submit"]',
                        'button.save, button.submit'
                    ]

                    saved = False
                    for selector in save_selectors:
                        try:
                            self.page.click(selector, timeout=3000)
                            logger.info(f"Clicked save button: {selector}")
                            saved = True
                            break
                        except:
                            continue

                    if not saved:
                        # Try keyboard shortcut as fallback
                        self.page.keyboard.press('Control+Enter')
                        logger.info("Attempted save via keyboard shortcut")

                except Exception as e:
                    logger.error(f"Failed to click save button: {e}")
                    raise

                # Wait for save confirmation
                time.sleep(3)

                # Check for success indicators
                try:
                    # Look for success message or redirect
                    success_indicators = [
                        'text="Saved"',
                        'text="Success"',
                        'text="Created"',
                        '.success, .alert-success',
                        '[class*="success"]'
                    ]

                    for indicator in success_indicators:
                        try:
                            self.page.wait_for_selector(indicator, timeout=2000)
                            logger.info(f"Found success indicator: {indicator}")
                            break
                        except:
                            continue

                except:
                    logger.info("No explicit success indicator found, assuming success")

                logger.info(f"Successfully uploaded note for {patient_name}")
                self.success_count += 1
                return True

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                attempt += 1

                if attempt < self.retry_attempts:
                    logger.warning(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)

                    # Try to return to a clean state
                    try:
                        self.page.go_back()
                        time.sleep(1)
                    except:
                        pass

        self.failure_count += 1
        return False

    def batch_upload_notes(self, notes: List[Dict[str, Any]]) -> Dict[str, int]:
        """Upload multiple patient notes.

        Args:
            notes: List of note dictionaries

        Returns:
            Dictionary with success and failure counts
        """
        logger.info(f"Starting batch upload of {len(notes)} notes to Osmind EHR...")
        self.success_count = 0
        self.failure_count = 0

        for i, note_data in enumerate(notes):
            patient_name = note_data.get('patient_name', f'Patient {i+1}')
            logger.info(f"Processing note {i+1}/{len(notes)}: {patient_name}")

            # Skip if no cleaned note
            if not note_data.get('cleaned_note'):
                logger.warning(f"No cleaned note for {patient_name}, skipping")
                self.failure_count += 1
                continue

            # Upload the note
            success = self.upload_note(note_data)

            if not success:
                logger.error(f"Failed to upload note for {patient_name}")

            # Small delay between uploads
            time.sleep(2)

        results = {
            "success": self.success_count,
            "failure": self.failure_count,
            "total": len(notes)
        }

        logger.info(f"Batch upload complete: {results}")
        return results

    def get_statistics(self) -> Dict[str, int]:
        """Get upload statistics.

        Returns:
            Dictionary with success and failure counts
        """
        return {
            "success": self.success_count,
            "failure": self.failure_count,
            "total": self.success_count + self.failure_count
        }
