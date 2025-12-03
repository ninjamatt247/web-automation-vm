"""Microsoft Graph API authentication for OneDrive."""
from typing import Optional
import requests
from datetime import datetime, timedelta
from loguru import logger
from src.utils.config import AppConfig


class OneDriveAuth:
    """Handle Microsoft Graph API authentication."""

    def __init__(self, config: AppConfig):
        """Initialize OneDrive authentication.

        Args:
            config: Application configuration with OneDrive credentials
        """
        self.tenant_id = config.onedrive_tenant_id
        self.client_id = config.onedrive_client_id
        self.client_secret = config.onedrive_client_secret

        self.token = None
        self.token_expiry = None

        self.auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    def get_access_token(self) -> str:
        """Get valid access token (cached or refresh).

        Returns:
            Access token string

        Raises:
            Exception if authentication fails
        """
        # Return cached token if still valid
        if self.token and self.token_expiry:
            if datetime.now() < self.token_expiry:
                return self.token

        # Request new token
        logger.info("Requesting new OneDrive access token...")

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }

        response = requests.post(self.auth_url, data=data)

        if response.status_code != 200:
            error_msg = f"OneDrive auth failed: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

        token_data = response.json()
        self.token = token_data['access_token']

        # Calculate expiry (subtract 5 min buffer)
        expires_in = token_data.get('expires_in', 3600)
        self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)

        logger.info(f"✓ OneDrive access token obtained (expires: {self.token_expiry})")
        return self.token

    def get_headers(self) -> dict:
        """Get authorization headers for Graph API requests.

        Returns:
            Dictionary with Authorization header
        """
        token = self.get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
