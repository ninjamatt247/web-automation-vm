"""PDF validation utilities."""
from typing import Dict, List
from pathlib import Path
from pypdf import PdfReader
from loguru import logger


class PDFValidator:
    """Validate PDF forms before and after filling."""

    def validate_data(self,
                     pdf_fields: Dict[str, str],
                     template_name: str) -> List[str]:
        """Validate data before filling PDF.

        Args:
            pdf_fields: Dictionary of field values
            template_name: Name of template being filled

        Returns:
            List of validation warnings (empty if all valid)
        """
        warnings = []

        # Check for required fields (customizable per template)
        required_fields = self._get_required_fields(template_name)

        for field in required_fields:
            if not pdf_fields.get(field):
                warnings.append(f"Missing required field: {field}")

        # Check field lengths
        for field, value in pdf_fields.items():
            if len(value) > 5000:  # PDF field limit
                warnings.append(f"Field '{field}' exceeds max length: {len(value)}")

        return warnings

    def validate_pdf_file(self, pdf_path: Path) -> bool:
        """Validate generated PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check file exists and is readable
            if not pdf_path.exists():
                logger.error(f"PDF file does not exist: {pdf_path}")
                return False

            # Try to read PDF
            reader = PdfReader(pdf_path)

            # Validate has pages
            if len(reader.pages) == 0:
                logger.error(f"PDF has no pages: {pdf_path}")
                return False

            # Check file size is reasonable (>1KB, <50MB)
            file_size = pdf_path.stat().st_size
            if file_size < 1024:
                logger.error(f"PDF file too small: {file_size} bytes")
                return False
            if file_size > 50 * 1024 * 1024:
                logger.warning(f"PDF file very large: {file_size / 1024 / 1024:.2f} MB")

            logger.info(f"PDF validation passed: {pdf_path.name} ({file_size / 1024:.1f} KB)")
            return True

        except Exception as e:
            logger.error(f"PDF validation failed for {pdf_path}: {e}")
            return False

    def _get_required_fields(self, template_name: str) -> List[str]:
        """Get list of required fields for a template.

        Args:
            template_name: Name of PDF template

        Returns:
            List of required field names
        """
        # Configurable per template type
        required_by_template = {
            'progress_note': ['patient_name', 'visit_date', 'provider_name'],
            'intake_form': ['patient_name', 'patient_dob', 'visit_date'],
            'prescription_form': ['patient_name', 'medication_name', 'provider_name']
        }
        return required_by_template.get(template_name, [])
