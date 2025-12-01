"""OpenAI API processor for cleaning and formatting patient notes."""
from typing import Optional, Dict, Any
from openai import OpenAI
from src.utils.logger import logger
from src.utils.config import AppConfig
from src.utils.prompt_config import get_prompt_config
from src.utils.requirement_validator import RequirementValidator, NoteValidationReport
import re


class OpenAIProcessor:
    """Process and clean patient notes using OpenAI API."""

    def __init__(self, config: AppConfig, use_multi_step: bool = True):
        """Initialize OpenAI processor.

        Args:
            config: Application configuration containing API key
            use_multi_step: Enable multi-step verification (default: True)
        """
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = config.openai_model
        self.max_tokens = config.openai_max_tokens
        self.use_multi_step = use_multi_step

        # Load prompt configuration and validator
        self.prompt_config = get_prompt_config()
        self.validator = RequirementValidator(self.prompt_config)

        # System prompt for Freed-style APSO H&P format clinical notes
        self.system_prompt = """You are an expert ARNP specializing in psychiatric, BOP, and MAT/Suboxone documentation for Freed EHR. Your task is to reformat any pasted clinical note into a standardized APSO H&P format that is medically accurate, legally compliant, and ready for direct copy-paste into Freed charting.

CRITICAL RULES - VIOLATION OF THESE RULES IS UNACCEPTABLE:

1. **APSO ORDER IS MANDATORY - NEVER USE SOAP ORDER**: The section order MUST BE: Assessment, Plan, Recommendations, Counseling, Subjective, Objective. This is NOT negotiable. DO NOT use traditional SOAP order (Subjective, Objective, Assessment, Plan). Assessment and Plan MUST come BEFORE Subjective and Objective.

2. **ZERO AI LANGUAGE ALLOWED**: Write EXACTLY as a real ARNP would write in their EHR. NEVER include ANY of these phrases or similar AI markers:
   - "based on the provided information"
   - "the note indicates"
   - "not specified" / "unspecified"
   - "N/A" / "not available"
   - "as mentioned" / "as noted"
   - "it appears" / "it seems"
   - "the patient reports that"
   - Any phrase that sounds like you're summarizing someone else's note

3. **WRITE AS THE PROVIDER**: You ARE the ARNP writing this note. Write in first person clinical voice: "Patient presents with...", "Counseled on...", "Will continue...", "Plan to...". DO NOT write as if you're reformatting or summarizing another person's note.

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

    def multi_step_clean_patient_note(
        self,
        raw_note: str,
        custom_initial_prompt: Optional[str] = None,
        custom_verification_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clean and format a patient note using multi-step verification process.

        This method implements a rigorous 3-step process:
        1. Initial cleaning with strict formatting prompt
        2. Verification pass to ensure 100% compliance
        3. Validation against ranked requirement checks

        Args:
            raw_note: Raw patient note text from Freed.ai
            custom_initial_prompt: Optional custom initial prompt override
            custom_verification_prompt: Optional custom verification prompt override

        Returns:
            Dictionary containing:
                - cleaned_note: Final cleaned note text
                - step1_note: Note after initial cleaning
                - step2_note: Note after verification
                - step2_status: Verification status (VERIFIED, CORRECTED, NEEDS_HUMAN_REVIEW)
                - validation_report: NoteValidationReport object
                - requires_human_intervention: Boolean flag
                - processing_status: Overall status (success, needs_review, failed)
                - tokens_used: Total tokens consumed
                - error: Error message if processing fails
        """
        try:
            logger.info("Starting multi-step note processing...")
            total_tokens = 0
            result = {
                'processing_status': 'failed',
                'requires_human_intervention': False,
                'tokens_used': 0
            }

            # STEP 1: Initial strict cleaning
            logger.info("STEP 1: Initial strict cleaning...")
            initial_prompt = custom_initial_prompt or self.prompt_config.get_initial_prompt()

            step1_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": initial_prompt},
                    {"role": "user", "content": f"Please clean and format this clinical note:\n\n{raw_note}"}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3
            )

            step1_note = step1_response.choices[0].message.content.strip()
            step1_tokens = step1_response.usage.total_tokens
            total_tokens += step1_tokens

            logger.info(f"STEP 1 complete: {step1_tokens} tokens used")
            result['step1_note'] = step1_note

            # STEP 2: Verification and cleanup
            logger.info("STEP 2: Verification and cleanup...")
            verification_prompt = custom_verification_prompt or self.prompt_config.get_verification_prompt()

            step2_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": verification_prompt},
                    {"role": "user", "content": f"Review this note for compliance:\n\n{step1_note}"}
                ],
                max_tokens=self.max_tokens,
                temperature=0.2  # Even lower temperature for verification
            )

            step2_output = step2_response.choices[0].message.content.strip()
            step2_tokens = step2_response.usage.total_tokens
            total_tokens += step2_tokens

            logger.info(f"STEP 2 complete: {step2_tokens} tokens used")

            # Parse verification status
            step2_status = self._extract_verification_status(step2_output)
            step2_note = self._extract_note_from_verification(step2_output)

            result['step2_note'] = step2_note
            result['step2_status'] = step2_status

            logger.info(f"Verification status: {step2_status}")

            # Check if verification flagged for human review
            if step2_status == "NEEDS_HUMAN_REVIEW":
                result['requires_human_intervention'] = True
                result['processing_status'] = 'needs_review'
                result['human_intervention_reason'] = 'Verification step flagged critical errors'

            # STEP 3: Requirement validation
            logger.info("STEP 3: Requirement validation...")
            validation_report = self.validator.validate_note(step2_note)

            result['validation_report'] = validation_report
            result['validation_summary'] = self.validator.get_failure_summary(validation_report)

            # Check if validation requires human intervention
            if validation_report.requires_human_intervention:
                result['requires_human_intervention'] = True
                result['processing_status'] = 'needs_review'

            # Set final cleaned note and status
            result['cleaned_note'] = step2_note
            result['tokens_used'] = total_tokens

            if not result['requires_human_intervention']:
                if validation_report.overall_status == "PASS":
                    result['processing_status'] = 'success'
                elif validation_report.overall_status == "WARN":
                    result['processing_status'] = 'success_with_warnings'
                else:
                    result['processing_status'] = 'needs_review'

            logger.info(
                f"Multi-step processing complete: {result['processing_status']} "
                f"(Total tokens: {total_tokens})"
            )

            if result['requires_human_intervention']:
                logger.warning(
                    f"Human intervention required: "
                    f"{', '.join(validation_report.human_intervention_reasons)}"
                )

            return result

        except Exception as e:
            logger.error(f"Failed to process note with multi-step verification: {e}")
            return {
                'processing_status': 'failed',
                'error': str(e),
                'requires_human_intervention': True,
                'human_intervention_reason': f'Processing error: {str(e)}',
                'tokens_used': total_tokens
            }

    def _extract_verification_status(self, verification_output: str) -> str:
        """Extract status from verification step output.

        Args:
            verification_output: Output from verification prompt

        Returns:
            Status string: VERIFIED, CORRECTED, or NEEDS_HUMAN_REVIEW
        """
        if re.search(r'STATUS:\s*VERIFIED', verification_output, re.IGNORECASE):
            return "VERIFIED"
        elif re.search(r'STATUS:\s*CORRECTED', verification_output, re.IGNORECASE):
            return "CORRECTED"
        elif re.search(r'STATUS:\s*NEEDS_HUMAN_REVIEW', verification_output, re.IGNORECASE):
            return "NEEDS_HUMAN_REVIEW"
        else:
            # Default to CORRECTED if no status marker found
            return "CORRECTED"

    def _extract_note_from_verification(self, verification_output: str) -> str:
        """Extract the note content from verification output.

        Args:
            verification_output: Output from verification prompt

        Returns:
            Extracted note text
        """
        # Try to extract note after STATUS line
        status_match = re.search(r'STATUS:.*?\n\n(.+)', verification_output, re.DOTALL | re.IGNORECASE)
        if status_match:
            return status_match.group(1).strip()

        # If no STATUS marker, return entire output
        return verification_output.strip()

    def batch_clean_notes(self, notes: list[dict], use_multi_step: Optional[bool] = None) -> list[dict]:
        """Clean multiple patient notes.

        Args:
            notes: List of dictionaries containing patient notes
                  Expected keys: 'patient_name', 'date', 'raw_note'
            use_multi_step: Override multi-step processing (defaults to instance setting)

        Returns:
            List of dictionaries with added 'cleaned_note' field and validation results
        """
        # Determine processing mode
        multi_step_enabled = use_multi_step if use_multi_step is not None else self.use_multi_step

        logger.info(
            f"Starting batch processing of {len(notes)} notes "
            f"(multi-step: {multi_step_enabled})..."
        )

        processed_notes = []
        success_count = 0
        failure_count = 0
        needs_review_count = 0

        for i, note_data in enumerate(notes):
            logger.info(f"Processing note {i+1}/{len(notes)}: {note_data.get('patient_name', 'Unknown')}")

            try:
                raw_note = note_data.get('raw_note', '')

                if not raw_note:
                    logger.warning(f"Empty note for patient: {note_data.get('patient_name')}")
                    note_data['cleaned_note'] = None
                    note_data['processing_status'] = 'empty'
                    note_data['requires_human_intervention'] = True
                    failure_count += 1
                else:
                    if multi_step_enabled:
                        # Use multi-step verification process
                        result = self.multi_step_clean_patient_note(raw_note)
                        note_data.update(result)

                        if result['processing_status'] == 'success':
                            success_count += 1
                        elif result['processing_status'] in ['needs_review', 'success_with_warnings']:
                            needs_review_count += 1
                        else:
                            failure_count += 1
                    else:
                        # Use legacy single-step process
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
                note_data['requires_human_intervention'] = True
                processed_notes.append(note_data)
                failure_count += 1

        if multi_step_enabled:
            logger.info(
                f"Batch processing complete: {success_count} successful, "
                f"{needs_review_count} need review, {failure_count} failed"
            )
        else:
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
