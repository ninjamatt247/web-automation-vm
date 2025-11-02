# Web Automation VM

Docker-based automation system for transferring data between two web applications using browser automation.

## Features

- **Browser Automation**: Playwright-powered web interaction
- **Scheduled Execution**: Cron-based automated data transfers
- **Secure Authentication**: Environment-based credential management
- **Data Transfer**: Forms, files, and tabular data support
- **Error Handling**: Comprehensive logging and monitoring
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
- GitHub account for repository management

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/web-automation-vm.git
   cd web-automation-vm
   ```

2. **Configure credentials**:
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your credentials
   ```

3. **Build and run**:
   ```bash
   docker-compose up -d
   ```

4. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

## Configuration

Edit `config/.env` to configure:

- **Source Application**: URL and credentials
- **Target Application**: URL and credentials
- **Schedule**: Cron expression for automation frequency
- **Data Mapping**: Field mappings between applications

## Usage

### Manual Execution

```bash
docker-compose exec automation python src/main.py
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
