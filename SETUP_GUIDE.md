# Setup Guide: Freed.ai → OpenAI → Osmind EHR Automation

Complete setup instructions for the automated patient notes transfer system.

## 🎯 What This Does

This automation system:
1. **Logs into Freed.ai** using Google OAuth
2. **Extracts patient notes** from the last N days
3. **Processes each note with OpenAI** to clean and format for EHR
4. **Logs into Osmind EHR**
5. **Uploads the cleaned notes** automatically

## 📋 Prerequisites

- Docker installed (for production deployment)
- OR Python 3.11+ and Playwright (for local testing)
- Freed.ai account with Google authentication
- Osmind EHR account with credentials
- OpenAI API key

## ⚙️ Configuration

### Step 1: Set Up Credentials

```bash
cd web-automation-vm
cp config/.env.example config/.env
```

Edit `config/.env` with your actual credentials:

```bash
# Freed.ai (uses Google OAuth)
SOURCE_APP_URL=https://secure.getfreed.ai/
SOURCE_APP_USERNAME=your_email@example.com
SOURCE_APP_PASSWORD=your_google_password

# Osmind EHR
TARGET_APP_URL=https://app.osmind.com/login
TARGET_APP_USERNAME=your_osmind_username
TARGET_APP_PASSWORD=your_osmind_password

# OpenAI API
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4000

# Data Processing
DAYS_TO_FETCH=1
DOWNLOAD_INDIVIDUAL_FILES=true

# Schedule (cron format)
SCHEDULE="0 */2 * * *"  # Every 2 hours

# Browser Settings
HEADLESS=true
BROWSER_TIMEOUT=30000
SCREENSHOT_ON_ERROR=true
```

### Step 2: Get Your OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy it to `OPENAI_API_KEY` in your `.env` file

**Cost Estimate**: With `gpt-4o-mini`, processing 10 notes costs approximately $0.01-0.05

## 🚀 Running the Automation

### Option A: Docker (Recommended for Production)

```bash
# Build the container
docker-compose build

# Run once to test
docker-compose run automation python src/main_workflow.py

# Run as scheduled service
docker-compose up -d

# View logs
docker-compose logs -f automation
```

### Option B: Local Python (For Testing)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run the workflow
python src/main_workflow.py
```

## 🔍 Testing Individual Components

### Test Freed.ai Login

```bash
python login_and_stay.py
```

This opens a browser, logs into Freed.ai, and keeps it open for inspection.

### Test OpenAI Processing

```python
from src.utils.config import get_config
from src.utils.openai_processor import OpenAIProcessor

config = get_config()
processor = OpenAIProcessor(config)

# Test connection
if processor.test_connection():
    print("✓ OpenAI API working")

# Test processing
test_note = "Patient has withdrawal symptoms..."
cleaned = processor.clean_patient_note(test_note)
print(cleaned)
```

### Test Osmind Login

You'll need to customize the selectors in `src/auth/target_auth.py` and `src/inserters/osmind_inserter.py` based on your actual Osmind EHR interface.

## 🎨 Customization

### Customize OpenAI Prompt

Edit `src/utils/openai_processor.py` and modify the `system_prompt` variable to change how notes are cleaned.

### Customize Freed.ai Extraction

Edit `src/extractors/freed_extractor.py`:
- Adjust selectors in `get_patient_list()`
- Modify `extract_patient_note()` for different note structures

### Customize Osmind Upload

Edit `src/inserters/osmind_inserter.py`:
- Update selectors in `navigate_to_patient_notes()`
- Modify `upload_note()` for your Osmind workflow

## 📊 Monitoring

### View Logs

```bash
# Docker
docker-compose logs -f automation

# Local
tail -f logs/automation.log
tail -f logs/errors.log
```

### Check Processed Files

```bash
# Raw extracted notes
ls -la data/temp/

# AI-processed notes
ls -la data/temp/processed/

# Archived files
ls -la data/archive/
```

## 🔧 Troubleshooting

### Problem: Login Fails

**Solution**: Run with visible browser to see what's happening:
```bash
# Set HEADLESS=false in .env
python login_and_stay.py
```

### Problem: Can't Find Patient Records

**Solution**: The selectors in `freed_extractor.py` may need adjustment. Inspect the Freed.ai HTML and update the JavaScript selectors in `get_patient_list()`.

### Problem: OpenAI API Errors

**Solutions**:
- Check API key is valid
- Verify you have credits in your OpenAI account
- Check rate limits (gpt-4o-mini: 10,000 RPM)

### Problem: Osmind Upload Fails

**Solution**: The Osmind EHR interface may have changed. You'll need to:
1. Log into Osmind manually
2. Inspect the HTML elements (right-click → Inspect)
3. Update selectors in `osmind_inserter.py`

## 🔒 Security Best Practices

1. **Never commit `.env` file** - it contains sensitive credentials
2. **Use environment variables** in production
3. **Rotate credentials regularly**
4. **Monitor OpenAI usage** to prevent unexpected charges
5. **Review logs** for any suspicious activity
6. **Enable 2FA** on all accounts where possible

## 📅 Scheduling

The system uses cron for scheduling. Edit `SCHEDULE` in `.env`:

```bash
# Every hour
SCHEDULE="0 * * * *"

# Every 2 hours (default)
SCHEDULE="0 */2 * * *"

# Once daily at 9 AM
SCHEDULE="0 9 * * *"

# Every weekday at 9 AM
SCHEDULE="0 9 * * 1-5"
```

## 💰 Cost Estimation

### OpenAI API Costs (gpt-4o-mini)

- **Input**: $0.150 / 1M tokens
- **Output**: $0.600 / 1M tokens

**Example**: Processing 100 patient notes/day
- Average input: 500 tokens/note = 50K tokens/day
- Average output: 400 tokens/note = 40K tokens/day
- **Daily cost**: ~$0.03
- **Monthly cost**: ~$0.90

## 🆘 Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Test individual components
3. Review screenshots in `logs/` directory
4. Open a GitHub issue with logs

## 📝 Next Steps

1. ✅ Configure your credentials in `.env`
2. ✅ Test Freed.ai login with visible browser
3. ✅ Test OpenAI API connection
4. ✅ Customize selectors for your Osmind EHR
5. ✅ Run a test with 1 day of data
6. ✅ Review the processed notes
7. ✅ Deploy with Docker for automated operation

---

**Need Help?** Open an issue on GitHub with your logs (remove sensitive data first!).
