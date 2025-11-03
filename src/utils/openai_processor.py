"""OpenAI API processor for cleaning and formatting patient notes."""
from typing import Optional
from openai import OpenAI
from src.utils.logger import logger
from src.utils.config import AppConfig


class OpenAIProcessor:
    """Process and clean patient notes using OpenAI API."""

    def __init__(self, config: AppConfig):
        """Initialize OpenAI processor.

        Args:
            config: Application configuration containing API key
        """
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = config.openai_model
        self.max_tokens = config.openai_max_tokens

        # Default system prompt for cleaning medical notes
        self.system_prompt = """You are a medical documentation specialist. Your task is to clean and format clinical notes for Electronic Health Record (EHR) systems.

**Your responsibilities:**
1. Preserve all medical information accurately - do not alter medical facts, diagnoses, medications, or clinical observations
2. Format the note in a clear, professional EHR-compatible structure
3. Organize information into standard sections: Assessment, Plan, Medications, etc.
4. Fix any obvious typos or grammatical errors while preserving medical terminology
5. Ensure consistent formatting (dates, medications, dosages)
6. Remove any duplicate information
7. Maintain HIPAA compliance - keep all patient information intact

**Output format:**
- Use clear section headers
- Use bullet points or numbered lists where appropriate
- Maintain professional medical language
- Ensure the note is ready for direct insertion into an EHR system"""

    def clean_patient_note(self, raw_note: str, custom_prompt: Optional[str] = None) -> Optional[str]:
        """Clean and format a patient note using OpenAI.

        Args:
            raw_note: Raw patient note text from Freed.ai
            custom_prompt: Optional custom prompt override

        Returns:
            Cleaned and formatted note, or None if processing fails
        """
        try:
            logger.info("Processing patient note with OpenAI...")

            # Use custom prompt if provided, otherwise use default
            system_message = custom_prompt if custom_prompt else self.system_prompt

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Please clean and format this clinical note:\n\n{raw_note}"}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3  # Lower temperature for consistency
            )

            # Extract cleaned note
            cleaned_note = response.choices[0].message.content.strip()

            # Log token usage
            usage = response.usage
            logger.info(f"OpenAI tokens used: {usage.total_tokens} "
                       f"(prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens})")

            logger.info("Successfully processed patient note")
            return cleaned_note

        except Exception as e:
            logger.error(f"Failed to process note with OpenAI: {e}")
            return None

    def batch_clean_notes(self, notes: list[dict]) -> list[dict]:
        """Clean multiple patient notes.

        Args:
            notes: List of dictionaries containing patient notes
                  Expected keys: 'patient_name', 'date', 'raw_note'

        Returns:
            List of dictionaries with added 'cleaned_note' field
        """
        logger.info(f"Starting batch processing of {len(notes)} notes...")

        processed_notes = []
        success_count = 0
        failure_count = 0

        for i, note_data in enumerate(notes):
            logger.info(f"Processing note {i+1}/{len(notes)}: {note_data.get('patient_name', 'Unknown')}")

            try:
                raw_note = note_data.get('raw_note', '')

                if not raw_note:
                    logger.warning(f"Empty note for patient: {note_data.get('patient_name')}")
                    note_data['cleaned_note'] = None
                    note_data['processing_status'] = 'empty'
                    failure_count += 1
                else:
                    cleaned = self.clean_patient_note(raw_note)

                    if cleaned:
                        note_data['cleaned_note'] = cleaned
                        note_data['processing_status'] = 'success'
                        success_count += 1
                    else:
                        note_data['cleaned_note'] = None
                        note_data['processing_status'] = 'failed'
                        failure_count += 1

                processed_notes.append(note_data)

            except Exception as e:
                logger.error(f"Error processing note {i+1}: {e}")
                note_data['cleaned_note'] = None
                note_data['processing_status'] = 'error'
                note_data['error_message'] = str(e)
                processed_notes.append(note_data)
                failure_count += 1

        logger.info(f"Batch processing complete: {success_count} successful, {failure_count} failed")
        return processed_notes

    def test_connection(self) -> bool:
        """Test OpenAI API connection.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info("Testing OpenAI API connection...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Test connection. Respond with 'OK'."}
                ],
                max_tokens=10
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"OpenAI API test successful: {result}")
            return True

        except Exception as e:
            logger.error(f"OpenAI API test failed: {e}")
            return False
