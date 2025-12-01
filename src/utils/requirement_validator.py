"""Requirement validator for clinical notes."""
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from src.utils.logger import logger
from src.utils.prompt_config import PromptConfig, RequirementCheck, get_prompt_config


@dataclass
class ValidationResult:
    """Result of a single requirement check."""
    requirement_id: str
    requirement_name: str
    priority: str
    passed: bool
    error_message: Optional[str] = None
    details: Optional[str] = None


@dataclass
class NoteValidationReport:
    """Complete validation report for a note."""
    note_text: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    critical_failures: int
    high_failures: int
    medium_failures: int
    low_failures: int
    requires_human_intervention: bool
    validation_results: List[ValidationResult]
    human_intervention_reasons: List[str]
    overall_status: str  # PASS, WARN, FAIL, NEEDS_REVIEW

    def get_failures_by_priority(self, priority: str) -> List[ValidationResult]:
        """Get all failed checks for a specific priority level.

        Args:
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)

        Returns:
            List of failed validation results
        """
        return [
            result for result in self.validation_results
            if not result.passed and result.priority == priority.upper()
        ]

    def get_all_failures(self) -> List[ValidationResult]:
        """Get all failed validation checks.

        Returns:
            List of all failed validation results
        """
        return [result for result in self.validation_results if not result.passed]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the report
        """
        return {
            'total_checks': self.total_checks,
            'passed_checks': self.passed_checks,
            'failed_checks': self.failed_checks,
            'critical_failures': self.critical_failures,
            'high_failures': self.high_failures,
            'medium_failures': self.medium_failures,
            'low_failures': self.low_failures,
            'requires_human_intervention': self.requires_human_intervention,
            'overall_status': self.overall_status,
            'human_intervention_reasons': self.human_intervention_reasons,
            'validation_results': [
                {
                    'requirement_id': result.requirement_id,
                    'requirement_name': result.requirement_name,
                    'priority': result.priority,
                    'passed': result.passed,
                    'error_message': result.error_message,
                    'details': result.details
                }
                for result in self.validation_results
            ]
        }


class RequirementValidator:
    """Validates clinical notes against configurable requirements."""

    def __init__(self, prompt_config: Optional[PromptConfig] = None):
        """Initialize validator.

        Args:
            prompt_config: PromptConfig instance (creates new if not provided)
        """
        self.config = prompt_config or get_prompt_config()
        logger.info("Requirement validator initialized")

    def validate_note(self, note_text: str) -> NoteValidationReport:
        """Validate a note against all requirement checks.

        Args:
            note_text: The clinical note text to validate

        Returns:
            NoteValidationReport with detailed validation results
        """
        logger.info("Starting note validation...")

        validation_results = []
        requirements = self.config.get_all_requirements()

        # Run all requirement checks
        for requirement in requirements:
            result = self._check_requirement(note_text, requirement)
            validation_results.append(result)

        # Count failures by priority
        critical_failures = sum(
            1 for r in validation_results
            if not r.passed and r.priority == "CRITICAL"
        )
        high_failures = sum(
            1 for r in validation_results
            if not r.passed and r.priority == "HIGH"
        )
        medium_failures = sum(
            1 for r in validation_results
            if not r.passed and r.priority == "MEDIUM"
        )
        low_failures = sum(
            1 for r in validation_results
            if not r.passed and r.priority == "LOW"
        )

        passed_checks = sum(1 for r in validation_results if r.passed)
        failed_checks = len(validation_results) - passed_checks

        # Determine if human intervention is required
        human_intervention_reasons = []
        requires_human_intervention = False

        # Check critical failures
        if critical_failures > 0:
            requires_human_intervention = True
            human_intervention_reasons.append(
                f"{critical_failures} CRITICAL requirement(s) failed"
            )

        # Check high priority failures threshold
        if high_failures >= 3:
            requires_human_intervention = True
            human_intervention_reasons.append(
                f"{high_failures} HIGH priority failures (threshold: 3)"
            )

        # Check note length
        note_length = len(note_text)
        if note_length < 200:
            requires_human_intervention = True
            human_intervention_reasons.append(
                f"Note too short ({note_length} chars, minimum: 200)"
            )
        elif note_length > 10000:
            requires_human_intervention = True
            human_intervention_reasons.append(
                f"Note unexpectedly long ({note_length} chars, maximum: 10000)"
            )

        # Determine overall status
        if requires_human_intervention:
            overall_status = "NEEDS_REVIEW"
        elif critical_failures > 0 or high_failures > 0:
            overall_status = "FAIL"
        elif medium_failures > 0 or low_failures > 0:
            overall_status = "WARN"
        else:
            overall_status = "PASS"

        report = NoteValidationReport(
            note_text=note_text,
            total_checks=len(validation_results),
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            critical_failures=critical_failures,
            high_failures=high_failures,
            medium_failures=medium_failures,
            low_failures=low_failures,
            requires_human_intervention=requires_human_intervention,
            validation_results=validation_results,
            human_intervention_reasons=human_intervention_reasons,
            overall_status=overall_status
        )

        logger.info(
            f"Validation complete: {overall_status} "
            f"({passed_checks}/{len(validation_results)} checks passed)"
        )

        if requires_human_intervention:
            logger.warning(
                f"Human intervention required: {', '.join(human_intervention_reasons)}"
            )

        return report

    def _check_requirement(self, note_text: str, requirement: RequirementCheck) -> ValidationResult:
        """Check a single requirement against the note.

        Args:
            note_text: The clinical note text
            requirement: The requirement to check

        Returns:
            ValidationResult for this requirement
        """
        # Check if requirement is conditional
        if requirement.condition_regex:
            if not re.search(requirement.condition_regex, note_text, re.IGNORECASE | re.DOTALL):
                # Condition not met, requirement doesn't apply
                return ValidationResult(
                    requirement_id=requirement.id,
                    requirement_name=requirement.name,
                    priority=requirement.priority,
                    passed=True,
                    details="Requirement not applicable (condition not met)"
                )

        # Check validation_regex
        if requirement.validation_regex:
            if not re.search(requirement.validation_regex, note_text, re.IGNORECASE | re.DOTALL):
                return ValidationResult(
                    requirement_id=requirement.id,
                    requirement_name=requirement.name,
                    priority=requirement.priority,
                    passed=False,
                    error_message=requirement.error_message,
                    details=f"Pattern not found: {requirement.validation_regex}"
                )

        # Check required_patterns
        if requirement.required_patterns:
            missing_patterns = []
            for pattern in requirement.required_patterns:
                if not re.search(pattern, note_text, re.IGNORECASE | re.DOTALL):
                    missing_patterns.append(pattern)

            if missing_patterns:
                return ValidationResult(
                    requirement_id=requirement.id,
                    requirement_name=requirement.name,
                    priority=requirement.priority,
                    passed=False,
                    error_message=requirement.error_message,
                    details=f"Missing required patterns: {', '.join(missing_patterns)}"
                )

        # Check banned_phrases
        if requirement.banned_phrases:
            found_banned = []
            for phrase in requirement.banned_phrases:
                # Case insensitive search for banned phrases
                if re.search(re.escape(phrase), note_text, re.IGNORECASE):
                    found_banned.append(phrase)

            if found_banned:
                return ValidationResult(
                    requirement_id=requirement.id,
                    requirement_name=requirement.name,
                    priority=requirement.priority,
                    passed=False,
                    error_message=requirement.error_message,
                    details=f"Found banned phrases: {', '.join(found_banned)}"
                )

        # All checks passed
        return ValidationResult(
            requirement_id=requirement.id,
            requirement_name=requirement.name,
            priority=requirement.priority,
            passed=True
        )

    def get_failure_summary(self, report: NoteValidationReport) -> str:
        """Generate a human-readable summary of validation failures.

        Args:
            report: NoteValidationReport to summarize

        Returns:
            Formatted summary string
        """
        if report.overall_status == "PASS":
            return "✅ All validation checks passed"

        lines = [f"Overall Status: {report.overall_status}"]
        lines.append(f"Passed: {report.passed_checks}/{report.total_checks}")

        if report.critical_failures > 0:
            lines.append(f"\n❌ CRITICAL Failures ({report.critical_failures}):")
            for result in report.get_failures_by_priority("CRITICAL"):
                lines.append(f"  - {result.requirement_name}: {result.error_message}")

        if report.high_failures > 0:
            lines.append(f"\n⚠️  HIGH Priority Failures ({report.high_failures}):")
            for result in report.get_failures_by_priority("HIGH"):
                lines.append(f"  - {result.requirement_name}: {result.error_message}")

        if report.medium_failures > 0:
            lines.append(f"\n⚡ MEDIUM Priority Failures ({report.medium_failures}):")
            for result in report.get_failures_by_priority("MEDIUM"):
                lines.append(f"  - {result.requirement_name}: {result.error_message}")

        if report.low_failures > 0:
            lines.append(f"\nℹ️  LOW Priority Failures ({report.low_failures}):")
            for result in report.get_failures_by_priority("LOW"):
                lines.append(f"  - {result.requirement_name}: {result.error_message}")

        if report.requires_human_intervention:
            lines.append("\n🚨 HUMAN INTERVENTION REQUIRED:")
            for reason in report.human_intervention_reasons:
                lines.append(f"  - {reason}")

        return "\n".join(lines)
