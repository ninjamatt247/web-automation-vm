import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

// TODO: Install @elevenlabs/react package: npm install @elevenlabs/react
// TODO: Set your ElevenLabs agent ID (get from setup process)
const AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID || 'YOUR_AGENT_ID_HERE'
const API_KEY = import.meta.env.VITE_ELEVENLABS_API_KEY || ''

function VoiceAssistant() {
  const [isOpen, setIsOpen] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState([])
  const [status, setStatus] = useState('idle') // idle, connecting, active, error

  // Simplified version without ElevenLabs SDK (for now)
  // Once SDK is installed, replace with actual ElevenLabs Conversation component

  const handleToggle = () => {
    setIsOpen(!isOpen)
    if (!isOpen) {
      setStatus('idle')
      setTranscript([])
    }
  }

  const addToTranscript = (speaker, message) => {
    setTranscript(prev => [...prev, { speaker, message, timestamp: new Date() }])
  }

  // Example function to test backend API
  const testVoiceAPI = async (query) => {
    try {
      const response = await axios.post('/api/voice/search_patients', null, {
        params: { query }
      })
      return response.data
    } catch (error) {
      console.error('Voice API error:', error)
      return null
    }
  }

  return (
    <>
      {/* Floating Voice Button */}
      <button
        onClick={handleToggle}
        className="voice-assistant-toggle"
        aria-label="Voice Assistant"
        style={{
          position: 'fixed',
          bottom: '2rem',
          right: '2rem',
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%)',
          border: 'none',
          cursor: 'pointer',
          boxShadow: '0 8px 24px rgba(14, 115, 204, 0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.75rem',
          color: 'white',
          transition: 'all 0.3s ease',
          zIndex: 1000
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.1)'
          e.currentTarget.style.boxShadow = '0 12px 32px rgba(14, 115, 204, 0.5)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = '0 8px 24px rgba(14, 115, 204, 0.4)'
        }}
      >
        {isListening ? '🎤' : '🎙️'}
      </button>

      {/* Voice Assistant Panel */}
      {isOpen && (
        <div
          className="voice-assistant-panel"
          style={{
            position: 'fixed',
            bottom: '6rem',
            right: '2rem',
            width: '400px',
            maxHeight: '600px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 999,
            overflow: 'hidden',
            animation: 'slideUp 0.3s ease'
          }}
        >
          {/* Header */}
          <div style={{
            padding: '1.5rem',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <h3 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '1.125rem', fontWeight: 600 }}>
                Voice Assistant
              </h3>
              <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                {status === 'idle' && 'Ready to help'}
                {status === 'connecting' && 'Connecting...'}
                {status === 'active' && 'Listening...'}
                {status === 'error' && 'Connection error'}
              </p>
            </div>
            <button
              onClick={handleToggle}
              style={{
                background: 'transparent',
                border: 'none',
                fontSize: '1.5rem',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: 0,
                width: '32px',
                height: '32px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              ×
            </button>
          </div>

          {/* Transcript/Conversation */}
          <div style={{
            flex: 1,
            overflow: 'auto',
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem'
          }}>
            {transcript.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '3rem 1rem',
                color: 'var(--text-muted)'
              }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎙️</div>
                <p style={{ margin: 0, fontSize: '0.875rem' }}>
                  Click the microphone to start talking
                </p>
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Try: "Search for patients named John"
                </p>
              </div>
            ) : (
              transcript.map((item, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    justifyContent: item.speaker === 'user' ? 'flex-end' : 'flex-start'
                  }}
                >
                  <div
                    style={{
                      maxWidth: '80%',
                      padding: '0.75rem 1rem',
                      borderRadius: '12px',
                      background: item.speaker === 'user'
                        ? 'linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%)'
                        : 'var(--bg-tertiary)',
                      color: item.speaker === 'user' ? 'white' : 'var(--text-primary)',
                      fontSize: '0.875rem',
                      lineHeight: 1.5
                    }}
                  >
                    {item.message}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Controls */}
          <div style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            gap: '0.75rem',
            alignItems: 'center'
          }}>
            <button
              className="btn btn-primary"
              onClick={() => {
                if (status === 'idle') {
                  setStatus('active')
                  setIsListening(true)
                  addToTranscript('assistant', 'Hello! How can I help you today?')
                } else {
                  setStatus('idle')
                  setIsListening(false)
                }
              }}
              style={{ flex: 1 }}
            >
              {isListening ? 'Stop' : 'Start Conversation'}
            </button>
            {transcript.length > 0 && (
              <button
                className="btn btn-secondary"
                onClick={() => setTranscript([])}
                style={{
                  padding: '0.625rem 1rem',
                  fontSize: '0.875rem'
                }}
              >
                Clear
              </button>
            )}
          </div>

          {/* Setup Notice */}
          {!API_KEY && (
            <div style={{
              padding: '0.75rem 1.5rem',
              background: 'rgba(245, 158, 11, 0.1)',
              borderTop: '1px solid rgba(245, 158, 11, 0.3)',
              fontSize: '0.75rem',
              color: 'var(--accent-amber)',
              lineHeight: 1.4
            }}>
              ⚠️ Voice assistant not configured. See VOICE_ASSISTANT_SETUP.md for setup instructions.
            </div>
          )}
        </div>
      )}

      {/* Mobile Responsive Overlay */}
      {isOpen && (
        <style>{`
          @media (max-width: 640px) {
            .voice-assistant-panel {
              right: 1rem !important;
              left: 1rem !important;
              bottom: 5rem !important;
              width: auto !important;
              max-height: 70vh !important;
            }
          }
        `}</style>
      )}
    </>
  )
}

export default VoiceAssistant
