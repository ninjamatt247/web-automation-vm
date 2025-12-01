#!/usr/bin/env python3
"""
Migrate existing JSON comparison data to SQLite database
"""

import json
import sys
from pathlib import Path
from database import Database

def migrate_json_files(data_dir: Path, db: Database):
    """Migrate all comparison JSON files to database"""

    # Find all comparison JSON files
    json_files = list(data_dir.glob("comparison_*.json"))

    if not json_files:
        print("No comparison JSON files found in data directory")
        return

    print(f"Found {len(json_files)} comparison files to migrate")
    print()

    migrated_count = 0
    skipped_count = 0

    for json_file in sorted(json_files):
        try:
            print(f"Processing: {json_file.name}")

            with open(json_file, 'r') as f:
                data = json.load(f)

            # Check if already migrated
            timestamp = data.get('timestamp', '')
            existing = db.get_comparison_by_timestamp(timestamp)

            if existing:
                print(f"  ⏭️  Skipped (already in database)")
                skipped_count += 1
                continue

            # Create comparison record
            comparison_id = db.create_comparison(
                timestamp=timestamp,
                method=data.get('method', 'unknown'),
                total_notes=data.get('total_notes', 0),
                complete=data.get('complete', 0),
                missing=data.get('missing', 0),
                incomplete=data.get('incomplete', 0),
                to_process=data.get('to_process', 0)
            )

            # Add all comparison results
            results = data.get('results', [])
            for result in results:
                db.add_comparison_result(
                    comparison_id=comparison_id,
                    patient_name=result.get('patient_name', 'Unknown'),
                    visit_date=result.get('visit_date', ''),
                    in_freed=result.get('in_freed', False),
                    in_osmind=result.get('in_osmind', False),
                    has_freed_content=result.get('has_freed_content', False),
                    is_signed=result.get('is_signed', False),
                    actual_date=result.get('actual_date'),
                    note_length_freed=result.get('note_length_freed', 0)
                )

            print(f"  ✅ Migrated {len(results)} results")
            migrated_count += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue

    print()
    print("=" * 60)
    print(f"Migration Summary:")
    print(f"  ✅ Migrated: {migrated_count} files")
    print(f"  ⏭️  Skipped: {skipped_count} files")
    print(f"  📊 Total: {len(json_files)} files")
    print("=" * 60)

def main():
    """Main migration process"""
    print("=" * 60)
    print("JSON to SQLite Migration Tool")
    print("=" * 60)
    print()

    # Initialize database
    backend_dir = Path(__file__).parent
    db = Database()

    # Get data directory (3 levels up from backend)
    data_dir = backend_dir.parent.parent / "data"

    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        sys.exit(1)

    print(f"📂 Data directory: {data_dir}")
    print(f"💾 Database: {db.db_path}")
    print()

    # Perform migration
    migrate_json_files(data_dir, db)

    # Show database statistics
    print()
    print("Database Statistics:")
    print(f"  Patients: {len(db.get_all_patients())}")
    print(f"  Comparisons: {len(db.get_all_comparisons())}")
    print()

    db.close()

if __name__ == "__main__":
    main()
