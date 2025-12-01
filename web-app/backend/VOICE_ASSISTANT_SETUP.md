# Voice Assistant Setup Guide

## ElevenLabs Conversational AI Integration

This guide explains how to set up and configure the voice assistant with ElevenLabs v3.

### Prerequisites

1. **ElevenLabs Account**: Sign up at [elevenlabs.io](https://elevenlabs.io)
2. **API Key**: Get your API key from the ElevenLabs dashboard
3. **Python Package**: Install the ElevenLabs Python SDK

```bash
cd /Users/harringhome/web-automation-vm
source .venv/bin/activate
pip install elevenlabs
```

### Backend Setup

#### 1. Configure Environment Variables

Add your ElevenLabs API key to your environment:

```bash
export ELEVENLABS_API_KEY="your_api_key_here"
```

Or add to a `.env` file in the backend directory:

```
ELEVENLABS_API_KEY=your_api_key_here
```

#### 2. Create the ElevenLabs Agent

Run the agent creation script:

```python
from elevenlabs.client import ElevenLabs
from elevenlabs_agent import AGENT_CONFIG, AGENT_FUNCTIONS
import os

client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

# Create the agent
agent = client.conversational_ai.create_agent(
    name=AGENT_CONFIG['name'],
    description=AGENT_CONFIG['description'],
    prompt=AGENT_CONFIG['system_prompt'],
    voice=AGENT_CONFIG['voice']['voice_id'],
    functions=AGENT_FUNCTIONS,
    conversation_config=AGENT_CONFIG['conversation_config']
)

print(f"Agent created! Agent ID: {agent.agent_id}")
# Save this agent_id for frontend configuration
```

#### 3. Function Webhook Configuration

Configure ElevenLabs to call your backend API endpoints for function execution:

**Webhook Base URL**: `http://your-domain.com/api/voice/`

**Function Mapping**:
- `search_patients` → POST `/api/voice/search_patients`
- `get_patient_details` → POST `/api/voice/get_patient_details`
- `get_comparison_stats` → POST `/api/voice/get_comparison_stats`
- `search_by_status` → POST `/api/voice/search_by_status`
- `add_patient_tag` → POST `/api/voice/add_patient_tag`
- `remove_patient_tag` → POST `/api/voice/remove_patient_tag`
- `search_by_tags` → POST `/api/voice/search_by_tags`
- `get_recent_comparisons` → POST `/api/voice/get_recent_comparisons`
- `get_all_tags` → POST `/api/voice/get_all_tags`

### Frontend Setup

#### 1. Install ElevenLabs React SDK

```bash
cd /Users/harringhome/web-automation-vm/web-app/frontend
npm install @eleven labs/react
```

#### 2. Configure Agent ID

Update the frontend component with your agent_id from step 2:

```javascript
const AGENT_ID = "your_agent_id_here";
```

### Available Voice Commands

Users can interact with the voice assistant using natural language:

**Patient Search**:
- "Search for patients named John"
- "Find Danny Handley"
- "Show me patients with the name Smith"

**Patient Details**:
- "Get details for Danny Handley"
- "Tell me about patient John Doe"
- "What's the status of Jane Smith?"

**Statistics**:
- "What are the overall statistics?"
- "Give me stats for the last week"
- "How many notes are complete?"

**Status Search**:
- "Show me patients with missing notes"
- "Find incomplete records"
- "List all complete notes"

**Tag Management**:
- "Add tag urgent to Danny Handley"
- "Tag John Doe as follow-up"
- "Remove tag urgent from Danny Handley"
- "Show me all patients with tag urgent"
- "What tags are available?"

**Recent Data**:
- "Get recent comparison results"
- "Show me the latest comparisons"

### Testing

Test the voice assistant API endpoints:

```bash
# Test search
curl -X POST http://localhost:8000/api/voice/search_patients \
  -H "Content-Type: application/json" \
  -d '{"query": "Danny"}'

# Test stats
curl -X POST http://localhost:8000/api/voice/get_comparison_stats \
  -H "Content-Type: application/json" \
  -d '{"filter_type": "all"}'

# Test tag addition
curl -X POST http://localhost:8000/api/voice/add_patient_tag \
  -H "Content-Type: application/json" \
  -d '{"patient_name": "Danny Handley", "tag_name": "urgent"}'
```

### Security Considerations

1. **API Key Protection**: Never expose your ElevenLabs API key in frontend code
2. **Rate Limiting**: Implement rate limiting on voice endpoints
3. **Authentication**: Add authentication to voice endpoints in production
4. **PHI Protection**: Voice responses avoid speaking full medical notes
5. **Audit Logging**: All voice assistant actions are logged

### Troubleshooting

**Agent Not Responding**:
- Check API key is valid
- Verify agent_id is correct
- Check webhook URLs are accessible
- Review ElevenLabs dashboard logs

**Function Calls Failing**:
- Verify backend endpoints are running
- Check function parameter formatting
- Review FastAPI logs for errors
- Test endpoints directly with curl

**Voice Quality Issues**:
- Try different voice models in AGENT_CONFIG
- Adjust stability and similarity_boost parameters
- Check audio input quality

### Advanced Configuration

#### Custom Voice Selection

Choose from ElevenLabs voice library:

```python
# Available voices:
# EXAVITQu4vr4xnSDxMaL - Sarah (Professional female)
# 21m00Tcm4TlvDq8ikWAM - Rachel (Calm female)
# pNInz6obpgDQGcFmaJgB - Adam (Professional male)
# N2lVS1w4EtoT3dr4eOWO - Callum (Assertive male)

AGENT_CONFIG['voice']['voice_id'] = "your_chosen_voice_id"
```

#### Conversation Timeout

Adjust conversation duration:

```python
AGENT_CONFIG['conversation_config']['turn_timeout'] = 30000  # 30 seconds
AGENT_CONFIG['conversation_config']['agent_max_duration'] = 600000  # 10 minutes
```

#### System Prompt Customization

Modify the system prompt in `elevenlabs_agent.py` to change assistant behavior.

### Production Deployment

1. **Environment Variables**: Use proper secret management
2. **HTTPS**: Ensure webhook URLs use HTTPS
3. **Load Balancing**: Handle concurrent voice sessions
4. **Monitoring**: Track function call success rates
5. **Error Handling**: Implement graceful error responses

### Support

For issues with:
- **ElevenLabs API**: Check [docs.elevenlabs.io](https://docs.elevenlabs.io)
- **Backend Functions**: Review FastAPI logs
- **Frontend Integration**: Check browser console

### License & Credits

- ElevenLabs Conversational AI v3
- Voice: Sarah (ElevenLabs)
- Integration: Custom implementation for medical records management
