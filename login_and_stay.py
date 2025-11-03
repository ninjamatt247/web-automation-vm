#!/usr/bin/env python3
"""Login to Freed.ai and keep browser open for interaction."""
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import time

# Load environment variables
load_dotenv('config/.env')

SOURCE_URL = os.getenv('SOURCE_APP_URL')
SOURCE_USERNAME = os.getenv('SOURCE_APP_USERNAME')
SOURCE_PASSWORD = os.getenv('SOURCE_APP_PASSWORD')


def login_and_stay():
    """Login to Freed.ai with Google OAuth and keep browser open."""
    print("=" * 80)
    print("Freed.ai Login - Interactive Mode")
    print("=" * 80)
    print()
    print(f"📍 URL: {SOURCE_URL}")
    print(f"👤 Email: {SOURCE_USERNAME}")
    print()

    with sync_playwright() as p:
        # Launch browser in visible mode
        print("🌐 Launching browser...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500  # Slow down for visibility
        )

        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            # Navigate to Freed.ai
            print("📍 Navigating to Freed.ai...")
            page.goto(SOURCE_URL)
            time.sleep(1)

            # Fill initial form
            print("📝 Filling login form...")
            try:
                email_selector = 'input[type="email"]'
                page.wait_for_selector(email_selector, timeout=5000)
                page.fill(email_selector, SOURCE_USERNAME)

                password_selector = 'input[type="password"]'
                page.fill(password_selector, SOURCE_PASSWORD)
                print("✓ Credentials entered")
            except Exception as e:
                print(f"⚠️  Form fill error: {e}")

            # Submit form
            print("🔘 Submitting form...")
            try:
                page.click('button:has-text("Sign in")', timeout=5000)
                print("✓ Form submitted")
            except:
                page.click('button[type="submit"]', timeout=5000)

            # Handle Google OAuth
            print("⏳ Checking for Google OAuth...")
            try:
                page.wait_for_url(lambda url: "google.com" in url.lower(), timeout=5000)
                print("✓ Google OAuth detected")
                time.sleep(2)

                # Enter Google email
                try:
                    print("📧 Entering Google email...")
                    google_email = 'input[type="email"]'
                    page.wait_for_selector(google_email, timeout=10000)
                    page.fill(google_email, SOURCE_USERNAME)
                    page.click('button:has-text("Next"), #identifierNext', timeout=5000)
                    print("✓ Email submitted")
                    time.sleep(2)

                    # Enter Google password
                    print("🔒 Entering Google password...")
                    google_password = 'input[type="password"]'
                    page.wait_for_selector(google_password, timeout=10000)
                    page.fill(google_password, SOURCE_PASSWORD)
                    page.click('button:has-text("Next"), #passwordNext', timeout=5000)
                    print("✓ Password submitted")
                except Exception as e:
                    print(f"⚠️  Google auth step: {e}")

                # Wait for redirect
                print("⏳ Waiting for redirect to Freed.ai...")
                page.wait_for_url(lambda url: "getfreed.ai" in url.lower(), timeout=30000)
                print("✓ Redirected back to Freed.ai")
                time.sleep(3)

            except:
                print("ℹ️  No Google OAuth redirect (may already be authenticated)")

            print()
            print("=" * 80)
            print("✅ LOGIN COMPLETE!")
            print("=" * 80)
            print()
            print(f"✓ Current URL: {page.url}")
            print()
            print("🌐 Browser is now ready for your use.")
            print("   The browser will stay open - you can interact with Freed.ai")
            print()
            print("   Press Ctrl+C in this terminal when you want to close the browser")
            print()

            # Keep the browser open indefinitely
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n⏸️  Closing browser...")
            context.close()
            browser.close()
            print("✓ Browser closed")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print(f"Current URL: {page.url}")
            print("\nBrowser will stay open for inspection.")
            print("Press Ctrl+C to close...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n⏸️  Closing browser...")


if __name__ == "__main__":
    login_and_stay()
