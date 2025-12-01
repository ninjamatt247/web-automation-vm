#!/usr/bin/env python3
"""
Example: Multi-Step Note Processing

This script demonstrates how to use the multi-step verification system
to process clinical notes with 100% compliance guarantees.
"""

from src.utils.openai_processor import OpenAIProcessor
from src.utils.config import AppConfig
from src.utils.logger import logger
import json


def main():
    """Demonstrate multi-step note processing."""

    # Initialize configuration and processor
    print("🔧 Initializing OpenAI processor with multi-step verification...")
    config = AppConfig.from_env()
    processor = OpenAIProcessor(config, use_multi_step=True)

    # Example raw note
    raw_note = """
    Patient: John Doe
    Date: 12/1/2025

    Chief Complaint: Follow-up for anxiety and depression

    The patient presents today for follow-up of anxiety and depression.
    Reports improved mood on current medications. No suicidal ideation.
    Continues sertraline 100mg daily. Tolerating well. No side effects.

    Vital Signs: BP 120/80, HR 72

    Mental Status: Alert, cooperative, normal mood and affect.

    Assessment: Generalized anxiety disorder, Major depressive disorder

    Plan: Continue sertraline 100mg daily. Follow up in 4 weeks.
    Call 911 for emergencies.
    """

    print("\n" + "="*70)
    print("📄 RAW NOTE")
    print("="*70)
    print(raw_note)

    # Process note with multi-step verification
    print("\n" + "="*70)
    print("⚙️  PROCESSING WITH MULTI-STEP VERIFICATION")
    print("="*70)

    result = processor.multi_step_clean_patient_note(raw_note)

    # Display results
    print("\n" + "="*70)
    print("📊 PROCESSING RESULTS")
    print("="*70)

    print(f"\nStatus: {result['processing_status'].upper()}")
    print(f"Tokens Used: {result['tokens_used']}")
    print(f"Verification Status: {result.get('step2_status', 'N/A')}")
    print(f"Requires Human Review: {'YES ⚠️' if result['requires_human_intervention'] else 'NO ✅'}")

    # Show validation summary
    if 'validation_summary' in result:
        print("\n" + "="*70)
        print("✅ VALIDATION SUMMARY")
        print("="*70)
        print(result['validation_summary'])

    # Show cleaned note
    print("\n" + "="*70)
    print("📝 CLEANED NOTE")
    print("="*70)
    if result.get('cleaned_note'):
        print(result['cleaned_note'])
    else:
        print("⚠️  Note processing failed")
        if 'error' in result:
            print(f"Error: {result['error']}")

    # Show validation details
    if 'validation_report' in result:
        report = result['validation_report']

        print("\n" + "="*70)
        print("🔍 DETAILED VALIDATION REPORT")
        print("="*70)

        print(f"\nTotal Checks: {report.total_checks}")
        print(f"Passed: {report.passed_checks}")
        print(f"Failed: {report.failed_checks}")

        if report.failed_checks > 0:
            print("\n📋 Failed Checks by Priority:")

            if report.critical_failures > 0:
                print(f"\n  ❌ CRITICAL ({report.critical_failures}):")
                for failure in report.get_failures_by_priority('CRITICAL'):
                    print(f"     - {failure.requirement_name}")
                    print(f"       Error: {failure.error_message}")
                    if failure.details:
                        print(f"       Details: {failure.details}")

            if report.high_failures > 0:
                print(f"\n  ⚠️  HIGH ({report.high_failures}):")
                for failure in report.get_failures_by_priority('HIGH'):
                    print(f"     - {failure.requirement_name}")
                    print(f"       Error: {failure.error_message}")

            if report.medium_failures > 0:
                print(f"\n  ⚡ MEDIUM ({report.medium_failures}):")
                for failure in report.get_failures_by_priority('MEDIUM'):
                    print(f"     - {failure.requirement_name}")

            if report.low_failures > 0:
                print(f"\n  ℹ️  LOW ({report.low_failures}):")
                for failure in report.get_failures_by_priority('LOW'):
                    print(f"     - {failure.requirement_name}")

        # Human intervention reasons
        if report.requires_human_intervention:
            print("\n" + "="*70)
            print("🚨 HUMAN INTERVENTION REQUIRED")
            print("="*70)
            for reason in report.human_intervention_reasons:
                print(f"  • {reason}")

    # Export results to JSON
    output_file = "data/multi_step_example_results.json"
    print(f"\n💾 Exporting detailed results to {output_file}...")

    # Prepare JSON-serializable result
    json_result = {
        'processing_status': result['processing_status'],
        'requires_human_intervention': result['requires_human_intervention'],
        'tokens_used': result['tokens_used'],
        'step2_status': result.get('step2_status'),
        'cleaned_note': result.get('cleaned_note'),
        'validation_report': result['validation_report'].to_dict() if 'validation_report' in result else None
    }

    with open(output_file, 'w') as f:
        json.dump(json_result, f, indent=2)

    print(f"✅ Results exported successfully")

    print("\n" + "="*70)
    print("✨ EXAMPLE COMPLETE")
    print("="*70)


def example_batch_processing():
    """Demonstrate batch processing with multi-step verification."""

    print("\n" + "="*70)
    print("📦 BATCH PROCESSING EXAMPLE")
    print("="*70)

    config = AppConfig.from_env()
    processor = OpenAIProcessor(config, use_multi_step=True)

    # Multiple notes to process
    notes = [
        {
            'patient_name': 'John Doe',
            'date': '2025-12-01',
            'raw_note': 'Sample note 1 content...'
        },
        {
            'patient_name': 'Jane Smith',
            'date': '2025-12-01',
            'raw_note': 'Sample note 2 content...'
        }
    ]

    print(f"\n📄 Processing {len(notes)} notes with multi-step verification...")
    results = processor.batch_clean_notes(notes, use_multi_step=True)

    # Summarize results
    success = sum(1 for r in results if r['processing_status'] == 'success')
    needs_review = sum(1 for r in results if r.get('requires_human_intervention'))

    print(f"\n📊 Batch Results:")
    print(f"  ✅ Success: {success}")
    print(f"  ⚠️  Needs Review: {needs_review}")
    print(f"  ❌ Failed: {len(results) - success - needs_review}")

    # Show details for notes needing review
    if needs_review > 0:
        print("\n🚨 Notes Requiring Human Review:")
        for note in results:
            if note.get('requires_human_intervention'):
                print(f"\n  Patient: {note['patient_name']}")
                if 'validation_summary' in note:
                    print(f"  {note['validation_summary']}")


def example_custom_prompts():
    """Demonstrate custom prompt usage."""

    print("\n" + "="*70)
    print("🎨 CUSTOM PROMPTS EXAMPLE")
    print("="*70)

    config = AppConfig.from_env()
    processor = OpenAIProcessor(config, use_multi_step=True)

    # Custom initial prompt
    custom_initial = """
    You are a clinical documentation specialist.
    Format this note in APSO order with extreme attention to detail.
    """

    # Custom verification prompt
    custom_verification = """
    Review this note and ensure it meets all requirements.
    Return STATUS: VERIFIED if perfect, CORRECTED if you fixed issues,
    or NEEDS_HUMAN_REVIEW if critical errors remain.
    """

    raw_note = "Sample clinical note..."

    print("\n🔧 Processing with custom prompts...")
    result = processor.multi_step_clean_patient_note(
        raw_note,
        custom_initial_prompt=custom_initial,
        custom_verification_prompt=custom_verification
    )

    print(f"✅ Processing complete: {result['processing_status']}")


if __name__ == "__main__":
    # Run main example
    main()

    # Uncomment to run additional examples:
    # example_batch_processing()
    # example_custom_prompts()
