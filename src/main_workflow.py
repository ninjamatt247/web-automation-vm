"""Complete automation workflow: Freed.ai → OpenAI → Osmind EHR."""
from playwright.sync_api import sync_playwright
from src.utils.logger import logger
from src.utils.config import get_config
from src.utils.openai_processor import OpenAIProcessor
from src.auth.source_auth import SourceAuth
from src.auth.target_auth import TargetAuth
from src.extractors.freed_extractor import FreedExtractor
from src.inserters.osmind_inserter import OsmindInserter
from datetime import datetime
import sys
import argparse
from pathlib import Path
import json


def main():
    """Complete automation workflow."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Automated patient notes transfer: Freed.ai → OpenAI → Osmind EHR')
    parser.add_argument('--days', type=int, default=1, help='Number of days to fetch (default: 1)')
    args = parser.parse_args()

    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"Freed.ai → OpenAI → Osmind EHR Automation")
    logger.info(f"Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    # Load configuration
    config = get_config()

    # Override days_to_fetch with command-line argument
    config.days_to_fetch = args.days

    # Validate configuration
    errors = config.validate()
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    logger.info("✓ Configuration validated successfully")
    logger.info(f"📅 Fetching records from last {config.days_to_fetch} day(s)")

    try:
        with sync_playwright() as p:
            # Launch browser
            logger.info(f"🌐 Launching browser (headless={config.headless})")
            browser = p.chromium.launch(headless=config.headless)

            # ========================================
            # STEP 1: Authenticate to Freed.ai
            # ========================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("STEP 1: Authenticating to Freed.ai")
            logger.info("=" * 80)

            source_auth = SourceAuth(config, browser)

            if not source_auth.login():
                logger.error("❌ Failed to login to Freed.ai")
                browser.close()
                sys.exit(1)

            logger.info("✓ Freed.ai authentication successful")

            # ========================================
            # STEP 2: Extract Patient Records from Freed.ai
            # ========================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("STEP 2: Extracting patient records from Freed.ai")
            logger.info("=" * 80)

            extractor = FreedExtractor(source_auth.page, days_back=config.days_to_fetch)
            patient_records = extractor.extract_all_records()

            if not patient_records:
                logger.warning("⚠️  No patient records found")
                browser.close()
                return

            logger.info(f"✓ Extracted {len(patient_records)} patient record(s)")

            # Save raw records
            if config.download_individual_files:
                saved_files = extractor.save_records()
                logger.info(f"✓ Saved {len(saved_files)} raw record file(s)")

            # ========================================
            # STEP 3: Process Records with OpenAI
            # ========================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("STEP 3: Processing records with OpenAI")
            logger.info("=" * 80)

            # Initialize OpenAI processor
            ai_processor = OpenAIProcessor(config)

            # Test OpenAI connection
            if not ai_processor.test_connection():
                logger.error("❌ OpenAI API connection failed")
                browser.close()
                sys.exit(1)

            logger.info("✓ OpenAI API connection verified")

            # Prepare records for processing
            notes_to_process = []
            for record in patient_records:
                # Extract the raw note text
                raw_note = ""

                # Try to get formatted sections first
                if record.get('sections'):
                    for section_name, section_content in record['sections'].items():
                        raw_note += f"{section_name}\n{section_content}\n\n"

                # Fallback to full text
                if not raw_note and record.get('full_text'):
                    raw_note = record['full_text']

                notes_to_process.append({
                    'patient_name': record.get('patient_name', 'Unknown'),
                    'visit_date': record.get('visit_date', ''),
                    'raw_note': raw_note
                })

            # Batch process with OpenAI
            logger.info(f"🤖 Processing {len(notes_to_process)} note(s) with OpenAI...")
            processed_notes = ai_processor.batch_clean_notes(notes_to_process)

            # Count successes
            successful_notes = [n for n in processed_notes if n.get('processing_status') == 'success']
            logger.info(f"✓ Successfully processed {len(successful_notes)}/{len(processed_notes)} note(s)")

            if not successful_notes:
                logger.error("❌ No notes were successfully processed")
                browser.close()
                sys.exit(1)

            # Save processed notes
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            processed_dir = Path("/app/data/temp/processed")
            processed_dir.mkdir(parents=True, exist_ok=True)

            for i, note in enumerate(successful_notes):
                patient_name = note.get('patient_name', f'patient_{i+1}')
                safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).strip()
                safe_name = safe_name.replace(' ', '_')

                filename = f"{timestamp}_{safe_name}_cleaned.json"
                filepath = processed_dir / filename

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(note, f, indent=2, ensure_ascii=False)

                logger.info(f"💾 Saved processed note: {filepath}")

            # ========================================
            # STEP 4: Authenticate to Osmind EHR
            # ========================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("STEP 4: Authenticating to Osmind EHR")
            logger.info("=" * 80)

            target_auth = TargetAuth(config, browser)

            if not target_auth.login():
                logger.error("❌ Failed to login to Osmind EHR")
                browser.close()
                sys.exit(1)

            logger.info("✓ Osmind EHR authentication successful")

            # ========================================
            # STEP 5: Upload Notes to Osmind EHR
            # ========================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("STEP 5: Uploading notes to Osmind EHR")
            logger.info("=" * 80)

            inserter = OsmindInserter(
                target_auth.page,
                retry_attempts=config.retry_attempts,
                retry_delay=config.retry_delay
            )

            upload_results = inserter.batch_upload_notes(successful_notes)

            logger.info(f"✓ Upload complete: {upload_results}")

            # ========================================
            # STEP 6: Cleanup and Summary
            # ========================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("STEP 6: Cleanup and logout")
            logger.info("=" * 80)

            source_auth.logout()
            target_auth.logout()
            browser.close()

            # Archive processed files
            if config.download_individual_files:
                archive_dir = Path("/app/data/archive")
                archive_dir.mkdir(parents=True, exist_ok=True)

                for file_path in saved_files:
                    try:
                        file_path_obj = Path(file_path)
                        if file_path_obj.exists():
                            archive_path = archive_dir / f"{timestamp}_{file_path_obj.name}"
                            file_path_obj.rename(archive_path)
                    except:
                        pass

            # ========================================
            # Final Summary
            # ========================================
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("")
            logger.info("=" * 80)
            logger.info("AUTOMATION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"⏰ Start Time:          {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏰ End Time:            {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏱️  Duration:            {duration:.2f} seconds")
            logger.info("")
            logger.info(f"📊 Records Extracted:   {len(patient_records)}")
            logger.info(f"🤖 AI Processed:        {len(successful_notes)}/{len(processed_notes)}")
            logger.info(f"📤 Successfully Uploaded: {upload_results['success']}")
            logger.info(f"❌ Failed Uploads:      {upload_results['failure']}")
            logger.info(f"✅ Success Rate:        {upload_results['success']/upload_results['total']*100:.1f}%")
            logger.info("=" * 80)

            if upload_results['success'] > 0:
                logger.info("✅ Automation completed successfully")
            else:
                logger.warning("⚠️  Automation completed with no successful uploads")

            logger.info("=" * 80)

    except KeyboardInterrupt:
        logger.warning("⚠️  Automation interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"❌ Automation failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
