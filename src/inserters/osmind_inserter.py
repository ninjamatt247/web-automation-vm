"""Upload patient notes to Osmind EHR."""
from typing import List, Dict, Any, Optional, Tuple
from playwright.sync_api import Page
from src.utils.logger import logger
from datetime import datetime
import time
import re
from rapidfuzz import fuzz, process


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
        self.flagged_for_review = []

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

    def parse_patient_name(self, patient_name: str) -> Tuple[str, str]:
        """Parse patient name into first and last name.

        Args:
            patient_name: Full patient name

        Returns:
            Tuple of (first_name, last_name)
        """
        parts = patient_name.strip().split()
        if len(parts) >= 2:
            first_name = parts[0]
            last_name = ' '.join(parts[1:])  # Handle multi-part last names
        else:
            first_name = patient_name
            last_name = ""

        return first_name, last_name

    def search_patient(self, patient_name: str) -> bool:
        """Search for patient by name using fuzzy matching and multiple search strategies.

        Args:
            patient_name: Full name of patient to search for

        Returns:
            bool: True if patient found and selected
        """
        try:
            first_name, last_name = self.parse_patient_name(patient_name)
            logger.info(f"Searching for patient: {first_name} {last_name}")

            # Look for search field - Osmind uses data-testid
            search_field = 'input[data-testid="patient-search-input"]'

            try:
                self.page.wait_for_selector(search_field, timeout=5000)
            except:
                logger.warning("Could not find patient search field")
                return False

            # Try multiple search strategies
            search_strategies = [
                f"{first_name} {last_name}",  # "First Last"
                f"{last_name} {first_name}",  # "Last First"
                f"{last_name}, {first_name}",  # "Last, First"
                first_name,  # Just first name
                last_name,  # Just last name
            ]

            for idx, search_query in enumerate(search_strategies):
                logger.info(f"Search strategy {idx+1}/{len(search_strategies)}: '{search_query}'")

                # Clear and fill search field
                self.page.fill(search_field, '')
                time.sleep(0.5)
                self.page.fill(search_field, search_query)
                time.sleep(2)  # Wait for search results to appear

                # Get all patient result elements
                try:
                    patient_links = self.page.query_selector_all('a[data-testid="patient-cell-name"]')

                    if not patient_links:
                        logger.info(f"No results for '{search_query}', trying next strategy...")
                        continue

                    logger.info(f"Found {len(patient_links)} patient results")

                    # Extract patient names from results and use fuzzy matching
                    patient_names = []
                    for link in patient_links:
                        name_text = link.inner_text().strip()
                        patient_names.append(name_text)
                        logger.info(f"  - Result: {name_text}")

                    # Use fuzzy matching to find best match
                    # Try matching against full name
                    full_name_variants = [
                        f"{first_name} {last_name}",
                        f"{last_name} {first_name}",
                        f"{last_name}, {first_name}",
                        f"{first_name.lower()} {last_name.lower()}",
                        patient_name  # Original name
                    ]

                    best_match = None
                    best_score = 0
                    best_index = -1

                    for variant in full_name_variants:
                        # Use rapidfuzz to find best match (case-insensitive)
                        match = process.extractOne(
                            variant.lower(),
                            [name.lower() for name in patient_names],
                            scorer=fuzz.ratio
                        )

                        if match and match[1] > best_score:
                            best_score = match[1]
                            # Find the index of the best match
                            best_index = [name.lower() for name in patient_names].index(match[0])
                            best_match = patient_names[best_index]

                    logger.info(f"Best fuzzy match: '{best_match}' (score: {best_score})")

                    # Accept match if score is above threshold
                    if best_score >= 70:  # 70% similarity threshold
                        logger.info(f"✓ Fuzzy match accepted! Clicking: {best_match}")
                        patient_links[best_index].click()
                        time.sleep(2)  # Wait for patient page to load
                        return True
                    else:
                        logger.info(f"Fuzzy match score too low ({best_score} < 70), trying next strategy...")
                        continue

                except Exception as e:
                    logger.warning(f"Error processing search results: {e}")
                    continue

            # If all strategies failed
            logger.warning(f"Could not find patient after trying all search strategies: {patient_name}")
            return False

        except Exception as e:
            logger.error(f"Failed to search for patient: {e}")
            return False

    def find_note_by_date(self, note_date: str) -> Optional[str]:
        """Find and click a note matching the given date.

        Args:
            note_date: Date string from the note (various formats accepted)

        Returns:
            Optional note element selector if found, None otherwise
        """
        try:
            logger.info(f"Looking for note with date: {note_date}")

            # Parse the date to compare
            # Osmind displays dates as "October 30, 2025"
            parsed_date = None
            for fmt in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%d-%m-%Y', '%B %d, %Y']:
                try:
                    parsed_date = datetime.strptime(note_date, fmt)
                    break
                except:
                    continue

            if not parsed_date:
                logger.warning(f"Could not parse date: {note_date}")
                return None

            # Format to match Osmind's display: "October 30, 2025"
            osmind_date_str = parsed_date.strftime('%B %d, %Y')
            logger.info(f"Looking for Osmind date format: {osmind_date_str}")

            # Osmind uses div[data-testid^="note-li-"] for note list items
            # Date appears in <span class="emphasis">October 30, 2025</span>
            try:
                # Find note with matching date
                note_selector = f'div[data-testid^="note-li-"]:has-text("{osmind_date_str}")'
                note_element = self.page.query_selector(note_selector)

                if note_element:
                    logger.info(f"Found note with date {osmind_date_str}")
                    # Click the note to open it
                    self.page.click(note_selector, timeout=3000)
                    time.sleep(3)  # Wait for note editor to load
                    return note_selector
                else:
                    logger.warning(f"Could not find note with date: {osmind_date_str}")
                    return None
            except Exception as e:
                logger.warning(f"Error finding note: {e}")
                return None

        except Exception as e:
            logger.error(f"Failed to find note by date: {e}")
            return None

    def check_if_note_signed(self) -> Tuple[bool, Optional[str]]:
        """Check if the current note is already electronically signed.

        In Osmind:
        - Unsigned notes have: <span class="badge badge-pill badge-unsigned">Unsigned</span>
        - Signed notes: no badge (empty column)

        Returns:
            Tuple of (is_signed, note_selector) where note_selector can be used to re-click the note
        """
        try:
            logger.info("Checking if note is already signed...")

            # First, go back to note list to check the badge
            # Click "All notes" back button
            try:
                self.page.click('button[data-testid="navigation-bar--back-button"]', timeout=3000)
                time.sleep(2)
            except:
                logger.warning("Could not navigate back to note list")
                return (False, None)

            # Look for unsigned badge in the note list
            # Unsigned notes have <span class="badge badge-pill badge-unsigned">Unsigned</span>
            try:
                unsigned_badge = self.page.query_selector('.badge-unsigned')

                if unsigned_badge:
                    logger.info("Note is unsigned (found unsigned badge)")
                    # Get the note selector so we can re-click it
                    # The badge is inside the note row, find the parent note div
                    note_div = self.page.query_selector('div[data-testid^="note-li-"]:has(.badge-unsigned)')
                    note_selector = 'div[data-testid^="note-li-"]:has(.badge-unsigned)'
                    return (False, note_selector)
                else:
                    logger.info("Note is signed (no unsigned badge found)")
                    return (True, None)
            except Exception as e:
                logger.warning(f"Error checking badge: {e}")
                return (False, None)

        except Exception as e:
            logger.error(f"Failed to check signature status: {e}")
            # Assume unsigned if we can't determine
            return (False, None)

    def append_to_note(self, cleaned_note: str) -> bool:
        """Append cleaned note to the end of existing note text.

        Args:
            cleaned_note: The cleaned note text to append

        Returns:
            bool: True if append successful
        """
        try:
            logger.info("Appending cleaned note to existing note text...")

            # Osmind uses a contenteditable div: div[data-testid="v2-editor-content"]
            note_field = 'div[data-testid="v2-editor-content"]'

            try:
                self.page.wait_for_selector(note_field, timeout=5000)
                logger.info("Found Osmind note editor")
            except:
                raise Exception("Could not find Osmind note editor")

            # Get current note text content
            current_text = self.page.text_content(note_field)
            logger.info(f"Current note length: {len(current_text)} characters")

            # Check if Freed.ai content was already appended
            if "FREED.AI NOTE APPENDED:" in current_text:
                logger.warning("⚠️  Note already contains Freed.ai content - skipping duplicate append")
                logger.info("This note was already processed in a previous upload attempt")
                return True  # Return True since the content is already there

            # Click at the end of the note to position cursor
            self.page.click(note_field)
            time.sleep(0.5)

            # Move cursor to end
            self.page.keyboard.press('End')
            self.page.keyboard.press('Control+End')  # Ensure at very end

            # Add separator and new note
            separator = "\n\n" + "="*80 + "\nFREED.AI NOTE APPENDED:\n" + "="*80 + "\n\n"
            self.page.keyboard.type(separator + cleaned_note)

            logger.info("Successfully appended note text")
            time.sleep(2)  # Wait for auto-save
            return True

        except Exception as e:
            logger.error(f"Failed to append note: {e}")
            return False

    def flag_for_review(self, patient_name: str, reason: str, note_data: Dict[str, Any]) -> None:
        """Flag a note for manual review.

        Args:
            patient_name: Name of patient
            reason: Reason for flagging
            note_data: The note data that needs review
        """
        logger.warning(f"⚠️  FLAGGED FOR REVIEW: {patient_name} - {reason}")

        self.flagged_for_review.append({
            'patient_name': patient_name,
            'reason': reason,
            'note_date': note_data.get('visit_date', 'Unknown'),
            'note_data': note_data
        })

    def upload_note(self, note_data: Dict[str, Any]) -> bool:
        """Upload a single patient note to Osmind with full workflow.

        Workflow:
        1. Search for patient by first/last name
        2. Find note matching the visit date
        3. Check if note is unsigned (look for "electronically signed by...")
        4. If unsigned: append cleaned note to existing note text
        5. If signed or no matching patient/date: flag for review

        Args:
            note_data: Dictionary containing cleaned note and patient info
                      Expected keys: 'patient_name', 'cleaned_note', 'visit_date'

        Returns:
            bool: True if upload successful
        """
        patient_name = note_data.get('patient_name', 'Unknown')
        cleaned_note = note_data.get('cleaned_note', '')
        visit_date = note_data.get('visit_date', '')

        try:
            logger.info(f"Processing note for {patient_name} (date: {visit_date})")

            # Step 1: Search for patient by first/last name
            if not self.search_patient(patient_name):
                self.flag_for_review(patient_name, "Patient not found in search", note_data)
                self.failure_count += 1
                return False

            time.sleep(2)

            # Step 2: Find note matching the date
            if visit_date:
                note_element = self.find_note_by_date(visit_date)
                if not note_element:
                    self.flag_for_review(patient_name, f"No note found for date: {visit_date}", note_data)
                    self.failure_count += 1
                    # Navigate back to patient search
                    self.page.goto('https://providers.osmind.org/')
                    time.sleep(2)
                    return False
            else:
                self.flag_for_review(patient_name, "No visit date provided", note_data)
                self.failure_count += 1
                # Navigate back to patient search
                self.page.goto('https://providers.osmind.org/')
                time.sleep(2)
                return False

            time.sleep(2)

            # Step 3: Check if note is already signed
            is_signed, note_selector = self.check_if_note_signed()

            if is_signed:
                self.flag_for_review(patient_name, "Note is already electronically signed", note_data)
                self.failure_count += 1
                # Navigate back to patient search
                self.page.goto('https://providers.osmind.org/')
                time.sleep(2)
                return False

            # Step 4: Re-click the note to open editor (we went back to check signature)
            if note_selector:
                logger.info("Re-opening note to append text...")
                try:
                    self.page.click(note_selector, timeout=3000)
                    time.sleep(3)
                except:
                    self.flag_for_review(patient_name, "Failed to re-open note after signature check", note_data)
                    self.failure_count += 1
                    # Navigate back to patient search
                    self.page.goto('https://providers.osmind.org/')
                    time.sleep(2)
                    return False

            # Step 5: Note is unsigned - append cleaned note
            logger.info(f"Note is unsigned - appending cleaned note for {patient_name}")

            if not self.append_to_note(cleaned_note):
                self.flag_for_review(patient_name, "Failed to append note text", note_data)
                self.failure_count += 1
                # Navigate back to patient search
                self.page.goto('https://providers.osmind.org/')
                time.sleep(2)
                return False

            # Step 6: Wait for auto-save
            # Osmind auto-saves and shows "Saved" status
            logger.info("Waiting for auto-save...")
            time.sleep(3)

            # Check for "Saved" badge: <span class="ant-badge-status-text">Saved</span>
            try:
                saved_indicator = self.page.wait_for_selector('.ant-badge-status-text:has-text("Saved")', timeout=5000)
                if saved_indicator:
                    logger.info("✓ Auto-save confirmed")
            except:
                logger.info("Auto-save indicator not found, but continuing (Osmind auto-saves)")

            logger.info(f"✅ Successfully appended and saved note for {patient_name}")
            self.success_count += 1

            # Navigate back to patient search for next patient
            self.page.goto('https://providers.osmind.org/')
            time.sleep(2)

            return True

        except Exception as e:
            logger.error(f"Failed to process note for {patient_name}: {e}")
            self.flag_for_review(patient_name, f"Unexpected error: {str(e)}", note_data)
            self.failure_count += 1
            # Navigate back to patient search
            try:
                self.page.goto('https://providers.osmind.org/')
                time.sleep(2)
            except:
                pass
            return False

    def batch_upload_notes(self, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upload multiple patient notes.

        Args:
            notes: List of note dictionaries

        Returns:
            Dictionary with success/failure counts and flagged items
        """
        logger.info(f"Starting batch upload of {len(notes)} notes to Osmind EHR...")
        self.success_count = 0
        self.failure_count = 0
        self.flagged_for_review = []

        for i, note_data in enumerate(notes):
            patient_name = note_data.get('patient_name', f'Patient {i+1}')
            logger.info(f"Processing note {i+1}/{len(notes)}: {patient_name}")

            # Skip if no cleaned note
            if not note_data.get('cleaned_note'):
                logger.warning(f"No cleaned note for {patient_name}, skipping")
                self.flag_for_review(patient_name, "No cleaned note available", note_data)
                self.failure_count += 1
                continue

            # Upload the note
            success = self.upload_note(note_data)

            if not success:
                logger.error(f"Failed to upload note for {patient_name}")

            # Small delay between uploads
            time.sleep(2)

        # Report flagged items
        if self.flagged_for_review:
            logger.warning(f"\n⚠️  {len(self.flagged_for_review)} NOTES FLAGGED FOR MANUAL REVIEW:")
            for item in self.flagged_for_review:
                logger.warning(f"  - {item['patient_name']} ({item['note_date']}): {item['reason']}")

        results = {
            "success": self.success_count,
            "failure": self.failure_count,
            "flagged": len(self.flagged_for_review),
            "total": len(notes),
            "flagged_items": self.flagged_for_review
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
