"""PDF form generation and management API routes."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import Database
from src.pdf.pdf_form_filler import PDFFormFiller
from src.workflows.pdf_form_orchestrator import PDFFormOrchestrator
from src.utils.config import AppConfig

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

# Initialize components
db = Database()
config = AppConfig.from_env()

pdf_filler = PDFFormFiller(
    template_dir=Path(config.pdf_template_dir),
    output_dir=Path(config.pdf_output_dir),
    field_mappings_dir=Path(config.pdf_field_mappings_dir),
    retry_attempts=config.pdf_retry_attempts
)

orchestrator = PDFFormOrchestrator(config)


# Request/Response Models
class GeneratePDFRequest(BaseModel):
    patient_id: int
    form_type: str
    visit_date: Optional[str] = None


class BatchGenerateRequest(BaseModel):
    start_date: str
    end_date: str
    form_types: List[str]
    dry_run: bool = True


class PDFRecord(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    visit_date: Optional[str]
    form_type: str
    onedrive_url: Optional[str]
    upload_status: str
    flagged_for_review: bool
    created_at: str


class PDFStats(BaseModel):
    total: int
    pending: int
    uploaded: int
    failed: int
    flagged: int


# Routes

@router.get("/templates")
async def get_available_templates():
    """Get list of available PDF templates."""
    try:
        templates = pdf_filler.get_available_templates()
        return {
            "success": True,
            "templates": templates,
            "count": len(templates)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forms")
async def get_generated_forms(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None
):
    """Get list of generated PDF forms with filters."""
    try:
        # Default to last 30 days if no dates provided
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
        if not end_date:
            end_date = date.today().isoformat()

        records = db.get_pdf_forms_by_date_range(start_date, end_date)

        # Filter by status if provided
        if status:
            records = [r for r in records if r.get('upload_status') == status]

        # Enrich with patient names
        for record in records:
            patient_id = record.get('patient_id')
            if patient_id:
                patient = db.get_patient(patient_id)
                if patient:
                    record['patient_name'] = patient.get('name', 'Unknown')

        return {
            "success": True,
            "forms": records,
            "count": len(records),
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "status": status
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forms/flagged")
async def get_flagged_forms():
    """Get all forms flagged for manual review."""
    try:
        flagged = db.get_flagged_pdfs()

        # Enrich with patient names
        for record in flagged:
            patient_id = record.get('patient_id')
            if patient_id:
                patient = db.get_patient(patient_id)
                if patient:
                    record['patient_name'] = patient.get('name', 'Unknown')

        return {
            "success": True,
            "flagged_forms": flagged,
            "count": len(flagged)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_pdf_statistics():
    """Get PDF generation statistics."""
    try:
        stats = db.get_pdf_generation_stats()

        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_single_pdf(request: GeneratePDFRequest):
    """Generate a single PDF form for a patient."""
    try:
        # Get patient data
        patient = db.get_patient(request.patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Check if already generated
        visit_date = request.visit_date or date.today().isoformat()
        exists = db.check_pdf_already_generated(
            request.patient_id,
            visit_date,
            request.form_type
        )

        if exists:
            return {
                "success": False,
                "message": "PDF already generated for this patient/date/form combination",
                "existing_record": exists
            }

        # Prepare data
        patient_data = {
            "name": patient.get("name", ""),
            "registration_number": patient.get("freed_username", "N/A")
        }

        visit_data = {
            "INMATE NAME": patient.get("name", ""),
            "REG NO": patient.get("freed_username", "N/A"),
            "Date": date.today().strftime("%m/%d/%Y"),
            "Date_of_initial": visit_date
        }

        # Generate PDF
        output_filename = f"{request.form_type}_{request.patient_id}_{visit_date}.pdf"
        output_path = pdf_filler.fill_form(
            template_name=request.form_type,
            patient_data=patient_data,
            visit_data=visit_data,
            output_filename=output_filename
        )

        if not output_path:
            raise HTTPException(status_code=500, detail="PDF generation failed")

        # Record in database
        pdf_id = db.add_pdf_form_record(
            patient_id=request.patient_id,
            visit_date=visit_date,
            form_type=request.form_type,
            local_path=str(output_path),
            upload_status="pending"
        )

        return {
            "success": True,
            "message": "PDF generated successfully",
            "pdf_id": pdf_id,
            "file_path": str(output_path),
            "patient_name": patient.get("name")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/batch")
async def generate_batch_pdfs(request: BatchGenerateRequest, background_tasks: BackgroundTasks):
    """Generate PDFs for multiple patients in a date range."""
    try:
        # Run in background
        def run_batch():
            results = orchestrator.process_date_range(
                start_date=datetime.fromisoformat(request.start_date).date(),
                end_date=datetime.fromisoformat(request.end_date).date(),
                form_types=request.form_types,
                dry_run=request.dry_run
            )
            return results

        if request.dry_run:
            # Run synchronously for dry run
            results = run_batch()
            return {
                "success": True,
                "message": "Dry run completed",
                "results": results
            }
        else:
            # Run in background
            background_tasks.add_task(run_batch)
            return {
                "success": True,
                "message": "Batch generation started in background",
                "filters": {
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "form_types": request.form_types
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forms/{pdf_id}/flag")
async def flag_pdf_for_review(pdf_id: int, reason: str):
    """Flag a PDF for manual review."""
    try:
        db.flag_pdf_for_review(pdf_id, reason)
        return {
            "success": True,
            "message": "PDF flagged for review",
            "pdf_id": pdf_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/forms/{pdf_id}")
async def delete_pdf_record(pdf_id: int):
    """Delete a PDF record from database."""
    try:
        # Note: This doesn't delete the actual file, just the database record
        # You may want to add file deletion logic here
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM pdf_forms_generated WHERE id = ?", (pdf_id,))
        db.conn.commit()

        return {
            "success": True,
            "message": "PDF record deleted",
            "pdf_id": pdf_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forms/{pdf_id}/download")
async def get_pdf_download_path(pdf_id: int):
    """Get download path for a generated PDF."""
    try:
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT local_path, form_type, patient_id FROM pdf_forms_generated WHERE id = ?",
            (pdf_id,)
        )
        record = cursor.fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="PDF not found")

        return {
            "success": True,
            "pdf_id": pdf_id,
            "local_path": record[0],
            "form_type": record[1],
            "patient_id": record[2]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
