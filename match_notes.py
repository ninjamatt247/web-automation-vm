#!/usr/bin/env python3
"""
Fuzzy Matching Script for Freed-Osmind Note Linking

Matches Freed.ai notes with Osmind EHR notes using 7-tier matching strategy:
- Tier 1-3: High confidence (exact ID/name matches)
- Tier 4-6: Medium confidence (fuzzy matches)
- Tier 7: Low confidence (partial matches for manual review)

Usage:
    python match_notes.py --dry-run              # Preview matches
    python match_notes.py                        # Run matching
    python match_notes.py --tier-limit 4         # High confidence only
    python match_notes.py --export-dir ./reports # Custom export directory
"""

import argparse
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.matchers.note_matcher import NoteMatcher
from src.utils.match_reporter import MatchReporter
from src.utils.match_validator import MatchValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'match_notes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Fuzzy match Freed.ai notes with Osmind EHR notes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--db-path',
        default='/Users/harringhome/web-automation-vm/web-app/backend/medical_notes.db',
        help='Path to SQLite database (default: medical_notes.db)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview matches without creating database records'
    )

    parser.add_argument(
        '--tier-limit',
        type=int,
        default=7,
        choices=range(1, 8),
        help='Maximum tier to use (1-7, default: 7)'
    )

    parser.add_argument(
        '--min-tier',
        type=int,
        default=1,
        choices=range(1, 8),
        help='Minimum tier to start from (1-7, default: 1 uses all tiers)'
    )

    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help='Re-process notes already in combined_notes (default: skip existing)'
    )

    parser.add_argument(
        '--include-has-freed-content',
        action='store_true',
        help='Include Osmind notes with has_freed_content=1 (default: skip)'
    )

    parser.add_argument(
        '--auto-match-threshold',
        type=float,
        default=0.70,
        help='Minimum confidence for auto-matching (default: 0.70)'
    )

    parser.add_argument(
        '--export-dir',
        default='./data',
        help='Directory for CSV exports (default: ./data)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def main():
    """Main execution flow"""
    args = parse_arguments()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 80)
    logger.info("FUZZY MATCHING - Freed.ai → Osmind EHR")
    logger.info("=" * 80)
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info(f"Tier Range: {args.min_tier}-{args.tier_limit}")
    logger.info(f"Auto-match Threshold: {args.auto_match_threshold}")
    logger.info(f"Skip Existing: {not args.no_skip_existing}")
    logger.info(f"Skip has_freed_content: {not args.include_has_freed_content}")
    logger.info("")

    # Phase 1: Pre-run validation
    logger.info("Phase 1: Pre-run Validation")
    logger.info("-" * 40)

    validator = MatchValidator(args.db_path)

    schema_result = validator.validate_database_schema()
    if not schema_result['valid']:
        logger.error("Schema validation failed:")
        for error in schema_result['errors']:
            logger.error(f"  • {error}")
        sys.exit(1)
    logger.info("✓ Schema validation passed")

    data_result = validator.validate_data_availability()
    if not data_result['valid']:
        logger.error("Data validation failed:")
        for warning in data_result['warnings']:
            logger.error(f"  • {warning}")
        sys.exit(1)
    logger.info("✓ Data validation passed")

    if data_result['warnings']:
        logger.warning("Data validation warnings:")
        for warning in data_result['warnings']:
            logger.warning(f"  • {warning}")

    validator.close()
    logger.info("")

    # Phase 2: Fuzzy Matching
    logger.info("Phase 2: Fuzzy Matching")
    logger.info("-" * 40)

    matcher = NoteMatcher(
        db_path=args.db_path,
        skip_existing=not args.no_skip_existing,
        skip_has_freed_content=not args.include_has_freed_content,
        auto_match_threshold=args.auto_match_threshold,
        min_tier=args.min_tier
    )

    try:
        results = matcher.match_all_notes(
            tier_limit=args.tier_limit,
            dry_run=args.dry_run
        )
    except Exception as e:
        logger.error(f"Matching failed: {e}", exc_info=True)
        matcher.close()
        sys.exit(1)

    matcher.close()
    logger.info("")

    # Phase 3: Reporting
    logger.info("Phase 3: Report Generation")
    logger.info("-" * 40)

    reporter = MatchReporter()

    # Generate summary report
    summary = reporter.generate_summary(results)
    print("\n" + summary)

    # Export CSVs
    if results.matches:
        os.makedirs(args.export_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export all matches
        all_matches_path = os.path.join(args.export_dir, f"all_matches_{timestamp}.csv")
        reporter.export_all_matches(results, all_matches_path)
        logger.info(f"✓ Exported all matches to {all_matches_path}")

        # Export low-confidence matches
        low_conf_path = os.path.join(args.export_dir, f"low_confidence_{timestamp}.csv")
        low_conf_count = reporter.export_low_confidence(results, low_conf_path, threshold=0.75)
        if low_conf_count > 0:
            logger.info(f"✓ Exported {low_conf_count} low-confidence matches to {low_conf_path}")

    logger.info("")

    # Phase 4: Post-run validation (if not dry run)
    if not args.dry_run:
        logger.info("Phase 4: Post-run Validation")
        logger.info("-" * 40)

        validator = MatchValidator(args.db_path)

        # Check for duplicates
        duplicates = validator.check_duplicate_links()
        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate links - manual review needed")
        else:
            logger.info("✓ No duplicate links found")

        # Validate results
        warnings = validator.validate_match_results(results)
        if warnings:
            logger.warning("Result validation warnings:")
            for warning in warnings:
                logger.warning(f"  • {warning}")
        else:
            logger.info("✓ Results validation passed")

        validator.close()
        logger.info("")

    # Final Summary
    logger.info("=" * 80)
    if args.dry_run:
        logger.info("DRY RUN COMPLETE - No database changes made")
        logger.info(f"Run without --dry-run to create {results.matched} combined_notes records")
    else:
        logger.info(f"MATCHING COMPLETE - {results.matched} records created")
        match_rate = (results.matched / results.total_freed * 100) if results.total_freed > 0 else 0
        logger.info(f"Match Rate: {match_rate:.1f}% ({results.matched}/{results.total_freed})")

        # Next steps
        low_conf_count = sum(1 for m in results.matches if m.confidence < 0.75)
        if low_conf_count > 0:
            logger.info(f"\nNext Steps:")
            logger.info(f"  1. Review {low_conf_count} low-confidence matches in CSV export")
            logger.info(f"  2. Manually verify matches in combined_notes table")
            logger.info(f"  3. Update sync_status to 'manually_verified' for reviewed records")

    logger.info("=" * 80)


if __name__ == '__main__':
    main()
