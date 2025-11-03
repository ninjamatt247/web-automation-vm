#!/usr/bin/env python3
"""Test script to verify Freed.ai login with visible browser."""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from playwright.sync_api import sync_playwright
from utils.logger import logger
from utils.config import get_config
from auth.source_auth import SourceAuth


def main():
    """Test Freed.ai authentication with visible browser."""
    print("=" * 80)
    print("Freed.ai Login Test - Visible Browser Mode")
    print("=" * 80)
    print()

    # Load configuration
    try:
        config = get_config()

        # Override headless setting for this test
        config.headless = False

        print(f"📍 URL: {config.source_url}")
        print(f"👤 Username: {config.source_username}")
        print(f"🔒 Password: {'*' * len(config.source_password)}")
        print()

    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    try:
        with sync_playwright() as p:
            # Launch browser in visible mode
            print("🌐 Launching Chromium browser (visible mode)...")
            browser = p.chromium.launch(
                headless=False,
                slow_mo=500  # Slow down actions for visibility
            )

            print("🔐 Attempting to authenticate...")
            print()

            # Create auth instance
            source_auth = SourceAuth(config, browser)

            # Attempt login
            if source_auth.login():
                print()
                print("=" * 80)
                print("✅ LOGIN SUCCESSFUL!")
                print("=" * 80)
                print()
                print("The browser will remain open for inspection.")
                print("Check the current page state.")
                print()

                # Check if logged in
                if source_auth.is_logged_in():
                    print("✓ Confirmed: Still logged in")
                    print(f"✓ Current URL: {source_auth.page.url}")
                else:
                    print("⚠️  Warning: Login state check failed")

                print()
                input("Press Enter to close the browser and exit...")

            else:
                print()
                print("=" * 80)
                print("❌ LOGIN FAILED")
                print("=" * 80)
                print()
                print("Check the browser window to see what went wrong.")
                print("Screenshots have been saved to logs/ directory.")
                print()
                input("Press Enter to close the browser and exit...")
                sys.exit(1)

            # Cleanup
            source_auth.logout()
            browser.close()

            print()
            print("✓ Test complete")

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
