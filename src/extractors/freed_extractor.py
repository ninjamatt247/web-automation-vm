"""Extract patient records from Freed.ai."""
from typing import List, Dict, Any, Optional
from playwright.sync_api import Page
from src.utils.logger import logger
from datetime import datetime, timedelta
import time
import json
from pathlib import Path


class FreedExtractor:
    """Extract patient records from Freed.ai."""

    def __init__(self, page: Page, days_back: int = 1):
        """Initialize Freed.ai extractor.

        Args:
            page: Playwright page instance (authenticated to Freed.ai)
            days_back: Number of days back to fetch records
        """
        self.page = page
        self.days_back = days_back
        self.records: List[Dict[str, Any]] = []

    def navigate_to_records(self) -> bool:
        """Navigate to the patient records page.

        Returns:
            bool: True if navigation successful
        """
        try:
            logger.info("Navigating to records page...")

            # Try to find and click the records/notes link
            # Based on the screenshot, it looks like we're already on a notes page
            # But let's make sure we're on the right page

            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")

            # If we're not on the records page, navigate there
            if "record" not in current_url.lower():
                # Try clicking a navigation link
                try:
                    self.page.click('a[href*="record"], a:has-text("Records"), a:has-text("Notes")', timeout=5000)
                    time.sleep(2)
                except:
                    logger.warning("Could not find records navigation link")

            # Wait for the page to load
            time.sleep(2)

            logger.info("Successfully navigated to records page")
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to records page: {e}")
            return False

    def get_patient_list(self) -> List[Dict[str, str]]:
        """Get list of patient records from the last N days.

        Returns:
            List of patient records with basic info (name, date, element selector)
        """
        try:
            logger.info(f"Fetching patient list from last {self.days_back} day(s)...")

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.days_back)
            logger.info(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")

            # Wait for patient list to load
            # Based on screenshot, patients are likely in a list or grid
            time.sleep(2)

            # Extract patient list using JavaScript
            # Updated for Freed.ai Material-UI structure
            patient_list = self.page.evaluate("""() => {
                const patients = [];

                // Find all visit/patient items using Material-UI data-testid
                const patientElements = document.querySelectorAll('[data-testid="visit-item-button"]');

                patientElements.forEach((element, index) => {
                    // Extract patient name from MUI structure
                    const nameElement = element.querySelector('[data-testid="VisitListItem-patientName"] .MuiListItemText-primary');
                    const name = nameElement ? nameElement.textContent.trim() : `Patient ${index + 1}`;

                    // Extract date/time from visit-duration
                    const dateElement = element.querySelector('[data-testid="visit-duration"]');
                    const dateText = dateElement ? dateElement.textContent.trim() : '';

                    // Extract summary/preview from pulse_body-medium
                    const summaryElement = element.querySelector('.MuiTypography-pulse_body-medium');
                    const summary = summaryElement ? summaryElement.textContent.trim() : '';

                    // Store element index for clicking later
                    element.setAttribute('data-patient-index', index);

                    patients.push({
                        name: name,
                        date: dateText,
                        summary: summary,
                        index: index
                    });
                });

                return patients;
            }""")

            logger.info(f"Found {len(patient_list)} potential patient records")

            # Filter by date if we can parse the dates
            filtered_patients = []
            for patient in patient_list:
                # Try to parse the date - this may need adjustment based on actual date format
                try:
                    # Common date formats to try
                    date_str = patient['date']

                    # If date contains today/yesterday or relative time, include it
                    if any(word in date_str.lower() for word in ['today', 'yesterday', 'hour', 'min', 'ago']):
                        filtered_patients.append(patient)
                        continue

                    # Try parsing absolute dates
                    # Freed.ai seems to use format like "10/31/25 1:13pm"
                    for fmt in ['%m/%d/%y', '%m/%d/%Y', '%Y-%m-%d']:
                        try:
                            # Extract just the date part
                            date_part = date_str.split()[0]
                            patient_date = datetime.strptime(date_part, fmt)

                            if patient_date >= cutoff_date:
                                filtered_patients.append(patient)
                                break
                        except:
                            continue

                except Exception as e:
                    logger.warning(f"Could not parse date for {patient['name']}: {e}")
                    # Include it anyway to be safe
                    filtered_patients.append(patient)

            logger.info(f"Filtered to {len(filtered_patients)} patients from last {self.days_back} day(s)")
            return filtered_patients

        except Exception as e:
            logger.error(f"Failed to get patient list: {e}")
            return []

    def extract_patient_note(self, patient_index: int, patient_name: str = None, list_date: str = None) -> Optional[Dict[str, Any]]:
        """Click into a patient and extract the full detailed note.

        Args:
            patient_index: Index of the patient element to click
            patient_name: Patient name from the list (optional, used as fallback)
            list_date: Date extracted from the list view (primary source)

        Returns:
            Dictionary containing patient note data, or None if extraction fails
        """
        try:
            logger.info(f"Extracting note for patient index {patient_index}...")

            # Click the patient element
            self.page.click(f'[data-patient-index="{patient_index}"]', timeout=10000)
            logger.info("Clicked patient record")

            # Wait for detail page to load
            time.sleep(2)

            # Extract the full note from the detail page
            note_data = self.page.evaluate("""() => {
                // Extract date/time
                const dateElement = document.querySelector('[class*="date"], [class*="time"], time');
                const visitDate = dateElement ? dateElement.textContent.trim() : '';

                // Extract note sections
                // Look for Visit Summary, Assessment, Plan, etc.
                const sections = {};

                // Method 1: Look for labeled sections
                const sectionHeaders = document.querySelectorAll('h2, h3, h4, [class*="section"], [class*="header"]');
                sectionHeaders.forEach(header => {
                    const sectionTitle = header.textContent.trim();
                    // Find the content after this header
                    let content = '';
                    let nextElement = header.nextElementSibling;

                    while (nextElement && !['H1', 'H2', 'H3', 'H4'].includes(nextElement.tagName)) {
                        content += nextElement.textContent.trim() + '\\n';
                        nextElement = nextElement.nextElementSibling;
                    }

                    if (content) {
                        sections[sectionTitle] = content.trim();
                    }
                });

                // Method 2: Get all text content as fallback
                const mainContent = document.querySelector('main, [role="main"], .content, .note-content, article');
                const fullText = mainContent ? mainContent.textContent.trim() : document.body.textContent.trim();

                return {
                    visit_date: visitDate,
                    sections: sections,
                    full_text: fullText,
                    extracted_at: new Date().toISOString()
                };
            }""")

            # Use the patient name from the list (more reliable than extracting from detail page)
            if patient_name:
                note_data['patient_name'] = patient_name
            else:
                note_data['patient_name'] = 'Unknown Patient'

            # Use list date as primary source (most reliable)
            if list_date:
                note_data['visit_date'] = list_date
                logger.info(f"Using list date: {list_date}")

            # Extract visit date from the raw text if not already captured
            elif not note_data.get('visit_date') and note_data.get('full_text'):
                # Look for "Saved Oct 30" or similar pattern at the beginning
                import re
                from datetime import datetime

                date_match = re.search(r'Saved\s+([A-Za-z]+\s+\d{1,2})', note_data['full_text'])
                if date_match:
                    try:
                        # Parse "Oct 30" and add current year
                        date_str = date_match.group(1)
                        current_year = datetime.now().year
                        full_date_str = f"{date_str} {current_year}"
                        parsed_date = datetime.strptime(full_date_str, '%b %d %Y')
                        note_data['visit_date'] = parsed_date.strftime('%m/%d/%Y')
                        logger.info(f"Extracted visit date: {note_data['visit_date']}")
                    except Exception as e:
                        logger.warning(f"Could not parse date '{date_str}': {e}")
                        note_data['visit_date'] = date_match.group(1)  # Store raw if parsing fails

            logger.info(f"Successfully extracted note for {note_data['patient_name']}")

            # Go back to list
            self.page.go_back()
            time.sleep(1)

            return note_data

        except Exception as e:
            logger.error(f"Failed to extract patient note: {e}")

            # Try to go back to list
            try:
                self.page.go_back()
                time.sleep(1)
            except:
                pass

            return None

    def extract_all_records(self) -> List[Dict[str, Any]]:
        """Extract all patient records from the last N days.

        Returns:
            List of extracted patient records
        """
        logger.info("Starting full record extraction...")

        # Navigate to records page
        if not self.navigate_to_records():
            logger.error("Failed to navigate to records page")
            return []

        # Get patient list
        patients = self.get_patient_list()

        if not patients:
            logger.warning("No patients found")
            return []

        # Extract each patient's full note
        extracted_records = []

        for i, patient in enumerate(patients):
            patient_name = patient.get('name', f'Patient {i+1}')
            list_date = patient.get('date', '')
            logger.info(f"Processing patient {i+1}/{len(patients)}: {patient_name} (Date: {list_date})")

            try:
                # Pass the patient name AND date from the list to avoid extraction issues
                note_data = self.extract_patient_note(
                    patient['index'],
                    patient_name=patient_name,
                    list_date=list_date
                )

                if note_data:
                    # Add list info to note data
                    note_data['list_summary'] = patient['summary']
                    extracted_records.append(note_data)
                else:
                    logger.warning(f"Failed to extract note for {patient_name}")

                # Small delay between patients
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error processing patient {patient_name}: {e}")
                continue

        logger.info(f"Extraction complete: {len(extracted_records)}/{len(patients)} records extracted")
        self.records = extracted_records
        return extracted_records

    def save_records(self, output_dir: str = "/app/data/temp") -> List[str]:
        """Save extracted records as individual JSON files.

        Args:
            output_dir: Directory to save files

        Returns:
            List of file paths
        """
        if not self.records:
            logger.warning("No records to save")
            return []

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i, record in enumerate(self.records):
            try:
                # Create filename from patient name and date
                patient_name = record.get('patient_name', f'patient_{i+1}')
                safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).strip()
                safe_name = safe_name.replace(' ', '_')

                filename = f"{timestamp}_{safe_name}.json"
                filepath = output_path / filename

                # Save as JSON
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(record, f, indent=2, ensure_ascii=False)

                logger.info(f"Saved record: {filepath}")
                saved_files.append(str(filepath))

            except Exception as e:
                logger.error(f"Failed to save record {i+1}: {e}")

        logger.info(f"Saved {len(saved_files)} records to {output_dir}")
        return saved_files
