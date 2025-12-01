#!/usr/bin/env python3
"""
FastAPI backend for medical note processing web application
"""

import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
from datetime import datetime, timedelta
from dateutil import parser

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config import get_config
from src.utils.openai_processor import OpenAIProcessor
from src.utils.logger import logger

# Import database module
from database import Database

# Import security utilities
from security import voice_security_middleware, audit_log, sanitize_for_voice

app = FastAPI(
    title="Medical Note Processing API",
    description="API for processing and managing medical notes from Freed.ai to Osmind",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and React default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize config and processor
config = get_config()
openai_processor = OpenAIProcessor(config)

# Initialize database
db = Database()

# Data models
class NoteRequest(BaseModel):
    patient_name: str
    visit_date: str
    note_text: str

class ProcessNoteRequest(BaseModel):
    note_text: str

class Note(BaseModel):
    patient_name: str
    visit_date: str
    note_text: str
    cleaned_note: Optional[str] = None
    processing_status: Optional[str] = None

# Helper functions
def get_data_directory():
    """Get the data directory path"""
    return Path(__file__).parent.parent.parent / "data"

def load_processed_notes():
    """DEPRECATED: Load all processed notes from data directory

    This function is deprecated and kept only for backwards compatibility.
    Use db.get_all_notes() instead.
    """
    logger.warning("load_processed_notes() is deprecated. Use db.get_all_notes() instead.")
    processed_dir = get_data_directory() / "temp" / "processed"
    notes = []

    if not processed_dir.exists():
        return notes

    for filename in processed_dir.glob("*_cleaned.json"):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                notes.append({
                    'id': filename.stem,
                    'patient_name': data.get('patient_name', 'Unknown'),
                    'visit_date': data.get('visit_date', ''),
                    'cleaned_note': data.get('cleaned_note', ''),
                    'original_note': data.get('original_note', ''),
                    'filename': filename.name
                })
        except Exception as e:
            print(f"Error loading {filename}: {e}")

    return notes

def load_comparison_results():
    """Load the latest comparison results from database"""
    try:
        # Load from database
        comparison = db.get_latest_comparison()
        if comparison:
            # Export from database in JSON format
            return db.export_comparison_to_json(comparison['id'])
        else:
            logger.warning("No comparison data found in database")
            return None
    except Exception as e:
        logger.error(f"Error loading from database: {e}")
        return None

def parse_visit_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats from visit_date field"""
    if not date_str or date_str == "" or date_str.lower() == "unknown":
        return None

    try:
        # Handle relative dates like "about 2" by returning None
        if "about" in date_str.lower():
            return None

        # Try parsing with dateutil parser (handles MM/DD/YYYY, etc.)
        return parser.parse(date_str, fuzzy=True)
    except:
        return None

def format_date_for_display(date_str: str, reference_date: Optional[datetime] = None) -> str:
    """Format date for display, returning standardized format or 'No Date' for invalid dates

    Args:
        date_str: The date string to format
        reference_date: The reference date for calculating relative dates (defaults to now)
    """
    import re

    if not reference_date:
        reference_date = datetime.now()

    # Handle "about X" relative dates
    if date_str and "about" in date_str.lower():
        try:
            # Extract the number from "about 19", "about 14", etc.
            match = re.search(r'about\s+(\d+)', date_str.lower())
            if match:
                days_ago = int(match.group(1))
                # Calculate the actual date based on reference date
                actual_date = reference_date - timedelta(days=days_ago)
                return actual_date.strftime('%m/%d/%Y')
        except:
            pass

    parsed_date = parse_visit_date(date_str)
    if parsed_date:
        # Return formatted date as MM/DD/YYYY
        return parsed_date.strftime('%m/%d/%Y')
    else:
        # Return 'No Date' for unparseable dates
        return 'No Date'

def get_date_range(filter_type: str, custom_start: Optional[str] = None, custom_end: Optional[str] = None):
    """Get start and end dates based on filter type"""
    now = datetime.now()

    if filter_type == "week":
        # Last 7 days
        start_date = now - timedelta(days=7)
        end_date = now
    elif filter_type == "month":
        # Last 30 days
        start_date = now - timedelta(days=30)
        end_date = now
    elif filter_type == "custom" and custom_start and custom_end:
        start_date = parser.parse(custom_start)
        end_date = parser.parse(custom_end)
    else:  # "all" or no filter
        return None, None

    return start_date, end_date

def filter_results_by_date(results: List[Dict], start_date: Optional[datetime], end_date: Optional[datetime]) -> List[Dict]:
    """Filter results by date range"""
    if not start_date or not end_date:
        return results

    filtered = []
    for result in results:
        visit_date = parse_visit_date(result.get('visit_date', ''))
        if visit_date:
            if start_date <= visit_date <= end_date:
                filtered.append(result)
        # Include results with unparseable dates if you want to show them
        # Comment out the next line if you only want dated results
        else:
            filtered.append(result)

    return filtered

# API Routes
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "Medical Note Processing API",
        "version": "1.0.0",
        "endpoints": {
            "notes": "/api/notes",
            "process": "/api/process",
            "stats": "/api/stats",
            "comparison": "/api/comparison"
        }
    }

@app.get("/api/notes")
async def get_notes(limit: int = 1000):
    """Get all processed notes from database with freed note details"""
    try:
        # Query notes with joined freed_notes to get all fields
        # Order by visit_date DESC to show most recent patient visits first
        if limit > 0:
            db.cursor.execute("""
                SELECT n.*, p.name as patient_name,
                       fn.description, fn.note_text as freed_note_text, fn.full_text,
                       fn.sections, fn.tags, fn.note_length, fn.visit_date as fn_visit_date
                FROM notes n
                JOIN patients p ON n.patient_id = p.id
                LEFT JOIN freed_notes fn ON n.freed_note_id = fn.id
                ORDER BY fn.visit_date DESC
                LIMIT ?
            """, (limit,))
        else:
            # No limit - return all notes
            db.cursor.execute("""
                SELECT n.*, p.name as patient_name,
                       fn.description, fn.note_text as freed_note_text, fn.full_text,
                       fn.sections, fn.tags, fn.note_length, fn.visit_date as fn_visit_date
                FROM notes n
                JOIN patients p ON n.patient_id = p.id
                LEFT JOIN freed_notes fn ON n.freed_note_id = fn.id
                ORDER BY fn.visit_date DESC
            """)
        notes = [dict(row) for row in db.cursor.fetchall()]

        # Format notes to match expected frontend structure
        formatted_notes = []
        for note in notes:
            formatted_notes.append({
                'id': note['id'],
                'patient_name': note['patient_name'],
                'visit_date': note.get('visit_date', ''),
                'description': note.get('description', ''),
                'note_text': note.get('freed_note_text', ''),
                'full_text': note.get('full_text', ''),
                'sections': note.get('sections', ''),
                'tags': note.get('tags', ''),
                'note_length': note.get('note_length', 0),
                'cleaned_note': note.get('final_note', ''),
                'original_note': note.get('original_freed_note', ''),
                'orig_note': note.get('orig_note', ''),
                'processing_status': note.get('processing_status', ''),
                'ai_enhanced': note.get('ai_enhanced', False),
                'uploaded_to_osmind': note.get('uploaded_to_osmind', False),
                'synced': note.get('synced', ''),
                'sent_to_ai_date': note.get('sent_to_ai_date', ''),
                'manual_match': note.get('manual_match', False),
                'created_at': note.get('created_at', '')
            })
        return {"notes": formatted_notes, "count": len(formatted_notes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notes: {str(e)}")

@app.get("/api/notes/{note_id}")
async def get_note(note_id: int):
    """Get a specific note by ID from database with freed note details"""
    try:
        # Query database for specific note with freed_notes join
        db.cursor.execute("""
            SELECT n.*, p.name as patient_name,
                   fn.description, fn.note_text as freed_note_text, fn.full_text,
                   fn.sections, fn.tags, fn.note_length
            FROM notes n
            JOIN patients p ON n.patient_id = p.id
            LEFT JOIN freed_notes fn ON n.freed_note_id = fn.id
            WHERE n.id = ?
        """, (note_id,))
        row = db.cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Note not found")

        note = dict(row)
        # Format to match expected frontend structure
        return {
            'id': note['id'],
            'patient_name': note['patient_name'],
            'visit_date': note.get('visit_date', ''),
            'description': note.get('description', ''),
            'note_text': note.get('freed_note_text', ''),
            'full_text': note.get('full_text', ''),
            'sections': note.get('sections', ''),
            'tags': note.get('tags', ''),
            'note_length': note.get('note_length', 0),
            'cleaned_note': note.get('final_note', ''),
            'original_note': note.get('original_freed_note', ''),
            'processing_status': note.get('processing_status', ''),
            'ai_enhanced': note.get('ai_enhanced', False),
            'uploaded_to_osmind': note.get('uploaded_to_osmind', False),
            'synced': note.get('synced', ''),
            'sent_to_ai_date': note.get('sent_to_ai_date', ''),
            'manual_match': note.get('manual_match', False),
            'created_at': note.get('created_at', '')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch note: {str(e)}")

@app.get("/api/osmind-notes")
async def get_osmind_notes(limit: int = 100, offset: int = 0):
    """Get Osmind notes from database with pagination"""
    try:
        # Get total count
        db.cursor.execute("""
            SELECT COUNT(*) as total
            FROM osmind_notes o
            JOIN patients p ON o.patient_id = p.id
        """)
        total = db.cursor.fetchone()['total']

        # Query osmind_notes table with pagination
        db.cursor.execute("""
            SELECT o.*, p.name as patient_name
            FROM osmind_notes o
            JOIN patients p ON o.patient_id = p.id
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        notes = [dict(row) for row in db.cursor.fetchall()]

        # Format notes to match expected frontend structure
        formatted_notes = []
        for note in notes:
            formatted_notes.append({
                'id': note['id'],
                'patient_name': note.get('patient_name', ''),
                'visit_date': note.get('visit_date', ''),
                'note_text': note.get('note_text', ''),
                'full_text': note.get('full_text', ''),
                'sections': note.get('sections', ''),
                'note_length': note.get('note_length', 0),
                'has_freed_content': note.get('has_freed_content', False),
                'is_signed': note.get('is_signed', False),
                'processing_status': note.get('processing_status', ''),
                'extracted_at': note.get('extracted_at', ''),
                'updated_at': note.get('updated_at', ''),
                'osmind_note_id': note.get('osmind_note_id', ''),
                'osmind_patient_id': note.get('osmind_patient_id', ''),
                'description': note.get('description', ''),
                'rendering_provider_id': note.get('rendering_provider_id', ''),
                'rendering_provider_name': note.get('rendering_provider_name', ''),
                'location_id': note.get('location_id', ''),
                'location_name': note.get('location_name', ''),
                'note_type': note.get('note_type', ''),
                'created_at': note.get('created_at', ''),
                'first_signed_at': note.get('first_signed_at', ''),
                'sync_source': note.get('sync_source', ''),
                'last_synced_at': note.get('last_synced_at', '')
            })
        return {"notes": formatted_notes, "count": len(formatted_notes), "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Osmind notes: {str(e)}")

@app.get("/api/osmind-notes/{note_id}")
async def get_osmind_note(note_id: int):
    """Get a specific Osmind note by ID"""
    try:
        db.cursor.execute("""
            SELECT o.*, p.name as patient_name
            FROM osmind_notes o
            JOIN patients p ON o.patient_id = p.id
            WHERE o.id = ?
        """, (note_id,))
        row = db.cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Osmind note not found")

        note = dict(row)
        return {
            'id': note['id'],
            'patient_name': note.get('patient_name', ''),
            'visit_date': note.get('visit_date', ''),
            'note_text': note.get('note_text', ''),
            'full_text': note.get('full_text', ''),
            'sections': note.get('sections', ''),
            'note_length': note.get('note_length', 0),
            'has_freed_content': note.get('has_freed_content', False),
            'is_signed': note.get('is_signed', False),
            'processing_status': note.get('processing_status', ''),
            'extracted_at': note.get('extracted_at', ''),
            'updated_at': note.get('updated_at', ''),
            'osmind_note_id': note.get('osmind_note_id', ''),
            'osmind_patient_id': note.get('osmind_patient_id', ''),
            'description': note.get('description', ''),
            'rendering_provider_id': note.get('rendering_provider_id', ''),
            'rendering_provider_name': note.get('rendering_provider_name', ''),
            'location_id': note.get('location_id', ''),
            'location_name': note.get('location_name', ''),
            'note_type': note.get('note_type', ''),
            'created_at': note.get('created_at', ''),
            'first_signed_at': note.get('first_signed_at', ''),
            'sync_source': note.get('sync_source', ''),
            'last_synced_at': note.get('last_synced_at', '')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Osmind note: {str(e)}")

@app.post("/api/process")
async def process_note(request: ProcessNoteRequest):
    """Process a note with OpenAI"""
    try:
        cleaned_note = openai_processor.clean_patient_note(request.note_text)
        return {
            "success": True,
            "cleaned_note": cleaned_note
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/api/stats")
async def get_stats(
    filter_type: str = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get statistics about notes with optional date filtering from database"""
    try:
        # Get all notes from database
        all_notes = db.get_all_notes(limit=1000)

        # Get latest comparison from database
        comparison = db.get_latest_comparison()

        stats = {
            "total_processed": len(all_notes),
            "timestamp": datetime.now().isoformat()
        }

        if comparison:
            # Get comparison results from database
            results = db.get_comparison_results(comparison['id'])

            # Convert to list of dicts with patient names
            results_with_names = []
            for result in results:
                results_with_names.append({
                    'patient_name': result['patient_name'],
                    'visit_date': result.get('visit_date', ''),
                    'in_osmind': result.get('in_osmind', False),
                    'has_freed_content': result.get('has_freed_content', False),
                    'in_freed': result.get('in_freed', False),
                    'is_signed': result.get('is_signed', False)
                })

            # Apply date filtering if requested
            if filter_type != "all":
                start, end = get_date_range(filter_type, start_date, end_date)
                if start and end:
                    results_with_names = filter_results_by_date(results_with_names, start, end)

            # Calculate filtered statistics
            complete = len([r for r in results_with_names if r.get('in_osmind') and r.get('has_freed_content')])
            missing = len([r for r in results_with_names if not r.get('in_osmind')])
            incomplete = len([r for r in results_with_names if r.get('in_osmind') and not r.get('has_freed_content')])

            stats.update({
                "total_in_freed": len(results_with_names),
                "complete_in_osmind": complete,
                "missing_from_osmind": missing,
                "incomplete_in_osmind": incomplete,
                "to_process": missing + incomplete,
                "comparison_timestamp": comparison.get('timestamp', ''),
                "filter": {
                    "type": filter_type,
                    "start_date": start_date,
                    "end_date": end_date
                }
            })

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/api/comparison")
async def get_comparison():
    """Get the latest comparison results"""
    comparison = load_comparison_results()
    if comparison:
        return comparison
    raise HTTPException(status_code=404, detail="No comparison results found")

@app.get("/api/comparison/details")
async def get_comparison_details(
    filter_type: str = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get detailed comparison results with optional date filtering"""
    comparison = load_comparison_results()
    if not comparison:
        raise HTTPException(status_code=404, detail="No comparison results found")

    results = comparison.get('results', [])

    # Apply date filtering if requested
    if filter_type != "all":
        start, end = get_date_range(filter_type, start_date, end_date)
        if start and end:
            results = filter_results_by_date(results, start, end)

    # Parse comparison timestamp to use as reference for relative dates
    comparison_timestamp_str = comparison.get('timestamp', '')
    reference_date = None
    if comparison_timestamp_str:
        try:
            # Parse timestamp format: YYYYMMDD_HHMMSS (e.g., "20251104_143130")
            reference_date = datetime.strptime(comparison_timestamp_str, '%Y%m%d_%H%M%S')
        except:
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    # Format dates for all results using the comparison timestamp as reference
    for result in results:
        result['visit_date'] = format_date_for_display(result.get('visit_date', ''), reference_date)
        # Add tags to each result
        result['tags'] = db.get_patient_tags(result.get('patient_name', ''))

    # Group by status
    complete = [r for r in results if r.get('in_osmind') and r.get('has_freed_content')]
    missing = [r for r in results if not r.get('in_osmind')]
    incomplete = [r for r in results if r.get('in_osmind') and not r.get('has_freed_content')]

    return {
        "complete": complete,
        "missing": missing,
        "incomplete": incomplete,
        "counts": {
            "complete": len(complete),
            "missing": len(missing),
            "incomplete": len(incomplete),
            "total": len(results)
        },
        "filter": {
            "type": filter_type,
            "start_date": start_date,
            "end_date": end_date
        }
    }

@app.post("/api/test-connection")
async def test_openai_connection():
    """Test OpenAI API connection"""
    try:
        result = openai_processor.test_connection()
        return {"success": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

# ========================================
# Database-Powered Endpoints
# ========================================

@app.get("/api/patients")
async def get_patients():
    """Get all patients"""
    try:
        patients = db.get_all_patients()
        return {"patients": patients, "count": len(patients)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patients: {str(e)}")

@app.get("/api/patients/{patient_name}/history")
async def get_patient_history(patient_name: str, limit: int = 10):
    """Get comparison history for a specific patient"""
    try:
        history = db.get_patient_comparison_history(patient_name, limit)
        return {"patient_name": patient_name, "history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patient history: {str(e)}")

@app.get("/api/comparisons/all")
async def get_all_comparisons(limit: int = 50):
    """Get all comparisons"""
    try:
        comparisons = db.get_all_comparisons(limit)
        return {"comparisons": comparisons, "count": len(comparisons)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch comparisons: {str(e)}")

@app.get("/api/trends/comparisons")
async def get_comparison_trends(days: int = 30):
    """Get comparison trends over time"""
    try:
        trends = db.get_comparison_trends(days)
        return {"trends": trends, "days": days, "count": len(trends)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trends: {str(e)}")

@app.get("/api/trends/completion-rate")
async def get_completion_rate_trend():
    """Get completion rate trend across all comparisons"""
    try:
        trend = db.get_completion_rate_trend()
        return {"trend": trend, "count": len(trend)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch completion rate: {str(e)}")

@app.get("/api/patients/{patient_name}/status-changes")
async def get_patient_status_changes(patient_name: str):
    """Get status changes for a patient across comparisons"""
    try:
        changes = db.get_patient_status_changes(patient_name)
        return {"patient_name": patient_name, "changes": changes, "count": len(changes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch status changes: {str(e)}")

@app.get("/api/export/comparison/{comparison_id}")
async def export_comparison(comparison_id: int):
    """Export a comparison to JSON format"""
    try:
        export_data = db.export_comparison_to_json(comparison_id)
        return export_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export comparison: {str(e)}")

# ========================================
# Tag Management Endpoints
# ========================================

@app.get("/api/tags")
async def get_tags():
    """Get all tags"""
    try:
        tags = db.get_all_tags()
        return {"tags": tags, "count": len(tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tags: {str(e)}")

@app.post("/api/patients/{patient_name}/tags")
async def add_patient_tag(patient_name: str, tag_name: str, color: str = "#3b82f6"):
    """Add a tag to a patient"""
    try:
        db.add_patient_tag(patient_name, tag_name, color)
        return {"success": True, "message": f"Tag '{tag_name}' added to {patient_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add tag: {str(e)}")

@app.delete("/api/patients/{patient_name}/tags/{tag_name}")
async def remove_patient_tag(patient_name: str, tag_name: str):
    """Remove a tag from a patient"""
    try:
        db.remove_patient_tag(patient_name, tag_name)
        return {"success": True, "message": f"Tag '{tag_name}' removed from {patient_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove tag: {str(e)}")

@app.get("/api/patients/{patient_name}/tags")
async def get_patient_tags(patient_name: str):
    """Get all tags for a specific patient"""
    try:
        tags = db.get_patient_tags(patient_name)
        return {"patient_name": patient_name, "tags": tags, "count": len(tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patient tags: {str(e)}")

@app.get("/api/tags/{tag_name}/patients")
async def get_patients_by_tag(tag_name: str):
    """Get all patients with a specific tag"""
    try:
        patients = db.get_patients_by_tag(tag_name)
        return {"tag_name": tag_name, "patients": patients, "count": len(patients)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch patients by tag: {str(e)}")

@app.post("/api/patients/search/tags")
async def search_by_tags(tag_names: List[str], match_all: bool = False):
    """Search for patients by tags"""
    try:
        patients = db.search_patients_by_tags(tag_names, match_all)
        return {
            "tag_names": tag_names,
            "match_all": match_all,
            "patients": patients,
            "count": len(patients)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search by tags: {str(e)}")

# ========================================
# Voice Assistant API Endpoints (ElevenLabs Functions)
# ========================================

@app.post("/api/voice/search_patients")
async def voice_search_patients(
    query: str,
    request: Request,
    client_id: str = Depends(voice_security_middleware)
):
    """Voice assistant function: Search for patients by name (secured)"""
    try:
        # Search through all patients
        all_patients = db.get_all_patients()
        query_lower = query.lower()

        # Fuzzy matching - find patients whose names contain the query
        matching_patients = [
            p for p in all_patients
            if query_lower in p['name'].lower()
        ]

        if not matching_patients:
            audit_log(
                action="search_patients",
                client_id=client_id,
                details={"query": query, "result_count": 0},
                success=True
            )
            return {
                "success": True,
                "message": f"No patients found matching '{query}'",
                "patients": [],
                "count": 0
            }

        # Format results for voice response
        patient_names = [p['name'] for p in matching_patients[:5]]  # Limit to 5 for voice

        # Audit log
        audit_log(
            action="search_patients",
            client_id=client_id,
            details={"query": query, "result_count": len(matching_patients)},
            success=True
        )

        return {
            "success": True,
            "message": f"Found {len(matching_patients)} patient(s) matching '{query}'",
            "patients": patient_names,
            "count": len(matching_patients),
            "showing": min(5, len(matching_patients))
        }
    except Exception as e:
        audit_log(
            action="search_patients",
            client_id=client_id,
            details={"query": query, "error": str(e)},
            success=False
        )
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/voice/get_patient_details")
async def voice_get_patient_details(patient_name: str):
    """Voice assistant function: Get patient details with tags and history"""
    try:
        # Get patient tags
        tags = db.get_patient_tags(patient_name)

        # Get comparison history
        history = db.get_patient_comparison_history(patient_name, limit=3)

        # Get latest status from comparison
        comparison = load_comparison_results()
        latest_status = "unknown"
        visit_date = None

        if comparison and 'results' in comparison:
            for result in comparison['results']:
                if result.get('patient_name') == patient_name:
                    if result.get('in_osmind') and result.get('has_freed_content'):
                        latest_status = "complete"
                    elif result.get('in_osmind') and not result.get('has_freed_content'):
                        latest_status = "incomplete"
                    elif not result.get('in_osmind'):
                        latest_status = "missing"
                    visit_date = result.get('visit_date')
                    break

        return {
            "success": True,
            "patient_name": patient_name,
            "tags": [t['name'] for t in tags] if tags else [],
            "latest_status": latest_status,
            "visit_date": visit_date,
            "history_count": len(history),
            "message": f"{patient_name} has {len(tags)} tag(s) and status is {latest_status}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patient details: {str(e)}")

@app.post("/api/voice/get_comparison_stats")
async def voice_get_comparison_stats(filter_type: str = "all"):
    """Voice assistant function: Get comparison statistics"""
    try:
        stats = await get_stats(filter_type)

        message = f"Overall statistics: {stats.get('complete_in_osmind', 0)} complete, "
        message += f"{stats.get('missing_from_osmind', 0)} missing, "
        message += f"{stats.get('incomplete_in_osmind', 0)} incomplete out of {stats.get('total_in_freed', 0)} total notes"

        return {
            "success": True,
            "filter": filter_type,
            "stats": {
                "complete": stats.get('complete_in_osmind', 0),
                "missing": stats.get('missing_from_osmind', 0),
                "incomplete": stats.get('incomplete_in_osmind', 0),
                "total": stats.get('total_in_freed', 0)
            },
            "message": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.post("/api/voice/search_by_status")
async def voice_search_by_status(status: str, filter_type: str = "all"):
    """Voice assistant function: Search patients by note status"""
    try:
        comparison = load_comparison_results()
        if not comparison:
            return {
                "success": False,
                "message": "No comparison data available",
                "patients": []
            }

        results = comparison.get('results', [])

        # Apply date filtering if needed
        if filter_type != "all":
            start, end = get_date_range(filter_type)
            if start and end:
                results = filter_results_by_date(results, start, end)

        # Filter by status
        if status == "complete":
            filtered = [r for r in results if r.get('in_osmind') and r.get('has_freed_content')]
        elif status == "missing":
            filtered = [r for r in results if not r.get('in_osmind')]
        elif status == "incomplete":
            filtered = [r for r in results if r.get('in_osmind') and not r.get('has_freed_content')]
        else:
            filtered = results

        patient_names = [r['patient_name'] for r in filtered[:10]]  # Limit to 10 for voice

        return {
            "success": True,
            "status": status,
            "filter": filter_type,
            "patients": patient_names,
            "count": len(filtered),
            "showing": min(10, len(filtered)),
            "message": f"Found {len(filtered)} patient(s) with {status} status"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/voice/add_patient_tag")
async def voice_add_patient_tag(
    patient_name: str,
    tag_name: str,
    request: Request,
    client_id: str = Depends(voice_security_middleware)
):
    """Voice assistant function: Add tag to patient (secured)"""
    try:
        db.add_patient_tag(patient_name, tag_name, "#3b82f6")

        # Audit log
        audit_log(
            action="add_patient_tag",
            client_id=client_id,
            patient_name=patient_name,
            details={"tag_name": tag_name},
            success=True
        )

        return {
            "success": True,
            "message": f"Added tag '{tag_name}' to {patient_name}",
            "patient_name": patient_name,
            "tag_name": tag_name
        }
    except Exception as e:
        audit_log(
            action="add_patient_tag",
            client_id=client_id,
            patient_name=patient_name,
            details={"tag_name": tag_name, "error": str(e)},
            success=False
        )
        raise HTTPException(status_code=500, detail=f"Failed to add tag: {str(e)}")

@app.post("/api/voice/remove_patient_tag")
async def voice_remove_patient_tag(patient_name: str, tag_name: str):
    """Voice assistant function: Remove tag from patient"""
    try:
        db.remove_patient_tag(patient_name, tag_name)
        return {
            "success": True,
            "message": f"Removed tag '{tag_name}' from {patient_name}",
            "patient_name": patient_name,
            "tag_name": tag_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove tag: {str(e)}")

@app.post("/api/voice/search_by_tags")
async def voice_search_by_tags(tags: List[str], match_all: bool = False):
    """Voice assistant function: Search patients by tags"""
    try:
        patients = db.search_patients_by_tags(tags, match_all)
        patient_names = [p['name'] for p in patients[:10]]  # Limit to 10 for voice

        match_type = "all" if match_all else "any"
        return {
            "success": True,
            "tags": tags,
            "match_all": match_all,
            "patients": patient_names,
            "count": len(patients),
            "showing": min(10, len(patients)),
            "message": f"Found {len(patients)} patient(s) with {match_type} of the tags: {', '.join(tags)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/api/voice/get_recent_comparisons")
async def voice_get_recent_comparisons(limit: int = 10):
    """Voice assistant function: Get recent comparison results"""
    try:
        comparisons = db.get_all_comparisons(limit)

        if not comparisons:
            return {
                "success": True,
                "message": "No comparison data available",
                "comparisons": [],
                "count": 0
            }

        # Format for voice
        formatted = []
        for comp in comparisons:
            formatted.append({
                "date": comp.get('created_at', ''),
                "total": comp.get('total_notes', 0),
                "complete": comp.get('complete', 0),
                "missing": comp.get('missing', 0),
                "incomplete": comp.get('incomplete', 0)
            })

        latest = comparisons[0] if comparisons else {}
        message = f"Most recent comparison: {latest.get('complete', 0)} complete, "
        message += f"{latest.get('missing', 0)} missing, {latest.get('incomplete', 0)} incomplete"

        return {
            "success": True,
            "comparisons": formatted,
            "count": len(comparisons),
            "message": message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comparisons: {str(e)}")

@app.post("/api/voice/get_all_tags")
async def voice_get_all_tags():
    """Voice assistant function: Get all tags in use"""
    try:
        tags = db.get_all_tags()
        tag_names = [t['name'] for t in tags]

        return {
            "success": True,
            "tags": tag_names,
            "count": len(tags),
            "message": f"There are {len(tags)} tags in use: {', '.join(tag_names[:5])}" +
                      (f" and {len(tags) - 5} more" if len(tags) > 5 else "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tags: {str(e)}")

@app.get("/api/voice/config")
async def get_voice_config():
    """Get ElevenLabs agent configuration"""
    from elevenlabs_agent import get_agent_config
    return get_agent_config()

@app.post("/api/voice/fetch_notes")
async def voice_fetch_notes(days: Optional[int] = None, date: Optional[str] = None):
    """Voice assistant function: Fetch and compare notes from Freed

    Args:
        days: Number of days to fetch (e.g., 7, 10, 30)
        date: Specific date to start from (format: YYYY-MM-DD)

    Returns:
        Success status and summary of fetch operation
    """
    try:
        import subprocess
        import os

        # Build command
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fetch_and_compare_only.py')
        cmd = ['python3', script_path]

        if days:
            cmd.extend(['--days', str(days)])
        elif date:
            cmd.extend(['--date', date])
        else:
            # Default to 7 days if no parameter provided
            cmd.extend(['--days', '7'])

        # Run the fetch script in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )

        # Don't wait for completion - this is a long-running task
        # Just confirm it started

        param_str = f"{days} days" if days else f"from {date}" if date else "7 days"

        return {
            "success": True,
            "message": f"Started fetching notes for {param_str}",
            "status": "running",
            "note": "This is a background task. Check the comparison page for results when complete."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start fetch: {str(e)}")

class FetchRequest(BaseModel):
    days: Optional[int] = 7

@app.post("/api/fetch-from-freed")
async def fetch_from_freed(request: FetchRequest):
    """Fetch notes from Freed.ai and compare with Osmind

    Args:
        request: FetchRequest with days parameter (default: 7)

    Returns:
        Success status and summary
    """
    try:
        import subprocess
        import os

        days = request.days
        # Build command with venv python
        # backend/main.py -> backend -> web-app -> project_root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        venv_python = os.path.join(project_root, '.venv', 'bin', 'python3')
        script_path = os.path.join(project_root, 'fetch_and_compare_only.py')
        cmd = [venv_python, script_path, '--days', str(days)]

        # Run the fetch script in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root
        )

        logger.info(f"Started Freed.ai fetch for {days} days")

        return {
            "success": True,
            "message": f"Started fetching notes from Freed.ai for the last {days} days",
            "status": "running",
            "note": "This is a background task. Results will appear in the comparison page when complete."
        }
    except Exception as e:
        logger.error(f"Failed to start Freed fetch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start fetch: {str(e)}")

@app.post("/api/fetch-from-osmind")
async def fetch_from_osmind(request: FetchRequest):
    """Sync notes from Osmind EHR

    Args:
        request: FetchRequest with days parameter (default: 7)

    Returns:
        Success status and summary
    """
    try:
        import subprocess
        import os
        from datetime import datetime, timedelta

        days = request.days

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Build command with venv python
        # backend/main.py -> backend -> web-app -> project_root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        venv_python = os.path.join(project_root, '.venv', 'bin', 'python3')
        script_path = os.path.join(project_root, 'sync_osmind.py')
        cmd = [
            venv_python,
            script_path,
            '--start-date', start_date.strftime('%Y-%m-%d'),
            '--end-date', end_date.strftime('%Y-%m-%d'),
            '--headless'
        ]

        # Run the sync script in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root
        )

        logger.info(f"Started Osmind sync for {days} days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")

        return {
            "success": True,
            "message": f"Started syncing notes from Osmind EHR for the last {days} days",
            "status": "running",
            "note": "This is a background task. Refresh the page in a few moments to see updated notes."
        }
    except Exception as e:
        logger.error(f"Failed to start Osmind sync: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")

# ========================================
# Note Upload Endpoint
# ========================================

class UploadRequest(BaseModel):
    patient_names: List[str]

@app.post("/api/upload-to-osmind")
async def upload_to_osmind(request: UploadRequest):
    """Upload notes to Osmind EHR for specified patients

    Args:
        request: UploadRequest with list of patient names to upload

    Returns:
        Dictionary with upload results including success/failure counts and flagged items
    """
    try:
        from playwright.sync_api import sync_playwright
        from src.auth.target_auth import TargetAuth
        from src.inserters.osmind_inserter import OsmindInserter

        # Get comparison data to find notes for these patients
        comparison = load_comparison_results()
        if not comparison:
            raise HTTPException(status_code=404, detail="No comparison data found. Please run comparison first.")

        # Filter notes for requested patients
        all_results = comparison.get('results', [])
        notes_to_upload = []

        for patient_name in request.patient_names:
            # Find this patient in the comparison results
            patient_notes = [r for r in all_results if r.get('patient_name') == patient_name]

            if not patient_notes:
                logger.warning(f"Patient not found in comparison data: {patient_name}")
                continue

            patient_note = patient_notes[0]  # Get the first match

            # Check if we have cleaned note data
            cleaned_note = patient_note.get('cleaned_note') or patient_note.get('note_text') or patient_note.get('raw_note')

            if not cleaned_note:
                logger.warning(f"No note text found for {patient_name}")
                continue

            # Add to upload queue
            notes_to_upload.append({
                'patient_name': patient_name,
                'visit_date': patient_note.get('visit_date', ''),
                'cleaned_note': cleaned_note
            })

        if not notes_to_upload:
            raise HTTPException(status_code=400, detail="No notes found for specified patients")

        logger.info(f"Preparing to upload {len(notes_to_upload)} notes to Osmind")

        # Initialize Playwright and authenticate
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Set to True for production

            try:
                # Authenticate to Osmind
                auth = TargetAuth(config, browser)
                if not auth.login():
                    raise HTTPException(status_code=500, detail="Failed to authenticate to Osmind EHR")

                # Initialize inserter with authenticated page
                inserter = OsmindInserter(auth.page)

                # Upload notes
                results = inserter.batch_upload_notes(notes_to_upload)

                # Close browser
                browser.close()

                return {
                    "success": True,
                    "message": f"Upload completed: {results['success']} successful, {results['failure']} failed",
                    "results": results
                }

            except Exception as e:
                browser.close()
                raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ========================================
# Development Tools - SQLite CRUD Endpoints
# ========================================

@app.get("/api/dev/db/tables")
async def get_database_tables():
    """Get all tables in the database with row counts (dev tool only)"""
    try:
        import sqlite3

        # Get database path from Database class
        db_path = db.db_path

        # Connect directly to read table info
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        table_info = []
        for (table_name,) in tables:
            # Get row count for each table
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

            table_info.append({
                "name": table_name,
                "row_count": row_count
            })

        conn.close()

        return {"tables": table_info, "count": len(table_info)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tables: {str(e)}")

@app.get("/api/dev/db/schema/{table}")
async def get_table_schema(table: str):
    """Get schema information for a specific table (dev tool only)"""
    try:
        import sqlite3

        db_path = db.db_path
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get table schema
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        schema = []
        for col in columns:
            schema.append({
                "cid": col[0],
                "name": col[1],
                "type": col[2],
                "notnull": col[3],
                "dflt_value": col[4],
                "pk": col[5]
            })

        conn.close()

        return {"table": table, "schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schema: {str(e)}")

class QueryRequest(BaseModel):
    query: str
    params: Optional[List] = None

@app.post("/api/dev/db/query")
async def execute_query(request: QueryRequest):
    """Execute a custom SQL query (dev tool only - read-only recommended)"""
    try:
        import sqlite3

        db_path = db.db_path
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Execute query
        if request.params:
            cursor.execute(request.query, request.params)
        else:
            cursor.execute(request.query)

        # Check if it's a SELECT query
        if request.query.strip().upper().startswith('SELECT'):
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            conn.close()
            return {
                "success": True,
                "data": results,
                "rows": len(results)
            }
        else:
            # For INSERT, UPDATE, DELETE
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return {
                "success": True,
                "message": f"Query executed successfully. {affected} rows affected.",
                "rows_affected": affected
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/api/dev/db/data/{table}")
async def get_table_data(
    table: str,
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None
):
    """Get data from a specific table with pagination and search (dev tool only)"""
    try:
        import sqlite3

        db_path = db.db_path
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query
        if search:
            # Get column names to search across
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]

            # Build WHERE clause for search
            where_clauses = [f"{col} LIKE ?" for col in columns]
            where_clause = " OR ".join(where_clauses)
            search_params = [f"%{search}%"] * len(columns)

            # Count total matching rows
            count_query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause}"
            cursor.execute(count_query, search_params)
            total = cursor.fetchone()[0]

            # Get data
            query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT ? OFFSET ?"
            cursor.execute(query, search_params + [limit, offset])
        else:
            # Count total rows
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            total = cursor.fetchone()[0]

            # Get data
            query = f"SELECT * FROM {table} LIMIT ? OFFSET ?"
            cursor.execute(query, (limit, offset))

        rows = cursor.fetchall()
        data = [dict(row) for row in rows]

        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []

        conn.close()

        return {
            "table": table,
            "columns": columns,
            "rows": data,
            "row_count": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")

class InsertRequest(BaseModel):
    data: Dict

@app.post("/api/dev/db/data/{table}")
async def insert_row(table: str, request: InsertRequest):
    """Insert a new row into a table (dev tool only)"""
    try:
        import sqlite3

        db_path = db.db_path
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Build INSERT query
        columns = list(request.data.keys())
        placeholders = ["?" for _ in columns]
        values = [request.data[col] for col in columns]

        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(query, values)
        conn.commit()

        new_id = cursor.lastrowid
        conn.close()

        return {
            "success": True,
            "message": f"Row inserted successfully",
            "id": new_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert row: {str(e)}")

class UpdateRequest(BaseModel):
    where: Dict
    data: Dict

@app.put("/api/dev/db/data/{table}")
async def update_row(table: str, request: UpdateRequest):
    """Update a row in a table (dev tool only)"""
    try:
        import sqlite3

        db_path = db.db_path
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Build UPDATE query
        set_clauses = [f"{col} = ?" for col in request.data.keys()]
        set_values = list(request.data.values())

        where_clauses = [f"{col} = ?" for col in request.where.keys()]
        where_values = list(request.where.values())

        query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        cursor.execute(query, set_values + where_values)
        conn.commit()

        affected = cursor.rowcount
        conn.close()

        return {
            "success": True,
            "message": f"Row updated successfully",
            "rows_affected": affected
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update row: {str(e)}")

class DeleteRequest(BaseModel):
    row: Dict

@app.delete("/api/dev/db/data/{table}")
async def delete_row(table: str, request: DeleteRequest):
    """Delete a row from a table (dev tool only)"""
    try:
        import sqlite3

        db_path = db.db_path
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Build DELETE query
        where_clauses = [f"{col} = ?" for col in request.row.keys()]
        where_values = list(request.row.values())

        query = f"DELETE FROM {table} WHERE {' AND '.join(where_clauses)}"
        cursor.execute(query, where_values)
        conn.commit()

        affected = cursor.rowcount
        conn.close()

        return {
            "success": True,
            "message": f"Row deleted successfully",
            "rows_affected": affected
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete row: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
