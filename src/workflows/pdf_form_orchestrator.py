"""Orchestrate PDF generation and upload workflow."""
from typing import List, Dict, Any, Optional
from datetime import date
from pathlib import Path
from src.pdf.pdf_form_filler import PDFFormFiller
from src.uploaders.onedrive_uploader import OneDriveUploader
from src.utils.config import AppConfig
from loguru import logger
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "web-app" / "backend"))
from database import Database
import json


class PDFFormOrchestrator:
    """Orchestrate PDF generation and OneDrive upload workflow."""

    def __init__(self, config: AppConfig):
        """Initialize orchestrator.

        Args:
            config: Application configuration
        """
        self.config = config
        self.db = Database()

        self.pdf_filler = PDFFormFiller(
            template_dir=Path(config.pdf_template_dir),
            output_dir=Path(config.pdf_output_dir),
            field_mappings_dir=Path(config.pdf_field_mappings_dir),
            retry_attempts=config.pdf_retry_attempts
        )

        self.onedrive_uploader = OneDriveUploader(
            config=config,
            retry_attempts=config.pdf_retry_attempts
        )

    def process_date_range(self,
                          start_date: date,
                          end_date: date,
                          form_types: List[str],
                          dry_run: bool = False) -> Dict[str, Any]:
        """Process all visits in date range and generate PDFs.

        Args:
            start_date: Start date for visit filtering
            end_date: End date for visit filtering
            form_types: List of form types to generate
            dry_run: If True, generate PDFs but don't upload

        Returns:
            Summary statistics
        """
        logger.info(f"Processing date range: {start_date} to {end_date}")
        logger.info(f"Form types: {form_types}")
        logger.info(f"Dry run: {dry_run}")

        # Fetch all visits in date range with patient data
        visits = self._fetch_visits_for_date_range(start_date, end_date)

        logger.info(f"Found {len(visits)} visits to process")

        total_generated = 0
        total_uploaded = 0
        total_skipped = 0
        total_failed = 0

        for visit in visits:
            for form_type in form_types:
                # Check if already processed
                if self.db.check_pdf_already_generated(
                    visit['patient_id'],
                    visit['visit_date'],
                    form_type
                ):
                    logger.info(f"Skipping {visit['patient_name']} - {form_type} (already generated)")
                    total_skipped += 1
                    continue

                # Generate PDF
                pdf_path = self._generate_pdf(visit, form_type)

                if pdf_path:
                    total_generated += 1

                    # Upload to OneDrive (unless dry run)
                    if not dry_run:
                        onedrive_url = self._upload_to_onedrive(visit, pdf_path)

                        if onedrive_url:
                            total_uploaded += 1
                        else:
                            total_failed += 1
                    else:
                        logger.info(f"DRY RUN: Would upload {pdf_path} to OneDrive")
                        total_uploaded += 1  # Count as success in dry run
                else:
                    total_failed += 1

        results = {
            "visits_processed": len(visits),
            "pdfs_generated": total_generated,
            "pdfs_uploaded": total_uploaded,
            "pdfs_skipped": total_skipped,
            "pdfs_failed": total_failed,
            "flagged_items": len(self.pdf_filler.flagged_for_review) +
                           len(self.onedrive_uploader.flagged_for_review)
        }

        logger.info(f"Processing complete: {results}")
        return results

    def _fetch_visits_for_date_range(self, start_date: date, end_date: date) -> List[Dict]:
        """Fetch all visits with patient data for date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of visit records with patient info
        """
        # Query combined_notes table joined with patients
        query = """
            SELECT
                cn.id as combined_note_id,
                cn.patient_id,
                cn.visit_date,
                cn.final_note,
                cn.original_freed_note,
                p.name as patient_name,
                p.freed_patient_id,
                p.osmind_patient_id,
                fn.note_text as freed_note_text,
                fn.sections as freed_sections,
                on.rendering_provider_name,
                on.location_name,
                on.note_type,
                on.first_signed_at
            FROM combined_notes cn
            JOIN patients p ON cn.patient_id = p.id
            LEFT JOIN freed_notes fn ON cn.freed_note_id = fn.id
            LEFT JOIN osmind_notes on ON cn.osmind_note_id = on.id
            WHERE DATE(cn.visit_date) BETWEEN DATE(?) AND DATE(?)
              AND cn.processing_status != 'pending'
            ORDER BY cn.visit_date DESC
        """

        self.db.cursor.execute(query, (str(start_date), str(end_date)))
        visits = [dict(row) for row in self.db.cursor.fetchall()]

        # Parse sections JSON and extract clinical data
        for visit in visits:
            if visit.get('freed_sections'):
                try:
                    sections = json.loads(visit['freed_sections'])
                    visit.update(self._parse_clinical_sections(sections))
                except:
                    pass

        return visits

    def _parse_clinical_sections(self, sections: Dict) -> Dict[str, str]:
        """Parse clinical sections from Freed.ai JSON.

        Args:
            sections: Sections dictionary from freed_notes

        Returns:
            Flattened clinical data
        """
        # Extract common sections
        return {
            'chief_complaint': sections.get('chief_complaint', ''),
            'history_present_illness': sections.get('history_present_illness', ''),
            'assessment': sections.get('assessment', ''),
            'plan': sections.get('plan', ''),
            'medications': sections.get('medications', ''),
            'mental_status_exam': sections.get('mental_status_exam', ''),
            'icd10_code_1': sections.get('diagnosis_codes', [''])[0] if sections.get('diagnosis_codes') else '',
            'icd10_code_2': sections.get('diagnosis_codes', ['', ''])[1] if len(sections.get('diagnosis_codes', [])) > 1 else ''
        }

    def _generate_pdf(self, visit: Dict[str, Any], form_type: str) -> Optional[Path]:
        """Generate PDF for a visit.

        Args:
            visit: Visit data dictionary
            form_type: Type of form to generate

        Returns:
            Path to generated PDF or None
        """
        # Prepare patient data
        patient_data = {
            'name': visit['patient_name'],
            'patient_id': visit['freed_patient_id'] or visit['osmind_patient_id'],
            'freed_patient_id': visit['freed_patient_id'],
            'osmind_patient_id': visit['osmind_patient_id']
        }

        # Prepare visit data
        visit_data = {
            'visit_date': visit['visit_date'],
            'note_text': visit['final_note'] or visit['freed_note_text'],
            'rendering_provider_name': visit.get('rendering_provider_name', ''),
            'location_name': visit.get('location_name', ''),
            'note_type': visit.get('note_type', ''),
            'first_signed_at': visit.get('first_signed_at', ''),
            **visit  # Include all parsed sections
        }

        # Generate filename
        safe_name = visit['patient_name'].replace(' ', '_')
        safe_date = str(visit['visit_date']).replace('/', '-')
        filename = f"{safe_name}_{safe_date}_{form_type}.pdf"

        # Fill PDF
        pdf_path = self.pdf_filler.fill_form(
            template_name=form_type,
            patient_data=patient_data,
            visit_data=visit_data,
            output_filename=filename
        )

        if pdf_path:
            # Record in database
            self.db.add_pdf_form_record(
                patient_id=visit['patient_id'],
                visit_date=visit['visit_date'],
                form_type=form_type,
                template_name=form_type,
                pdf_filename=filename,
                pdf_local_path=str(pdf_path)
            )

        return pdf_path

    def _upload_to_onedrive(self, visit: Dict[str, Any], pdf_path: Path) -> Optional[str]:
        """Upload PDF to OneDrive.

        Args:
            visit: Visit data
            pdf_path: Path to PDF file

        Returns:
            OneDrive URL or None
        """
        onedrive_url = self.onedrive_uploader.upload_pdf(
            pdf_path=pdf_path,
            patient_name=visit['patient_name'],
            patient_id=visit['freed_patient_id'] or visit['osmind_patient_id'],
            metadata={'visit_date': visit['visit_date']}
        )

        if onedrive_url:
            # Update database record
            # Find the PDF record
            self.db.cursor.execute("""
                SELECT id FROM pdf_forms_generated
                WHERE patient_id = ? AND visit_date = ?
                ORDER BY created_at DESC LIMIT 1
            """, (visit['patient_id'], visit['visit_date']))

            record = self.db.cursor.fetchone()
            if record:
                folder_name = self.onedrive_uploader._sanitize_folder_name(
                    f"{visit['patient_name']}_{visit['freed_patient_id'] or visit['osmind_patient_id']}"
                )
                self.db.update_pdf_upload_status(
                    pdf_form_id=record['id'],
                    onedrive_url=onedrive_url,
                    onedrive_folder_name=folder_name
                )

        return onedrive_url
