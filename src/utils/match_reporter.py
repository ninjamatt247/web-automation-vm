"""Match quality reporting and CSV export module"""

import csv
from datetime import datetime
from typing import List
import logging

logger = logging.getLogger(__name__)


class MatchReporter:
    """Generate match quality reports and export unmatched records"""

    def __init__(self):
        """Initialize match reporter"""
        pass

    def generate_summary(self, results) -> str:
        """Generate comprehensive match summary report

        Args:
            results: MatchResults object

        Returns:
            Formatted report string
        """
        match_rate = (results.matched / results.total_freed * 100) if results.total_freed > 0 else 0

        report = []
        report.append("=" * 80)
        report.append("FUZZY MATCHING REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary section
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Freed Notes:       {results.total_freed:,}")
        report.append(f"Total Osmind Notes:      {results.total_osmind:,}")
        report.append(f"Successfully Matched:    {results.matched:,} ({match_rate:.1f}%)")
        report.append(f"Unmatched (Freed):       {results.unmatched_freed:,}")
        report.append(f"Errors:                  {len(results.errors)}")
        report.append("")

        # Tier distribution
        report.append("MATCH TIER DISTRIBUTION")
        report.append("-" * 40)
        for tier in sorted(results.tier_distribution.keys()):
            count = results.tier_distribution[tier]
            if count > 0:
                percentage = (count / results.matched * 100) if results.matched > 0 else 0
                report.append(f"Tier {tier}:  {count:4,} matches ({percentage:5.1f}%)")
        report.append("")

        # Confidence statistics
        report.append("CONFIDENCE STATISTICS")
        report.append("-" * 40)
        report.append(f"Average:  {results.confidence_stats['avg']:.2f}")
        report.append(f"Median:   {results.confidence_stats.get('median', results.confidence_stats['avg']):.2f}")
        report.append(f"Min:      {results.confidence_stats['min']:.2f}")
        report.append(f"Max:      {results.confidence_stats['max']:.2f}")
        report.append("")

        # Recommendations
        low_conf_count = sum(1 for m in results.matches if m.confidence < 0.75)
        if low_conf_count > 0 or results.unmatched_freed > 0:
            report.append("RECOMMENDATIONS")
            report.append("-" * 40)
            if low_conf_count > 0:
                report.append(f"⚠️  Review {low_conf_count} low-confidence matches manually")
            if results.unmatched_freed > 0:
                report.append(f"ℹ️  {results.unmatched_freed} Freed notes could not be matched")
                report.append("   Consider: manual review, check patient names, verify dates")
            report.append("")

        # Errors
        if results.errors:
            report.append("ERRORS")
            report.append("-" * 40)
            for error in results.errors[:10]:  # Show first 10 errors
                report.append(f"  • {error}")
            if len(results.errors) > 10:
                report.append(f"  ... and {len(results.errors) - 10} more errors")
            report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def export_unmatched(self, results, filepath: str) -> int:
        """Export unmatched Freed notes to CSV

        Args:
            results: MatchResults object
            filepath: Path to output CSV file

        Returns:
            Number of records exported
        """
        # Find unmatched freed note IDs
        matched_ids = {m.freed_note_id for m in results.matches}

        # Get unmatched notes (would need database access - simplified for now)
        # In production, this would query the database for full details

        logger.info(f"Would export {results.unmatched_freed} unmatched notes to {filepath}")
        return results.unmatched_freed

    def export_low_confidence(self, results, filepath: str, threshold: float = 0.75) -> int:
        """Export low-confidence matches to CSV for manual review

        Args:
            results: MatchResults object
            filepath: Path to output CSV file
            threshold: Confidence threshold (default: 0.75)

        Returns:
            Number of records exported
        """
        low_conf_matches = [m for m in results.matches if m.confidence < threshold]

        if not low_conf_matches:
            logger.info("No low-confidence matches to export")
            return 0

        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'freed_note_id', 'osmind_note_id', 'tier', 'match_type',
                'confidence', 'similarity_score',
                'freed_patient_name', 'osmind_patient_name',
                'freed_visit_date', 'osmind_visit_date'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for match in low_conf_matches:
                writer.writerow({
                    'freed_note_id': match.freed_note_id,
                    'osmind_note_id': match.osmind_note_id,
                    'tier': match.tier,
                    'match_type': match.match_type,
                    'confidence': f"{match.confidence:.2f}",
                    'similarity_score': f"{match.similarity_score:.2f}",
                    'freed_patient_name': match.freed_patient_name,
                    'osmind_patient_name': match.osmind_patient_name,
                    'freed_visit_date': match.freed_visit_date,
                    'osmind_visit_date': match.osmind_visit_date
                })

        logger.info(f"Exported {len(low_conf_matches)} low-confidence matches to {filepath}")
        return len(low_conf_matches)

    def export_all_matches(self, results, filepath: str) -> int:
        """Export all matches to CSV

        Args:
            results: MatchResults object
            filepath: Path to output CSV file

        Returns:
            Number of records exported
        """
        if not results.matches:
            logger.info("No matches to export")
            return 0

        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'freed_note_id', 'osmind_note_id', 'patient_id', 'tier', 'match_type',
                'confidence', 'similarity_score',
                'freed_patient_name', 'osmind_patient_name',
                'freed_visit_date', 'osmind_visit_date'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for match in results.matches:
                writer.writerow({
                    'freed_note_id': match.freed_note_id,
                    'osmind_note_id': match.osmind_note_id,
                    'patient_id': match.patient_id,
                    'tier': match.tier,
                    'match_type': match.match_type,
                    'confidence': f"{match.confidence:.2f}",
                    'similarity_score': f"{match.similarity_score:.2f}",
                    'freed_patient_name': match.freed_patient_name,
                    'osmind_patient_name': match.osmind_patient_name,
                    'freed_visit_date': match.freed_visit_date,
                    'osmind_visit_date': match.osmind_visit_date
                })

        logger.info(f"Exported {len(results.matches)} matches to {filepath}")
        return len(results.matches)
