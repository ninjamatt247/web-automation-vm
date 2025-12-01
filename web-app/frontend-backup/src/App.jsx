import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import NotesView from './pages/NotesView'
import OsmindNotesView from './pages/OsmindNotesView'
import ComparisonView from './pages/ComparisonView'
import ProcessNote from './pages/ProcessNote'
import PatientDetailView from './pages/PatientDetailView'
import VoiceAssistant from './components/VoiceAssistant'
import './App.css'

function Navigation() {
  const location = useLocation()

  const isActive = (path) => {
    return location.pathname === path ? 'nav-link active' : 'nav-link'
  }

  return (
    <nav className="navbar">
      <div className="nav-brand">
        <h1>Medical Notes Processor</h1>
      </div>
      <div className="nav-links">
        <Link to="/" className={isActive('/')}>Dashboard</Link>
        <Link to="/notes" className={isActive('/notes')}>Freed Notes</Link>
        <Link to="/osmind-notes" className={isActive('/osmind-notes')}>Osmind Notes</Link>
        <Link to="/comparison" className={isActive('/comparison')}>Comparison</Link>
        <Link to="/process" className={isActive('/process')}>Process</Link>
      </div>
    </nav>
  )
}

function App() {
  return (
    <Router>
      <div className="app">
        <Navigation />
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/notes" element={<NotesView />} />
            <Route path="/osmind-notes" element={<OsmindNotesView />} />
            <Route path="/comparison" element={<ComparisonView />} />
            <Route path="/patient/:patientName" element={<PatientDetailView />} />
            <Route path="/process" element={<ProcessNote />} />
          </Routes>
        </main>
        <VoiceAssistant />
      </div>
    </Router>
  )
}

export default App
