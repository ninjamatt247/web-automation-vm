"""Pre/post validation for fuzzy matching"""

import sqlite3
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class MatchValidator:
    """Validate database schema, data availability, and match results"""

    def __init__(self, db_path: str):
        """Initialize validator

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def validate_database_schema(self) -> Dict:
        """Validate that required tables and columns exist

        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        required_tables = {
            'patients': ['id', 'name', 'freed_patient_id', 'osmind_patient_id'],
            'freed_notes': ['id', 'patient_id', 'visit_date', 'note_text'],
            'osmind_notes': ['id', 'patient_id', 'visit_date', 'note_text', 'has_freed_content'],
            'combined_notes': ['id', 'patient_id', 'freed_note_id', 'osmind_note_id',
                             'match_tier', 'match_confidence', 'match_type', 'similarity_score']
        }

        for table, columns in required_tables.items():
            # Check table exists
            self.cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name=?
            """, (table,))

            if not self.cursor.fetchone():
                results['valid'] = False
                results['errors'].append(f"Required table '{table}' does not exist")
                continue

            # Check columns exist
            self.cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = {row['name'] for row in self.cursor.fetchall()}

            for column in columns:
                if column not in existing_columns:
                    results['valid'] = False
                    results['errors'].append(f"Required column '{table}.{column}' does not exist")

        logger.info(f"Schema validation: {'PASSED' if results['valid'] else 'FAILED'}")
        return results

    def validate_data_availability(self) -> Dict:
        """Check that required data is available

        Returns:
            Dictionary with data statistics and validation results
        """
        results = {
            'valid': True,
            'stats': {},
            'warnings': []
        }

        # Count records
        self.cursor.execute("SELECT COUNT(*) as count FROM patients")
        results['stats']['patients'] = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) as count FROM freed_notes")
        results['stats']['freed_notes'] = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) as count FROM osmind_notes")
        results['stats']['osmind_notes'] = self.cursor.fetchone()['count']

        self.cursor.execute("SELECT COUNT(*) as count FROM combined_notes")
        results['stats']['combined_notes'] = self.cursor.fetchone()['count']

        # Validate minimum data
        if results['stats']['freed_notes'] == 0:
            results['valid'] = False
            results['warnings'].append("No Freed notes found - nothing to match")

        if results['stats']['osmind_notes'] == 0:
            results['valid'] = False
            results['warnings'].append("No Osmind notes found - cannot match")

        # Check for orphaned notes
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM freed_notes
            WHERE patient_id NOT IN (SELECT id FROM patients)
        """)
        orphaned_freed = self.cursor.fetchone()['count']
        if orphaned_freed > 0:
            results['warnings'].append(f"{orphaned_freed} Freed notes have invalid patient_id")

        self.cursor.execute("""
            SELECT COUNT(*) as count FROM osmind_notes
            WHERE patient_id NOT IN (SELECT id FROM patients)
        """)
        orphaned_osmind = self.cursor.fetchone()['count']
        if orphaned_osmind > 0:
            results['warnings'].append(f"{orphaned_osmind} Osmind notes have invalid patient_id")

        # Check date quality
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM freed_notes
            WHERE visit_date IS NULL OR visit_date = ''
        """)
        null_freed_dates = self.cursor.fetchone()['count']
        if null_freed_dates > 0:
            results['warnings'].append(f"{null_freed_dates} Freed notes missing visit_date")

        self.cursor.execute("""
            SELECT COUNT(*) as count FROM osmind_notes
            WHERE visit_date IS NULL OR visit_date = ''
        """)
        null_osmind_dates = self.cursor.fetchone()['count']
        if null_osmind_dates > 0:
            results['warnings'].append(f"{null_osmind_dates} Osmind notes missing visit_date")

        logger.info(f"Data validation: {'PASSED' if results['valid'] else 'FAILED'}")
        logger.info(f"  Patients: {results['stats']['patients']}")
        logger.info(f"  Freed Notes: {results['stats']['freed_notes']}")
        logger.info(f"  Osmind Notes: {results['stats']['osmind_notes']}")
        logger.info(f"  Combined Notes: {results['stats']['combined_notes']}")

        return results

    def validate_match_results(self, results) -> List[str]:
        """Validate matching results for issues

        Args:
            results: MatchResults object

        Returns:
            List of validation warnings
        """
        warnings = []

        # Check match rate
        if results.total_freed > 0:
            match_rate = results.matched / results.total_freed
            if match_rate < 0.80:
                warnings.append(f"Low match rate: {match_rate:.1%} (expected >80%)")

        # Check for low confidence matches
        low_conf_count = sum(1 for m in results.matches if m.confidence < 0.70)
        if low_conf_count > 0:
            warnings.append(f"{low_conf_count} matches below 0.70 confidence threshold")

        # Check for errors
        if results.errors:
            warnings.append(f"{len(results.errors)} errors occurred during matching")

        return warnings

    def check_duplicate_links(self) -> List[Dict]:
        """Check for duplicate links in combined_notes

        Returns:
            List of duplicate link records
        """
        self.cursor.execute("""
            SELECT freed_note_id, osmind_note_id, COUNT(*) as count
            FROM combined_notes
            WHERE freed_note_id IS NOT NULL AND osmind_note_id IS NOT NULL
            GROUP BY freed_note_id, osmind_note_id
            HAVING COUNT(*) > 1
        """)

        duplicates = [dict(row) for row in self.cursor.fetchall()]

        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate links in combined_notes")

        return duplicates

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
