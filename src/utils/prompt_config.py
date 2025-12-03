"""Prompt configuration loader for multi-step note processing."""
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from src.utils.logger import logger


@dataclass
class RequirementCheck:
    """Single requirement check configuration."""
    id: str
    name: str
    description: str
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    validation_regex: Optional[str] = None
    required_patterns: Optional[List[str]] = None
    banned_phrases: Optional[List[str]] = None
    condition_regex: Optional[str] = None
    error_message: str = ""


class PromptConfig:
    """Manages prompt configuration and requirement checks."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize prompt configuration.

        Args:
            config_path: Path to prompts_config.yaml (defaults to config/prompts_config.yaml)
        """
        if config_path is None:
            # Try Docker path first, then local path
            docker_path = Path("/app/config/prompts_config.yaml")
            local_path = Path(__file__).parent.parent.parent / "config" / "prompts_config.yaml"

            if docker_path.exists():
                config_path = docker_path
            elif local_path.exists():
                config_path = local_path
            else:
                raise FileNotFoundError("prompts_config.yaml not found in expected locations")

        self.config_path = config_path
        self.config = self._load_config()
        self.requirements = self._parse_requirements()

        logger.info(f"Loaded prompt configuration from {config_path}")
        logger.info(f"Total requirement checks: {len(self.requirements)}")

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file.

        Returns:
            Parsed configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load prompt configuration: {e}")
            raise

    def _parse_requirements(self) -> List[RequirementCheck]:
        """Parse requirement checks from configuration.

        Returns:
            List of RequirementCheck objects ordered by priority
        """
        requirements = []
        req_config = self.config.get('requirements', {})

        # Process each priority level
        for priority in ['critical', 'high', 'medium', 'low']:
            checks = req_config.get(priority, [])
            for check in checks:
                requirements.append(RequirementCheck(
                    id=check.get('id', ''),
                    name=check.get('name', ''),
                    description=check.get('description', ''),
                    priority=priority.upper(),
                    validation_regex=check.get('validation_regex'),
                    required_patterns=check.get('required_patterns'),
                    banned_phrases=check.get('banned_phrases'),
                    condition_regex=check.get('condition_regex'),
                    error_message=check.get('error_message', '')
                ))

        logger.info(f"Parsed {len(requirements)} requirement checks")
        return requirements

    def get_initial_prompt(self) -> str:
        """Get the initial strict prompt.

        Returns:
            Initial prompt string
        """
        return self.config.get('initial_prompt', '').strip()

    def get_verification_prompt(self) -> str:
        """Get the verification/cleanup prompt.

        Returns:
            Verification prompt string
        """
        return self.config.get('verification_prompt', '').strip()

    def get_requirements_by_priority(self, priority: str) -> List[RequirementCheck]:
        """Get requirement checks for a specific priority level.

        Args:
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)

        Returns:
            List of requirements matching the priority
        """
        return [req for req in self.requirements if req.priority == priority.upper()]

    def get_all_requirements(self) -> List[RequirementCheck]:
        """Get all requirement checks ordered by priority.

        Returns:
            List of all requirement checks
        """
        return self.requirements

    def get_requirements_by_priority(self) -> Dict[str, List[RequirementCheck]]:
        """Get requirements organized by priority level.

        Returns:
            Dictionary with priority levels as keys and lists of requirements as values
        """
        result = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }
        for req in self.requirements:
            priority = req.priority.lower()
            if priority in result:
                result[priority].append(req)
        return result

    def get_human_intervention_triggers(self) -> List[str]:
        """Get list of conditions that trigger human intervention.

        Returns:
            List of human intervention trigger conditions
        """
        return self.config.get('human_intervention_triggers', [])

    def reload(self) -> None:
        """Reload configuration from file.

        Useful for picking up user modifications without restarting.
        """
        logger.info("Reloading prompt configuration...")
        self.config = self._load_config()
        self.requirements = self._parse_requirements()
        logger.info("Prompt configuration reloaded successfully")

    def get_config_path(self) -> Path:
        """Get the path to the configuration file.

        Returns:
            Path to prompts_config.yaml
        """
        return self.config_path

    def validate_config(self) -> List[str]:
        """Validate configuration structure and return errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for required top-level keys
        if not self.config.get('initial_prompt'):
            errors.append("Missing 'initial_prompt' in configuration")

        if not self.config.get('verification_prompt'):
            errors.append("Missing 'verification_prompt' in configuration")

        if not self.config.get('requirements'):
            errors.append("Missing 'requirements' in configuration")

        # Validate requirement structure
        for req in self.requirements:
            if not req.id:
                errors.append(f"Requirement missing 'id': {req.name}")

            if not req.name:
                errors.append(f"Requirement {req.id} missing 'name'")

            # Check that at least one validation method is defined
            if not any([req.validation_regex, req.required_patterns, req.banned_phrases]):
                errors.append(
                    f"Requirement {req.id} has no validation method "
                    "(needs validation_regex, required_patterns, or banned_phrases)"
                )

        return errors


# Global instance for singleton access
_prompt_config: Optional[PromptConfig] = None


def get_prompt_config(reload: bool = False) -> PromptConfig:
    """Get or create the global prompt configuration instance.

    Args:
        reload: Force reload configuration from file

    Returns:
        PromptConfig instance
    """
    global _prompt_config

    if _prompt_config is None or reload:
        _prompt_config = PromptConfig()
    elif reload:
        _prompt_config.reload()

    return _prompt_config
