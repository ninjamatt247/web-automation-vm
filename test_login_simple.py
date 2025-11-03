#!/usr/bin/env python3
"""Simple test script to verify Freed.ai login with visible browser."""
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# Load environment variables
load_dotenv('config/.env')

SOURCE_URL = os.getenv('SOURCE_APP_URL')
SOURCE_USERNAME = os.getenv('SOURCE_APP_USERNAME')
SOURCE_PASSWORD = os.getenv('SOURCE_APP_PASSWORD')


def test_login():
    """Test Freed.ai authentication with visible browser."""
    print("=" * 80)
    print("Freed.ai Login Test - Visible Browser Mode")
    print("=" * 80)
    print()
    print(f"📍 URL: {SOURCE_URL}")
    print(f"👤 Username: {SOURCE_USERNAME}")
    print(f"🔒 Password: {'*' * len(SOURCE_PASSWORD)}")
    print()

    with sync_playwright() as p:
        # Launch browser in visible mode
        print("🌐 Launching Chromium browser (visible mode)...")
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500  # Slow down actions for visibility
        )

        page = browser.new_page()
        page.set_default_timeout(30000)

        try:
            print("🔐 Navigating to Freed.ai...")
            page.goto(SOURCE_URL)
            print("✓ Page loaded")
            print()

            print("🔍 Looking for login form...")

            # Try to find email input
            try:
                page.wait_for_selector('input[type="email"]', timeout=5000)
                email_selector = 'input[type="email"]'
                print("✓ Found email input")
            except:
                try:
                    page.wait_for_selector('input[name="email"]', timeout=5000)
                    email_selector = 'input[name="email"]'
                    print("✓ Found email input (by name)")
                except:
                    page.wait_for_selector('input[placeholder*="email" i]', timeout=5000)
                    email_selector = 'input[placeholder*="email" i]'
                    print("✓ Found email input (by placeholder)")

            # Try to find password input
            try:
                page.wait_for_selector('input[type="password"]', timeout=5000)
                password_selector = 'input[type="password"]'
                print("✓ Found password input")
            except:
                page.wait_for_selector('input[name="password"]', timeout=5000)
                password_selector = 'input[name="password"]'
                print("✓ Found password input (by name)")

            print()
            print("📝 Filling credentials...")
            page.fill(email_selector, SOURCE_USERNAME)
            page.fill(password_selector, SOURCE_PASSWORD)
            print("✓ Credentials filled")
            print()

            print("🔘 Clicking submit button...")
            # Try to find and click submit button
            try:
                page.click('button:has-text("Sign in")', timeout=5000)
                print("✓ Clicked 'Sign in' button")
            except:
                try:
                    page.click('button:has-text("Login")', timeout=5000)
                    print("✓ Clicked 'Login' button")
                except:
                    try:
                        page.click('button[type="submit"]', timeout=5000)
                        print("✓ Clicked submit button")
                    except:
                        page.click('form button:not([type="button"])', timeout=5000)
                        print("✓ Clicked form button")

            print()
            print("⏳ Waiting for login to complete...")

            # Wait for successful login
            try:
                page.wait_for_selector('[data-testid*="dashboard"], .dashboard, #dashboard', timeout=15000)
                print("✓ Dashboard detected!")
            except:
                try:
                    page.wait_for_selector('[data-testid*="user"], .user-menu, .profile', timeout=15000)
                    print("✓ User menu detected!")
                except:
                    page.wait_for_url(lambda url: "login" not in url.lower(), timeout=15000)
                    print("✓ Redirected away from login page!")

            print()
            print("=" * 80)
            print("✅ LOGIN SUCCESSFUL!")
            print("=" * 80)
            print()
            print(f"✓ Current URL: {page.url}")
            print()
            print("The browser will remain open for inspection.")
            print("Check if you can see the Freed.ai dashboard.")
            print()
            input("Press Enter to close the browser and exit...")

            page.close()
            browser.close()

            print()
            print("✓ Test complete - Login was successful!")
            return True

        except PlaywrightTimeout as e:
            print()
            print("=" * 80)
            print("❌ LOGIN FAILED - TIMEOUT")
            print("=" * 80)
            print()
            print(f"Error: {e}")
            print()
            print("The browser will remain open for inspection.")
            print("Check what's shown on the page.")
            print()

            # Take screenshot
            try:
                screenshot_path = 'login_error.png'
                page.screenshot(path=screenshot_path)
                print(f"📸 Screenshot saved: {screenshot_path}")
            except:
                pass

            input("Press Enter to close the browser and exit...")
            page.close()
            browser.close()
            return False

        except Exception as e:
            print()
            print("=" * 80)
            print("❌ LOGIN FAILED - ERROR")
            print("=" * 80)
            print()
            print(f"Error: {e}")
            print()

            # Take screenshot
            try:
                screenshot_path = 'login_error.png'
                page.screenshot(path=screenshot_path)
                print(f"📸 Screenshot saved: {screenshot_path}")
            except:
                pass

            input("Press Enter to close the browser and exit...")
            page.close()
            browser.close()
            return False


if __name__ == "__main__":
    import sys
    try:
        success = test_login()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
