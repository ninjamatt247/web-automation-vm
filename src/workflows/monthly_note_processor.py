#!/usr/bin/env python3
"""
Monthly Note Processor - Batch ASOP Conversion Workflow

Processes a month's worth of Freed notes through the 3-step OpenAI ASOP conversion
pipeline and stores results in the review database for human review before upload.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import sqlite3
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.logger import logger
from src.utils.config import get_config
from src.utils.openai_processor import OpenAIProcessor

# Import Database for manual storage
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "web-app" / "backend"))
from database import Database


class MonthlyNoteProcessor:
    """Process monthly notes through ASOP conversion workflow"""

    def __init__(self, db_path: str = None):
        """Initialize the monthly processor

        Args:
            db_path: Path to database (defaults to web-app/backend/medical_notes.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "web-app" / "backend" / "medical_notes.db"

        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Initialize OpenAI processor with multi-step processing enabled
        # Note: store_in_db=False because we'll manually store with patient_name/visit_date
        self.config = get_config()
        self.openai_processor = OpenAIProcessor(
            config=self.config,
            use_multi_step=True,
            store_in_db=False
        )

        # Initialize Database instance for manual storage
        self.db = Database(self.db_path)

        logger.info(f"Monthly Note Processor initialized with database: {self.db_path}")

    def get_notes_to_process(
        self,
        start_date: str,
        end_date: str,
        skip_duplicates: bool = True,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get notes within date range that need processing

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            skip_duplicates: Skip notes that already exist in Osmind (default: True)
            limit: Maximum number of notes to process (None = all)

        Returns:
            List of note records with patient info
        """
        try:
            # Build query based on duplicate handling
            # Note: visit_date is stored in various formats (MM/DD/YY, YYYY-MM-DD, etc.)
            # We'll use a more flexible approach - just get all notes and filter by limit
            # Convert YYYY-MM-DD to MM/% pattern for matching
            # e.g., 2025-10-01 -> "10/%"
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            month_pattern = f"{start_dt.month:02d}/%"

            if skip_duplicates:
                # Skip notes where Osmind already has this patient/visit_date combo
                query = """
                    SELECT
                        fn.id as freed_note_id,
                        fn.patient_id,
                        p.name as patient_name,
                        fn.visit_date,
                        fn.full_text as raw_note,
                        fn.note_length,
                        fn.freed_visit_id
                    FROM freed_notes fn
                    JOIN patients p ON fn.patient_id = p.id
                    LEFT JOIN osmind_notes onn ON (
                        onn.patient_id = fn.patient_id
                        AND onn.visit_date = fn.visit_date
                    )
                    WHERE fn.full_text IS NOT NULL
                      AND fn.note_length > 100
                      AND onn.id IS NULL
                      AND fn.visit_date LIKE ?
                    ORDER BY fn.id DESC
                """
            else:
                # Process all notes
                query = """
                    SELECT
                        fn.id as freed_note_id,
                        fn.patient_id,
                        p.name as patient_name,
                        fn.visit_date,
                        fn.full_text as raw_note,
                        fn.note_length,
                        fn.freed_visit_id
                    FROM freed_notes fn
                    JOIN patients p ON fn.patient_id = p.id
                    WHERE fn.full_text IS NOT NULL
                      AND fn.note_length > 100
                      AND fn.visit_date LIKE ?
                    ORDER BY fn.id DESC
                """

            # Add LIMIT if specified
            if limit:
                query += f" LIMIT {limit}"

            self.cursor.execute(query, (month_pattern,))
            notes = [dict(row) for row in self.cursor.fetchall()]

            logger.info(f"Found {len(notes)} notes to process")
            return notes

        except Exception as e:
            logger.error(f"Error fetching notes to process: {e}")
            return []

    def create_batch_run(
        self,
        start_date: str,
        end_date: str,
        total_notes: int
    ) -> str:
        """Create a new batch processing run record

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            total_notes: Total number of notes in this batch

        Returns:
            Generated batch_id
        """
        try:
            # Generate unique batch ID
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            self.cursor.execute("""
                INSERT INTO batch_processing_runs (
                    batch_id,
                    start_date,
                    end_date,
                    total_notes,
                    status
                ) VALUES (?, ?, ?, ?, 'running')
            """, (batch_id, start_date, end_date, total_notes))

            self.conn.commit()
            logger.info(f"Created batch run: {batch_id}")
            return batch_id

        except Exception as e:
            logger.error(f"Error creating batch run: {e}")
            raise

    def update_batch_run(
        self,
        batch_id: str,
        updates: Dict[str, Any]
    ):
        """Update batch run with processing results

        Args:
            batch_id: Batch ID to update
            updates: Dictionary of fields to update
        """
        try:
            # Build UPDATE statement dynamically
            set_clauses = []
            values = []

            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)

            values.append(batch_id)

            query = f"""
                UPDATE batch_processing_runs
                SET {', '.join(set_clauses)}
                WHERE batch_id = ?
            """

            self.cursor.execute(query, values)
            self.conn.commit()

        except Exception as e:
            logger.error(f"Error updating batch run: {e}")

    def process_batch(
        self,
        start_date: str,
        end_date: str,
        skip_duplicates: bool = True,
        batch_size: int = 50,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process a batch of notes through the ASOP conversion pipeline

        Args:
            start_date: Start date in YYYY-MM-DD format (e.g., "2024-12-01") - NOTE: Currently ignored, processes all notes
            end_date: End date in YYYY-MM-DD format (e.g., "2024-12-31") - NOTE: Currently ignored, processes all notes
            skip_duplicates: Skip notes already in Osmind (default: True)
            batch_size: Number of notes to process in each chunk (default: 50)
            limit: Maximum number of notes to process (None = all notes, useful for testing)

        Returns:
            Dictionary with processing statistics
        """
        start_time = datetime.now()
        logger.info("="*80)
        logger.info(f"MONTHLY NOTE PROCESSOR - Starting batch processing")
        logger.info(f"Date Range: {start_date} to {end_date}")
        logger.info(f"Skip Duplicates: {skip_duplicates}")
        logger.info("="*80)

        try:
            # Get notes to process
            notes_to_process = self.get_notes_to_process(start_date, end_date, skip_duplicates, limit)

            if not notes_to_process:
                logger.warning("No notes found to process!")
                return {
                    "success": False,
                    "message": "No notes found in date range",
                    "total_notes": 0
                }

            # Create batch run
            batch_id = self.create_batch_run(start_date, end_date, len(notes_to_process))

            # Initialize counters
            processed_count = 0
            success_count = 0
            needs_review_count = 0
            failed_count = 0
            duplicate_count = 0
            skipped_count = 0
            total_tokens = 0

            # Process notes in batches
            for batch_start in range(0, len(notes_to_process), batch_size):
                batch_end = min(batch_start + batch_size, len(notes_to_process))
                batch = notes_to_process[batch_start:batch_end]

                logger.info(f"\nProcessing batch {batch_start//batch_size + 1} "
                           f"({batch_start+1}-{batch_end} of {len(notes_to_process)})")

                for idx, note in enumerate(batch, batch_start + 1):
                    try:
                        logger.info(f"[{idx}/{len(notes_to_process)}] Processing: "
                                   f"{note['patient_name']} - {note['visit_date']}")

                        # Process through OpenAI multi-step pipeline
                        result = self.openai_processor.multi_step_clean_patient_note(
                            raw_note=note['raw_note']
                        )

                        if result and result.get('processing_status') != 'failed':
                            # Add metadata to result
                            result['raw_note'] = note['raw_note']
                            result['model_used'] = self.config.openai_model

                            # Store in database with patient info
                            processing_id = self.db.store_ai_processing_result(
                                result=result,
                                patient_name=note['patient_name'],
                                visit_date=note['visit_date']
                            )

                            # Update the result with batch metadata
                            self.cursor.execute("""
                                UPDATE ai_processing_results
                                SET
                                    batch_id = ?,
                                    batch_timestamp = CURRENT_TIMESTAMP,
                                    review_status = 'pending',
                                    upload_status = 'pending'
                                WHERE id = ?
                            """, (batch_id, processing_id))

                            self.conn.commit()

                            processed_count += 1
                            total_tokens += result.get('tokens_used', 0)

                            # Categorize result based on processing status
                            status = result.get('processing_status', 'failed')

                            if status == 'needs_review' or result.get('requires_human_intervention'):
                                needs_review_count += 1
                                reasons = []
                                if result.get('validation_report'):
                                    reasons = result['validation_report'].human_intervention_reasons
                                logger.info(f"   ⚠️  Needs review: {', '.join(reasons) if reasons else 'Quality checks failed'}")
                            elif status in ('success', 'success_with_warnings'):
                                success_count += 1
                                logger.info(f"   ✓ Success")
                            else:
                                failed_count += 1
                                logger.error(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
                        else:
                            failed_count += 1
                            error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                            logger.error(f"   ❌ Processing failed: {error_msg}")

                    except Exception as e:
                        logger.error(f"   ❌ Error processing note: {e}")
                        failed_count += 1
                        continue

            # Calculate duration
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Update batch run with final stats
            self.update_batch_run(batch_id, {
                'processed_notes': processed_count,
                'success_count': success_count,
                'needs_review_count': needs_review_count,
                'failed_count': failed_count,
                'duplicate_count': duplicate_count,
                'skipped_count': skipped_count,
                'total_tokens_used': total_tokens,
                'processing_duration_ms': duration_ms,
                'status': 'completed',
                'completed_at': datetime.now().isoformat()
            })

            # Print summary
            logger.info("\n" + "="*80)
            logger.info("BATCH PROCESSING COMPLETE")
            logger.info("="*80)
            logger.info(f"Batch ID: {batch_id}")
            logger.info(f"Date Range: {start_date} to {end_date}")
            logger.info(f"Total Notes: {len(notes_to_process)}")
            logger.info(f"Processed: {processed_count}")
            logger.info(f"  ✓ Success: {success_count}")
            logger.info(f"  ⚠️  Needs Review: {needs_review_count}")
            logger.info(f"  ❌ Failed: {failed_count}")
            logger.info(f"Total Tokens: {total_tokens:,}")
            logger.info(f"Duration: {duration_ms/1000:.2f}s")
            logger.info("="*80)

            return {
                "success": True,
                "batch_id": batch_id,
                "total_notes": len(notes_to_process),
                "processed": processed_count,
                "success_count": success_count,
                "needs_review_count": needs_review_count,
                "failed_count": failed_count,
                "total_tokens": total_tokens,
                "duration_ms": duration_ms,
                "start_date": start_date,
                "end_date": end_date
            }

        except Exception as e:
            logger.error(f"Batch processing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Batch processing failed: {str(e)}"
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
        description="Process monthly notes through ASOP conversion pipeline"
    )
    parser.add_argument(
        '--start-date',
        required=True,
        help='Start date in YYYY-MM-DD format (e.g., 2024-12-01)'
    )
    parser.add_argument(
        '--end-date',
        required=True,
        help='End date in YYYY-MM-DD format (e.g., 2024-12-31)'
    )
    parser.add_argument(
        '--skip-duplicates',
        action='store_true',
        default=True,
        help='Skip notes already in Osmind (default: True)'
    )
    parser.add_argument(
        '--include-duplicates',
        action='store_true',
        help='Process all notes including duplicates'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of notes to process per batch (default: 50)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of notes to process (useful for testing, e.g., --limit 5)'
    )

    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD (e.g., 2024-12-01)")
        sys.exit(1)

    # Process batch
    skip_dupes = not args.include_duplicates if args.include_duplicates else args.skip_duplicates

    processor = MonthlyNoteProcessor()
    result = processor.process_batch(
        start_date=args.start_date,
        end_date=args.end_date,
        skip_duplicates=skip_dupes,
        batch_size=args.batch_size,
        limit=args.limit
    )

    processor.close()

    # Exit with appropriate code
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()
