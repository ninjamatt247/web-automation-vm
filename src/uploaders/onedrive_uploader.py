"""Upload PDFs to Microsoft OneDrive using Graph API."""
from typing import Optional, Dict, Any
from pathlib import Path
import requests
import time
from src.uploaders.onedrive_auth import OneDriveAuth
from loguru import logger
from src.utils.config import AppConfig


class OneDriveUploader:
    """Upload files to OneDrive via Microsoft Graph API."""

    def __init__(self,
                 config: AppConfig,
                 retry_attempts: int = 3,
                 retry_delay: int = 5):
        """Initialize OneDrive uploader.

        Args:
            config: Application configuration
            retry_attempts: Number of retry attempts for failed uploads
            retry_delay: Delay in seconds between retries
        """
        self.config = config
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        self.auth = OneDriveAuth(config)
        self.graph_api_base = "https://graph.microsoft.com/v1.0"

        # Configure root folder (use service account's OneDrive)
        self.root_folder_path = config.onedrive_root_folder  # e.g., "/PDF_Forms"

        self.success_count = 0
        self.failure_count = 0
        self.flagged_for_review = []

    def upload_pdf(self,
                   pdf_path: Path,
                   patient_name: str,
                   patient_id: str,
                   metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Upload PDF to OneDrive in patient-specific folder.

        Args:
            pdf_path: Path to PDF file
            patient_name: Patient name for folder organization
            patient_id: Patient ID for folder naming
            metadata: Additional metadata to store

        Returns:
            OneDrive web URL of uploaded file or None if failed
        """
        try:
            # Sanitize folder name
            folder_name = self._sanitize_folder_name(f"{patient_name}_{patient_id}")

            logger.info(f"Uploading {pdf_path.name} to OneDrive folder: {folder_name}")

            # Create patient folder if doesn't exist
            folder_id = self._ensure_folder_exists(folder_name)

            if not folder_id:
                raise Exception(f"Failed to create folder: {folder_name}")

            # Upload file with retry logic
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    upload_url = self._upload_file_to_folder(pdf_path, folder_id)

                    if upload_url:
                        logger.info(f"✓ Successfully uploaded to OneDrive: {upload_url}")
                        self.success_count += 1
                        return upload_url

                except Exception as e:
                    logger.warning(f"Upload attempt {attempt}/{self.retry_attempts} failed: {e}")

                    if attempt < self.retry_attempts:
                        logger.info(f"Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        raise

            return None

        except Exception as e:
            logger.error(f"Failed to upload {pdf_path.name}: {e}")
            self.failure_count += 1
            self.flag_for_review(
                patient_name,
                f"OneDrive upload failed: {str(e)}",
                {"pdf_path": str(pdf_path), "metadata": metadata}
            )
            return None

    def _ensure_folder_exists(self, folder_name: str) -> Optional[str]:
        """Create patient folder if doesn't exist.

        Args:
            folder_name: Name of folder to create

        Returns:
            Folder ID or None if failed
        """
        headers = self.auth.get_headers()

        # Check if folder exists
        search_url = f"{self.graph_api_base}/me/drive/root:{self.root_folder_path}/{folder_name}"

        response = requests.get(search_url, headers=headers)

        if response.status_code == 200:
            # Folder exists
            folder_id = response.json()['id']
            logger.info(f"Folder already exists: {folder_name} (ID: {folder_id})")
            return folder_id

        # Create new folder
        create_url = f"{self.graph_api_base}/me/drive/root:{self.root_folder_path}:/children"

        folder_data = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail"
        }

        response = requests.post(create_url, headers=headers, json=folder_data)

        if response.status_code in [200, 201]:
            folder_id = response.json()['id']
            logger.info(f"✓ Created folder: {folder_name} (ID: {folder_id})")
            return folder_id
        else:
            logger.error(f"Failed to create folder: {response.status_code} - {response.text}")
            return None

    def _upload_file_to_folder(self, pdf_path: Path, folder_id: str) -> Optional[str]:
        """Upload file to specific folder.

        Args:
            pdf_path: Path to PDF file
            folder_id: OneDrive folder ID

        Returns:
            Web URL of uploaded file or None if failed
        """
        headers = self.auth.get_headers()
        headers['Content-Type'] = 'application/pdf'

        # For files < 4MB use simple upload, else use resumable upload session
        file_size = pdf_path.stat().st_size

        if file_size < 4 * 1024 * 1024:  # 4MB
            # Simple upload
            upload_url = f"{self.graph_api_base}/me/drive/items/{folder_id}:/{pdf_path.name}:/content"

            with open(pdf_path, 'rb') as f:
                response = requests.put(upload_url, headers=headers, data=f)

            if response.status_code in [200, 201]:
                file_data = response.json()
                web_url = file_data.get('webUrl')
                logger.info(f"File uploaded: {pdf_path.name} ({file_size / 1024:.1f} KB)")
                return web_url
            else:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
        else:
            # Use upload session for large files
            return self._resumable_upload(pdf_path, folder_id)

    def _resumable_upload(self, pdf_path: Path, folder_id: str) -> Optional[str]:
        """Resumable upload for large files (>4MB).

        Args:
            pdf_path: Path to PDF file
            folder_id: OneDrive folder ID

        Returns:
            Web URL of uploaded file
        """
        headers = self.auth.get_headers()

        # Create upload session
        session_url = f"{self.graph_api_base}/me/drive/items/{folder_id}:/{pdf_path.name}:/createUploadSession"

        response = requests.post(session_url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Failed to create upload session: {response.text}")

        upload_url = response.json()['uploadUrl']

        # Upload file in chunks
        chunk_size = 320 * 1024  # 320KB chunks
        file_size = pdf_path.stat().st_size

        with open(pdf_path, 'rb') as f:
            chunk_start = 0

            while chunk_start < file_size:
                chunk_end = min(chunk_start + chunk_size, file_size)
                chunk_data = f.read(chunk_end - chunk_start)

                chunk_headers = {
                    'Content-Length': str(len(chunk_data)),
                    'Content-Range': f'bytes {chunk_start}-{chunk_end - 1}/{file_size}'
                }

                response = requests.put(upload_url, headers=chunk_headers, data=chunk_data)

                if response.status_code not in [200, 201, 202]:
                    raise Exception(f"Chunk upload failed: {response.status_code}")

                chunk_start = chunk_end
                logger.info(f"Uploaded {chunk_end / file_size * 100:.1f}%")

        # Get final file data
        file_data = response.json()
        return file_data.get('webUrl')

    def _sanitize_folder_name(self, name: str) -> str:
        """Sanitize folder name for OneDrive.

        Args:
            name: Original folder name

        Returns:
            Sanitized folder name
        """
        # Remove invalid characters
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        sanitized = name

        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')

        # Limit length
        return sanitized[:200]

    def flag_for_review(self, patient_name: str, reason: str, metadata: Dict[str, Any]):
        """Flag upload for manual review.

        Args:
            patient_name: Patient name
            reason: Reason for flagging
            metadata: Additional context information
        """
        logger.warning(f"⚠️  FLAGGED FOR REVIEW: {patient_name} - {reason}")
        self.flagged_for_review.append({
            'patient_name': patient_name,
            'reason': reason,
            'metadata': metadata
        })

    def get_statistics(self) -> Dict[str, int]:
        """Get upload statistics.

        Returns:
            Dictionary with success, failure, and flagged counts
        """
        return {
            "success": self.success_count,
            "failure": self.failure_count,
            "flagged": len(self.flagged_for_review),
            "total": self.success_count + self.failure_count
        }
