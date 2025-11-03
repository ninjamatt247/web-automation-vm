#!/usr/bin/env python3
"""Test script: Extract from Freed.ai and process with OpenAI (no Osmind upload)."""
import os
import sys
import argparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from datetime import datetime
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.logger import logger
from utils.config import get_config
from utils.openai_processor import OpenAIProcessor
from auth.source_auth import SourceAuth
from extractors.freed_extractor import FreedExtractor


def main():
    """Test extraction and AI processing only."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Extract patient records from Freed.ai and process with OpenAI')
    parser.add_argument('--days', type=int, default=1, help='Number of days to fetch (default: 1)')
    args = parser.parse_args()

    print("=" * 80)
    print("TEST: Freed.ai Extraction → OpenAI Processing")
    print("=" * 80)
    print()

    start_time = datetime.now()

    # Load configuration
    try:
        config = get_config()
        # Override days_to_fetch with command-line argument
        config.days_to_fetch = args.days

        print(f"✓ Configuration loaded")
        print(f"  - Freed.ai: {config.source_url}")
        print(f"  - OpenAI Model: {config.openai_model}")
        print(f"  - Days to fetch: {config.days_to_fetch}")
        print()
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return

    # Validate OpenAI key
    if not config.openai_api_key or config.openai_api_key == "your_openai_api_key_here":
        print("❌ ERROR: OpenAI API key not configured!")
        print()
        print("Please add your OpenAI API key to config/.env:")
        print("  OPENAI_API_KEY=sk-your-key-here")
        print()
        print("Get your key at: https://platform.openai.com/api-keys")
        return

    try:
        with sync_playwright() as p:
            # ========================================
            # STEP 1: Login to Freed.ai
            # ========================================
            print("=" * 80)
            print("STEP 1: Authenticating to Freed.ai")
            print("=" * 80)
            print()

            browser = p.chromium.launch(
                headless=False,  # Visible for testing
                slow_mo=500
            )

            source_auth = SourceAuth(config, browser)

            print("🔐 Logging into Freed.ai...")
            if not source_auth.login():
                print("❌ Failed to login to Freed.ai")
                browser.close()
                return

            print("✅ Freed.ai authentication successful")
            print(f"   Current URL: {source_auth.page.url}")
            print()

            # ========================================
            # STEP 2: Extract Patient Records
            # ========================================
            print("=" * 80)
            print("STEP 2: Extracting patient records")
            print("=" * 80)
            print()

            extractor = FreedExtractor(source_auth.page, days_back=config.days_to_fetch)

            print(f"📋 Fetching records from last {config.days_to_fetch} day(s)...")
            patient_records = extractor.extract_all_records()

            if not patient_records:
                print("⚠️  No patient records found")
                print()
                print("This could mean:")
                print("  - No patients in the last day")
                print("  - Selectors need adjustment for your Freed.ai interface")
                print()
                print("Browser will stay open for 60 seconds for inspection...")
                time.sleep(60)
                browser.close()
                return

            print(f"✅ Extracted {len(patient_records)} patient record(s)")
            print()

            # Show extracted records
            for i, record in enumerate(patient_records):
                print(f"  {i+1}. {record.get('patient_name', 'Unknown')}")
                print(f"     Date: {record.get('visit_date', 'Unknown')}")
                print(f"     Sections: {len(record.get('sections', {}))} sections")
                print()

            # Save raw records
            print("💾 Saving raw records...")
            saved_files = extractor.save_records(output_dir="data/temp")
            for file_path in saved_files:
                print(f"   Saved: {file_path}")
            print()

            # ========================================
            # STEP 3: Test OpenAI Connection
            # ========================================
            print("=" * 80)
            print("STEP 3: Testing OpenAI API")
            print("=" * 80)
            print()

            ai_processor = OpenAIProcessor(config)

            print("🤖 Testing OpenAI API connection...")
            if not ai_processor.test_connection():
                print("❌ OpenAI API connection failed")
                print()
                print("Please check:")
                print("  - API key is correct")
                print("  - You have credits in your OpenAI account")
                print("  - API key has proper permissions")
                print()
                input("Press Enter to close browser...")
                browser.close()
                return

            print("✅ OpenAI API connection successful")
            print()

            # ========================================
            # STEP 4: Process with OpenAI
            # ========================================
            print("=" * 80)
            print("STEP 4: Processing notes with OpenAI")
            print("=" * 80)
            print()

            # Prepare notes for processing
            notes_to_process = []
            for record in patient_records:
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

            print(f"🤖 Processing {len(notes_to_process)} note(s) with OpenAI...")
            print(f"   Model: {config.openai_model}")
            print(f"   Max tokens: {config.openai_max_tokens}")
            print()

            # Process each note and show progress
            processed_notes = []
            for i, note_data in enumerate(notes_to_process):
                patient_name = note_data['patient_name']
                print(f"   [{i+1}/{len(notes_to_process)}] Processing {patient_name}...")

                cleaned_note = ai_processor.clean_patient_note(note_data['raw_note'])

                if cleaned_note:
                    note_data['cleaned_note'] = cleaned_note
                    note_data['processing_status'] = 'success'
                    print(f"       ✅ Success")
                    processed_notes.append(note_data)
                else:
                    note_data['cleaned_note'] = None
                    note_data['processing_status'] = 'failed'
                    print(f"       ❌ Failed")
                    processed_notes.append(note_data)

                print()

            # Show results
            successful_notes = [n for n in processed_notes if n.get('processing_status') == 'success']
            print(f"✅ Successfully processed {len(successful_notes)}/{len(processed_notes)} note(s)")
            print()

            # Save processed notes
            if successful_notes:
                print("💾 Saving processed notes...")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                processed_dir = Path("data/temp/processed")
                processed_dir.mkdir(parents=True, exist_ok=True)

                for i, note in enumerate(successful_notes):
                    patient_name = note.get('patient_name', f'patient_{i+1}')
                    safe_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).strip()
                    safe_name = safe_name.replace(' ', '_')

                    filename = f"{timestamp}_{safe_name}_cleaned.json"
                    filepath = processed_dir / filename

                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(note, f, indent=2, ensure_ascii=False)

                    print(f"   Saved: {filepath}")

                print()

                # Show preview of first cleaned note
                if successful_notes:
                    print("=" * 80)
                    print("PREVIEW: First Cleaned Note")
                    print("=" * 80)
                    print()
                    first_note = successful_notes[0]
                    print(f"Patient: {first_note['patient_name']}")
                    print(f"Date: {first_note['visit_date']}")
                    print()
                    print("Cleaned Note:")
                    print("-" * 80)
                    print(first_note['cleaned_note'][:500])
                    if len(first_note['cleaned_note']) > 500:
                        print("... (truncated)")
                    print("-" * 80)
                    print()

            # ========================================
            # Summary
            # ========================================
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            print()
            print("=" * 80)
            print("TEST COMPLETE")
            print("=" * 80)
            print()
            print(f"⏱️  Duration: {duration:.2f} seconds")
            print(f"📊 Records Extracted: {len(patient_records)}")
            print(f"🤖 AI Processed: {len(successful_notes)}/{len(processed_notes)}")
            print()
            print("✅ Next step: Configure Osmind credentials and run full workflow")
            print()
            print("Files saved to:")
            print(f"  - Raw: data/temp/")
            print(f"  - Processed: data/temp/processed/")
            print()

            print("Browser will stay open for 60 seconds for inspection...")
            time.sleep(60)

            # Cleanup
            source_auth.logout()
            browser.close()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return

    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()
