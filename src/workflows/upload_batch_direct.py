#!/usr/bin/env python3
"""
Direct Upload to Osmind - Bypass Approval Process

Uploads AI-processed notes directly to Osmind without requiring approval.
Use this when you want to upload all notes from a batch immediately.
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


class DirectBatchUploader:
    """Upload batch notes directly to Osmind (bypass approval)"""

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

        logger.info(f"Direct Batch Uploader initialized with database: {self.db_path}")

    def get_batch_notes(
        self,
        batch_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all processed notes from batch (regardless of approval status)

        Args:
            batch_id: Optional batch ID to filter by
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            limit: Optional limit on number of notes

        Returns:
            List of processed note records
        """
        try:
            # Build query - get all notes with final_cleaned_note
            query = """
                SELECT
                    id,
                    patient_name,
                    visit_date,
                    final_cleaned_note,
                    batch_id,
                    processing_status,
                    review_status,
                    upload_status,
                    upload_attempts
                FROM ai_processing_results
                WHERE final_cleaned_note IS NOT NULL
                  AND final_cleaned_note != ''
                  AND (upload_status IS NULL OR upload_status = 'pending' OR upload_status = 'failed')
            """
            params = []

            # Add filters
            if batch_id:
                query += " AND batch_id = ?"
                params.append(batch_id)

            if start_date and end_date:
                # Convert to month pattern (e.g., "11/%" for November)
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query += " AND visit_date LIKE ?"
                params.append(f"{start_dt.month:02d}/%")

            query += " ORDER BY patient_name, visit_date"

            # Add limit
            if limit:
                query += f" LIMIT {limit}"

            self.cursor.execute(query, params)
            notes = [dict(row) for row in self.cursor.fetchall()]

            logger.info(f"Found {len(notes)} notes to upload")
            return notes

        except Exception as e:
            logger.error(f"Error fetching notes: {e}")
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
        """Record an upload attempt in the database"""
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

            # Get patient info
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

    def upload_batch_direct(
        self,
        batch_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Upload batch notes directly to Osmind (bypass approval)

        Args:
            batch_id: Optional batch ID to filter by
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            limit: Optional limit on number of notes

        Returns:
            Dictionary with upload statistics
        """
        start_time = datetime.now()
        logger.info("="*80)
        logger.info("DIRECT BATCH UPLOADER - Starting Upload Process")
        logger.info("⚠️  BYPASSING APPROVAL - Uploading all processed notes")
        if batch_id:
            logger.info(f"Batch ID: {batch_id}")
        if start_date and end_date:
            logger.info(f"Date Range: {start_date} to {end_date}")
        logger.info("="*80)

        try:
            # Get notes to upload
            notes = self.get_batch_notes(batch_id, start_date, end_date, limit)

            if not notes:
                logger.warning("No notes found to upload")
                return {
                    "success": False,
                    "message": "No notes found",
                    "total_notes": 0
                }

            # Show notes to be uploaded
            logger.info(f"\nFound {len(notes)} notes to upload:")
            for i, note in enumerate(notes, 1):
                status_info = f"[{note['processing_status']}]"
                logger.info(f"  {i}. {note['patient_name']} - {note['visit_date']} {status_info}")
            logger.info("")

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
                    slow_mo=500
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
        description="Upload notes directly to Osmind (bypass approval process)"
    )
    parser.add_argument(
        '--batch-id',
        help='Batch ID to filter notes'
    )
    parser.add_argument(
        '--start-date',
        help='Start date in YYYY-MM-DD format (e.g., 2025-11-01)'
    )
    parser.add_argument(
        '--end-date',
        help='End date in YYYY-MM-DD format (e.g., 2025-11-30)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of notes to upload (useful for testing)'
    )

    args = parser.parse_args()

    # Create uploader
    uploader = DirectBatchUploader()

    # Run upload
    result = uploader.upload_batch_direct(
        batch_id=args.batch_id,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit
    )

    uploader.close()

    # Exit with appropriate code
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()
