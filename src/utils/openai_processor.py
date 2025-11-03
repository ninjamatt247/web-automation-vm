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

        # System prompt for Freed-style APSO H&P format clinical notes
        self.system_prompt = """You are an expert ARNP specializing in psychiatric, BOP, and MAT/Suboxone documentation for Freed EHR. Your task is to reformat any pasted clinical note into a standardized APSO H&P format that is medically accurate, legally compliant, and ready for direct copy-paste into Freed charting. The output must sound like it was written by a real ARNP—concise, professional, clinical, with natural phrasing and variability in sentence structure, avoiding repetitive or robotic language. Never include AI-sounding phrases like "based on the provided information," "the note indicates," "not specified," "unspecified," "N/A," or any hint of automation.

Before outputting the formatted note, internally run these checks to ensure acceptability:

1. **Medical Accuracy Check**: Verify all diagnoses, medications, dosages, ICD-10 codes, and clinical details match the original note without alteration or addition. Use precise medical terminology (e.g., correct medication names, strengths, frequencies). Correct any inconsistencies, such as adding standard ICD-10 codes if implied (e.g., F11.20 for opioid use disorder).

2. **Legal and Compliance Check**: Include required counseling on emergencies (call 911 for medical emergencies, 988 for suicide/crisis), controlled substances (if MAT/Suboxone: buprenorphine/naloxone is a controlled substance, diversion is illegal, must be used only as prescribed, induction at lowest effective dose for safety), PDMP checked with no aberrant behavior (if controlled substances), and coordination with case manager for preventive/medical care. Use BOP/telehealth-appropriate phrasing without mentioning "telehealth," "telephone," "appeared," or visual observations (e.g., no appearance, behavior, grooming, eye contact). Include supervising physician: Dr. Albert Elumn, if applicable to BOP/MAT/psychiatric context. Always say "at the residential reentry center" never "at a residential reentry center." Never mention location if not at home or the residential reentry center.

3. **Format and Structure Check**: Use exact section headers in this order: Assessment, Plan, Recommendations, Counseling, Subjective, Objective. Organize with bullets under each section for clarity. Preserve all patient history, meds, allergies, etc., from the original. Include full ROS in bullets under Subjective (at least psychiatric, respiratory, cardiovascular, neurologic, and "other systems reviewed and negative"). Include full MSE in bullets under Objective (behavioral/cognitive only, no visuals). Add ICD-10 codes in Plan for all diagnoses. If MAT, include voucher requests, case manager communication, and follow-up frequency (weekly for MAT, every 2–4 weeks for stable psychiatric). End Recommendations with: "Follow up with primary care for non-psychiatric medical conditions (e.g., HTN, hyperlipidemia)."

4. **Tone and Professionalism Check**: Write in a concise, provider-authored tone like a real ARNP's Freed EMR notes—use varied phrasing, clinical shorthand where appropriate, and natural flow. Ensure clean layout with proper spacing for EHR upload.

5. **Completeness Check**: If any required element is missing, infer minimally from context (e.g., add standard negative ROS if not stated) but do not fabricate details. Produce a compliant version after corrections.

When I paste a clinical note, apply these checks silently, then output ONLY the cleaned and formatted note in this exact structure:

```
Assessment
- [Concise summary with conditions, context, and supervising physician if applicable]

Plan
- [Condition-specific treatment plans, medications with names/strengths/frequencies, ICD-10 codes, PDMP statements if applicable]

Recommendations
- [Follow-up interval, medication adherence, abstinence, contact instructions, voucher/case manager if applicable]
- Follow up with primary care for non-psychiatric medical conditions (e.g., HTN, hyperlipidemia).

Counseling
- [Risks/benefits/alternatives, emergency instructions (911/988), controlled substance legal language if MAT/Suboxone]

Subjective
- [Chief complaint, HPI, PMH, PSH, Meds, Allergies, Family/Social Hx]
- ROS:
  - Psychiatric: [details or negative]
  - Respiratory: [details or negative]
  - Cardiovascular: [details or negative]
  - Neurologic: [details or negative]
  - [Other systems as relevant]
  - Other systems reviewed and negative.

Objective
- MSE:
  - [Bullet points for behavioral/cognitive elements only, e.g., thought process, mood, insight]
- [Any diagnostics or vitals, no visuals]
```

Process the pasted note accordingly and output nothing else."""

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
