#!/usr/bin/env python3
"""
Upload Approved Notes to Osmind EHR

Queries the review database for approved notes and uploads them to Osmind
using Playwright automation. Tracks upload attempts and results.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import sqlite3

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from src.utils.logger import logger
from src.utils.config import get_config
from src.auth.target_auth import TargetAuth
from src.inserters.osmind_inserter import OsmindInserter


class ApprovedNotesUploader:
    """Upload approved notes from review database to Osmind EHR"""

    def __init__(self, db_path: str = None):
        """Initialize uploader

        Args:
            db_path: Path to database (defaults to web-app/backend/medical_notes.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "web-app" / "backend" / "medical_notes.db"

        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        logger.info(f"Approved Notes Uploader initialized with database: {self.db_path}")

    def get_approved_notes(
        self,
        batch_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get notes that have been approved and are ready for upload

        Args:
            batch_id: Optional batch ID to filter by
            limit: Optional limit on number of notes to retrieve

        Returns:
            List of approved note records
        """
        try:
            # Build query to get approved notes that haven't been uploaded yet
            if batch_id:
                query = """
                    SELECT
                        id,
                        patient_name,
                        visit_date,
                        final_cleaned_note,
                        batch_id,
                        review_status,
                        upload_status,
                        upload_attempts
                    FROM ai_processing_results
                    WHERE review_status = 'approved'
                      AND (upload_status = 'pending' OR upload_status IS NULL)
                      AND batch_id = ?
                    ORDER BY patient_name, visit_date
                """
                params = [batch_id]
            else:
                query = """
                    SELECT
                        id,
                        patient_name,
                        visit_date,
                        final_cleaned_note,
                        batch_id,
                        review_status,
                        upload_status,
                        upload_attempts
                    FROM ai_processing_results
                    WHERE review_status = 'approved'
                      AND (upload_status = 'pending' OR upload_status IS NULL)
                    ORDER BY patient_name, visit_date
                """
                params = []

            # Add limit if specified
            if limit:
                query += f" LIMIT {limit}"

            self.cursor.execute(query, params)
            notes = [dict(row) for row in self.cursor.fetchall()]

            logger.info(f"Found {len(notes)} approved notes ready for upload")
            return notes

        except Exception as e:
            logger.error(f"Error fetching approved notes: {e}")
            return []

    def record_upload_attempt(
        self,
        result_id: int,
        upload_status: str,
        error_message: Optional[str] = None,
        osmind_note_found: bool = False,
        note_was_signed: bool = False,
        content_appended: bool = False
    ):
        """Record an upload attempt in the database

        Args:
            result_id: ID of the ai_processing_results record
            upload_status: Status of upload ('success', 'failed', 'flagged')
            error_message: Optional error message
            osmind_note_found: Whether the note was found in Osmind
            note_was_signed: Whether the note was already signed
            content_appended: Whether content was successfully appended
        """
        try:
            # Get current upload attempts
            self.cursor.execute("""
                SELECT upload_attempts, batch_id
                FROM ai_processing_results
                WHERE id = ?
            """, (result_id,))

            result = self.cursor.fetchone()
            if not result:
                logger.error(f"Result {result_id} not found in database")
                return

            current_attempts = result['upload_attempts'] or 0
            new_attempts = current_attempts + 1
            batch_id = result['batch_id']

            # Get patient info for upload history
            self.cursor.execute("""
                SELECT patient_name, visit_date
                FROM ai_processing_results
                WHERE id = ?
            """, (result_id,))

            info = dict(self.cursor.fetchone())

            # Insert into upload_history
            self.cursor.execute("""
                INSERT INTO upload_history (
                    processing_result_id,
                    batch_id,
                    patient_name,
                    visit_date,
                    upload_status,
                    error_message,
                    attempt_number,
                    osmind_note_found,
                    note_was_signed,
                    content_appended
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result_id,
                batch_id,
                info['patient_name'],
                info['visit_date'],
                upload_status,
                error_message,
                new_attempts,
                osmind_note_found,
                note_was_signed,
                content_appended
            ))

            # Update ai_processing_results
            if upload_status == 'success':
                self.cursor.execute("""
                    UPDATE ai_processing_results
                    SET
                        upload_status = 'success',
                        upload_attempts = ?,
                        uploaded_at = CURRENT_TIMESTAMP,
                        upload_error = NULL
                    WHERE id = ?
                """, (new_attempts, result_id))
            else:
                self.cursor.execute("""
                    UPDATE ai_processing_results
                    SET
                        upload_status = ?,
                        upload_attempts = ?,
                        upload_error = ?
                    WHERE id = ?
                """, (upload_status, new_attempts, error_message, result_id))

            self.conn.commit()
            logger.info(f"Recorded upload attempt #{new_attempts} for result {result_id}: {upload_status}")

        except Exception as e:
            logger.error(f"Failed to record upload attempt: {e}")

    def upload_approved_batch(
        self,
        batch_id: Optional[str] = None,
        limit: Optional[int] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Upload a batch of approved notes to Osmind

        Args:
            batch_id: Optional batch ID to filter by
            limit: Optional limit on number of notes to upload
            dry_run: If True, only show what would be uploaded without actually uploading

        Returns:
            Dictionary with upload statistics
        """
        start_time = datetime.now()
        logger.info("="*80)
        logger.info("APPROVED NOTES UPLOADER - Starting Upload Process")
        if batch_id:
            logger.info(f"Batch ID: {batch_id}")
        if dry_run:
            logger.info("DRY RUN MODE - No actual uploads will be performed")
        logger.info("="*80)

        try:
            # Get approved notes
            notes = self.get_approved_notes(batch_id, limit)

            if not notes:
                logger.warning("No approved notes found ready for upload")
                return {
                    "success": False,
                    "message": "No approved notes found",
                    "total_notes": 0
                }

            # Show notes to be uploaded
            logger.info(f"\nFound {len(notes)} approved notes ready for upload:")
            for i, note in enumerate(notes, 1):
                logger.info(f"  {i}. {note['patient_name']} - {note['visit_date']} (ID: {note['id']})")
            logger.info("")

            if dry_run:
                logger.info("DRY RUN COMPLETE - No notes were uploaded")
                return {
                    "success": True,
                    "dry_run": True,
                    "total_notes": len(notes),
                    "notes": notes
                }

            # Initialize counters
            success_count = 0
            failed_count = 0
            flagged_count = 0

            # Get configuration
            config = get_config()

            # Start Playwright automation
            with sync_playwright() as p:
                logger.info("🌐 Launching browser for Osmind authentication...")
                browser = p.chromium.launch(
                    headless=False,
                    slow_mo=500  # Slow down actions for visibility
                )

                # Authenticate to Osmind
                logger.info("🔐 Logging into Osmind EHR...")
                target_auth = TargetAuth(config, browser)

                if not target_auth.login():
                    logger.error("❌ Failed to authenticate to Osmind EHR")
                    browser.close()
                    return {
                        "success": False,
                        "error": "Authentication failed",
                        "total_notes": len(notes)
                    }

                logger.info("✅ Successfully authenticated to Osmind EHR")
                logger.info("")

                # Initialize inserter
                inserter = OsmindInserter(target_auth.page)

                # Upload each note
                for i, note_record in enumerate(notes, 1):
                    result_id = note_record['id']
                    patient_name = note_record['patient_name']
                    visit_date = note_record['visit_date']

                    logger.info(f"[{i}/{len(notes)}] Uploading: {patient_name} - {visit_date}")

                    # Prepare note data for inserter
                    note_data = {
                        'patient_name': patient_name,
                        'visit_date': visit_date,
                        'cleaned_note': note_record['final_cleaned_note']
                    }

                    # Attempt upload
                    try:
                        upload_success = inserter.upload_note(note_data)

                        if upload_success:
                            success_count += 1
                            self.record_upload_attempt(
                                result_id=result_id,
                                upload_status='success',
                                osmind_note_found=True,
                                note_was_signed=False,
                                content_appended=True
                            )
                            logger.info(f"  ✅ Successfully uploaded")
                        else:
                            failed_count += 1
                            # Check if it was flagged
                            if inserter.flagged_for_review:
                                flagged_count += 1
                                last_flag = inserter.flagged_for_review[-1]
                                reason = last_flag.get('reason', 'Unknown error')

                                self.record_upload_attempt(
                                    result_id=result_id,
                                    upload_status='flagged',
                                    error_message=reason,
                                    osmind_note_found='not found' not in reason.lower(),
                                    note_was_signed='signed' in reason.lower(),
                                    content_appended=False
                                )
                                logger.warning(f"  ⚠️  Flagged: {reason}")
                            else:
                                self.record_upload_attempt(
                                    result_id=result_id,
                                    upload_status='failed',
                                    error_message='Upload failed',
                                    osmind_note_found=False,
                                    note_was_signed=False,
                                    content_appended=False
                                )
                                logger.error(f"  ❌ Upload failed")

                    except Exception as e:
                        failed_count += 1
                        error_msg = str(e)
                        self.record_upload_attempt(
                            result_id=result_id,
                            upload_status='failed',
                            error_message=error_msg,
                            osmind_note_found=False,
                            note_was_signed=False,
                            content_appended=False
                        )
                        logger.error(f"  ❌ Exception during upload: {e}")

                # Cleanup
                logger.info("\nClosing browser...")
                target_auth.logout()
                browser.close()

            # Calculate duration
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Print summary
            logger.info("\n" + "="*80)
            logger.info("UPLOAD COMPLETE")
            logger.info("="*80)
            logger.info(f"Total Notes: {len(notes)}")
            logger.info(f"  ✅ Successful: {success_count}")
            logger.info(f"  ❌ Failed: {failed_count}")
            logger.info(f"  ⚠️  Flagged for Review: {flagged_count}")
            logger.info(f"Duration: {duration_ms/1000:.2f}s")
            logger.info("="*80)

            return {
                "success": True,
                "total_notes": len(notes),
                "success_count": success_count,
                "failed_count": failed_count,
                "flagged_count": flagged_count,
                "duration_ms": duration_ms,
                "batch_id": batch_id
            }

        except Exception as e:
            logger.error(f"Upload process failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Upload process failed: {str(e)}"
            }

    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()

    def __del__(self):
        """Cleanup on deletion"""
        self.close()


def main():
    """Main entry point for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload approved notes from review database to Osmind EHR"
    )
    parser.add_argument(
        '--batch-id',
        help='Batch ID to filter notes (optional)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of notes to upload (useful for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be uploaded without actually uploading'
    )

    args = parser.parse_args()

    # Create uploader
    uploader = ApprovedNotesUploader()

    # Run upload
    result = uploader.upload_approved_batch(
        batch_id=args.batch_id,
        limit=args.limit,
        dry_run=args.dry_run
    )

    uploader.close()

    # Exit with appropriate code
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()
