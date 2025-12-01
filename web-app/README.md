# Medical Notes Processing Web App

A web application for viewing, comparing, and processing medical notes from Freed.ai to Osmind EHR.

## Features

- **Dashboard**: View statistics about processed notes
- **Notes View**: Browse all processed notes with original and cleaned versions
- **Comparison View**: Compare Freed.ai notes with Osmind status
- **Process Note**: Process individual notes with OpenAI APSO formatting

## Technology Stack

### Backend
- FastAPI (Python web framework)
- Uvicorn (ASGI server)
- Integration with existing note processing infrastructure

### Frontend
- React 18
- Vite (build tool)
- Axios (HTTP client)
- React Router (routing)

## Setup Instructions

### Backend Setup

1. Install backend dependencies:
```bash
cd web-app/backend
source ../../.venv/bin/activate
pip install -r requirements.txt
```

2. Start the backend server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### Frontend Setup

1. Install frontend dependencies:
```bash
cd web-app/frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The web app will be available at `http://localhost:5173`

## Running Both Servers

### Terminal 1 (Backend):
```bash
cd ~/web-automation-vm
source .venv/bin/activate
cd web-app/backend
python main.py
```

### Terminal 2 (Frontend):
```bash
cd ~/web-automation-vm/web-app/frontend
npm run dev
```

## API Endpoints

- `GET /api/notes` - Get all processed notes
- `GET /api/notes/{note_id}` - Get a specific note
- `POST /api/process` - Process a note with OpenAI
- `GET /api/stats` - Get processing statistics
- `GET /api/comparison` - Get comparison results
- `GET /api/comparison/details` - Get detailed comparison data

## Features Breakdown

### Dashboard
- Real-time statistics
- Quick action buttons
- Visual status cards

### Notes View
- List all processed notes
- View original and cleaned versions
- Expandable note details

### Comparison View
- Tabbed interface (All, Complete, Missing, Incomplete)
- Color-coded status badges
- Filterable results

### Process Note
- Side-by-side view
- Real-time processing
- Copy to clipboard functionality
- APSO format validation indicators

## Notes Processing

The application enforces APSO format (Assessment, Plan, Recommendations, Counseling, Subjective, Objective) and removes AI language to ensure clinical authenticity.

### APSO Format Features:
- ✅ Correct section order
- ✅ No AI language
- ✅ Provider voice (first person)
- ✅ Medically accurate
- ✅ Legally compliant

## Development

### Build for Production

Frontend:
```bash
cd web-app/frontend
npm run build
```

The production build will be in `web-app/frontend/dist`

## Environment

- Backend: Python 3.9+
- Frontend: Node.js 18+
- OpenAI API key required (configured in parent project)
