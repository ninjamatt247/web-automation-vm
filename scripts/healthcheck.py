"""Healthcheck script for Docker container."""
import sys
from pathlib import Path
from datetime import datetime, timedelta


def check_logs_recent() -> bool:
    """Check if automation logs are recent (within last 3 hours)."""
    log_file = Path("/app/logs/automation.log")

    if not log_file.exists():
        # Log file doesn't exist yet - might be first run
        return True

    try:
        # Check last modification time
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        age = datetime.now() - mtime

        # Alert if no activity in last 3 hours
        if age > timedelta(hours=3):
            print(f"WARNING: Log file is {age.total_seconds() / 3600:.1f} hours old")
            return False

        return True

    except Exception as e:
        print(f"ERROR: Failed to check log file: {e}")
        return False


def check_errors() -> bool:
    """Check for recent critical errors in logs."""
    error_log = Path("/app/logs/errors.log")

    if not error_log.exists():
        return True

    try:
        # Read last 100 lines
        with open(error_log, 'r') as f:
            lines = f.readlines()[-100:]

        # Check for critical errors in last hour
        recent_criticals = []
        one_hour_ago = datetime.now() - timedelta(hours=1)

        for line in lines:
            if "CRITICAL" in line or "FATAL" in line:
                try:
                    # Parse timestamp from log line
                    timestamp_str = line.split('|')[0].strip()
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                    if timestamp > one_hour_ago:
                        recent_criticals.append(line)
                except:
                    pass

        if recent_criticals:
            print(f"WARNING: {len(recent_criticals)} critical errors in last hour")
            return False

        return True

    except Exception as e:
        print(f"ERROR: Failed to check error log: {e}")
        return True  # Don't fail healthcheck on read errors


def main():
    """Run healthcheck."""
    checks = [
        ("Log Activity", check_logs_recent()),
        ("Critical Errors", check_errors())
    ]

    all_passed = all(result for _, result in checks)

    print("Healthcheck Results:")
    for name, result in checks:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name}: {status}")

    if all_passed:
        print("Overall: HEALTHY")
        sys.exit(0)
    else:
        print("Overall: UNHEALTHY")
        sys.exit(1)


if __name__ == "__main__":
    main()
