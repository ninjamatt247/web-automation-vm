#!/usr/bin/env python3
"""Test script for Freed.ai login with Google OAuth."""
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import time

# Load environment variables
load_dotenv('config/.env')

SOURCE_URL = os.getenv('SOURCE_APP_URL')
SOURCE_USERNAME = os.getenv('SOURCE_APP_USERNAME')
SOURCE_PASSWORD = os.getenv('SOURCE_APP_PASSWORD')


def test_login_with_google_oauth():
    """Test Freed.ai authentication with Google OAuth flow."""
    print("=" * 80)
    print("Freed.ai Login Test - Google OAuth Flow")
    print("=" * 80)
    print()
    print(f"📍 URL: {SOURCE_URL}")
    print(f"👤 Email: {SOURCE_USERNAME}")
    print(f"🔒 Password: {'*' * len(SOURCE_PASSWORD)}")
    print()

    with sync_playwright() as p:
        # Launch browser in visible mode
        print("🌐 Launching Chromium browser (visible mode)...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500  # Slow down actions for visibility
        )

        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            # ========================================
            # STEP 1: Navigate to Freed.ai
            # ========================================
            print("STEP 1: Navigating to Freed.ai...")
            page.goto(SOURCE_URL)
            print("✓ Page loaded")
            print()

            # ========================================
            # STEP 2: Fill initial Freed.ai form
            # ========================================
            print("STEP 2: Looking for Freed.ai login form...")

            # Find and fill email
            try:
                page.wait_for_selector('input[type="email"]', timeout=5000)
                email_selector = 'input[type="email"]'
            except:
                email_selector = 'input[name="email"], input[placeholder*="email" i]'

            # Find and fill password
            try:
                page.wait_for_selector('input[type="password"]', timeout=5000)
                password_selector = 'input[type="password"]'
            except:
                password_selector = 'input[name="password"]'

            print("✓ Found login form")
            print("📝 Filling Freed.ai credentials...")
            page.fill(email_selector, SOURCE_USERNAME)
            page.fill(password_selector, SOURCE_PASSWORD)
            print("✓ Credentials filled")
            print()

            # ========================================
            # STEP 3: Submit and wait for Google OAuth redirect
            # ========================================
            print("STEP 3: Submitting form...")
            try:
                page.click('button:has-text("Sign in")', timeout=5000)
                print("✓ Clicked 'Sign in' button")
            except:
                page.click('button[type="submit"]', timeout=5000)
                print("✓ Clicked submit button")

            print()
            print("⏳ Waiting for Google OAuth redirect...")

            # Wait for Google OAuth page
            page.wait_for_url(lambda url: "google.com" in url.lower(), timeout=15000)
            print("✓ Redirected to Google OAuth")
            print(f"✓ Current URL: {page.url[:80]}...")
            print()

            # ========================================
            # STEP 4: Handle Google OAuth authentication
            # ========================================
            print("STEP 4: Authenticating with Google...")

            # Wait for Google login page to load
            time.sleep(2)

            # Look for email input on Google's page
            try:
                print("🔍 Looking for Google email input...")
                # Google uses identifier field for email
                google_email_selector = 'input[type="email"]'
                page.wait_for_selector(google_email_selector, timeout=10000)
                print("✓ Found Google email input")

                print(f"📝 Entering email: {SOURCE_USERNAME}")
                page.fill(google_email_selector, SOURCE_USERNAME)

                # Click Next button
                print("🔘 Clicking Next...")
                page.click('button:has-text("Next"), #identifierNext', timeout=5000)
                print("✓ Submitted email")
                print()

                # Wait for password page
                time.sleep(2)

                # Enter password
                print("🔍 Looking for Google password input...")
                google_password_selector = 'input[type="password"]'
                page.wait_for_selector(google_password_selector, timeout=10000)
                print("✓ Found Google password input")

                print("📝 Entering password...")
                page.fill(google_password_selector, SOURCE_PASSWORD)

                # Click Next button
                print("🔘 Clicking Next...")
                page.click('button:has-text("Next"), #passwordNext', timeout=5000)
                print("✓ Submitted password")
                print()

            except Exception as e:
                print(f"⚠️  Note: {e}")
                print("This might be normal if:")
                print("  - You're already logged into Google in this browser")
                print("  - Google requires 2FA verification")
                print()

            # ========================================
            # STEP 5: Wait for redirect back to Freed.ai
            # ========================================
            print("STEP 5: Waiting for redirect back to Freed.ai...")

            try:
                # Wait to be redirected back to Freed.ai domain
                page.wait_for_url(lambda url: "getfreed.ai" in url.lower(), timeout=30000)
                print("✓ Redirected back to Freed.ai!")
                print()

                # Wait for dashboard to load
                time.sleep(3)

                print("=" * 80)
                print("✅ LOGIN SUCCESSFUL!")
                print("=" * 80)
                print()
                print(f"✓ Current URL: {page.url}")
                print()
                print("The browser will remain open for inspection.")
                print("You should see the Freed.ai dashboard.")
                print()

                # Take success screenshot
                try:
                    screenshot_path = 'login_success.png'
                    page.screenshot(path=screenshot_path)
                    print(f"📸 Screenshot saved: {screenshot_path}")
                except:
                    pass

                print()
                input("Press Enter to close the browser and exit...")

                context.close()
                browser.close()

                print()
                print("✓ Test complete - Login was successful!")
                return True

            except PlaywrightTimeout:
                print()
                print("⏳ Still on Google page after 30 seconds...")
                print("This might mean:")
                print("  - 2FA verification is required")
                print("  - Manual interaction needed")
                print()
                print("Current URL:", page.url[:100])
                print()
                print("Please complete the login manually in the browser.")
                print("The script will wait for you...")
                print()

                # Wait longer for manual completion
                try:
                    page.wait_for_url(lambda url: "getfreed.ai" in url.lower(), timeout=120000)
                    print()
                    print("✅ Login completed!")
                    print(f"✓ Current URL: {page.url}")
                    print()
                    input("Press Enter to close the browser...")
                    return True
                except:
                    print()
                    print("⏸️  Timeout waiting for login completion")
                    input("Press Enter to close the browser...")
                    return False

        except Exception as e:
            print()
            print("=" * 80)
            print("❌ ERROR OCCURRED")
            print("=" * 80)
            print()
            print(f"Error: {e}")
            print()
            print(f"Current URL: {page.url}")
            print()

            # Take screenshot
            try:
                screenshot_path = 'login_error.png'
                page.screenshot(path=screenshot_path)
                print(f"📸 Screenshot saved: {screenshot_path}")
            except:
                pass

            print()
            print("Browser will remain open for inspection.")
            input("Press Enter to close...")
            return False

        finally:
            try:
                context.close()
                browser.close()
            except:
                pass


if __name__ == "__main__":
    import sys
    try:
        success = test_login_with_google_oauth()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
