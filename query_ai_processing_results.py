#!/usr/bin/env python3
"""
Query and view AI processing results stored in the database.

This script provides utilities to:
- View all processing results
- Filter by status or patient
- View human intervention queue
- Get processing statistics
- View detailed validation results
"""

import sys
from pathlib import Path

# Add web-app backend to path
backend_path = Path(__file__).parent / "web-app" / "backend"
sys.path.insert(0, str(backend_path))

from database import Database
import json
from datetime import datetime


def print_separator(char="=", length=70):
    """Print a separator line."""
    print(char * length)


def print_processing_result(result):
    """Print a single processing result in detail."""
    print(f"\n{'='*70}")
    print(f"Processing Result ID: {result['id']}")
    print(f"{'='*70}")
    print(f"Patient: {result.get('patient_name', 'N/A')}")
    print(f"Visit Date: {result.get('visit_date', 'N/A')}")
    print(f"Processing Status: {result['processing_status']}")
    print(f"Needs Human Review: {'YES ⚠️' if result['requires_human_intervention'] else 'NO ✅'}")
    print(f"Created: {result['created_at']}")
    print(f"\nTokens Used: {result['tokens_used']}")
    print(f"Model: {result.get('model_used', 'N/A')}")

    # Validation summary
    if result['total_checks'] > 0:
        print(f"\nValidation Summary:")
        print(f"  Total Checks: {result['total_checks']}")
        print(f"  Passed: {result['passed_checks']} ({result['passed_checks']*100//result['total_checks']}%)")
        print(f"  Failed: {result['failed_checks']}")

        if result['critical_failures'] > 0:
            print(f"  ❌ CRITICAL Failures: {result['critical_failures']}")
        if result['high_failures'] > 0:
            print(f"  ⚠️  HIGH Failures: {result['high_failures']}")
        if result['medium_failures'] > 0:
            print(f"  ⚡ MEDIUM Failures: {result['medium_failures']}")
        if result['low_failures'] > 0:
            print(f"  ℹ️  LOW Failures: {result['low_failures']}")

    # Intervention reasons
    if result['requires_human_intervention']:
        print(f"\n🚨 Human Intervention Reasons:")
        reasons = json.loads(result['human_intervention_reasons']) if result['human_intervention_reasons'] else []
        for reason in reasons:
            print(f"  • {reason}")

    # Review status
    if result.get('reviewed_at'):
        print(f"\n✅ Reviewed:")
        print(f"  By: {result.get('reviewed_by', 'N/A')}")
        print(f"  At: {result['reviewed_at']}")
        if result.get('review_notes'):
            print(f"  Notes: {result['review_notes']}")


def view_all_results(db, limit=10):
    """View all processing results."""
    print_separator()
    print("📋 ALL PROCESSING RESULTS")
    print_separator()

    results = db.cursor.execute("""
        SELECT * FROM ai_processing_results
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()

    if not results:
        print("\nNo processing results found.")
        return

    print(f"\nShowing {len(results)} most recent results:\n")

    for result in results:
        result = dict(result)
        status_emoji = "✅" if result['processing_status'] == 'success' else "⚠️" if result['processing_status'] == 'success_with_warnings' else "❌"
        intervention_flag = "🚨" if result['requires_human_intervention'] else ""

        print(f"{status_emoji} {intervention_flag} ID:{result['id']} | "
              f"{result.get('patient_name', 'Unknown')[:20]:20s} | "
              f"{result['processing_status']:20s} | "
              f"Checks: {result['passed_checks']}/{result['total_checks']} | "
              f"{result['created_at']}")


def view_intervention_queue(db):
    """View human intervention queue."""
    print_separator()
    print("🚨 HUMAN INTERVENTION QUEUE")
    print_separator()

    queue = db.get_intervention_queue(status='pending')

    if not queue:
        print("\n✅ No items in intervention queue!")
        return

    print(f"\n{len(queue)} items needing review:\n")

    for item in queue:
        reasons = json.loads(item['intervention_reasons'])
        print(f"\n{'─'*70}")
        print(f"Queue ID: {item['id']} | Priority: {item['priority']}")
        print(f"Patient: {item.get('patient_name', 'N/A')}")
        print(f"Visit Date: {item.get('visit_date', 'N/A')}")
        print(f"Created: {item['created_at']}")
        print(f"\nReasons for intervention:")
        for reason in reasons:
            print(f"  • {reason}")


def view_processing_stats(db, days=30):
    """View processing statistics."""
    print_separator()
    print(f"📊 PROCESSING STATISTICS (Last {days} days)")
    print_separator()

    stats = db.get_processing_stats(days)

    print(f"\nTotal Processed: {stats['total_processed']}")
    print(f"\nStatus Breakdown:")
    print(f"  ✅ Success: {stats['success_count']}")
    print(f"  ⚠️  Success with Warnings: {stats['warning_count']}")
    print(f"  🚨 Needs Review: {stats['needs_review_count']}")
    print(f"  ❌ Failed: {stats['failed_count']}")
    print(f"\nIntervention: {stats['intervention_count']} notes flagged")
    print(f"\nToken Usage:")
    print(f"  Total: {stats['total_tokens']:,}")
    print(f"  Average: {stats['avg_tokens']:.0f} per note")
    print(f"\nFailures:")
    print(f"  Critical: {stats['total_critical_failures']}")
    print(f"  High: {stats['total_high_failures']}")
    print(f"\nAverage Pass Rate: {stats['avg_pass_rate']:.1f}%")


def view_validation_failures(db, days=30):
    """View most common validation failures."""
    print_separator()
    print(f"❌ TOP VALIDATION FAILURES (Last {days} days)")
    print_separator()

    failures = db.get_validation_failure_summary(days)

    if not failures:
        print("\n✅ No validation failures!")
        return

    print(f"\n{len(failures)} most common failures:\n")

    for failure in failures:
        priority_emoji = {
            'CRITICAL': '❌',
            'HIGH': '⚠️',
            'MEDIUM': '⚡',
            'LOW': 'ℹ️'
        }.get(failure['priority'], '')

        print(f"{priority_emoji} [{failure['priority']:8s}] {failure['requirement_name']}")
        print(f"   Count: {failure['failure_count']}")
        print(f"   Error: {failure['error_message']}")
        print()


def view_result_details(db, result_id):
    """View detailed information about a specific result."""
    result = db.get_processing_result(result_id)

    if not result:
        print(f"\n❌ Result ID {result_id} not found.")
        return

    print_processing_result(result)

    # Show validation checks
    if result.get('validation_checks'):
        print(f"\n{'='*70}")
        print("DETAILED VALIDATION CHECKS")
        print(f"{'='*70}\n")

        by_priority = {}
        for check in result['validation_checks']:
            priority = check['priority']
            if priority not in by_priority:
                by_priority[priority] = {'passed': [], 'failed': []}

            if check['passed']:
                by_priority[priority]['passed'].append(check)
            else:
                by_priority[priority]['failed'].append(check)

        for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if priority in by_priority:
                priority_emoji = {
                    'CRITICAL': '❌',
                    'HIGH': '⚠️',
                    'MEDIUM': '⚡',
                    'LOW': 'ℹ️'
                }[priority]

                print(f"\n{priority_emoji} {priority} Priority:")

                failed = by_priority[priority]['failed']
                if failed:
                    print(f"  Failed ({len(failed)}):")
                    for check in failed:
                        print(f"    ❌ {check['requirement_name']}")
                        print(f"       {check['error_message']}")
                        if check.get('details'):
                            print(f"       Details: {check['details']}")

                passed = by_priority[priority]['passed']
                if passed:
                    print(f"  Passed ({len(passed)}): {', '.join(c['requirement_name'] for c in passed[:5])}")
                    if len(passed) > 5:
                        print(f"    ... and {len(passed) - 5} more")


def main():
    """Main function."""
    print("\n" + "="*70)
    print(" AI PROCESSING RESULTS VIEWER")
    print("="*70 + "\n")

    # Connect to database
    db = Database()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "stats":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            view_processing_stats(db, days)
            print()
            view_validation_failures(db, days)

        elif command == "queue":
            view_intervention_queue(db)

        elif command == "view" and len(sys.argv) > 2:
            result_id = int(sys.argv[2])
            view_result_details(db, result_id)

        elif command == "patient" and len(sys.argv) > 2:
            patient_name = sys.argv[2]
            results = db.get_processing_results_by_patient(patient_name)
            print(f"\n📋 Results for {patient_name}:\n")
            for result in results:
                print(f"  ID:{result['id']} | {result['processing_status']} | {result['created_at']}")

        else:
            print("❌ Invalid command or missing arguments")
            print_usage()

    else:
        # Default: show overview
        view_processing_stats(db, 30)
        print("\n")
        view_intervention_queue(db)
        print("\n")
        view_all_results(db, 10)

    db.close()


def print_usage():
    """Print usage information."""
    print("\nUsage:")
    print("  python query_ai_processing_results.py              # Show overview")
    print("  python query_ai_processing_results.py stats [days] # Show statistics")
    print("  python query_ai_processing_results.py queue        # Show intervention queue")
    print("  python query_ai_processing_results.py view <id>    # View specific result")
    print("  python query_ai_processing_results.py patient <name> # View patient's results")


if __name__ == "__main__":
    main()
