"""PDF form filling from database records."""
from typing import Dict, Any, Optional, List
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from loguru import logger
from src.pdf.field_mapper import FieldMapper
from src.pdf.pdf_validator import PDFValidator
import json


class PDFFormFiller:
    """Fill PDF forms with patient data from database."""

    def __init__(self,
                 template_dir: Path,
                 output_dir: Path,
                 field_mappings_dir: Path,
                 retry_attempts: int = 3):
        """Initialize PDF form filler.

        Args:
            template_dir: Directory containing PDF templates
            output_dir: Directory for generated PDFs
            field_mappings_dir: Directory with YAML field mapping configs
            retry_attempts: Number of retry attempts for failed fills
        """
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        self.field_mappings_dir = Path(field_mappings_dir)
        self.retry_attempts = retry_attempts

        # Create output directories
        (self.output_dir / "generated").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "failed").mkdir(parents=True, exist_ok=True)

        self.field_mapper = FieldMapper(field_mappings_dir)
        self.validator = PDFValidator()

        self.success_count = 0
        self.failure_count = 0
        self.flagged_for_review = []

    def fill_form(self,
                  template_name: str,
                  patient_data: Dict[str, Any],
                  visit_data: Dict[str, Any],
                  output_filename: str) -> Optional[Path]:
        """Fill a PDF form with patient/visit data.

        Args:
            template_name: Name of PDF template (e.g., '1a Initial Contact - Dallas')
            patient_data: Patient demographic data from database
            visit_data: Visit details (note text, date, provider, etc.)
            output_filename: Desired filename for output PDF

        Returns:
            Path to generated PDF or None if failed
        """
        try:
            # Load template
            template_path = self.template_dir / f"{template_name}.pdf"
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")

            logger.info(f"Filling form: {template_name} for {patient_data.get('name')}")

            # Read template
            reader = PdfReader(template_path)
            writer = PdfWriter()

            # Get field mapping for this template (if exists)
            try:
                field_map = self.field_mapper.get_mapping(template_name)
                # Map database fields to PDF form fields
                pdf_fields = self.field_mapper.map_data_to_fields(
                    field_map,
                    patient_data,
                    visit_data
                )
            except FileNotFoundError:
                # No field mapping exists, use data directly
                logger.warning(f"No field mapping found for {template_name}, using data directly")
                pdf_fields = {**patient_data, **visit_data}

            # Validate data before filling
            validation_errors = self.validator.validate_data(pdf_fields, template_name)
            if validation_errors:
                logger.warning(f"Validation warnings: {validation_errors}")

            # Add pages from reader
            for page in reader.pages:
                writer.add_page(page)

            # Fill form fields (PyPDF2 fills all fields regardless of page)
            writer.update_page_form_field_values(
                writer.pages[0],
                pdf_fields
            )

            # Write output
            output_path = self.output_dir / "generated" / output_filename
            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            # Validate output PDF
            if self.validator.validate_pdf_file(output_path):
                logger.info(f"✓ Successfully generated PDF: {output_path}")
                self.success_count += 1
                return output_path
            else:
                logger.error(f"PDF validation failed: {output_path}")
                self.failure_count += 1
                return None

        except Exception as e:
            logger.error(f"Failed to fill form {template_name}: {e}")
            self.failure_count += 1
            self.flag_for_review(
                patient_data.get('name', 'Unknown'),
                f"PDF generation failed: {str(e)}",
                {"template": template_name, "visit_data": visit_data}
            )
            return None

    def flag_for_review(self, patient_name: str, reason: str, metadata: Dict[str, Any]):
        """Flag a PDF for manual review.

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

    def get_available_templates(self) -> List[str]:
        """Get list of available PDF templates.

        Returns:
            List of template names (without .pdf extension)
        """
        templates = list(self.template_dir.glob("*.pdf"))
        return [t.stem for t in templates]

    def get_statistics(self) -> Dict[str, int]:
        """Get PDF generation statistics.

        Returns:
            Dictionary with success, failure, and flagged counts
        """
        return {
            "success": self.success_count,
            "failure": self.failure_count,
            "flagged": len(self.flagged_for_review),
            "total": self.success_count + self.failure_count
        }

    def save_flagged_report(self, output_path: Path):
        """Save flagged items to JSON file.

        Args:
            output_path: Path to save flagged report
        """
        with open(output_path, 'w') as f:
            json.dump(self.flagged_for_review, f, indent=2)
        logger.info(f"Flagged report saved: {output_path}")
