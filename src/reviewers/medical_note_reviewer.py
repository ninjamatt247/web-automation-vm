"""
Medical Note Reviewer using OpenAI API
Reviews notes for completeness, readability, billing codes, and medical recommendations
"""

import os
import re
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
from src.utils.logger import logger


class MedicalNoteReviewer:
    """Reviews medical notes using OpenAI API for completeness and billing accuracy"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI client

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY env var not set")

        self.client = OpenAI(api_key=self.api_key)
        logger.info("Medical Note Reviewer initialized with OpenAI API")

    def extract_dx_codes(self, note_text: str) -> List[str]:
        """Extract ICD-10 diagnosis codes from note text

        Args:
            note_text: The full note text

        Returns:
            List of ICD-10 codes found
        """
        # ICD-10 codes format: Letter + 2 digits + optional decimal + up to 4 more digits
        # Examples: F41.1, Z13.89, E11.9
        dx_pattern = r'\b[A-Z]\d{2}(?:\.\d{1,4})?\b'
        dx_codes = re.findall(dx_pattern, note_text)

        # Filter out common false positives
        filtered_codes = [code for code in dx_codes if not code.startswith(('A1', 'B1', 'C1')) or len(code) > 3]

        return list(set(filtered_codes))  # Remove duplicates

    def extract_cpt_codes(self, note_text: str) -> List[str]:
        """Extract CPT codes from note text

        Args:
            note_text: The full note text

        Returns:
            List of CPT codes found
        """
        # CPT codes are 5-digit numerical codes
        # Common psychiatry codes: 90791-90899, 96136-96146, 99201-99499
        cpt_pattern = r'\b(9[0-9]{4})\b'
        cpt_codes = re.findall(cpt_pattern, note_text)

        # Filter to valid CPT code ranges
        valid_cpt = []
        for code in cpt_codes:
            code_num = int(code)
            if ((90000 <= code_num <= 90899) or  # Psychiatry
                (96000 <= code_num <= 96999) or  # Neurology/Testing
                (99000 <= code_num <= 99499)):   # E&M codes
                valid_cpt.append(code)

        return list(set(valid_cpt))  # Remove duplicates

    def review_note(self, patient_name: str, visit_date: str, note_text: str,
                   dx_codes: Optional[List[str]] = None,
                   cpt_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Review a medical note using OpenAI API

        Args:
            patient_name: Patient name
            visit_date: Visit date
            note_text: Full note text
            dx_codes: Pre-extracted DX codes (optional, will extract if not provided)
            cpt_codes: Pre-extracted CPT codes (optional, will extract if not provided)

        Returns:
            Dictionary with review results
        """
        # Extract codes if not provided
        if dx_codes is None:
            dx_codes = self.extract_dx_codes(note_text)
        if cpt_codes is None:
            cpt_codes = self.extract_cpt_codes(note_text)

        logger.info(f"Reviewing note for {patient_name} on {visit_date}")
        logger.info(f"Found {len(dx_codes)} DX codes and {len(cpt_codes)} CPT codes")

        # Construct the review prompt
        prompt = self._construct_review_prompt(patient_name, visit_date, note_text, dx_codes, cpt_codes)

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use GPT-4 for medical review
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert medical billing and documentation specialist with extensive knowledge of psychiatry, behavioral health, and medical coding (ICD-10, CPT). You review clinical notes for completeness, accuracy, medical necessity, and billing compliance."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent, factual responses
                max_tokens=2000
            )

            review_text = response.choices[0].message.content

            # Parse the review into structured format
            review_result = self._parse_review_response(review_text)

            # Add metadata
            review_result['patient_name'] = patient_name
            review_result['visit_date'] = visit_date
            review_result['dx_codes_found'] = dx_codes
            review_result['cpt_codes_found'] = cpt_codes
            review_result['tokens_used'] = response.usage.total_tokens

            logger.info(f"Review completed for {patient_name} - {response.usage.total_tokens} tokens used")

            return review_result

        except Exception as e:
            logger.error(f"Error reviewing note with OpenAI API: {e}")
            return {
                'patient_name': patient_name,
                'visit_date': visit_date,
                'error': str(e),
                'dx_codes_found': dx_codes,
                'cpt_codes_found': cpt_codes
            }

    def _construct_review_prompt(self, patient_name: str, visit_date: str,
                                 note_text: str, dx_codes: List[str],
                                 cpt_codes: List[str]) -> str:
        """Construct the review prompt for OpenAI

        Args:
            patient_name: Patient name
            visit_date: Visit date
            note_text: Full note text
            dx_codes: Extracted DX codes
            cpt_codes: Extracted CPT codes

        Returns:
            Formatted prompt string
        """
        prompt = f"""Please review the following psychiatric/behavioral health clinical note for completeness, accuracy, and billing compliance.

**Patient:** {patient_name}
**Visit Date:** {visit_date}

**Diagnosis Codes Found:** {', '.join(dx_codes) if dx_codes else 'None detected'}
**CPT Codes Found:** {', '.join(cpt_codes) if cpt_codes else 'None detected'}

**Clinical Note:**
---
{note_text}
---

**Please provide a comprehensive review covering:**

1. **Note Completeness** (0-10 score):
   - Are all required elements present (chief complaint, history, assessment, plan)?
   - Is there sufficient detail to support medical necessity?
   - Are subjective and objective findings documented?

2. **Readability & Quality** (0-10 score):
   - Is the note well-organized and easy to follow?
   - Is medical terminology used appropriately?
   - Are there any grammatical or clarity issues?

3. **Diagnosis Code (ICD-10) Review**:
   - Are the diagnosis codes appropriate for the documented conditions?
   - Are codes specific enough (e.g., not using unspecified codes when specifics are documented)?
   - Are any additional diagnosis codes needed based on the documentation?

4. **CPT Code Review**:
   - Are the procedure codes appropriate for the services documented?
   - Is the level of service (E&M code) supported by the documentation?
   - Time-based vs. complexity-based coding - which is more appropriate?

5. **Medical Necessity & Documentation**:
   - Is medical necessity clearly established?
   - Are risk factors, severity, and treatment rationale documented?
   - Is there documentation to support the level of service billed?

6. **Recommended Changes**:
   - Specific additions or clarifications needed in the note
   - Missing elements that should be added
   - Areas that need more detail

7. **Billing & Compliance Recommendations**:
   - Suggested diagnosis code changes or additions
   - Suggested procedure code changes
   - Risk areas for audit or denial
   - Documentation improvements for better reimbursement

8. **Clinical Recommendations**:
   - Follow-up care suggestions
   - Additional assessments or interventions to consider
   - Safety considerations
   - Medication management observations

**Please format your response with clear section headers and bullet points for easy reading.**
"""
        return prompt

    def _parse_review_response(self, review_text: str) -> Dict[str, Any]:
        """Parse OpenAI review response into structured format

        Args:
            review_text: Raw review text from OpenAI

        Returns:
            Structured dictionary of review findings
        """
        # Extract scores using regex
        completeness_match = re.search(r'Note Completeness.*?(\d+)/10', review_text, re.IGNORECASE | re.DOTALL)
        readability_match = re.search(r'Readability.*?(\d+)/10', review_text, re.IGNORECASE | re.DOTALL)

        completeness_score = int(completeness_match.group(1)) if completeness_match else None
        readability_score = int(readability_match.group(1)) if readability_match else None

        return {
            'full_review': review_text,
            'completeness_score': completeness_score,
            'readability_score': readability_score,
            'has_recommendations': 'recommended' in review_text.lower() or 'suggest' in review_text.lower()
        }

    def batch_review_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Review multiple notes in batch

        Args:
            notes: List of note dictionaries with keys: patient_name, visit_date, note_text

        Returns:
            List of review results
        """
        logger.info(f"Starting batch review of {len(notes)} notes")

        reviews = []
        total_tokens = 0

        for idx, note in enumerate(notes, 1):
            logger.info(f"Reviewing note {idx}/{len(notes)}: {note.get('patient_name', 'Unknown')}")

            review = self.review_note(
                patient_name=note.get('patient_name', 'Unknown'),
                visit_date=note.get('visit_date', 'Unknown'),
                note_text=note.get('note_text', note.get('cleaned_note', ''))
            )

            reviews.append(review)
            total_tokens += review.get('tokens_used', 0)

            logger.info(f"Progress: {idx}/{len(notes)} - Total tokens used: {total_tokens}")

        logger.info(f"Batch review complete - {total_tokens} total tokens used")

        return reviews
