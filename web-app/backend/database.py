#!/usr/bin/env python3
"""
SQLite database module for medical note processing
"""

import sqlite3
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json

# Add src to path for logger import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from utils.logger import logger

class Database:
    """SQLite database handler for medical notes"""

    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        if db_path is None:
            # Default to backend directory
            backend_dir = Path(__file__).parent
            db_path = backend_dir / "medical_notes.db"

        self.db_path = str(db_path)
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Create database connection"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()

    def _create_tables(self):
        """Create database tables if they don't exist"""

        # Patients table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                freed_patient_id TEXT UNIQUE,
                osmind_patient_id TEXT,
                freed_metadata TEXT,
                osmind_metadata TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add osmind columns to patients table if they don't exist (migration)
        try:
            self.cursor.execute("ALTER TABLE patients ADD COLUMN osmind_patient_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            self.cursor.execute("ALTER TABLE patients ADD COLUMN freed_metadata TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            self.cursor.execute("ALTER TABLE patients ADD COLUMN osmind_metadata TEXT")
        except sqlite3.OperationalError:
            pass

        # Create unique index on osmind_patient_id
        self.cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_osmind_patient_id
            ON patients(osmind_patient_id)
        """)

        # Comparisons table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS comparisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL UNIQUE,
                method TEXT NOT NULL,
                total_notes INTEGER NOT NULL,
                complete INTEGER NOT NULL,
                missing INTEGER NOT NULL,
                incomplete INTEGER NOT NULL,
                to_process INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Comparison results table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS comparison_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comparison_id INTEGER NOT NULL,
                patient_id INTEGER NOT NULL,
                visit_date TEXT,
                in_freed BOOLEAN NOT NULL,
                in_osmind BOOLEAN NOT NULL,
                has_freed_content BOOLEAN NOT NULL,
                is_signed BOOLEAN NOT NULL,
                actual_date TEXT,
                note_length_freed INTEGER DEFAULT 0,
                FOREIGN KEY (comparison_id) REFERENCES comparisons(id),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)

        # Freed.ai notes table (raw notes from Freed.ai)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS freed_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                freed_visit_id TEXT UNIQUE,
                visit_date TEXT,
                note_text TEXT NOT NULL,
                full_text TEXT,
                sections TEXT,
                description TEXT,
                tags TEXT,
                note_length INTEGER DEFAULT 0,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)

        # Osmind notes table (raw notes from Osmind) - Enhanced to match FreedNotes schema
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS osmind_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                patient_name TEXT,
                osmind_note_id TEXT,
                osmind_patient_id TEXT,
                visit_date TEXT,
                note_text TEXT NOT NULL,
                full_text TEXT,
                sections TEXT,
                description TEXT,
                has_freed_content BOOLEAN DEFAULT 0,
                is_signed BOOLEAN DEFAULT 0,
                processing_status TEXT,
                note_length INTEGER DEFAULT 0,
                rendering_provider_id TEXT,
                rendering_provider_name TEXT,
                location_id TEXT,
                location_name TEXT,
                note_type TEXT,
                created_at TEXT,
                first_signed_at TEXT,
                osmind_metadata TEXT,
                sync_source TEXT DEFAULT 'api',
                last_synced_at TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)

        # Add osmind-specific columns to osmind_notes table if they don't exist (migration)
        osmind_note_columns = [
            ("patient_name", "TEXT"),
            ("osmind_note_id", "TEXT"),
            ("osmind_patient_id", "TEXT"),
            ("description", "TEXT"),
            ("rendering_provider_id", "TEXT"),
            ("rendering_provider_name", "TEXT"),
            ("location_id", "TEXT"),
            ("location_name", "TEXT"),
            ("note_type", "TEXT"),
            ("created_at", "TEXT"),
            ("first_signed_at", "TEXT"),
            ("osmind_metadata", "TEXT"),
            ("sync_source", "TEXT DEFAULT 'api'"),
            ("last_synced_at", "TEXT")
        ]

        for col_name, col_type in osmind_note_columns:
            try:
                self.cursor.execute(f"ALTER TABLE osmind_notes ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Create indexes for osmind_notes
        self.cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_osmind_note_id
            ON osmind_notes(osmind_note_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_osmind_notes_patient_id
            ON osmind_notes(osmind_patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_osmind_notes_sync_date
            ON osmind_notes(last_synced_at)
        """)

        # Combined notes table (links Freed.ai + Osmind notes with AI enhancements and sync tracking)
        # Enhanced with proper cascading foreign keys and unique constraints
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS combined_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                visit_date TEXT,
                freed_note_id INTEGER,
                osmind_note_id INTEGER,
                original_freed_note TEXT,
                final_note TEXT,
                processing_status TEXT DEFAULT 'pending',
                ai_enhanced BOOLEAN DEFAULT 0,
                uploaded_to_osmind BOOLEAN DEFAULT 0,
                last_synced TIMESTAMP,
                sent_to_ai_date TIMESTAMP,
                manual_match BOOLEAN DEFAULT 0,
                sync_status TEXT DEFAULT 'pending',
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                FOREIGN KEY (freed_note_id) REFERENCES freed_notes(id) ON DELETE SET NULL,
                FOREIGN KEY (osmind_note_id) REFERENCES osmind_notes(id) ON DELETE SET NULL,
                UNIQUE(freed_note_id, osmind_note_id),
                CHECK (freed_note_id IS NOT NULL OR osmind_note_id IS NOT NULL)
            )
        """)

        # Keep old 'notes' table for backwards compatibility (deprecated)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                visit_date TEXT,
                freed_note_id INTEGER,
                osmind_note_id INTEGER,
                original_freed_note TEXT,
                final_note TEXT,
                processing_status TEXT DEFAULT 'pending',
                ai_enhanced BOOLEAN DEFAULT 0,
                uploaded_to_osmind BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (freed_note_id) REFERENCES freed_notes(id),
                FOREIGN KEY (osmind_note_id) REFERENCES osmind_notes(id)
            )
        """)

        # Tags table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT '#3b82f6',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Patient tags junction table (many-to-many)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                UNIQUE(patient_id, tag_id)
            )
        """)

        # Sync stats table for tracking sync operations
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app TEXT NOT NULL,
                sync_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                records_synced INTEGER DEFAULT 0,
                records_failed INTEGER DEFAULT 0,
                errors TEXT,
                status TEXT DEFAULT 'pending',
                duration_seconds REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for better query performance
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_comparison_results_comparison
            ON comparison_results(comparison_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_comparison_results_patient
            ON comparison_results(patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notes_patient
            ON notes(patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_combined_notes_patient
            ON combined_notes(patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_combined_notes_freed
            ON combined_notes(freed_note_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_combined_notes_osmind
            ON combined_notes(osmind_note_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_combined_notes_sync_status
            ON combined_notes(sync_status)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_osmind_notes_patient
            ON osmind_notes(patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_freed_notes_patient
            ON freed_notes(patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_patient_tags_patient
            ON patient_tags(patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_patient_tags_tag
            ON patient_tags(tag_id)
        """)

        # PDF Forms Generated table - tracks all generated PDFs and upload status
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pdf_forms_generated (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                visit_id INTEGER,
                visit_date TEXT,
                form_type TEXT NOT NULL,
                template_name TEXT NOT NULL,
                pdf_filename TEXT NOT NULL,
                pdf_local_path TEXT,
                onedrive_url TEXT,
                onedrive_folder_name TEXT,
                upload_status TEXT DEFAULT 'pending',
                generation_status TEXT DEFAULT 'pending',
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_at TIMESTAMP,
                metadata TEXT,
                flagged_for_review BOOLEAN DEFAULT 0,
                flag_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                UNIQUE(patient_id, visit_date, form_type)
            )
        """)

        # Create indexes for pdf_forms_generated
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pdf_forms_patient
            ON pdf_forms_generated(patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pdf_forms_visit_date
            ON pdf_forms_generated(visit_date)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pdf_forms_upload_status
            ON pdf_forms_generated(upload_status)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pdf_forms_flagged
            ON pdf_forms_generated(flagged_for_review)
        """)

        # AI Processing Results table - stores multi-step processing data
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_processing_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                patient_name TEXT,
                visit_date TEXT,
                raw_note TEXT NOT NULL,
                step1_note TEXT,
                step2_note TEXT,
                final_cleaned_note TEXT,
                step2_status TEXT,
                verification_status TEXT,
                processing_status TEXT NOT NULL,
                requires_human_intervention BOOLEAN DEFAULT 0,
                human_intervention_reasons TEXT,
                total_checks INTEGER DEFAULT 0,
                passed_checks INTEGER DEFAULT 0,
                failed_checks INTEGER DEFAULT 0,
                critical_failures INTEGER DEFAULT 0,
                high_failures INTEGER DEFAULT 0,
                medium_failures INTEGER DEFAULT 0,
                low_failures INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                model_used TEXT,
                error_message TEXT,
                processing_duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by TEXT,
                review_notes TEXT,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE SET NULL
            )
        """)

        # Validation Checks table - stores individual validation check results
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processing_result_id INTEGER NOT NULL,
                requirement_id TEXT NOT NULL,
                requirement_name TEXT NOT NULL,
                priority TEXT NOT NULL,
                passed BOOLEAN NOT NULL,
                error_message TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (processing_result_id) REFERENCES ai_processing_results(id) ON DELETE CASCADE
            )
        """)

        # Human Intervention Queue table - tracks notes needing human review
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS human_intervention_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processing_result_id INTEGER NOT NULL,
                patient_id INTEGER,
                patient_name TEXT,
                visit_date TEXT,
                priority TEXT DEFAULT 'HIGH',
                intervention_reasons TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                assigned_to TEXT,
                assigned_at TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (processing_result_id) REFERENCES ai_processing_results(id) ON DELETE CASCADE,
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE SET NULL
            )
        """)

        # Create indexes for AI processing tables
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_processing_patient
            ON ai_processing_results(patient_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_processing_status
            ON ai_processing_results(processing_status)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_processing_intervention
            ON ai_processing_results(requires_human_intervention)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_validation_checks_result
            ON validation_checks(processing_result_id)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_validation_checks_priority
            ON validation_checks(priority, passed)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intervention_queue_status
            ON human_intervention_queue(status)
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intervention_queue_priority
            ON human_intervention_queue(priority, status)
        """)

        # Migrate existing database: add new columns if they don't exist
        self._migrate_database()

        self.conn.commit()

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize patient name for fuzzy matching.

        Args:
            name: Patient full name

        Returns:
            Normalized name (lowercase, no extra spaces/punctuation)
        """
        import re

        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower()

        # Remove common punctuation and special characters
        normalized = re.sub(r'[,.\-\'\"()]', '', normalized)

        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)

        # Strip leading/trailing spaces
        normalized = normalized.strip()

        return normalized

    def _migrate_database(self):
        """Add new columns to existing tables if they don't exist"""
        # Migrate notes table
        self.cursor.execute("PRAGMA table_info(notes)")
        notes_columns = {row[1] for row in self.cursor.fetchall()}

        # Add missing columns to notes table
        if 'orig_note' not in notes_columns:
            self.cursor.execute("ALTER TABLE notes ADD COLUMN orig_note TEXT")

        if 'synced' not in notes_columns:
            self.cursor.execute("ALTER TABLE notes ADD COLUMN synced TIMESTAMP")

        if 'sent_to_ai_date' not in notes_columns:
            self.cursor.execute("ALTER TABLE notes ADD COLUMN sent_to_ai_date TIMESTAMP")

        if 'manual_match' not in notes_columns:
            self.cursor.execute("ALTER TABLE notes ADD COLUMN manual_match BOOLEAN DEFAULT 0")

        # Update existing records with NULL created_at to current timestamp
        self.cursor.execute("""
            UPDATE notes
            SET created_at = CURRENT_TIMESTAMP
            WHERE created_at IS NULL
        """)

        # Copy original_freed_note to orig_note if orig_note is NULL
        self.cursor.execute("""
            UPDATE notes
            SET orig_note = original_freed_note
            WHERE orig_note IS NULL AND original_freed_note IS NOT NULL
        """)

        # Migrate osmind_notes table
        self.cursor.execute("PRAGMA table_info(osmind_notes)")
        osmind_columns = {row[1] for row in self.cursor.fetchall()}

        # Add missing columns to osmind_notes table (to match freed_notes schema)
        if 'full_text' not in osmind_columns:
            self.cursor.execute("ALTER TABLE osmind_notes ADD COLUMN full_text TEXT")

        if 'sections' not in osmind_columns:
            self.cursor.execute("ALTER TABLE osmind_notes ADD COLUMN sections TEXT")

        if 'note_length' not in osmind_columns:
            self.cursor.execute("ALTER TABLE osmind_notes ADD COLUMN note_length INTEGER DEFAULT 0")

        if 'updated_at' not in osmind_columns:
            self.cursor.execute("ALTER TABLE osmind_notes ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        # Migrate freed_notes table
        self.cursor.execute("PRAGMA table_info(freed_notes)")
        freed_columns = {row[1] for row in self.cursor.fetchall()}

        # Add missing columns to freed_notes table
        if 'description' not in freed_columns:
            self.cursor.execute("ALTER TABLE freed_notes ADD COLUMN description TEXT")

        if 'tags' not in freed_columns:
            self.cursor.execute("ALTER TABLE freed_notes ADD COLUMN tags TEXT")

        if 'note_length' not in freed_columns:
            self.cursor.execute("ALTER TABLE freed_notes ADD COLUMN note_length INTEGER DEFAULT 0")

        if 'freed_visit_id' not in freed_columns:
            self.cursor.execute("ALTER TABLE freed_notes ADD COLUMN freed_visit_id TEXT")
            # Create unique index on freed_visit_id
            try:
                self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_freed_visit_id ON freed_notes(freed_visit_id)")
            except sqlite3.OperationalError:
                pass  # Index may already exist

    # ========================================
    # Patient Operations
    # ========================================

    def sync_patient(self, freed_patient_id: str, name: str) -> int:
        """Sync/upsert patient from Freed.ai with UUID

        Args:
            freed_patient_id: Patient UUID from Freed.ai
            name: Patient name

        Returns:
            Patient database ID
        """
        # Try to get existing patient by freed_patient_id
        self.cursor.execute(
            "SELECT id FROM patients WHERE freed_patient_id = ?",
            (freed_patient_id,)
        )
        row = self.cursor.fetchone()

        if row:
            # Update name and last_seen if exists
            self.cursor.execute(
                "UPDATE patients SET name = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                (name, row['id'])
            )
            self.conn.commit()
            return row['id']

        # Create new patient
        self.cursor.execute(
            "INSERT INTO patients (freed_patient_id, name) VALUES (?, ?)",
            (freed_patient_id, name)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_patients_map(self) -> Dict:
        """Get all patients as dictionary mapping freed_patient_id to name

        Returns:
            Dictionary {freed_patient_id: name}
        """
        self.cursor.execute(
            "SELECT freed_patient_id, name FROM patients WHERE freed_patient_id IS NOT NULL"
        )
        return {row['freed_patient_id']: row['name'] for row in self.cursor.fetchall()}

    def get_or_create_patient(self, name: str, freed_patient_id: str = None) -> int:
        """Get patient ID or create new patient

        Args:
            name: Patient name
            freed_patient_id: Optional Freed.ai patient UUID

        Returns:
            Patient database ID
        """
        # If we have freed_patient_id, use sync_patient for better matching
        if freed_patient_id:
            return self.sync_patient(freed_patient_id, name)

        # Try to get existing patient by name
        self.cursor.execute("SELECT id FROM patients WHERE name = ?", (name,))
        row = self.cursor.fetchone()

        if row:
            # Update last_seen
            self.cursor.execute(
                "UPDATE patients SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                (row['id'],)
            )
            self.conn.commit()
            return row['id']

        # Create new patient
        self.cursor.execute(
            "INSERT INTO patients (name, freed_patient_id) VALUES (?, ?)",
            (name, freed_patient_id)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_patients(self) -> List[Dict]:
        """Get all patients"""
        self.cursor.execute("SELECT * FROM patients ORDER BY name")
        return [dict(row) for row in self.cursor.fetchall()]

    # ========================================
    # Comparison Operations
    # ========================================

    def create_comparison(self, timestamp: str, method: str, total_notes: int,
                         complete: int, missing: int, incomplete: int,
                         to_process: int) -> int:
        """Create a new comparison record"""
        self.cursor.execute("""
            INSERT INTO comparisons
            (timestamp, method, total_notes, complete, missing, incomplete, to_process)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, method, total_notes, complete, missing, incomplete, to_process))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_comparison_by_timestamp(self, timestamp: str) -> Optional[Dict]:
        """Get comparison by timestamp"""
        self.cursor.execute(
            "SELECT * FROM comparisons WHERE timestamp = ?",
            (timestamp,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_latest_comparison(self) -> Optional[Dict]:
        """Get the most recent comparison"""
        self.cursor.execute("""
            SELECT * FROM comparisons
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_all_comparisons(self, limit: int = 50) -> List[Dict]:
        """Get all comparisons, ordered by most recent"""
        self.cursor.execute("""
            SELECT * FROM comparisons
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    # ========================================
    # Comparison Results Operations
    # ========================================

    def add_comparison_result(self, comparison_id: int, patient_name: str,
                             visit_date: str, in_freed: bool, in_osmind: bool,
                             has_freed_content: bool, is_signed: bool,
                             actual_date: Optional[str] = None,
                             note_length_freed: int = 0):
        """Add a comparison result"""
        patient_id = self.get_or_create_patient(patient_name)

        self.cursor.execute("""
            INSERT INTO comparison_results
            (comparison_id, patient_id, visit_date, in_freed, in_osmind,
             has_freed_content, is_signed, actual_date, note_length_freed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (comparison_id, patient_id, visit_date, in_freed, in_osmind,
              has_freed_content, is_signed, actual_date, note_length_freed))
        self.conn.commit()

    def get_comparison_results(self, comparison_id: int) -> List[Dict]:
        """Get all results for a comparison"""
        self.cursor.execute("""
            SELECT cr.*, p.name as patient_name
            FROM comparison_results cr
            JOIN patients p ON cr.patient_id = p.id
            WHERE cr.comparison_id = ?
            ORDER BY p.name
        """, (comparison_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_patient_comparison_history(self, patient_name: str, limit: int = 10) -> List[Dict]:
        """Get comparison history for a specific patient"""
        self.cursor.execute("""
            SELECT cr.*, c.timestamp, c.method, c.created_at
            FROM comparison_results cr
            JOIN comparisons c ON cr.comparison_id = c.id
            JOIN patients p ON cr.patient_id = p.id
            WHERE p.name = ?
            ORDER BY c.created_at DESC
            LIMIT ?
        """, (patient_name, limit))
        return [dict(row) for row in self.cursor.fetchall()]

    def import_comparison_results(self, data: Dict) -> int:
        """Import comparison results from JSON structure

        Args:
            data: Dictionary with keys: timestamp, total_notes, complete, missing,
                  incomplete, to_process, results (list of result dicts)

        Returns:
            comparison_id: ID of created comparison record
        """
        # Create the comparison record
        comparison_id = self.create_comparison(
            timestamp=data['timestamp'],
            method='web-scraping',  # Default method
            total_notes=data['total_notes'],
            complete=data['complete'],
            missing=data['missing'],
            incomplete=data['incomplete'],
            to_process=data['to_process']
        )

        # Add all comparison results
        for result in data['results']:
            self.add_comparison_result(
                comparison_id=comparison_id,
                patient_name=result['patient_name'],
                visit_date=result.get('visit_date', ''),
                in_freed=result['in_freed'],
                in_osmind=result['in_osmind'],
                has_freed_content=result.get('has_freed_content', False),
                is_signed=result.get('is_signed', False),
                note_length_freed=result.get('note_length_freed', 0)
            )

        return comparison_id

    # ========================================
    # Freed.ai Notes Operations
    # ========================================

    def add_freed_note(self, patient_name: str, visit_date: str, note_text: str,
                       full_text: Optional[str] = None, sections: Optional[str] = None,
                       description: Optional[str] = None, tags: Optional[str] = None,
                       freed_visit_id: Optional[str] = None) -> int:
        """Add or update a note from Freed.ai (upsert based on freed_visit_id)"""
        patient_id = self.get_or_create_patient(patient_name)

        # Calculate note length
        note_length = len(note_text) if note_text else 0

        # If freed_visit_id is provided, check if note already exists
        if freed_visit_id:
            self.cursor.execute(
                "SELECT id FROM freed_notes WHERE freed_visit_id = ?",
                (freed_visit_id,)
            )
            existing = self.cursor.fetchone()

            if existing:
                # Update existing note
                self.cursor.execute("""
                    UPDATE freed_notes
                    SET patient_id = ?, visit_date = ?, note_text = ?, full_text = ?,
                        sections = ?, description = ?, tags = ?, note_length = ?, extracted_at = CURRENT_TIMESTAMP
                    WHERE freed_visit_id = ?
                """, (patient_id, visit_date, note_text, full_text, sections, description, tags, note_length, freed_visit_id))
                self.conn.commit()
                return existing['id']

        # Insert new note
        self.cursor.execute("""
            INSERT INTO freed_notes
            (patient_id, freed_visit_id, visit_date, note_text, full_text, sections, description, tags, note_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, freed_visit_id, visit_date, note_text, full_text, sections, description, tags, note_length))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_freed_notes(self, patient_name: str) -> List[Dict]:
        """Get all Freed.ai notes for a patient"""
        self.cursor.execute("""
            SELECT fn.*, p.name as patient_name
            FROM freed_notes fn
            JOIN patients p ON fn.patient_id = p.id
            WHERE p.name = ?
            ORDER BY fn.extracted_at DESC
        """, (patient_name,))
        return [dict(row) for row in self.cursor.fetchall()]

    # ========================================
    # Osmind Notes Operations
    # ========================================

    def add_osmind_note(self, patient_name: str, visit_date: str, note_text: str,
                        full_text: Optional[str] = None,
                        sections: Optional[str] = None,
                        has_freed_content: bool = False, is_signed: bool = False,
                        processing_status: Optional[str] = None,
                        note_length: int = 0) -> int:
        """Add a note from Osmind (enhanced to match FreedNotes schema)

        Args:
            patient_name: Name of the patient
            visit_date: Date of visit
            note_text: Main note content
            full_text: Full text of the note (optional)
            sections: JSON string of note sections (optional)
            has_freed_content: Whether note contains Freed.ai content
            is_signed: Whether note is signed
            processing_status: Current processing status
            note_length: Length of note in characters

        Returns:
            ID of created osmind_note
        """
        patient_id = self.get_or_create_patient(patient_name)

        # Calculate note length if not provided
        if note_length == 0 and note_text:
            note_length = len(note_text)

        self.cursor.execute("""
            INSERT INTO osmind_notes
            (patient_id, visit_date, note_text, full_text, sections,
             has_freed_content, is_signed, processing_status, note_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, visit_date, note_text, full_text, sections,
              has_freed_content, is_signed, processing_status, note_length))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_osmind_note(self, note_id: int, note_text: Optional[str] = None,
                          full_text: Optional[str] = None,
                          sections: Optional[str] = None,
                          has_freed_content: Optional[bool] = None,
                          is_signed: Optional[bool] = None,
                          processing_status: Optional[str] = None) -> None:
        """Update an existing Osmind note

        Args:
            note_id: ID of the note to update
            note_text: Updated note text
            full_text: Updated full text
            sections: Updated sections JSON
            has_freed_content: Updated Freed content flag
            is_signed: Updated signed status
            processing_status: Updated processing status
        """
        updates = []
        params = []

        if note_text is not None:
            updates.append("note_text = ?")
            params.append(note_text)
            updates.append("note_length = ?")
            params.append(len(note_text))

        if full_text is not None:
            updates.append("full_text = ?")
            params.append(full_text)

        if sections is not None:
            updates.append("sections = ?")
            params.append(sections)

        if has_freed_content is not None:
            updates.append("has_freed_content = ?")
            params.append(has_freed_content)

        if is_signed is not None:
            updates.append("is_signed = ?")
            params.append(is_signed)

        if processing_status is not None:
            updates.append("processing_status = ?")
            params.append(processing_status)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(note_id)

            query = f"""
                UPDATE osmind_notes
                SET {', '.join(updates)}
                WHERE id = ?
            """
            self.cursor.execute(query, params)
            self.conn.commit()

    def get_osmind_notes(self, patient_name: str) -> List[Dict]:
        """Get all Osmind notes for a patient"""
        self.cursor.execute("""
            SELECT osm.*, p.name as patient_name
            FROM osmind_notes osm
            JOIN patients p ON osm.patient_id = p.id
            WHERE p.name = ?
            ORDER BY osm.extracted_at DESC
        """, (patient_name,))
        return [dict(row) for row in self.cursor.fetchall()]

    def upsert_patient(self, patient_name: str, osmind_patient_id: Optional[str] = None,
                      freed_patient_id: Optional[str] = None,
                      osmind_metadata: Optional[str] = None,
                      freed_metadata: Optional[str] = None,
                      visit_date: Optional[str] = None) -> int:
        """Insert or update a patient record with fuzzy name matching.

        Matching priority:
        1. Exact osmind_patient_id match
        2. Exact freed_patient_id match
        3. Exact name match
        4. Fuzzy name match (>85% similarity) with same-day visit

        Args:
            patient_name: Patient full name
            osmind_patient_id: Osmind system patient ID (e.g., us-west-2:...)
            freed_patient_id: Freed.ai system patient ID
            osmind_metadata: JSON string of full Osmind patient data
            freed_metadata: JSON string of full Freed patient data
            visit_date: Visit date (YYYY-MM-DD) for fuzzy matching

        Returns:
            Patient ID
        """
        from difflib import SequenceMatcher

        # Try to find existing patient by system IDs or name
        existing_id = None

        # Priority 1: Exact osmind_patient_id match
        if osmind_patient_id:
            self.cursor.execute(
                "SELECT id FROM patients WHERE osmind_patient_id = ?",
                (osmind_patient_id,)
            )
            row = self.cursor.fetchone()
            if row:
                existing_id = row['id']

        # Priority 2: Exact freed_patient_id match
        if not existing_id and freed_patient_id:
            self.cursor.execute(
                "SELECT id FROM patients WHERE freed_patient_id = ?",
                (freed_patient_id,)
            )
            row = self.cursor.fetchone()
            if row:
                existing_id = row['id']

        # Priority 3: Exact name match
        if not existing_id:
            self.cursor.execute(
                "SELECT id FROM patients WHERE name = ?",
                (patient_name,)
            )
            row = self.cursor.fetchone()
            if row:
                existing_id = row['id']

        # Priority 4: Fuzzy name match with same-day visit
        if not existing_id and visit_date:
            # Normalize the input name
            normalized_input = self._normalize_name(patient_name)

            # Get all patients with notes on the same day
            self.cursor.execute("""
                SELECT DISTINCT p.id, p.name
                FROM patients p
                LEFT JOIN freed_notes fn ON p.id = fn.patient_id
                LEFT JOIN osmind_notes on_notes ON p.id = on_notes.patient_id
                WHERE DATE(fn.visit_date) = DATE(?)
                   OR DATE(on_notes.visit_date) = DATE(?)
            """, (visit_date, visit_date))

            candidates = self.cursor.fetchall()
            best_match = None
            best_score = 0.0

            for candidate in candidates:
                normalized_candidate = self._normalize_name(candidate['name'])
                similarity = SequenceMatcher(None, normalized_input, normalized_candidate).ratio()

                if similarity > best_score:
                    best_score = similarity
                    best_match = candidate['id']

            # Use fuzzy match if similarity > 85%
            if best_score > 0.85:
                existing_id = best_match
                logger.info(f"Fuzzy matched '{patient_name}' with similarity {best_score:.2%}")

        # Priority 5: Fuzzy name match within ±1 day
        if not existing_id and visit_date:
            normalized_input = self._normalize_name(patient_name)

            # Get patients with notes within ±1 day
            self.cursor.execute("""
                SELECT DISTINCT p.id, p.name
                FROM patients p
                LEFT JOIN freed_notes fn ON p.id = fn.patient_id
                LEFT JOIN osmind_notes on_notes ON p.id = on_notes.patient_id
                WHERE DATE(fn.visit_date) BETWEEN DATE(?, '-1 day') AND DATE(?, '+1 day')
                   OR DATE(on_notes.visit_date) BETWEEN DATE(?, '-1 day') AND DATE(?, '+1 day')
            """, (visit_date, visit_date, visit_date, visit_date))

            candidates = self.cursor.fetchall()
            best_match = None
            best_score = 0.0

            for candidate in candidates:
                normalized_candidate = self._normalize_name(candidate['name'])
                similarity = SequenceMatcher(None, normalized_input, normalized_candidate).ratio()

                if similarity > best_score:
                    best_score = similarity
                    best_match = candidate['id']

            # Use fuzzy match if similarity > 85%
            if best_score > 0.85:
                existing_id = best_match
                logger.info(f"Fuzzy matched '{patient_name}' (±1 day) with similarity {best_score:.2%}")

        # Priority 6: Fuzzy match without date constraint (last resort)
        if not existing_id:
            normalized_input = self._normalize_name(patient_name)

            self.cursor.execute("SELECT id, name FROM patients")
            all_patients = self.cursor.fetchall()

            best_match = None
            best_score = 0.0

            for patient in all_patients:
                normalized_candidate = self._normalize_name(patient['name'])
                similarity = SequenceMatcher(None, normalized_input, normalized_candidate).ratio()

                if similarity > best_score:
                    best_score = similarity
                    best_match = patient['id']

            # Use fuzzy match if similarity > 90% (stricter without date)
            if best_score > 0.90:
                existing_id = best_match
                logger.info(f"Fuzzy matched '{patient_name}' (no date) with similarity {best_score:.2%}")

        if existing_id:
            # Update existing patient
            updates = ["last_seen = CURRENT_TIMESTAMP"]
            params = []

            if osmind_patient_id:
                updates.append("osmind_patient_id = ?")
                params.append(osmind_patient_id)

            if freed_patient_id:
                updates.append("freed_patient_id = ?")
                params.append(freed_patient_id)

            if osmind_metadata:
                updates.append("osmind_metadata = ?")
                params.append(osmind_metadata)

            if freed_metadata:
                updates.append("freed_metadata = ?")
                params.append(freed_metadata)

            params.append(existing_id)

            query = f"""
                UPDATE patients
                SET {', '.join(updates)}
                WHERE id = ?
            """
            self.cursor.execute(query, params)
            self.conn.commit()
            return existing_id
        else:
            # Insert new patient
            self.cursor.execute("""
                INSERT INTO patients
                (name, osmind_patient_id, freed_patient_id, osmind_metadata, freed_metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (patient_name, osmind_patient_id, freed_patient_id, osmind_metadata, freed_metadata))
            self.conn.commit()
            return self.cursor.lastrowid

    def upsert_osmind_note(self, note_data: Dict) -> int:
        """Insert or update Osmind note using osmind_note_id as unique key.

        Args:
            note_data: Dictionary containing note fields

        Returns:
            Note ID
        """
        osmind_note_id = note_data.get('osmind_note_id')
        if not osmind_note_id:
            raise ValueError("osmind_note_id is required for upsert")

        # Check if note already exists
        self.cursor.execute(
            "SELECT id FROM osmind_notes WHERE osmind_note_id = ?",
            (osmind_note_id,)
        )
        row = self.cursor.fetchone()
        existing_id = row['id'] if row else None

        # Get or create patient
        patient_name = note_data.get('patient_name', '')
        osmind_patient_id = note_data.get('osmind_patient_id')
        visit_date = note_data.get('visit_date')
        patient_id = self.upsert_patient(
            patient_name=patient_name,
            osmind_patient_id=osmind_patient_id,
            visit_date=visit_date
        )

        if existing_id:
            # Update existing note
            self.cursor.execute("""
                UPDATE osmind_notes
                SET patient_id = ?,
                    patient_name = ?,
                    osmind_patient_id = ?,
                    visit_date = ?,
                    note_text = ?,
                    full_text = ?,
                    sections = ?,
                    description = ?,
                    has_freed_content = ?,
                    is_signed = ?,
                    processing_status = ?,
                    note_length = ?,
                    rendering_provider_id = ?,
                    rendering_provider_name = ?,
                    location_id = ?,
                    location_name = ?,
                    note_type = ?,
                    created_at = ?,
                    first_signed_at = ?,
                    osmind_metadata = ?,
                    sync_source = ?,
                    last_synced_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                patient_id,
                note_data.get('patient_name'),
                note_data.get('osmind_patient_id'),
                note_data.get('visit_date'),
                note_data.get('note_text', ''),
                note_data.get('full_text'),
                note_data.get('sections'),
                note_data.get('description'),
                note_data.get('has_freed_content', False),
                note_data.get('is_signed', False),
                note_data.get('processing_status'),
                note_data.get('note_length', 0),
                note_data.get('rendering_provider_id'),
                note_data.get('rendering_provider_name'),
                note_data.get('location_id'),
                note_data.get('location_name'),
                note_data.get('note_type'),
                note_data.get('created_at'),
                note_data.get('first_signed_at'),
                note_data.get('osmind_metadata'),
                note_data.get('sync_source', 'api'),
                note_data.get('last_synced_at'),
                existing_id
            ))
            self.conn.commit()
            return existing_id
        else:
            # Insert new note
            self.cursor.execute("""
                INSERT INTO osmind_notes
                (patient_id, patient_name, osmind_note_id, osmind_patient_id,
                 visit_date, note_text, full_text, sections, description,
                 has_freed_content, is_signed, processing_status, note_length,
                 rendering_provider_id, rendering_provider_name,
                 location_id, location_name, note_type,
                 created_at, first_signed_at, osmind_metadata,
                 sync_source, last_synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                patient_id,
                note_data.get('patient_name'),
                osmind_note_id,
                note_data.get('osmind_patient_id'),
                note_data.get('visit_date'),
                note_data.get('note_text', ''),
                note_data.get('full_text'),
                note_data.get('sections'),
                note_data.get('description'),
                note_data.get('has_freed_content', False),
                note_data.get('is_signed', False),
                note_data.get('processing_status'),
                note_data.get('note_length', 0),
                note_data.get('rendering_provider_id'),
                note_data.get('rendering_provider_name'),
                note_data.get('location_id'),
                note_data.get('location_name'),
                note_data.get('note_type'),
                note_data.get('created_at'),
                note_data.get('first_signed_at'),
                note_data.get('osmind_metadata'),
                note_data.get('sync_source', 'api'),
                note_data.get('last_synced_at')
            ))
            self.conn.commit()
            return self.cursor.lastrowid

    # ========================================
    # Matched Notes Operations
    # ========================================

    def add_matched_note(self, patient_name: str, visit_date: str,
                        freed_note_id: Optional[int] = None,
                        osmind_note_id: Optional[int] = None,
                        original_freed_note: Optional[str] = None,
                        final_note: Optional[str] = None,
                        processing_status: str = 'pending') -> int:
        """Add a matched note (combines Freed.ai and Osmind)"""
        patient_id = self.get_or_create_patient(patient_name)

        # Copy original_freed_note to orig_note if orig_note would be empty
        orig_note = original_freed_note

        self.cursor.execute("""
            INSERT INTO notes
            (patient_id, visit_date, freed_note_id, osmind_note_id,
             original_freed_note, orig_note, final_note, processing_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, visit_date, freed_note_id, osmind_note_id,
              original_freed_note, orig_note, final_note, processing_status))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_matched_note(self, note_id: int, final_note: str,
                           ai_enhanced: bool = True,
                           processing_status: str = 'enhanced'):
        """Update a matched note with AI-enhanced version"""
        self.cursor.execute("""
            UPDATE notes
            SET final_note = ?,
                ai_enhanced = ?,
                processing_status = ?,
                sent_to_ai_date = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (final_note, ai_enhanced, processing_status, note_id))
        self.conn.commit()

    def update_note_sync(self, note_id: int):
        """Update synced timestamp for a note"""
        self.cursor.execute("""
            UPDATE notes
            SET synced = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (note_id,))
        self.conn.commit()

    def mark_note_uploaded(self, note_id: int):
        """Mark a note as uploaded to Osmind"""
        self.cursor.execute("""
            UPDATE notes
            SET uploaded_to_osmind = 1,
                processing_status = 'uploaded',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (note_id,))
        self.conn.commit()

    # ========================================
    # Combined Notes Operations (Enhanced)
    # ========================================

    def add_combined_note(self, patient_name: str, visit_date: str,
                         freed_note_id: Optional[int] = None,
                         osmind_note_id: Optional[int] = None,
                         original_freed_note: Optional[str] = None,
                         final_note: Optional[str] = None,
                         processing_status: str = 'pending',
                         sync_status: str = 'pending') -> int:
        """Add a combined note linking Freed.ai and Osmind notes

        Args:
            patient_name: Name of the patient
            visit_date: Date of visit
            freed_note_id: Reference to freed_notes table
            osmind_note_id: Reference to osmind_notes table
            original_freed_note: Original note from Freed.ai
            final_note: Final processed note
            processing_status: AI processing status
            sync_status: Sync status with external systems

        Returns:
            ID of created combined_note
        """
        patient_id = self.get_or_create_patient(patient_name)

        self.cursor.execute("""
            INSERT INTO combined_notes
            (patient_id, visit_date, freed_note_id, osmind_note_id,
             original_freed_note, final_note, processing_status, sync_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, visit_date, freed_note_id, osmind_note_id,
              original_freed_note, final_note, processing_status, sync_status))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_combined_note(self, note_id: int,
                            final_note: Optional[str] = None,
                            processing_status: Optional[str] = None,
                            ai_enhanced: Optional[bool] = None,
                            uploaded_to_osmind: Optional[bool] = None,
                            sync_status: Optional[str] = None,
                            error_message: Optional[str] = None) -> None:
        """Update a combined note

        Args:
            note_id: ID of the note to update
            final_note: Updated final note content
            processing_status: Updated processing status
            ai_enhanced: Whether note has been AI enhanced
            uploaded_to_osmind: Whether uploaded to Osmind
            sync_status: Updated sync status
            error_message: Error message if sync failed
        """
        updates = []
        params = []

        if final_note is not None:
            updates.append("final_note = ?")
            params.append(final_note)

        if processing_status is not None:
            updates.append("processing_status = ?")
            params.append(processing_status)

        if ai_enhanced is not None:
            updates.append("ai_enhanced = ?")
            params.append(ai_enhanced)
            if ai_enhanced:
                updates.append("sent_to_ai_date = CURRENT_TIMESTAMP")

        if uploaded_to_osmind is not None:
            updates.append("uploaded_to_osmind = ?")
            params.append(uploaded_to_osmind)

        if sync_status is not None:
            updates.append("sync_status = ?")
            params.append(sync_status)
            if sync_status == 'synced':
                updates.append("last_synced = CURRENT_TIMESTAMP")

        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
            if error_message:
                updates.append("retry_count = retry_count + 1")

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(note_id)

            query = f"""
                UPDATE combined_notes
                SET {', '.join(updates)}
                WHERE id = ?
            """
            self.cursor.execute(query, params)
            self.conn.commit()

    def get_combined_notes(self, patient_name: str) -> List[Dict]:
        """Get all combined notes for a patient

        Args:
            patient_name: Name of the patient

        Returns:
            List of combined notes with patient info
        """
        self.cursor.execute("""
            SELECT cn.*, p.name as patient_name
            FROM combined_notes cn
            JOIN patients p ON cn.patient_id = p.id
            WHERE p.name = ?
            ORDER BY cn.created_at DESC
        """, (patient_name,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_all_combined_notes(self, limit: int = 100) -> List[Dict]:
        """Get all combined notes

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of combined notes with patient info
        """
        self.cursor.execute("""
            SELECT cn.*, p.name as patient_name
            FROM combined_notes cn
            JOIN patients p ON cn.patient_id = p.id
            ORDER BY cn.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_combined_notes_by_sync_status(self, sync_status: str, limit: int = 100) -> List[Dict]:
        """Get combined notes by sync status

        Args:
            sync_status: Status to filter by ('pending', 'synced', 'failed', etc.)
            limit: Maximum number of notes to return

        Returns:
            List of combined notes with matching status
        """
        self.cursor.execute("""
            SELECT cn.*, p.name as patient_name
            FROM combined_notes cn
            JOIN patients p ON cn.patient_id = p.id
            WHERE cn.sync_status = ?
            ORDER BY cn.created_at DESC
            LIMIT ?
        """, (sync_status, limit))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_combined_note_with_sources(self, note_id: int) -> Optional[Dict]:
        """Get a combined note with its source notes from Freed and Osmind

        Args:
            note_id: ID of the combined note

        Returns:
            Dictionary with combined note and source note details
        """
        self.cursor.execute("""
            SELECT
                cn.*,
                p.name as patient_name,
                fn.note_text as freed_note_text,
                fn.full_text as freed_full_text,
                fn.sections as freed_sections,
                fn.extracted_at as freed_extracted_at,
                osm.note_text as osmind_note_text,
                osm.full_text as osmind_full_text,
                osm.sections as osmind_sections,
                osm.has_freed_content as osmind_has_freed_content,
                osm.is_signed as osmind_is_signed,
                osm.extracted_at as osmind_extracted_at
            FROM combined_notes cn
            JOIN patients p ON cn.patient_id = p.id
            LEFT JOIN freed_notes fn ON cn.freed_note_id = fn.id
            LEFT JOIN osmind_notes osm ON cn.osmind_note_id = osm.id
            WHERE cn.id = ?
        """, (note_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    # ========================================
    # Relational Link Management Methods
    # ========================================

    def link_freed_to_osmind(self, freed_note_id: int, osmind_note_id: int,
                            manual_match: bool = False) -> int:
        """Link a Freed note to an Osmind note by creating a combined note

        Args:
            freed_note_id: ID of the freed_notes record
            osmind_note_id: ID of the osmind_notes record
            manual_match: Whether this is a manual match (default: False)

        Returns:
            ID of created combined_note

        Raises:
            ValueError: If notes don't exist or already linked
        """
        # Verify freed note exists
        self.cursor.execute("SELECT patient_id, visit_date, note_text FROM freed_notes WHERE id = ?",
                          (freed_note_id,))
        freed_row = self.cursor.fetchone()
        if not freed_row:
            raise ValueError(f"Freed note {freed_note_id} not found")

        # Verify osmind note exists
        self.cursor.execute("SELECT patient_id, visit_date FROM osmind_notes WHERE id = ?",
                          (osmind_note_id,))
        osmind_row = self.cursor.fetchone()
        if not osmind_row:
            raise ValueError(f"Osmind note {osmind_note_id} not found")

        # Check if already linked
        self.cursor.execute("""
            SELECT id FROM combined_notes
            WHERE freed_note_id = ? AND osmind_note_id = ?
        """, (freed_note_id, osmind_note_id))
        if self.cursor.fetchone():
            raise ValueError(f"Notes already linked: freed={freed_note_id}, osmind={osmind_note_id}")

        # Create combined note linking both
        patient_id = freed_row['patient_id']
        visit_date = freed_row['visit_date'] or osmind_row['visit_date']
        original_note = freed_row['note_text']

        self.cursor.execute("""
            INSERT INTO combined_notes
            (patient_id, visit_date, freed_note_id, osmind_note_id,
             original_freed_note, manual_match, sync_status)
            VALUES (?, ?, ?, ?, ?, ?, 'linked')
        """, (patient_id, visit_date, freed_note_id, osmind_note_id,
              original_note, manual_match))
        self.conn.commit()
        return self.cursor.lastrowid

    def link_freed_only(self, freed_note_id: int) -> int:
        """Create a combined note from only a Freed note (no Osmind match yet)

        Args:
            freed_note_id: ID of the freed_notes record

        Returns:
            ID of created combined_note
        """
        # Verify freed note exists
        self.cursor.execute("""
            SELECT patient_id, visit_date, note_text, full_text
            FROM freed_notes WHERE id = ?
        """, (freed_note_id,))
        row = self.cursor.fetchone()
        if not row:
            raise ValueError(f"Freed note {freed_note_id} not found")

        # Check if already linked
        self.cursor.execute("SELECT id FROM combined_notes WHERE freed_note_id = ?",
                          (freed_note_id,))
        if self.cursor.fetchone():
            raise ValueError(f"Freed note {freed_note_id} already has a combined note")

        # Create combined note
        self.cursor.execute("""
            INSERT INTO combined_notes
            (patient_id, visit_date, freed_note_id, original_freed_note,
             sync_status, processing_status)
            VALUES (?, ?, ?, ?, 'pending', 'unmatched')
        """, (row['patient_id'], row['visit_date'], freed_note_id, row['note_text']))
        self.conn.commit()
        return self.cursor.lastrowid

    def link_osmind_to_combined(self, combined_note_id: int, osmind_note_id: int) -> None:
        """Link an Osmind note to an existing combined note

        Args:
            combined_note_id: ID of the combined_notes record
            osmind_note_id: ID of the osmind_notes record

        Raises:
            ValueError: If records don't exist or already linked
        """
        # Verify combined note exists
        self.cursor.execute("""
            SELECT osmind_note_id, freed_note_id
            FROM combined_notes WHERE id = ?
        """, (combined_note_id,))
        row = self.cursor.fetchone()
        if not row:
            raise ValueError(f"Combined note {combined_note_id} not found")
        if row['osmind_note_id'] is not None:
            raise ValueError(f"Combined note {combined_note_id} already linked to Osmind note {row['osmind_note_id']}")

        # Verify osmind note exists
        self.cursor.execute("SELECT id FROM osmind_notes WHERE id = ?", (osmind_note_id,))
        if not self.cursor.fetchone():
            raise ValueError(f"Osmind note {osmind_note_id} not found")

        # Check for duplicate link
        freed_id = row['freed_note_id']
        if freed_id:
            self.cursor.execute("""
                SELECT id FROM combined_notes
                WHERE freed_note_id = ? AND osmind_note_id = ?
            """, (freed_id, osmind_note_id))
            if self.cursor.fetchone():
                raise ValueError(f"Osmind note {osmind_note_id} already linked to Freed note {freed_id}")

        # Update combined note
        self.cursor.execute("""
            UPDATE combined_notes
            SET osmind_note_id = ?,
                sync_status = 'linked',
                processing_status = 'matched',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (osmind_note_id, combined_note_id))
        self.conn.commit()

    def unlink_notes(self, combined_note_id: int,
                    unlink_freed: bool = False,
                    unlink_osmind: bool = False) -> None:
        """Unlink notes from a combined note

        Args:
            combined_note_id: ID of the combined_notes record
            unlink_freed: Whether to unlink the freed note
            unlink_osmind: Whether to unlink the osmind note

        Raises:
            ValueError: If combined note doesn't exist
        """
        # Verify combined note exists
        self.cursor.execute("SELECT id FROM combined_notes WHERE id = ?", (combined_note_id,))
        if not self.cursor.fetchone():
            raise ValueError(f"Combined note {combined_note_id} not found")

        updates = []
        if unlink_freed:
            updates.append("freed_note_id = NULL")
        if unlink_osmind:
            updates.append("osmind_note_id = NULL")

        if updates:
            updates.append("sync_status = 'unlinked'")
            updates.append("updated_at = CURRENT_TIMESTAMP")

            query = f"UPDATE combined_notes SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, (combined_note_id,))
            self.conn.commit()

    def get_unlinked_freed_notes(self, limit: int = 100) -> List[Dict]:
        """Get Freed notes that don't have a combined note yet

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of freed notes without combined notes
        """
        self.cursor.execute("""
            SELECT fn.*, p.name as patient_name
            FROM freed_notes fn
            JOIN patients p ON fn.patient_id = p.id
            LEFT JOIN combined_notes cn ON fn.id = cn.freed_note_id
            WHERE cn.id IS NULL
            ORDER BY fn.extracted_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_unlinked_osmind_notes(self, limit: int = 100) -> List[Dict]:
        """Get Osmind notes that don't have a combined note yet

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of osmind notes without combined notes
        """
        self.cursor.execute("""
            SELECT osm.*, p.name as patient_name
            FROM osmind_notes osm
            JOIN patients p ON osm.patient_id = p.id
            LEFT JOIN combined_notes cn ON osm.id = cn.osmind_note_id
            WHERE cn.id IS NULL
            ORDER BY osm.extracted_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_partially_linked_notes(self, limit: int = 100) -> List[Dict]:
        """Get combined notes that only have a Freed or Osmind note (not both)

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of combined notes with only one source
        """
        self.cursor.execute("""
            SELECT cn.*, p.name as patient_name,
                   CASE
                       WHEN cn.freed_note_id IS NOT NULL AND cn.osmind_note_id IS NULL THEN 'freed_only'
                       WHEN cn.freed_note_id IS NULL AND cn.osmind_note_id IS NOT NULL THEN 'osmind_only'
                   END as link_type
            FROM combined_notes cn
            JOIN patients p ON cn.patient_id = p.id
            WHERE (cn.freed_note_id IS NULL AND cn.osmind_note_id IS NOT NULL)
               OR (cn.freed_note_id IS NOT NULL AND cn.osmind_note_id IS NULL)
            ORDER BY cn.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def find_matching_notes(self, patient_name: str, visit_date: str) -> Dict:
        """Find potential matches between Freed and Osmind notes

        Args:
            patient_name: Name of the patient
            visit_date: Visit date to match

        Returns:
            Dictionary with freed_notes and osmind_notes lists
        """
        self.cursor.execute("""
            SELECT * FROM freed_notes fn
            JOIN patients p ON fn.patient_id = p.id
            WHERE p.name = ? AND fn.visit_date = ?
        """, (patient_name, visit_date))
        freed_notes = [dict(row) for row in self.cursor.fetchall()]

        self.cursor.execute("""
            SELECT * FROM osmind_notes osm
            JOIN patients p ON osm.patient_id = p.id
            WHERE p.name = ? AND osm.visit_date = ?
        """, (patient_name, visit_date))
        osmind_notes = [dict(row) for row in self.cursor.fetchall()]

        return {
            'patient_name': patient_name,
            'visit_date': visit_date,
            'freed_notes': freed_notes,
            'osmind_notes': osmind_notes,
            'can_link': len(freed_notes) > 0 and len(osmind_notes) > 0
        }

    def get_patient_notes(self, patient_name: str) -> List[Dict]:
        """Get all notes for a patient"""
        self.cursor.execute("""
            SELECT n.*, p.name as patient_name
            FROM notes n
            JOIN patients p ON n.patient_id = p.id
            WHERE p.name = ?
            ORDER BY n.created_at DESC
        """, (patient_name,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_all_notes(self, limit: int = 100) -> List[Dict]:
        """Get all notes"""
        self.cursor.execute("""
            SELECT n.*, p.name as patient_name
            FROM notes n
            JOIN patients p ON n.patient_id = p.id
            ORDER BY n.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    # ========================================
    # Tag Operations
    # ========================================

    def get_or_create_tag(self, name: str, color: str = '#3b82f6') -> int:
        """Get tag ID or create new tag"""
        # Try to get existing tag
        self.cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
        row = self.cursor.fetchone()

        if row:
            return row['id']

        # Create new tag
        self.cursor.execute(
            "INSERT INTO tags (name, color) VALUES (?, ?)",
            (name, color)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_tags(self) -> List[Dict]:
        """Get all tags"""
        self.cursor.execute("SELECT * FROM tags ORDER BY name")
        return [dict(row) for row in self.cursor.fetchall()]

    def add_patient_tag(self, patient_name: str, tag_name: str, color: str = '#3b82f6'):
        """Add a tag to a patient"""
        patient_id = self.get_or_create_patient(patient_name)
        tag_id = self.get_or_create_tag(tag_name, color)

        try:
            self.cursor.execute(
                "INSERT INTO patient_tags (patient_id, tag_id) VALUES (?, ?)",
                (patient_id, tag_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            # Tag already exists for this patient
            pass

    def remove_patient_tag(self, patient_name: str, tag_name: str):
        """Remove a tag from a patient"""
        self.cursor.execute("""
            DELETE FROM patient_tags
            WHERE patient_id = (SELECT id FROM patients WHERE name = ?)
            AND tag_id = (SELECT id FROM tags WHERE name = ?)
        """, (patient_name, tag_name))
        self.conn.commit()

    def get_patient_tags(self, patient_name: str) -> List[Dict]:
        """Get all tags for a patient"""
        self.cursor.execute("""
            SELECT t.id, t.name, t.color, pt.created_at
            FROM tags t
            JOIN patient_tags pt ON t.id = pt.tag_id
            JOIN patients p ON pt.patient_id = p.id
            WHERE p.name = ?
            ORDER BY t.name
        """, (patient_name,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_patients_by_tag(self, tag_name: str) -> List[Dict]:
        """Get all patients with a specific tag"""
        self.cursor.execute("""
            SELECT p.*
            FROM patients p
            JOIN patient_tags pt ON p.id = pt.patient_id
            JOIN tags t ON pt.tag_id = t.id
            WHERE t.name = ?
            ORDER BY p.name
        """, (tag_name,))
        return [dict(row) for row in self.cursor.fetchall()]

    def search_patients_by_tags(self, tag_names: List[str], match_all: bool = False) -> List[Dict]:
        """
        Search for patients by multiple tags

        Args:
            tag_names: List of tag names to search for
            match_all: If True, patient must have ALL tags. If False, patient must have ANY tag.

        Returns:
            List of patients with their tags
        """
        if not tag_names:
            return []

        if match_all:
            # Patient must have ALL tags (AND logic)
            placeholders = ','.join(['?' for _ in tag_names])
            self.cursor.execute(f"""
                SELECT DISTINCT p.*, GROUP_CONCAT(t.name) as tags
                FROM patients p
                JOIN patient_tags pt ON p.id = pt.patient_id
                JOIN tags t ON pt.tag_id = t.id
                WHERE p.id IN (
                    SELECT pt2.patient_id
                    FROM patient_tags pt2
                    JOIN tags t2 ON pt2.tag_id = t2.id
                    WHERE t2.name IN ({placeholders})
                    GROUP BY pt2.patient_id
                    HAVING COUNT(DISTINCT t2.name) = ?
                )
                GROUP BY p.id
                ORDER BY p.name
            """, (*tag_names, len(tag_names)))
        else:
            # Patient must have ANY tag (OR logic)
            placeholders = ','.join(['?' for _ in tag_names])
            self.cursor.execute(f"""
                SELECT DISTINCT p.*, GROUP_CONCAT(t.name) as tags
                FROM patients p
                JOIN patient_tags pt ON p.id = pt.patient_id
                JOIN tags t ON pt.tag_id = t.id
                WHERE t.name IN ({placeholders})
                GROUP BY p.id
                ORDER BY p.name
            """, tag_names)

        return [dict(row) for row in self.cursor.fetchall()]

    # ========================================
    # Sync Stats Operations
    # ========================================

    def add_sync_stat(self, app: str, records_synced: int = 0, records_failed: int = 0,
                     errors: Optional[str] = None, status: str = 'pending',
                     duration_seconds: Optional[float] = None, notes: Optional[str] = None) -> int:
        """Add a sync operation record"""
        self.cursor.execute("""
            INSERT INTO sync_stats (app, records_synced, records_failed, errors, status, duration_seconds, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (app, records_synced, records_failed, errors, status, duration_seconds, notes))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_sync_stat(self, sync_id: int, records_synced: Optional[int] = None,
                        records_failed: Optional[int] = None, errors: Optional[str] = None,
                        status: Optional[str] = None, duration_seconds: Optional[float] = None,
                        notes: Optional[str] = None) -> None:
        """Update an existing sync stat record"""
        updates = []
        params = []

        if records_synced is not None:
            updates.append("records_synced = ?")
            params.append(records_synced)
        if records_failed is not None:
            updates.append("records_failed = ?")
            params.append(records_failed)
        if errors is not None:
            updates.append("errors = ?")
            params.append(errors)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if duration_seconds is not None:
            updates.append("duration_seconds = ?")
            params.append(duration_seconds)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return

        params.append(sync_id)
        query = f"UPDATE sync_stats SET {', '.join(updates)} WHERE id = ?"
        self.cursor.execute(query, params)
        self.conn.commit()

    def get_sync_stats(self, app: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get sync statistics, optionally filtered by app"""
        if app:
            self.cursor.execute("""
                SELECT * FROM sync_stats
                WHERE app = ?
                ORDER BY sync_datetime DESC
                LIMIT ?
            """, (app, limit))
        else:
            self.cursor.execute("""
                SELECT * FROM sync_stats
                ORDER BY sync_datetime DESC
                LIMIT ?
            """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_sync_summary(self, app: Optional[str] = None, days: int = 30) -> Dict:
        """Get summary of sync operations"""
        if app:
            self.cursor.execute("""
                SELECT
                    COUNT(*) as total_syncs,
                    SUM(records_synced) as total_records,
                    SUM(records_failed) as total_failures,
                    AVG(duration_seconds) as avg_duration,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_syncs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_syncs
                FROM sync_stats
                WHERE app = ? AND sync_datetime >= datetime('now', '-' || ? || ' days')
            """, (app, days))
        else:
            self.cursor.execute("""
                SELECT
                    COUNT(*) as total_syncs,
                    SUM(records_synced) as total_records,
                    SUM(records_failed) as total_failures,
                    AVG(duration_seconds) as avg_duration,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_syncs,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_syncs
                FROM sync_stats
                WHERE sync_datetime >= datetime('now', '-' || ? || ' days')
            """, (days,))

        result = self.cursor.fetchone()
        return dict(result) if result else {}

    # ========================================
    # Analytics & Statistics
    # ========================================

    def get_comparison_trends(self, days: int = 30) -> List[Dict]:
        """Get comparison trends over time"""
        self.cursor.execute("""
            SELECT
                timestamp,
                total_notes,
                complete,
                missing,
                incomplete,
                to_process,
                created_at
            FROM comparisons
            WHERE created_at >= datetime('now', '-' || ? || ' days')
            ORDER BY created_at ASC
        """, (days,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_patient_status_changes(self, patient_name: str) -> List[Dict]:
        """Get status changes for a patient across comparisons"""
        self.cursor.execute("""
            SELECT
                c.timestamp,
                c.created_at,
                cr.visit_date,
                cr.in_osmind,
                cr.has_freed_content,
                cr.is_signed
            FROM comparison_results cr
            JOIN comparisons c ON cr.comparison_id = c.id
            JOIN patients p ON cr.patient_id = p.id
            WHERE p.name = ?
            ORDER BY c.created_at ASC
        """, (patient_name,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_completion_rate_trend(self) -> List[Dict]:
        """Get completion rate trend across all comparisons"""
        self.cursor.execute("""
            SELECT
                timestamp,
                created_at,
                total_notes,
                complete,
                ROUND(CAST(complete AS FLOAT) / total_notes * 100, 2) as completion_rate
            FROM comparisons
            WHERE total_notes > 0
            ORDER BY created_at ASC
        """)
        return [dict(row) for row in self.cursor.fetchall()]

    # ========================================
    # Export & Backup
    # ========================================

    def export_comparison_to_json(self, comparison_id: int) -> Dict:
        """Export a comparison and its results to JSON format"""
        # Get comparison
        self.cursor.execute("SELECT * FROM comparisons WHERE id = ?", (comparison_id,))
        comparison = dict(self.cursor.fetchone())

        # Get results
        results = self.get_comparison_results(comparison_id)

        # Format as original JSON structure
        export_data = {
            'timestamp': comparison['timestamp'],
            'method': comparison['method'],
            'total_notes': comparison['total_notes'],
            'complete': comparison['complete'],
            'missing': comparison['missing'],
            'incomplete': comparison['incomplete'],
            'to_process': comparison['to_process'],
            'results': [
                {
                    'patient_name': r['patient_name'],
                    'visit_date': r['visit_date'],
                    'in_freed': bool(r['in_freed']),
                    'in_osmind': bool(r['in_osmind']),
                    'has_freed_content': bool(r['has_freed_content']),
                    'is_signed': bool(r['is_signed']),
                    'actual_date': r['actual_date'],
                    'note_length_freed': r['note_length_freed']
                }
                for r in results
            ]
        }

        return export_data

    # ========================================
    # PDF Forms Operations
    # ========================================

    def add_pdf_form_record(self,
                           patient_id: int,
                           visit_date: str,
                           form_type: str,
                           template_name: str,
                           pdf_filename: str,
                           pdf_local_path: Optional[str] = None,
                           metadata: Optional[str] = None) -> int:
        """Add a PDF form generation record.

        Args:
            patient_id: Patient database ID
            visit_date: Visit date
            form_type: Type of form (progress_note, intake_form, etc.)
            template_name: PDF template name
            pdf_filename: Generated PDF filename
            pdf_local_path: Local filesystem path
            metadata: JSON metadata

        Returns:
            ID of created record
        """
        self.cursor.execute("""
            INSERT INTO pdf_forms_generated
            (patient_id, visit_date, form_type, template_name, pdf_filename,
             pdf_local_path, metadata, generation_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'generated')
        """, (patient_id, visit_date, form_type, template_name, pdf_filename,
              pdf_local_path, metadata))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_pdf_upload_status(self,
                                 pdf_form_id: int,
                                 onedrive_url: str,
                                 onedrive_folder_name: str):
        """Update PDF record after successful upload.

        Args:
            pdf_form_id: PDF form record ID
            onedrive_url: OneDrive web URL
            onedrive_folder_name: Folder name in OneDrive
        """
        self.cursor.execute("""
            UPDATE pdf_forms_generated
            SET onedrive_url = ?,
                onedrive_folder_name = ?,
                upload_status = 'uploaded',
                uploaded_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (onedrive_url, onedrive_folder_name, pdf_form_id))
        self.conn.commit()

    def flag_pdf_for_review(self,
                           pdf_form_id: int,
                           reason: str):
        """Flag a PDF form for manual review.

        Args:
            pdf_form_id: PDF form record ID
            reason: Reason for flagging
        """
        self.cursor.execute("""
            UPDATE pdf_forms_generated
            SET flagged_for_review = 1,
                flag_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reason, pdf_form_id))
        self.conn.commit()

    def get_pdf_forms_by_date_range(self,
                                   start_date: str,
                                   end_date: str) -> List[Dict]:
        """Get PDF forms generated within date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of PDF form records
        """
        self.cursor.execute("""
            SELECT pf.*, p.name as patient_name
            FROM pdf_forms_generated pf
            JOIN patients p ON pf.patient_id = p.id
            WHERE DATE(pf.visit_date) BETWEEN DATE(?) AND DATE(?)
            ORDER BY pf.created_at DESC
        """, (start_date, end_date))
        return [dict(row) for row in self.cursor.fetchall()]

    def check_pdf_already_generated(self,
                                   patient_id: int,
                                   visit_date: str,
                                   form_type: str) -> bool:
        """Check if PDF already generated for this visit.

        Args:
            patient_id: Patient ID
            visit_date: Visit date
            form_type: Form type

        Returns:
            True if already generated
        """
        self.cursor.execute("""
            SELECT id FROM pdf_forms_generated
            WHERE patient_id = ?
              AND visit_date = ?
              AND form_type = ?
              AND upload_status = 'uploaded'
        """, (patient_id, visit_date, form_type))
        return self.cursor.fetchone() is not None

    def get_flagged_pdfs(self, limit: int = 50) -> List[Dict]:
        """Get PDFs flagged for manual review.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of flagged PDF records
        """
        self.cursor.execute("""
            SELECT pf.*, p.name as patient_name
            FROM pdf_forms_generated pf
            JOIN patients p ON pf.patient_id = p.id
            WHERE pf.flagged_for_review = 1
            ORDER BY pf.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_pdf_generation_stats(self) -> Dict:
        """Get PDF generation statistics.

        Returns:
            Dictionary with statistics by upload status
        """
        self.cursor.execute("""
            SELECT
                upload_status,
                COUNT(*) as count
            FROM pdf_forms_generated
            GROUP BY upload_status
        """)
        stats = {row['upload_status']: row['count'] for row in self.cursor.fetchall()}

        # Add flagged count
        self.cursor.execute("""
            SELECT COUNT(*) as count
            FROM pdf_forms_generated
            WHERE flagged_for_review = 1
        """)
        stats['flagged'] = self.cursor.fetchone()['count']

        return stats

    # ========================================
    # AI Processing Results Operations
    # ========================================

    def store_ai_processing_result(self, result: Dict, patient_name: Optional[str] = None,
                                    visit_date: Optional[str] = None) -> int:
        """Store multi-step AI processing result in database.

        Args:
            result: Processing result dictionary from OpenAIProcessor.multi_step_clean_patient_note()
            patient_name: Optional patient name
            visit_date: Optional visit date

        Returns:
            ID of created ai_processing_results record
        """
        import json
        import time

        # Get or create patient ID if name provided
        patient_id = None
        if patient_name:
            patient_id = self.get_or_create_patient(patient_name)

        # Extract validation report data
        validation_report = result.get('validation_report')
        if validation_report:
            total_checks = validation_report.total_checks
            passed_checks = validation_report.passed_checks
            failed_checks = validation_report.failed_checks
            critical_failures = validation_report.critical_failures
            high_failures = validation_report.high_failures
            medium_failures = validation_report.medium_failures
            low_failures = validation_report.low_failures
        else:
            total_checks = passed_checks = failed_checks = 0
            critical_failures = high_failures = medium_failures = low_failures = 0

        # Store main processing result
        self.cursor.execute("""
            INSERT INTO ai_processing_results
            (patient_id, patient_name, visit_date, raw_note, step1_note, step2_note,
             final_cleaned_note, step2_status, verification_status, processing_status,
             requires_human_intervention, human_intervention_reasons,
             total_checks, passed_checks, failed_checks, critical_failures,
             high_failures, medium_failures, low_failures, tokens_used,
             model_used, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            patient_name,
            visit_date,
            result.get('raw_note', ''),
            result.get('step1_note', ''),
            result.get('step2_note', ''),
            result.get('cleaned_note', ''),
            result.get('step2_status', ''),
            result.get('verification_status', ''),
            result.get('processing_status', ''),
            result.get('requires_human_intervention', False),
            json.dumps(validation_report.human_intervention_reasons) if validation_report else None,
            total_checks,
            passed_checks,
            failed_checks,
            critical_failures,
            high_failures,
            medium_failures,
            low_failures,
            result.get('tokens_used', 0),
            result.get('model_used', ''),
            result.get('error', '')
        ))
        processing_result_id = self.cursor.lastrowid

        # Store individual validation check results
        if validation_report and hasattr(validation_report, 'validation_results'):
            for check_result in validation_report.validation_results:
                self.cursor.execute("""
                    INSERT INTO validation_checks
                    (processing_result_id, requirement_id, requirement_name, priority,
                     passed, error_message, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    processing_result_id,
                    check_result.requirement_id,
                    check_result.requirement_name,
                    check_result.priority,
                    check_result.passed,
                    check_result.error_message,
                    check_result.details
                ))

        # Add to human intervention queue if needed
        if result.get('requires_human_intervention'):
            self.add_to_intervention_queue(
                processing_result_id=processing_result_id,
                patient_id=patient_id,
                patient_name=patient_name,
                visit_date=visit_date,
                intervention_reasons=validation_report.human_intervention_reasons if validation_report else []
            )

        self.conn.commit()
        return processing_result_id

    def get_processing_result(self, result_id: int) -> Optional[Dict]:
        """Get a processing result by ID with all validation checks.

        Args:
            result_id: ID of the processing result

        Returns:
            Dictionary with processing result and validation checks
        """
        self.cursor.execute("""
            SELECT * FROM ai_processing_results WHERE id = ?
        """, (result_id,))
        row = self.cursor.fetchone()

        if not row:
            return None

        result = dict(row)

        # Get validation checks
        self.cursor.execute("""
            SELECT * FROM validation_checks
            WHERE processing_result_id = ?
            ORDER BY priority, id
        """, (result_id,))
        result['validation_checks'] = [dict(r) for r in self.cursor.fetchall()]

        return result

    def get_processing_results_by_patient(self, patient_name: str, limit: int = 50) -> List[Dict]:
        """Get all processing results for a patient.

        Args:
            patient_name: Patient name
            limit: Maximum number of results

        Returns:
            List of processing results
        """
        self.cursor.execute("""
            SELECT * FROM ai_processing_results
            WHERE patient_name = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (patient_name, limit))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_processing_results_needing_review(self, limit: int = 100) -> List[Dict]:
        """Get all processing results requiring human intervention.

        Args:
            limit: Maximum number of results

        Returns:
            List of processing results needing review
        """
        self.cursor.execute("""
            SELECT * FROM ai_processing_results
            WHERE requires_human_intervention = 1
            AND reviewed_at IS NULL
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for r in self.cursor.fetchall()]

    def mark_result_reviewed(self, result_id: int, reviewed_by: str, review_notes: Optional[str] = None):
        """Mark a processing result as reviewed.

        Args:
            result_id: ID of the processing result
            reviewed_by: Name/ID of reviewer
            review_notes: Optional notes from review
        """
        self.cursor.execute("""
            UPDATE ai_processing_results
            SET reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = ?,
                review_notes = ?
            WHERE id = ?
        """, (reviewed_by, review_notes, result_id))
        self.conn.commit()

    # ========================================
    # Human Intervention Queue Operations
    # ========================================

    def add_to_intervention_queue(self, processing_result_id: int,
                                    patient_id: Optional[int] = None,
                                    patient_name: Optional[str] = None,
                                    visit_date: Optional[str] = None,
                                    intervention_reasons: Optional[List[str]] = None,
                                    priority: str = 'HIGH') -> int:
        """Add a note to the human intervention queue.

        Args:
            processing_result_id: ID of the processing result
            patient_id: Optional patient ID
            patient_name: Optional patient name
            visit_date: Optional visit date
            intervention_reasons: List of reasons for intervention
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)

        Returns:
            ID of created queue item
        """
        import json

        reasons_json = json.dumps(intervention_reasons) if intervention_reasons else '[]'

        self.cursor.execute("""
            INSERT INTO human_intervention_queue
            (processing_result_id, patient_id, patient_name, visit_date,
             priority, intervention_reasons, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (processing_result_id, patient_id, patient_name, visit_date,
              priority, reasons_json))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_intervention_queue(self, status: Optional[str] = None,
                               priority: Optional[str] = None,
                               limit: int = 100) -> List[Dict]:
        """Get items from the human intervention queue.

        Args:
            status: Filter by status (pending, assigned, resolved)
            priority: Filter by priority (CRITICAL, HIGH, MEDIUM, LOW)
            limit: Maximum number of items

        Returns:
            List of intervention queue items
        """
        query = "SELECT * FROM human_intervention_queue WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if priority:
            query += " AND priority = ?"
            params.append(priority)

        query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
        params.append(limit)

        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]

    def assign_intervention_item(self, queue_id: int, assigned_to: str):
        """Assign an intervention queue item to a reviewer.

        Args:
            queue_id: ID of the queue item
            assigned_to: Name/ID of person assigned
        """
        self.cursor.execute("""
            UPDATE human_intervention_queue
            SET status = 'assigned',
                assigned_to = ?,
                assigned_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (assigned_to, queue_id))
        self.conn.commit()

    def resolve_intervention_item(self, queue_id: int, resolution_notes: Optional[str] = None):
        """Mark an intervention queue item as resolved.

        Args:
            queue_id: ID of the queue item
            resolution_notes: Optional notes about resolution
        """
        self.cursor.execute("""
            UPDATE human_intervention_queue
            SET status = 'resolved',
                resolved_at = CURRENT_TIMESTAMP,
                resolution_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (resolution_notes, queue_id))
        self.conn.commit()

    def get_intervention_queue_stats(self) -> Dict:
        """Get statistics about the human intervention queue.

        Returns:
            Dictionary with queue statistics
        """
        self.cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved,
                SUM(CASE WHEN priority = 'CRITICAL' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN priority = 'HIGH' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN priority = 'MEDIUM' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN priority = 'LOW' THEN 1 ELSE 0 END) as low
            FROM human_intervention_queue
            WHERE status != 'resolved'
        """)
        return dict(self.cursor.fetchone())

    # ========================================
    # AI Processing Analytics
    # ========================================

    def get_processing_stats(self, days: int = 30) -> Dict:
        """Get AI processing statistics for the last N days.

        Args:
            days: Number of days to include

        Returns:
            Dictionary with processing statistics
        """
        self.cursor.execute("""
            SELECT
                COUNT(*) as total_processed,
                SUM(CASE WHEN processing_status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN processing_status = 'success_with_warnings' THEN 1 ELSE 0 END) as warning_count,
                SUM(CASE WHEN processing_status = 'needs_review' THEN 1 ELSE 0 END) as needs_review_count,
                SUM(CASE WHEN processing_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN requires_human_intervention = 1 THEN 1 ELSE 0 END) as intervention_count,
                SUM(tokens_used) as total_tokens,
                AVG(tokens_used) as avg_tokens,
                SUM(critical_failures) as total_critical_failures,
                SUM(high_failures) as total_high_failures,
                AVG(passed_checks * 100.0 / NULLIF(total_checks, 0)) as avg_pass_rate
            FROM ai_processing_results
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        return dict(self.cursor.fetchone())

    def get_validation_failure_summary(self, days: int = 30) -> List[Dict]:
        """Get summary of most common validation failures.

        Args:
            days: Number of days to include

        Returns:
            List of validation failures with counts
        """
        self.cursor.execute("""
            SELECT
                vc.requirement_name,
                vc.priority,
                vc.error_message,
                COUNT(*) as failure_count
            FROM validation_checks vc
            JOIN ai_processing_results apr ON vc.processing_result_id = apr.id
            WHERE vc.passed = 0
            AND apr.created_at >= datetime('now', '-' || ? || ' days')
            GROUP BY vc.requirement_name, vc.priority, vc.error_message
            ORDER BY failure_count DESC, vc.priority
            LIMIT 20
        """, (days,))
        return [dict(row) for row in self.cursor.fetchall()]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
