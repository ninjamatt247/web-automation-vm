#!/usr/bin/env python3
"""
Batch Reporter - Generate reports for batch processing runs

Provides utilities for generating summary reports, CSV exports, and statistics
for monthly note processing batches.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import sqlite3
import csv
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.logger import logger


class BatchReporter:
    """Generate reports for batch processing runs"""

    def __init__(self, db_path: str = None):
        """Initialize reporter with database connection

        Args:
            db_path: Path to database (defaults to web-app/backend/medical_notes.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "web-app" / "backend" / "medical_notes.db"

        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def get_batch_summary(self, batch_id: str) -> Dict:
        """Get summary statistics for a batch

        Args:
            batch_id: Batch ID to generate report for

        Returns:
            Dictionary with batch statistics
        """
        try:
            # Get batch run info
            self.cursor.execute("""
                SELECT * FROM batch_processing_runs
                WHERE batch_id = ?
            """, (batch_id,))

            batch = self.cursor.fetchone()
            if not batch:
                logger.error(f"Batch {batch_id} not found")
                return {}

            batch_dict = dict(batch)

            # Get processing results breakdown
            self.cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN processing_status = 'success' THEN 1 END) as success,
                    COUNT(CASE WHEN requires_human_intervention = 1 THEN 1 END) as needs_review,
                    COUNT(CASE WHEN critical_failures > 0 THEN 1 END) as has_critical,
                    AVG(passed_checks * 1.0 / NULLIF(total_checks, 0)) as avg_pass_rate,
                    SUM(tokens_used) as total_tokens
                FROM ai_processing_results
                WHERE batch_id = ?
            """, (batch_id,))

            stats = dict(self.cursor.fetchone())

            # Get review status breakdown
            self.cursor.execute("""
                SELECT
                    review_status,
                    COUNT(*) as count
                FROM ai_processing_results
                WHERE batch_id = ?
                GROUP BY review_status
            """, (batch_id,))

            review_breakdown = {row['review_status']: row['count'] for row in self.cursor.fetchall()}

            # Get upload status breakdown
            self.cursor.execute("""
                SELECT
                    upload_status,
                    COUNT(*) as count
                FROM ai_processing_results
                WHERE batch_id = ?
                GROUP BY upload_status
            """, (batch_id,))

            upload_breakdown = {row['upload_status']: row['count'] for row in self.cursor.fetchall()}

            return {
                "batch_id": batch_id,
                "batch_info": batch_dict,
                "processing_stats": stats,
                "review_breakdown": review_breakdown,
                "upload_breakdown": upload_breakdown
            }

        except Exception as e:
            logger.error(f"Error getting batch summary: {e}")
            return {}

    def print_batch_summary(self, batch_id: str):
        """Print formatted batch summary to console

        Args:
            batch_id: Batch ID to print summary for
        """
        summary = self.get_batch_summary(batch_id)

        if not summary:
            logger.error(f"No summary available for batch {batch_id}")
            return

        batch_info = summary['batch_info']
        processing_stats = summary['processing_stats']
        review_breakdown = summary['review_breakdown']
        upload_breakdown = summary['upload_breakdown']

        print("\n" + "="*80)
        print(f"BATCH PROCESSING SUMMARY: {batch_id}")
        print("="*80)
        print(f"Date Range: {batch_info['start_date']} to {batch_info['end_date']}")
        print(f"Status: {batch_info['status']}")
        print(f"Created: {batch_info['created_at']}")
        if batch_info['completed_at']:
            print(f"Completed: {batch_info['completed_at']}")
        print(f"Duration: {batch_info['processing_duration_ms']/1000:.2f}s" if batch_info['processing_duration_ms'] else "In Progress...")

        print(f"\nPROCESSING STATS:")
        print(f"  Total Notes: {batch_info['total_notes']}")
        print(f"  Processed: {batch_info['processed_notes']}")
        print(f"  Success: {batch_info['success_count']}")
        print(f"  Needs Review: {batch_info['needs_review_count']}")
        print(f"  Failed: {batch_info['failed_count']}")

        print(f"\nQUALITY METRICS:")
        print(f"  Critical Failures: {processing_stats['has_critical']}")
        print(f"  Avg Pass Rate: {processing_stats['avg_pass_rate']:.1%}" if processing_stats['avg_pass_rate'] else "  Avg Pass Rate: N/A")
        print(f"  Total Tokens: {processing_stats['total_tokens']:,}" if processing_stats['total_tokens'] else "  Total Tokens: 0")

        print(f"\nREVIEW STATUS:")
        for status, count in review_breakdown.items():
            print(f"  {status or 'unknown'}: {count}")

        print(f"\nUPLOAD STATUS:")
        for status, count in upload_breakdown.items():
            print(f"  {status or 'unknown'}: {count}")

        print("="*80 + "\n")

    def export_batch_results(self, batch_id: str, output_path: str = None) -> str:
        """Export batch results to CSV

        Args:
            batch_id: Batch ID to export
            output_path: Path to output CSV (defaults to data/batch_{batch_id}.csv)

        Returns:
            Path to exported CSV file
        """
        try:
            if output_path is None:
                data_dir = Path(__file__).parent.parent.parent / "data"
                data_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = data_dir / f"batch_{batch_id}_{timestamp}.csv"

            # Get batch results
            self.cursor.execute("""
                SELECT
                    patient_name,
                    visit_date,
                    processing_status,
                    requires_human_intervention,
                    human_intervention_reasons,
                    review_status,
                    upload_status,
                    total_checks,
                    passed_checks,
                    failed_checks,
                    critical_failures,
                    high_failures,
                    medium_failures,
                    tokens_used,
                    processing_duration_ms,
                    created_at
                FROM ai_processing_results
                WHERE batch_id = ?
                ORDER BY visit_date DESC, patient_name
            """, (batch_id,))

            results = [dict(row) for row in self.cursor.fetchall()]

            if not results:
                logger.warning(f"No results found for batch {batch_id}")
                return ""

            # Write to CSV
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)

            logger.info(f"Exported {len(results)} results to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error exporting batch results: {e}")
            return ""

    def list_recent_batches(self, limit: int = 10):
        """List recent batch processing runs

        Args:
            limit: Maximum number of batches to list (default: 10)
        """
        try:
            self.cursor.execute("""
                SELECT
                    batch_id,
                    start_date,
                    end_date,
                    total_notes,
                    processed_notes,
                    success_count,
                    needs_review_count,
                    failed_count,
                    status,
                    created_at
                FROM batch_processing_runs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            batches = [dict(row) for row in self.cursor.fetchall()]

            if not batches:
                print("No batch runs found.")
                return

            print("\n" + "="*80)
            print(f"RECENT BATCH RUNS (Last {limit})")
            print("="*80)

            for batch in batches:
                print(f"\nBatch ID: {batch['batch_id']}")
                print(f"  Date Range: {batch['start_date']} to {batch['end_date']}")
                print(f"  Status: {batch['status']}")
                print(f"  Total: {batch['total_notes']}, "
                      f"Processed: {batch['processed_notes']}, "
                      f"Success: {batch['success_count']}, "
                      f"Needs Review: {batch['needs_review_count']}, "
                      f"Failed: {batch['failed_count']}")
                print(f"  Created: {batch['created_at']}")

            print("="*80 + "\n")

        except Exception as e:
            logger.error(f"Error listing batches: {e}")

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

    parser = argparse.ArgumentParser(description="Generate batch processing reports")
    parser.add_argument('--batch-id', help='Batch ID to generate report for')
    parser.add_argument('--export', action='store_true', help='Export batch results to CSV')
    parser.add_argument('--list', action='store_true', help='List recent batch runs')
    parser.add_argument('--limit', type=int, default=10, help='Number of batches to list (default: 10)')

    args = parser.parse_args()

    reporter = BatchReporter()

    if args.list:
        reporter.list_recent_batches(limit=args.limit)
    elif args.batch_id:
        reporter.print_batch_summary(args.batch_id)
        if args.export:
            csv_path = reporter.export_batch_results(args.batch_id)
            if csv_path:
                print(f"\nResults exported to: {csv_path}")
    else:
        parser.print_help()

    reporter.close()


if __name__ == "__main__":
    main()
