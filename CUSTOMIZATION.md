# Customization Guide

This guide will help you customize the automation for your specific web applications.

## ✅ Current Status

- **Source App (Freed.ai)**: ✅ Configured with credentials and authentication
- **Target App**: ⏳ Needs configuration
- **Data Extraction**: ⏳ Needs customization
- **Data Insertion**: ⏳ Needs customization

## Overview

The automation system consists of 5 main components that need customization:

1. **✅ Authentication** - Login to both applications (Freed.ai source configured)
2. **⏳ Navigation** - Navigate to correct sections
3. **⏳ Extraction** - Extract data from source app
4. **⏳ Transformation** - Map data between applications
5. **⏳ Insertion** - Insert data into target app

## Step-by-Step Customization

### 1. Configure Credentials

Edit `config/.env`:

```bash
# Source Application (Freed.ai)
SOURCE_APP_URL=https://secure.getfreed.ai/
SOURCE_APP_USERNAME=l@livewellbyl.com
SOURCE_APP_PASSWORD=Newlife2025!

# Target Application
TARGET_APP_URL=https://your-target-app.com/login
TARGET_APP_USERNAME=your_username
TARGET_APP_PASSWORD=your_password

# Schedule (cron format)
SCHEDULE="0 */2 * * *"  # Every 2 hours
```

### 2. Customize Source Authentication

**✅ Freed.ai authentication is already configured** with robust selectors that handle modern login forms. The system will automatically try multiple selector patterns:

- **Email field**: `input[type="email"]`, `input[name="email"]`, or email placeholder inputs
- **Password field**: `input[type="password"]` or `input[name="password"]`
- **Submit button**: "Sign in", "Login", or `button[type="submit"]` selectors
- **Success detection**: Dashboard elements, user menus, or URL changes

If you need to customize further, edit `src/auth/source_auth.py`:

```python
# The code already includes fallback selectors for Freed.ai
# If you encounter issues, you can inspect the actual selectors:

1. Open https://secure.getfreed.ai/ in a browser
2. Right-click on the email field → Inspect
3. Note the selector and update the email_selector variable
4. Repeat for password field and submit button
```

**Customize navigation**:

```python
def navigate_to_data_section(self) -> bool:
    # Option 1: Direct URL
    self.page.goto(f"{self.url}/data-export")

    # Option 2: Click menu items
    self.page.click('a[href="/data"]')

    # Wait for data section to load
    self.page.wait_for_selector('table.data-table')
    return True
```

### 3. Customize Target Authentication

Edit `src/auth/target_auth.py` - same process as source authentication.

### 4. Customize Data Extraction

Edit `src/main.py` in the extraction section:

**For table data**:

```python
# Extract from HTML table
data = extractor.extract_table_data("table.your-table-class")
```

**For form fields**:

```python
# Extract specific fields
custom_selectors = {
    "name": "#customer-name",
    "email": "input[name='email']",
    "amount": ".amount-field"
}
data = [extractor.extract_custom_data(custom_selectors)]
```

**For file downloads**:

```python
# Download and extract from file
file_path = extractor.download_file('button.download-btn')
# Then process the file as needed
```

### 5. Customize Data Insertion

Edit `src/main.py` in the insertion section:

**For form submission**:

```python
# Fill and submit a form for each record
for record in data:
    inserter.fill_form(record, form_selector="form.data-entry")
    inserter.submit_form('button.submit-btn')
```

**For table row insertion**:

```python
# Click "Add Row" button and fill fields
results = inserter.insert_batch(
    data,
    add_button_selector='button.add-row',  # ← Your add button
    batch_size=config.batch_size
)
```

**For file upload**:

```python
# Upload a file
inserter.upload_file(
    file_path="/app/data/temp/export.xlsx",
    upload_selector='input[type="file"]'
)
```

### 6. Field Mapping

If field names differ between applications, add mapping:

```python
# In src/main.py, after extraction
def transform_data(source_data):
    """Map source fields to target fields."""
    return [{
        "target_name": item["source_name"],
        "target_email": item["source_email_address"],
        "target_amount": item["source_total"]
    } for item in source_data]

data = transform_data(data)
```

## Finding Selectors

### Method 1: Browser DevTools

1. Open the web application
2. Right-click element → "Inspect"
3. In the Elements panel, right-click the element
4. Copy → Copy selector

### Method 2: Use Playwright Codegen

```bash
# Generate selectors automatically
docker-compose run automation playwright codegen https://your-app.com
```

This will open a browser and record your actions, generating selector code.

### Method 3: Test Selectors in Console

In browser DevTools console:

```javascript
// Test if selector works
document.querySelector('your-selector-here')
```

## Common Selector Patterns

```css
/* By ID */
#username

/* By name attribute */
input[name="email"]

/* By class */
.btn-primary

/* By data attribute */
[data-testid="submit-button"]

/* By text content */
button:has-text("Login")

/* Combination */
form.login-form input[type="email"]
```

## Testing Your Customization

### 1. Test Authentication

**✅ Freed.ai authentication is ready to test:**

```bash
# Run container in non-headless mode to test Freed.ai login
docker-compose run -e HEADLESS=false automation python -c "
from playwright.sync_api import sync_playwright
from src.utils.config import get_config
from src.auth.source_auth import SourceAuth

config = get_config()
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    auth = SourceAuth(config, browser)
    if auth.login():
        print('✅ Login successful!')
    else:
        print('❌ Login failed - check logs and screenshots')
    input('Press Enter to close...')
    browser.close()
"
```

### 2. Test Data Extraction

```bash
# Test extraction and save results
docker-compose exec automation python -c "
from src.main import main
main()
"
```

Check `data/temp/` for extracted files.

### 3. Test Full Workflow

```bash
# Run complete automation
docker-compose exec automation python src/main.py
```

## Debugging Tips

1. **Enable screenshots**: Set `SCREENSHOT_ON_ERROR=true` in `.env`
2. **Disable headless mode**: Set `HEADLESS=false` to see browser actions
3. **Check logs**: `docker-compose logs -f automation`
4. **Increase timeouts**: Adjust `BROWSER_TIMEOUT` in `.env`
5. **Add wait conditions**: Use `page.wait_for_selector()` for dynamic content

## Advanced Customization

### Handle Pagination

```python
# In src/extractors/data_extractor.py
def extract_all_pages(self):
    all_data = []
    while True:
        # Extract current page
        page_data = self.extract_table_data()
        all_data.extend(page_data)

        # Check for next button
        next_button = self.page.query_selector('button.next-page')
        if not next_button or 'disabled' in next_button.get_attribute('class'):
            break

        next_button.click()
        self.page.wait_for_load_state('networkidle')

    return all_data
```

### Handle Dynamic Content

```python
# Wait for dynamic content to load
self.page.wait_for_function("""
    () => document.querySelectorAll('tr').length > 0
""")
```

### Handle Modals/Popups

```python
# Wait for and interact with modal
self.page.click('button.open-modal')
self.page.wait_for_selector('.modal.active')
self.page.fill('.modal input[name="field"]', 'value')
self.page.click('.modal button.save')
```

## Schedule Customization

Edit `crontab` for different schedules:

```cron
# Every hour
0 * * * * /usr/local/bin/python /app/src/main.py

# Every day at 2 AM
0 2 * * * /usr/local/bin/python /app/src/main.py

# Every Monday at 9 AM
0 9 * * 1 /usr/local/bin/python /app/src/main.py

# Every 15 minutes
*/15 * * * * /usr/local/bin/python /app/src/main.py
```

## Need Help?

1. Check logs: `docker-compose logs -f`
2. Review screenshots in `logs/` directory
3. Test selectors using Playwright Codegen
4. Open a GitHub issue with your question
