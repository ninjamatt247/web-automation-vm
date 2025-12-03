#!/usr/bin/env python3
"""
Review workflow API endpoints for monthly ASOP note processing
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import sqlite3

from src.utils.logger import logger

router = APIRouter(prefix="/api/review", tags=["Review Workflow"])

# Database helper
def get_db_connection():
    """Get database connection"""
    db_path = Path(__file__).parent / "medical_notes.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# ==============================================================================
# PYDANTIC MODELS
# ==============================================================================

class BatchProcessRequest(BaseModel):
    start_date: str
    end_date: str
    batch_id: Optional[str] = None
    process_duplicates: bool = False


class ReviewStatusUpdate(BaseModel):
    result_id: int
    review_status: str  # 'approved', 'rejected', 'needs_revision'
    review_notes: Optional[str] = None
    reviewed_by: str


class BatchReviewUpdate(BaseModel):
    review_status: str
    review_notes: Optional[str] = None
    reviewed_by: str
    result_ids: List[int]


class UploadRequest(BaseModel):
    result_ids: List[int]
    upload_mode: str = "manual"  # 'manual', 'auto'


# ==============================================================================
# BATCH PROCESSING ENDPOINTS
# ==============================================================================

@router.get("/batches")
async def get_batch_runs(limit: int = 50, status: Optional[str] = None):
    """Get all batch processing runs with optional status filter"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT * FROM batch_processing_runs
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT * FROM batch_processing_runs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        batches = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return {
            "batches": batches,
            "count": len(batches),
            "filter": {"status": status, "limit": limit}
        }
    except Exception as e:
        logger.error(f"Failed to fetch batch runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch batch runs: {str(e)}")


@router.get("/batches/{batch_id}")
async def get_batch_details(batch_id: str):
    """Get detailed information about a specific batch"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get batch run info
        cursor.execute("""
            SELECT * FROM batch_processing_runs
            WHERE batch_id = ?
        """, (batch_id,))

        batch = cursor.fetchone()
        if not batch:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        batch_dict = dict(batch)

        # Get processing results for this batch
        cursor.execute("""
            SELECT
                id,
                patient_name,
                visit_date,
                processing_status,
                requires_human_intervention,
                review_status,
                upload_status,
                total_checks,
                passed_checks,
                failed_checks,
                critical_failures,
                created_at
            FROM ai_processing_results
            WHERE batch_id = ?
            ORDER BY created_at DESC
        """, (batch_id,))

        results = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "batch": batch_dict,
            "results": results,
            "count": len(results)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch batch details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch batch details: {str(e)}")


@router.get("/batches/{batch_id}/stats")
async def get_batch_stats(batch_id: str):
    """Get statistics for a specific batch"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get batch info
        cursor.execute("""
            SELECT * FROM batch_processing_runs
            WHERE batch_id = ?
        """, (batch_id,))

        batch = cursor.fetchone()
        if not batch:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        # Get review status breakdown
        cursor.execute("""
            SELECT
                review_status,
                COUNT(*) as count
            FROM ai_processing_results
            WHERE batch_id = ?
            GROUP BY review_status
        """, (batch_id,))

        review_breakdown = {row['review_status']: row['count'] for row in cursor.fetchall()}

        # Get upload status breakdown
        cursor.execute("""
            SELECT
                upload_status,
                COUNT(*) as count
            FROM ai_processing_results
            WHERE batch_id = ?
            GROUP BY upload_status
        """, (batch_id,))

        upload_breakdown = {row['upload_status']: row['count'] for row in cursor.fetchall()}

        # Get quality metrics
        cursor.execute("""
            SELECT
                AVG(passed_checks * 1.0 / NULLIF(total_checks, 0)) as avg_pass_rate,
                COUNT(CASE WHEN critical_failures > 0 THEN 1 END) as critical_count,
                COUNT(CASE WHEN requires_human_intervention = 1 THEN 1 END) as intervention_count
            FROM ai_processing_results
            WHERE batch_id = ?
        """, (batch_id,))

        quality_row = cursor.fetchone()

        conn.close()

        return {
            "batch_id": batch_id,
            "batch_info": dict(batch),
            "review_breakdown": review_breakdown,
            "upload_breakdown": upload_breakdown,
            "quality_metrics": {
                "avg_pass_rate": round(quality_row['avg_pass_rate'] or 0, 3),
                "critical_failures": quality_row['critical_count'],
                "needs_intervention": quality_row['intervention_count']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch batch stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch batch stats: {str(e)}")


# ==============================================================================
# REVIEW WORKFLOW ENDPOINTS
# ==============================================================================

@router.get("/pending")
async def get_pending_reviews(
    batch_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get notes pending review with optional batch filter"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if batch_id:
            cursor.execute("""
                SELECT
                    id,
                    patient_name,
                    visit_date,
                    processing_status,
                    requires_human_intervention,
                    human_intervention_reasons,
                    review_status,
                    total_checks,
                    passed_checks,
                    failed_checks,
                    critical_failures,
                    high_failures,
                    medium_failures,
                    final_cleaned_note,
                    batch_id,
                    created_at
                FROM ai_processing_results
                WHERE review_status = 'pending'
                  AND batch_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (batch_id, limit, offset))
        else:
            cursor.execute("""
                SELECT
                    id,
                    patient_name,
                    visit_date,
                    processing_status,
                    requires_human_intervention,
                    human_intervention_reasons,
                    review_status,
                    total_checks,
                    passed_checks,
                    failed_checks,
                    critical_failures,
                    high_failures,
                    medium_failures,
                    final_cleaned_note,
                    batch_id,
                    created_at
                FROM ai_processing_results
                WHERE review_status = 'pending'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        results = [dict(row) for row in cursor.fetchall()]

        # Get total count
        if batch_id:
            cursor.execute("""
                SELECT COUNT(*) as total FROM ai_processing_results
                WHERE review_status = 'pending' AND batch_id = ?
            """, (batch_id,))
        else:
            cursor.execute("""
                SELECT COUNT(*) as total FROM ai_processing_results
                WHERE review_status = 'pending'
            """)

        total = cursor.fetchone()['total']

        conn.close()

        return {
            "results": results,
            "count": len(results),
            "total": total,
            "limit": limit,
            "offset": offset,
            "batch_id": batch_id
        }
    except Exception as e:
        logger.error(f"Failed to fetch pending reviews: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending reviews: {str(e)}")


@router.post("/update-status")
async def update_review_status(update: ReviewStatusUpdate):
    """Update review status for a single note"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Validate review_status
        valid_statuses = ['approved', 'rejected', 'needs_revision', 'pending']
        if update.review_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid review_status. Must be one of: {', '.join(valid_statuses)}"
            )

        cursor.execute("""
            UPDATE ai_processing_results
            SET
                review_status = ?,
                reviewed_at = CURRENT_TIMESTAMP,
                reviewed_by = ?,
                review_notes = ?
            WHERE id = ?
        """, (
            update.review_status,
            update.reviewed_by,
            update.review_notes,
            update.result_id
        ))

        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Result {update.result_id} not found")

        conn.close()

        return {
            "success": True,
            "message": f"Review status updated to '{update.review_status}'",
            "result_id": update.result_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update review status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update review status: {str(e)}")


@router.post("/batch-update-status")
async def batch_update_review_status(update: BatchReviewUpdate):
    """Update review status for multiple notes at once"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Validate review_status
        valid_statuses = ['approved', 'rejected', 'needs_revision', 'pending']
        if update.review_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid review_status. Must be one of: {', '.join(valid_statuses)}"
            )

        updated_count = 0
        for result_id in update.result_ids:
            cursor.execute("""
                UPDATE ai_processing_results
                SET
                    review_status = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = ?,
                    review_notes = ?
                WHERE id = ?
            """, (
                update.review_status,
                update.reviewed_by,
                update.review_notes,
                result_id
            ))
            updated_count += cursor.rowcount

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Updated {updated_count} notes to '{update.review_status}'",
            "updated_count": updated_count,
            "requested_count": len(update.result_ids)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch update review status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to batch update review status: {str(e)}")


@router.get("/result/{result_id}")
async def get_processing_result(result_id: int):
    """Get detailed processing result for a specific note"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM ai_processing_results
            WHERE id = ?
        """, (result_id,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Result {result_id} not found")

        result_dict = dict(result)

        # Get validation checks for this result
        cursor.execute("""
            SELECT * FROM validation_checks
            WHERE processing_result_id = ?
            ORDER BY priority DESC, check_name
        """, (result_id,))

        checks = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            "result": result_dict,
            "validation_checks": checks,
            "check_count": len(checks)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch processing result: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch processing result: {str(e)}")


# ==============================================================================
# UPLOAD TRACKING ENDPOINTS
# ==============================================================================

@router.get("/upload-ready")
async def get_upload_ready_notes(batch_id: Optional[str] = None, limit: int = 100):
    """Get notes ready for upload (approved and not yet uploaded)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if batch_id:
            cursor.execute("""
                SELECT
                    id,
                    patient_name,
                    visit_date,
                    final_cleaned_note,
                    review_status,
                    upload_status,
                    upload_attempts,
                    batch_id,
                    created_at
                FROM ai_processing_results
                WHERE review_status = 'approved'
                  AND (upload_status = 'pending' OR upload_status IS NULL)
                  AND batch_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (batch_id, limit))
        else:
            cursor.execute("""
                SELECT
                    id,
                    patient_name,
                    visit_date,
                    final_cleaned_note,
                    review_status,
                    upload_status,
                    upload_attempts,
                    batch_id,
                    created_at
                FROM ai_processing_results
                WHERE review_status = 'approved'
                  AND (upload_status = 'pending' OR upload_status IS NULL)
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return {
            "results": results,
            "count": len(results),
            "batch_id": batch_id
        }
    except Exception as e:
        logger.error(f"Failed to fetch upload-ready notes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch upload-ready notes: {str(e)}")


@router.get("/upload-history")
async def get_upload_history(
    batch_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get upload history with optional batch filter"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if batch_id:
            cursor.execute("""
                SELECT * FROM upload_history
                WHERE batch_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (batch_id, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM upload_history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        history = [dict(row) for row in cursor.fetchall()]

        # Get total count
        if batch_id:
            cursor.execute("""
                SELECT COUNT(*) as total FROM upload_history
                WHERE batch_id = ?
            """, (batch_id,))
        else:
            cursor.execute("SELECT COUNT(*) as total FROM upload_history")

        total = cursor.fetchone()['total']

        conn.close()

        return {
            "history": history,
            "count": len(history),
            "total": total,
            "limit": limit,
            "offset": offset,
            "batch_id": batch_id
        }
    except Exception as e:
        logger.error(f"Failed to fetch upload history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch upload history: {str(e)}")


@router.post("/record-upload")
async def record_upload_attempt(
    result_id: int,
    upload_status: str,
    error_message: Optional[str] = None,
    osmind_note_found: bool = False,
    note_was_signed: bool = False,
    content_appended: bool = False
):
    """Record an upload attempt in the upload_history table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get processing result info
        cursor.execute("""
            SELECT patient_name, visit_date, batch_id, upload_attempts
            FROM ai_processing_results
            WHERE id = ?
        """, (result_id,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Result {result_id} not found")

        result_dict = dict(result)
        attempt_number = (result_dict['upload_attempts'] or 0) + 1

        # Insert upload history record
        cursor.execute("""
            INSERT INTO upload_history (
                processing_result_id,
                batch_id,
                patient_name,
                visit_date,
                upload_status,
                error_message,
                attempt_number,
                osmind_note_found,
                note_was_signed,
                content_appended
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_id,
            result_dict['batch_id'],
            result_dict['patient_name'],
            result_dict['visit_date'],
            upload_status,
            error_message,
            attempt_number,
            osmind_note_found,
            note_was_signed,
            content_appended
        ))

        # Update ai_processing_results
        cursor.execute("""
            UPDATE ai_processing_results
            SET
                upload_status = ?,
                upload_attempts = ?,
                uploaded_at = CASE WHEN ? = 'success' THEN CURRENT_TIMESTAMP ELSE uploaded_at END,
                upload_error = ?
            WHERE id = ?
        """, (upload_status, attempt_number, upload_status, error_message, result_id))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Upload attempt #{attempt_number} recorded",
            "result_id": result_id,
            "attempt_number": attempt_number,
            "upload_status": upload_status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record upload attempt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record upload attempt: {str(e)}")


# ==============================================================================
# DASHBOARD SUMMARY ENDPOINTS
# ==============================================================================

@router.get("/dashboard/summary")
async def get_review_dashboard_summary(batch_id: Optional[str] = None):
    """Get summary statistics for review dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Base WHERE clause
        where_clause = f"WHERE batch_id = '{batch_id}'" if batch_id else ""

        # Get review status counts
        cursor.execute(f"""
            SELECT
                review_status,
                COUNT(*) as count
            FROM ai_processing_results
            {where_clause}
            GROUP BY review_status
        """)

        review_counts = {row['review_status']: row['count'] for row in cursor.fetchall()}

        # Get upload status counts
        cursor.execute(f"""
            SELECT
                upload_status,
                COUNT(*) as count
            FROM ai_processing_results
            {where_clause}
            GROUP BY upload_status
        """)

        upload_counts = {row['upload_status']: row['count'] for row in cursor.fetchall()}

        # Get quality breakdown
        cursor.execute(f"""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN requires_human_intervention = 1 THEN 1 END) as needs_intervention,
                COUNT(CASE WHEN critical_failures > 0 THEN 1 END) as has_critical_failures,
                AVG(passed_checks * 1.0 / NULLIF(total_checks, 0)) as avg_pass_rate
            FROM ai_processing_results
            {where_clause}
        """)

        quality = dict(cursor.fetchone())

        conn.close()

        return {
            "batch_id": batch_id,
            "review_status": review_counts,
            "upload_status": upload_counts,
            "quality_metrics": {
                "total_notes": quality['total'],
                "needs_intervention": quality['needs_intervention'],
                "critical_failures": quality['has_critical_failures'],
                "avg_pass_rate": round(quality['avg_pass_rate'] or 0, 3)
            }
        }
    except Exception as e:
        logger.error(f"Failed to fetch dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard summary: {str(e)}")


# ==============================================================================
# RE-PROCESSING ENDPOINTS
# ==============================================================================

class ReprocessRequest(BaseModel):
    result_id: int
    max_attempts: int = 3


class BulkReprocessRequest(BaseModel):
    result_ids: List[int]
    max_attempts: int = 3


@router.get("/note/{result_id}")
async def get_note_detail(result_id: int):
    """Get detailed note information including original note, processed note, and validation checks

    Args:
        result_id: ID of the ai_processing_results record

    Returns:
        Detailed note information with validation checks
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the note details
        cursor.execute("""
            SELECT
                id,
                patient_name,
                visit_date,
                raw_note,
                step1_note,
                step2_note,
                final_cleaned_note,
                processing_status,
                requires_human_intervention,
                human_intervention_reasons,
                total_checks,
                passed_checks,
                failed_checks,
                critical_failures,
                high_failures,
                medium_failures,
                low_failures,
                tokens_used,
                model_used,
                processing_attempts,
                last_processed_at,
                review_status,
                upload_status
            FROM ai_processing_results
            WHERE id = ?
        """, (result_id,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Note with ID {result_id} not found")

        note_data = dict(result)

        # Get validation check details by re-running validation
        from src.utils.requirement_validator import RequirementValidator
        from src.utils.prompt_config import PromptConfig

        prompt_config = PromptConfig()
        validator = RequirementValidator(prompt_config)

        # Run validation on the processed note (use final_cleaned_note if available, otherwise step2_note)
        note_to_validate = note_data.get('final_cleaned_note') or note_data.get('step2_note')
        if note_to_validate:
            validation_report = validator.validate_note(note_to_validate)

            # Format check results
            check_results = []
            for check in validation_report.validation_results:
                check_results.append({
                    "id": check.requirement_id,
                    "name": check.requirement_name,
                    "priority": check.priority,
                    "passed": check.passed,
                    "message": check.error_message or "",
                    "details": check.details or ""
                })

            note_data['validation_checks'] = check_results
            note_data['human_intervention_reasons_list'] = validation_report.human_intervention_reasons
        else:
            note_data['validation_checks'] = []
            note_data['human_intervention_reasons_list'] = []

        conn.close()

        return note_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get note detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get note detail: {str(e)}")


@router.post("/reprocess")
async def reprocess_note(request: ReprocessRequest):
    """Re-process a single note through OpenAI pipeline

    This endpoint takes a note that failed validation and sends it back through
    the 3-step OpenAI processing pipeline with the updated prompts.

    Args:
        result_id: ID of the ai_processing_results record to re-process
        max_attempts: Maximum number of re-processing attempts (default: 3)

    Returns:
        Updated processing result with new validation status
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the existing result
        cursor.execute("""
            SELECT
                id,
                patient_name,
                visit_date,
                raw_note,
                processing_attempts,
                processing_status
            FROM ai_processing_results
            WHERE id = ?
        """, (request.result_id,))

        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail=f"Result ID {request.result_id} not found")

        result_dict = dict(result)
        current_attempts = result_dict.get('processing_attempts') or 0

        # Check if we've exceeded max attempts
        if current_attempts >= request.max_attempts:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Note has already been processed {current_attempts} times (max: {request.max_attempts})"
            )

        # Initialize OpenAI processor
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.utils.config import get_config
        from src.utils.openai_processor import OpenAIProcessor

        config = get_config()
        processor = OpenAIProcessor(
            config=config,
            use_multi_step=True,
            store_in_db=False
        )

        logger.info(f"Re-processing note {request.result_id} (attempt {current_attempts + 1}/{request.max_attempts})")

        # Re-process the note
        new_result = processor.multi_step_clean_patient_note(
            raw_note=result_dict['raw_note']
        )

        if not new_result or new_result.get('processing_status') == 'failed':
            conn.close()
            raise HTTPException(
                status_code=500,
                detail=f"Re-processing failed: {new_result.get('error', 'Unknown error')}"
            )

        # Extract validation report for easier access
        validation_report = new_result.get('validation_report')

        # Update the existing record with new results
        cursor.execute("""
            UPDATE ai_processing_results
            SET
                final_cleaned_note = ?,
                processing_status = ?,
                requires_human_intervention = ?,
                human_intervention_reasons = ?,
                total_checks = ?,
                passed_checks = ?,
                failed_checks = ?,
                critical_failures = ?,
                high_failures = ?,
                medium_failures = ?,
                low_failures = ?,
                tokens_used = tokens_used + ?,
                processing_duration_ms = processing_duration_ms + ?,
                processing_attempts = processing_attempts + 1,
                last_processed_at = CURRENT_TIMESTAMP,
                review_status = CASE
                    WHEN ? = 'success' OR ? = 'success_with_warnings' THEN 'pending'
                    ELSE 'needs_review'
                END
            WHERE id = ?
        """, (
            new_result.get('final_cleaned_note'),
            new_result.get('processing_status'),
            1 if new_result.get('requires_human_intervention') else 0,
            ','.join(validation_report.human_intervention_reasons) if validation_report else None,
            validation_report.total_checks if validation_report else 0,
            validation_report.passed_checks if validation_report else 0,
            validation_report.failed_checks if validation_report else 0,
            validation_report.critical_failures if validation_report else 0,
            validation_report.high_failures if validation_report else 0,
            validation_report.medium_failures if validation_report else 0,
            validation_report.low_failures if validation_report else 0,
            new_result.get('tokens_used', 0),
            new_result.get('processing_duration_ms', 0),
            new_result.get('processing_status'),
            new_result.get('processing_status'),
            request.result_id
        ))

        conn.commit()

        # Get updated result
        cursor.execute("""
            SELECT * FROM ai_processing_results
            WHERE id = ?
        """, (request.result_id,))

        updated_result = dict(cursor.fetchone())
        conn.close()

        logger.info(f"Re-processing complete for note {request.result_id}: {new_result.get('processing_status')}")

        return {
            "success": True,
            "result_id": request.result_id,
            "previous_status": result_dict['processing_status'],
            "new_status": new_result.get('processing_status'),
            "attempts": current_attempts + 1,
            "max_attempts": request.max_attempts,
            "passed_checks": validation_report.passed_checks if validation_report else 0,
            "total_checks": validation_report.total_checks if validation_report else 0,
            "tokens_used": new_result.get('tokens_used', 0),
            "result": updated_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to re-process note: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to re-process note: {str(e)}")


@router.post("/reprocess/bulk")
async def bulk_reprocess_notes(request: BulkReprocessRequest):
    """Re-process multiple notes through OpenAI pipeline

    This endpoint processes multiple notes in bulk. Useful for re-processing
    all notes that failed certain validation checks after prompt updates.

    Args:
        result_ids: List of ai_processing_results IDs to re-process
        max_attempts: Maximum number of re-processing attempts per note (default: 3)

    Returns:
        Summary of bulk re-processing results
    """
    try:
        results = {
            "success": [],
            "failed": [],
            "skipped": [],
            "total": len(request.result_ids)
        }

        for result_id in request.result_ids:
            try:
                # Re-process individual note
                reprocess_result = await reprocess_note(ReprocessRequest(
                    result_id=result_id,
                    max_attempts=request.max_attempts
                ))
                results["success"].append({
                    "result_id": result_id,
                    "new_status": reprocess_result["new_status"],
                    "passed_checks": reprocess_result["passed_checks"],
                    "total_checks": reprocess_result["total_checks"]
                })
            except HTTPException as e:
                if e.status_code == 400:
                    results["skipped"].append({
                        "result_id": result_id,
                        "reason": e.detail
                    })
                else:
                    results["failed"].append({
                        "result_id": result_id,
                        "error": e.detail
                    })
            except Exception as e:
                results["failed"].append({
                    "result_id": result_id,
                    "error": str(e)
                })

        return {
            "success": True,
            "summary": {
                "total": results["total"],
                "successful": len(results["success"]),
                "failed": len(results["failed"]),
                "skipped": len(results["skipped"])
            },
            "details": results
        }

    except Exception as e:
        logger.error(f"Bulk re-processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bulk re-processing failed: {str(e)}")
