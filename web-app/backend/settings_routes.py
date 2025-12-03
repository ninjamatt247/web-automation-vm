#!/usr/bin/env python3
"""
API routes for AI prompt settings management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import yaml
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.prompt_config import get_prompt_config
from src.utils.logger import logger

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Pydantic models for request/response
class PromptSettings(BaseModel):
    initial_prompt: str
    verification_prompt: str


class RequirementCheck(BaseModel):
    id: str
    name: str
    description: str
    priority: str
    validation_regex: Optional[str] = None
    required_patterns: Optional[List[str]] = None
    banned_phrases: Optional[List[str]] = None
    condition_regex: Optional[str] = None
    error_message: str


class RequirementsSettings(BaseModel):
    critical: List[RequirementCheck]
    high: List[RequirementCheck]
    medium: List[RequirementCheck]
    low: List[RequirementCheck]


class FullSettings(BaseModel):
    initial_prompt: str
    verification_prompt: str
    requirements: Dict[str, List[Dict[str, Any]]]
    human_intervention_triggers: List[str]


# ===== GET ENDPOINTS =====

@router.get("/prompts")
async def get_prompts():
    """Get current AI prompts"""
    try:
        config = get_prompt_config()

        return {
            "initial_prompt": config.get_initial_prompt(),
            "verification_prompt": config.get_verification_prompt()
        }
    except Exception as e:
        logger.error(f"Error getting prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requirements")
async def get_requirements():
    """Get all requirement checks organized by priority"""
    try:
        config = get_prompt_config()

        requirements = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for req in config.get_all_requirements():
            req_dict = {
                'id': req.id,
                'name': req.name,
                'description': req.description,
                'priority': req.priority.lower(),
                'validation_regex': req.validation_regex,
                'required_patterns': req.required_patterns,
                'banned_phrases': req.banned_phrases,
                'condition_regex': req.condition_regex,
                'error_message': req.error_message
            }
            requirements[req.priority.lower()].append(req_dict)

        return requirements
    except Exception as e:
        logger.error(f"Error getting requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intervention-triggers")
async def get_intervention_triggers():
    """Get human intervention trigger conditions"""
    try:
        config = get_prompt_config()
        return {
            "triggers": config.get_human_intervention_triggers()
        }
    except Exception as e:
        logger.error(f"Error getting intervention triggers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/full")
async def get_full_settings():
    """Get complete settings configuration"""
    try:
        config = get_prompt_config()

        # Get requirements
        requirements = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for req in config.get_all_requirements():
            req_dict = {
                'id': req.id,
                'name': req.name,
                'description': req.description,
                'validation_regex': req.validation_regex,
                'required_patterns': req.required_patterns,
                'banned_phrases': req.banned_phrases,
                'condition_regex': req.condition_regex,
                'error_message': req.error_message
            }
            requirements[req.priority.lower()].append(req_dict)

        return {
            "initial_prompt": config.get_initial_prompt(),
            "verification_prompt": config.get_verification_prompt(),
            "requirements": requirements,
            "human_intervention_triggers": config.get_human_intervention_triggers(),
            "config_path": str(config.get_config_path())
        }
    except Exception as e:
        logger.error(f"Error getting full settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate")
async def validate_settings():
    """Validate current settings configuration"""
    try:
        config = get_prompt_config()
        errors = config.validate_config()

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error validating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== UPDATE ENDPOINTS =====

@router.put("/prompts")
async def update_prompts(settings: PromptSettings):
    """Update AI prompts"""
    try:
        config = get_prompt_config()
        config_path = config.get_config_path()

        # Load current config
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Update prompts
        config_data['initial_prompt'] = settings.initial_prompt
        config_data['verification_prompt'] = settings.verification_prompt

        # Save back to file
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Reload configuration
        get_prompt_config(reload=True)

        logger.info("Successfully updated AI prompts")

        return {
            "success": True,
            "message": "Prompts updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/requirements")
async def update_requirements(requirements: Dict[str, List[Dict[str, Any]]]):
    """Update requirement checks"""
    try:
        config = get_prompt_config()
        config_path = config.get_config_path()

        # Load current config
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Update requirements
        config_data['requirements'] = requirements

        # Save back to file
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Reload configuration
        get_prompt_config(reload=True)

        # Validate after update
        new_config = get_prompt_config()
        errors = new_config.validate_config()

        if errors:
            logger.warning(f"Requirements updated with validation warnings: {errors}")

        logger.info("Successfully updated requirement checks")

        return {
            "success": True,
            "message": "Requirements updated successfully",
            "validation_errors": errors
        }
    except Exception as e:
        logger.error(f"Error updating requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/intervention-triggers")
async def update_intervention_triggers(triggers: Dict[str, List[str]]):
    """Update human intervention triggers"""
    try:
        config = get_prompt_config()
        config_path = config.get_config_path()

        # Load current config
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Update triggers
        config_data['human_intervention_triggers'] = triggers.get('triggers', [])

        # Save back to file
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Reload configuration
        get_prompt_config(reload=True)

        logger.info("Successfully updated intervention triggers")

        return {
            "success": True,
            "message": "Intervention triggers updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating intervention triggers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/full")
async def update_full_settings(settings: FullSettings):
    """Update complete settings configuration"""
    try:
        config = get_prompt_config()
        config_path = config.get_config_path()

        # Create new config structure
        config_data = {
            'initial_prompt': settings.initial_prompt,
            'verification_prompt': settings.verification_prompt,
            'requirements': settings.requirements,
            'human_intervention_triggers': settings.human_intervention_triggers
        }

        # Save to file
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Reload configuration
        get_prompt_config(reload=True)

        # Validate after update
        new_config = get_prompt_config()
        errors = new_config.validate_config()

        logger.info("Successfully updated all settings")

        return {
            "success": True,
            "message": "All settings updated successfully",
            "validation_errors": errors
        }
    except Exception as e:
        logger.error(f"Error updating full settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== RESET ENDPOINT =====

@router.post("/reset")
async def reset_to_defaults():
    """Reset settings to default values (creates backup first)"""
    try:
        config = get_prompt_config()
        config_path = config.get_config_path()

        # Create backup
        import shutil
        from datetime import datetime
        backup_path = config_path.parent / f"prompts_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        shutil.copy(config_path, backup_path)

        logger.info(f"Created backup at {backup_path}")

        # Note: You would need to define default settings here
        # For now, we'll just return success with backup info

        return {
            "success": True,
            "message": f"Backup created at {backup_path}. Manual reset required.",
            "backup_path": str(backup_path)
        }
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== STATS ENDPOINT =====

@router.get("/stats")
async def get_settings_stats():
    """Get statistics about current settings"""
    try:
        config = get_prompt_config()

        requirements = config.get_all_requirements()
        by_priority = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        }

        for req in requirements:
            by_priority[req.priority] += 1

        return {
            "total_requirements": len(requirements),
            "by_priority": by_priority,
            "prompts": {
                "initial_length": len(config.get_initial_prompt()),
                "verification_length": len(config.get_verification_prompt())
            },
            "intervention_triggers": len(config.get_human_intervention_triggers()),
            "config_path": str(config.get_config_path())
        }
    except Exception as e:
        logger.error(f"Error getting settings stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
