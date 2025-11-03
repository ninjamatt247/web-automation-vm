# Web Automation VM: Freed.ai → OpenAI → Osmind EHR

Automated system for transferring patient notes from Freed.ai to Osmind EHR with AI-powered cleaning and formatting.

## 🎯 What It Does

1. **Logs into Freed.ai** (with Google OAuth support)
2. **Extracts patient notes** from the last N days
3. **Processes with OpenAI** to clean and format for EHR compliance
4. **Logs into Osmind EHR**
5. **Uploads cleaned notes** automatically

## ✨ Features

- **Google OAuth Support**: Handles Freed.ai's Google authentication flow
- **AI-Powered Processing**: Uses OpenAI to clean and format clinical notes
- **Browser Automation**: Playwright-powered web interaction
- **Scheduled Execution**: Cron-based automated transfers
- **Individual File Processing**: Each patient note saved and processed separately
- **Comprehensive Logging**: Detailed logs with screenshots on errors
- **Docker Containerized**: Easy deployment and scaling

## Architecture

```
web-automation-vm/
├── src/
│   ├── auth/           # Authentication modules
│   ├── extractors/     # Data extraction from source app
│   ├── inserters/      # Data insertion to target app
│   └── utils/          # Shared utilities
├── config/             # Configuration files
├── logs/               # Application logs
├── data/               # Temporary and archived data
└── scripts/            # Automation scripts
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Freed.ai account with Google authentication
- Osmind EHR account
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Quick Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ninjamatt247/web-automation-vm.git
   cd web-automation-vm
   ```

2. **Configure credentials**:
   ```bash
   cp config/.env.example config/.env
   nano config/.env  # Edit with your actual credentials
   ```

   Required settings:
   - `SOURCE_APP_USERNAME` - Your Freed.ai email
   - `SOURCE_APP_PASSWORD` - Your Google password
   - `TARGET_APP_USERNAME` - Your Osmind username
   - `TARGET_APP_PASSWORD` - Your Osmind password
   - `OPENAI_API_KEY` - Your OpenAI API key

3. **Build and run**:
   ```bash
   docker-compose build
   docker-compose run automation python src/main_workflow.py
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

📖 **For detailed setup instructions**, see [SETUP_GUIDE.md](./SETUP_GUIDE.md)

## Configuration

Edit `config/.env` to configure:

- **Source Application**: URL and credentials
- **Target Application**: URL and credentials
- **Schedule**: Cron expression for automation frequency
- **Data Mapping**: Field mappings between applications

## Usage

### Manual Execution

```bash
# Default: fetch last 1 day
docker-compose exec automation python src/main_workflow.py

# Fetch last 3 days
docker-compose exec automation python src/main_workflow.py --days 3

# Fetch last 7 days
docker-compose exec automation python src/main_workflow.py --days 7
```

### Local Testing

```bash
# Test extraction and OpenAI (no Osmind upload)
python3 test_extraction_and_ai.py --days 1

# Test with last 3 days
python3 test_extraction_and_ai.py --days 3
```

### View Logs

```bash
docker-compose logs -f automation
```

### Stop Container

```bash
docker-compose down
```

## Security

- Never commit credentials to version control
- Use environment variables for sensitive data
- Regularly rotate passwords and tokens
- Monitor logs for suspicious activity

## Development

Built with:
- Python 3.11
- Playwright for browser automation
- Docker for containerization
- Cron for scheduling

## License

MIT License

## Support

For issues and questions, please open a GitHub issue.
