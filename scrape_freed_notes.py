#!/usr/bin/env python3
"""
Screen scrape full note content from Freed.ai and upsert to database.
Works from most recent to oldest to prioritize current data.
"""
import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from playwright.sync_api import sync_playwright, Page

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.logger import logger
from utils.config import get_config
from auth.source_auth import SourceAuth
from extractors.freed_extractor import FreedExtractor


class FreedNoteScraper:
    """Scrape full note content from Freed.ai using screen scraping."""

    def __init__(self, db_path: str = None):
        """Initialize scraper with database connection."""
        if db_path is None:
            # Use absolute path to database
            db_path = "/Users/harringhome/web-automation-vm/web-app/backend/medical_notes.db"
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def get_notes_to_scrape(self, limit: int = None) -> List[Dict]:
        """Get notes from database that need full content scraped.

        Args:
            limit: Maximum number of notes to scrape (None = all)

        Returns:
            List of note records ordered by most recent first
        """
        # Get notes where note_text is short (just description) or null
        # Order by visit_date DESC to process most recent first
        query = """
            SELECT
                fn.id,
                fn.patient_id,
                p.name as patient_name,
                fn.visit_date,
                fn.freed_visit_id,
                fn.note_text,
                fn.note_length
            FROM freed_notes fn
            JOIN patients p ON fn.patient_id = p.id
            WHERE fn.note_length < 100 OR fn.note_text IS NULL OR fn.full_text IS NULL
            ORDER BY fn.visit_date DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        self.cursor.execute(query)
        notes = [dict(row) for row in self.cursor.fetchall()]
        logger.info(f"Found {len(notes)} notes needing full content extraction")
        return notes

    def scrape_note_content(self, page: Page, extractor: FreedExtractor,
                           patient_name: str, visit_date: str) -> Optional[Dict[str, Any]]:
        """Scrape full note content using screen scraping.

        Args:
            page: Playwright page instance
            extractor: FreedExtractor instance
            patient_name: Patient name
            visit_date: Visit date string

        Returns:
            Dict with full note content or None if failed
        """
        try:
            logger.info(f"Scraping note for {patient_name} - {visit_date}")

            # Navigate to freed.ai records page
            page.goto("https://secure.getfreed.ai/record", wait_until="networkidle")
            page.wait_for_timeout(2000)

            # Search for the patient note by date/name
            # This will need to click into the specific note to get full content
            # For now, let's try to extract from the list if visible

            try:
                # Try to find and click the note
                note_selector = f"[data-date='{visit_date}']"
                if page.locator(note_selector).count() > 0:
                    page.locator(note_selector).first.click()
                    page.wait_for_timeout(1000)
                else:
                    # Try alternative selectors
                    notes = page.locator('.note-item, .visit-card, [role="listitem"]').all()
                    for note in notes:
                        if visit_date in note.inner_text() or patient_name in note.inner_text():
                            note.click()
                            page.wait_for_timeout(1000)
                            break

                # Extract full note content from the detail view
                # Look for common content containers
                content_selectors = [
                    '.note-content',
                    '.note-body',
                    '[data-testid="note-content"]',
                    '.editor-content',
                    '.clinical-note',
                    'textarea[name="note"]',
                    '.ql-editor'  # Quill editor
                ]

                full_text = None
                for selector in content_selectors:
                    if page.locator(selector).count() > 0:
                        full_text = page.locator(selector).first.inner_text()
                        if full_text and len(full_text) > 50:
                            break

                if not full_text:
                    # Try to get all visible text in main content area
                    full_text = page.locator('main, .main-content, #content').first.inner_text()

                if full_text and len(full_text) > 50:
                    return {
                        'full_text': full_text.strip(),
                        'note_length': len(full_text.strip()),
                        'sections': ''  # Could parse sections if needed
                    }
                else:
                    logger.warning(f"Could not extract full content for {patient_name} - {visit_date}")
                    return None

            except Exception as e:
                logger.error(f"Error extracting note content: {e}")
                return None

        except Exception as e:
            logger.error(f"Error scraping note for {patient_name}: {e}")
            return None

    def update_note_content(self, note_id: int, content: Dict[str, Any]):
        """Update freed_notes record with scraped content.

        Args:
            note_id: freed_notes.id
            content: Dict with full_text, note_length, sections
        """
        try:
            self.cursor.execute("""
                UPDATE freed_notes
                SET
                    full_text = ?,
                    note_text = ?,
                    note_length = ?,
                    sections = ?,
                    extracted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                content['full_text'],
                content['full_text'][:500],  # Store first 500 chars in note_text
                content['note_length'],
                content.get('sections', ''),
                note_id
            ))
            self.conn.commit()
            logger.info(f"Updated note {note_id} with {content['note_length']} characters")

        except Exception as e:
            logger.error(f"Error updating note {note_id}: {e}")
            self.conn.rollback()

    def scrape_all_notes(self, limit: int = None, visible: bool = False):
        """Scrape full content for all notes needing it.

        Args:
            limit: Max notes to process (None = all)
            visible: Show browser (True) or headless (False)
        """
        notes_to_scrape = self.get_notes_to_scrape(limit=limit)

        if not notes_to_scrape:
            logger.info("No notes need scraping!")
            return

        logger.info(f"Starting to scrape {len(notes_to_scrape)} notes (most recent first)")

        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=not visible)

            try:
                # Login to Freed.ai
                logger.info("Logging into Freed.ai...")
                config = get_config()
                auth = SourceAuth(config, browser)
                if not auth.login():
                    logger.error("Failed to login to Freed.ai")
                    return
                logger.info("✓ Logged into Freed.ai")

                # Get page from auth
                page = auth.page

                # Create extractor
                extractor = FreedExtractor(page)

                # Process each note
                success_count = 0
                for idx, note in enumerate(notes_to_scrape, 1):
                    logger.info(f"\n[{idx}/{len(notes_to_scrape)}] Processing: {note['patient_name']} - {note['visit_date']}")

                    content = self.scrape_note_content(
                        page,
                        extractor,
                        note['patient_name'],
                        note['visit_date']
                    )

                    if content:
                        self.update_note_content(note['id'], content)
                        success_count += 1
                    else:
                        logger.warning(f"Skipped note {note['id']} - could not extract content")

                    # Brief pause between notes
                    page.wait_for_timeout(500)

                logger.info(f"\n✓ Scraping complete: {success_count}/{len(notes_to_scrape)} notes updated")

            finally:
                browser.close()

    def __del__(self):
        """Close database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape full note content from Freed.ai")
    parser.add_argument('--limit', type=int, help='Limit number of notes to scrape')
    parser.add_argument('--visible', action='store_true', help='Show browser window')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("FREED.AI NOTE SCRAPER - Full Content Extraction")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📋 Extracting full note content using screen scraping")
    logger.info("📅 Processing from most recent to oldest")
    logger.info("")

    scraper = FreedNoteScraper()
    scraper.scrape_all_notes(limit=args.limit, visible=args.visible)


if __name__ == "__main__":
    main()
