#!/usr/bin/env python3
"""
ElevenLabs Conversational AI Agent Configuration
Voice assistant with access to patient database, Freed.ai, and Osmind
"""

from typing import Dict, List, Any
import os

# ElevenLabs Agent Configuration
AGENT_CONFIG = {
    "name": "Medical Records Assistant",
    "description": "AI assistant for medical note management between Freed.ai and Osmind",
    "voice": {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Sarah - Professional female voice
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    },
    "conversation_config": {
        "turn_timeout": 30000,  # 30 seconds
        "agent_max_duration": 300000,  # 5 minutes
    },
    "system_prompt": """You are a helpful medical records assistant with access to patient data, Freed.ai notes, and Osmind records.

Your capabilities:
- Search for patients by name or tags
- Get patient comparison history between Freed.ai and Osmind
- View statistics about note completion rates
- Search for specific notes in Freed.ai
- Check Osmind records
- Add or remove patient tags
- Get recent comparison results

Guidelines:
- Be professional and concise
- Confirm patient names before performing actions
- Summarize results clearly
- Ask for clarification when needed
- Protect patient privacy - never share full medical notes verbally unless explicitly requested
- Use tags to help organize patients efficiently

When responding:
- Keep responses brief and conversational
- Use natural language, not technical jargon
- Confirm actions before executing them
- Provide summaries rather than reading entire lists"""
}

# Function definitions for ElevenLabs agent
AGENT_FUNCTIONS = [
    {
        "name": "search_patients",
        "description": "Search for patients by name or partial name. Returns matching patient records.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Patient name or partial name to search for"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_patient_details",
        "description": "Get detailed information about a specific patient including tags and comparison history",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Exact patient name"
                }
            },
            "required": ["patient_name"]
        }
    },
    {
        "name": "get_comparison_stats",
        "description": "Get overall statistics about Freed.ai vs Osmind comparison results",
        "parameters": {
            "type": "object",
            "properties": {
                "filter_type": {
                    "type": "string",
                    "enum": ["all", "week", "month"],
                    "description": "Time filter for statistics",
                    "default": "all"
                }
            }
        }
    },
    {
        "name": "search_by_status",
        "description": "Search for patients by their note completion status in Osmind",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["complete", "missing", "incomplete"],
                    "description": "Note status to filter by"
                },
                "filter_type": {
                    "type": "string",
                    "enum": ["all", "week", "month"],
                    "description": "Time filter",
                    "default": "all"
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "add_patient_tag",
        "description": "Add a tag to a patient for organization and filtering",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Exact patient name"
                },
                "tag_name": {
                    "type": "string",
                    "description": "Tag to add (e.g., 'urgent', 'follow-up', 'review')"
                }
            },
            "required": ["patient_name", "tag_name"]
        }
    },
    {
        "name": "remove_patient_tag",
        "description": "Remove a tag from a patient",
        "parameters": {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Exact patient name"
                },
                "tag_name": {
                    "type": "string",
                    "description": "Tag to remove"
                }
            },
            "required": ["patient_name", "tag_name"]
        }
    },
    {
        "name": "search_by_tags",
        "description": "Find all patients with specific tags",
        "parameters": {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags to search for"
                },
                "match_all": {
                    "type": "boolean",
                    "description": "If true, patient must have ALL tags. If false, patient needs ANY tag.",
                    "default": False
                }
            },
            "required": ["tags"]
        }
    },
    {
        "name": "get_recent_comparisons",
        "description": "Get the most recent comparison results between Freed.ai and Osmind",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10
                }
            }
        }
    },
    {
        "name": "get_all_tags",
        "description": "Get list of all tags currently in use",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]


def get_agent_config() -> Dict[str, Any]:
    """Get the complete ElevenLabs agent configuration"""
    return {
        **AGENT_CONFIG,
        "functions": AGENT_FUNCTIONS
    }


def get_function_schemas() -> List[Dict[str, Any]]:
    """Get function schemas for ElevenLabs agent"""
    return AGENT_FUNCTIONS


# Example agent creation code (for reference)
AGENT_CREATION_EXAMPLE = """
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation

client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

# Create agent
agent = client.conversational_ai.create_agent(
    name=AGENT_CONFIG['name'],
    description=AGENT_CONFIG['description'],
    prompt=AGENT_CONFIG['system_prompt'],
    voice=AGENT_CONFIG['voice']['voice_id'],
    functions=AGENT_FUNCTIONS,
    conversation_config=AGENT_CONFIG['conversation_config']
)

# Store agent_id for later use
agent_id = agent.agent_id
"""
