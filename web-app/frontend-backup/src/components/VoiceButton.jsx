import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

function VoiceButton({ onToggle, isListening, showHint = true }) {
  const [bars, setBars] = useState([])
  const [particles, setParticles] = useState([])
  const [transcript, setTranscript] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const animationRef = useRef(null)
  const recognitionRef = useRef(null)
  const audioRef = useRef(null)

  // Generate random bar heights for radial audio visualizer
  const generateBars = () => {
    const numBars = 32
    return Array.from({ length: numBars }, (_, i) => ({
      height: isListening
        ? Math.random() * 45 + 35
        : Math.random() * 15 + 8,
      rotation: (360 / numBars) * i,
      delay: i * 0.015
    }))
  }

  // Generate floating particles for glow effect
  const generateParticles = () => {
    if (!isListening) return []
    return Array.from({ length: 12 }, () => ({
      x: (Math.random() - 0.5) * 120,
      y: (Math.random() - 0.5) * 120,
      size: Math.random() * 4 + 2,
      opacity: Math.random() * 0.5 + 0.2,
      duration: Math.random() * 2 + 1
    }))
  }

  // Initialize Web Speech API
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = false
      recognitionRef.current.lang = 'en-US'

      recognitionRef.current.onresult = async (event) => {
        const speechResult = event.results[0][0].transcript
        setTranscript(speechResult)
        console.log('Voice input:', speechResult)

        // Process the voice command
        await processVoiceCommand(speechResult)
      }

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        if (isListening) {
          onToggle() // Stop listening on error
        }
      }

      recognitionRef.current.onend = () => {
        if (isListening && !isProcessing) {
          // Restart if still in listening mode
          recognitionRef.current.start()
        }
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [])

  // Process voice commands through backend
  const processVoiceCommand = async (command) => {
    setIsProcessing(true)
    try {
      // Determine which endpoint to call based on command
      let response

      if (command.toLowerCase().includes('search') || command.toLowerCase().includes('find') || command.toLowerCase().includes('patient')) {
        // Extract patient name from command
        const nameMatch = command.match(/(?:search|find|patient)(?:\s+for)?\s+(.+)/i)
        const query = nameMatch ? nameMatch[1] : command

        response = await axios.post('/api/voice/search_patients', null, {
          params: { query }
        })

        if (response.data.success && response.data.patients.length > 0) {
          const patients = response.data.patients
          const message = `Found ${patients.length} patient${patients.length > 1 ? 's' : ''}: ${patients.map(p => p.name).join(', ')}`
          speak(message)
        } else {
          speak('No patients found matching that query.')
        }
      } else if (command.toLowerCase().includes('stat')) {
        response = await axios.get('/api/voice/get_stats')

        if (response.data.success) {
          const stats = response.data.stats
          const message = `You have ${stats.total_processed} total processed notes, ${stats.complete_in_osmind} complete in Osmind, ${stats.missing_from_osmind} missing, and ${stats.incomplete_in_osmind} incomplete.`
          speak(message)
        }
      } else if (command.toLowerCase().includes('tag') || command.toLowerCase().includes('add')) {
        // Add tag command
        const match = command.match(/(?:add|tag)\s+(.+?)\s+(?:to|for)\s+(.+)/i)
        if (match) {
          const [, tagName, patientName] = match
          response = await axios.post('/api/voice/add_tag', null, {
            params: {
              patient_name: patientName.trim(),
              tag_name: tagName.trim()
            }
          })

          if (response.data.success) {
            speak(`Added tag ${tagName} to ${patientName}`)
          } else {
            speak('Failed to add tag. Please try again.')
          }
        }
      } else if (command.toLowerCase().includes('need') && (command.toLowerCase().includes('done') || command.toLowerCase().includes('do'))) {
        // Notes that need to be done (missing or incomplete)
        const missingResponse = await axios.post('/api/voice/search_by_status', null, {
          params: { status: 'missing' }
        })
        const incompleteResponse = await axios.post('/api/voice/search_by_status', null, {
          params: { status: 'incomplete' }
        })

        const missingCount = missingResponse.data.count || 0
        const incompleteCount = incompleteResponse.data.count || 0
        const totalNeeded = missingCount + incompleteCount

        let message = `You have ${totalNeeded} notes that need to be done. `
        if (missingCount > 0) {
          message += `${missingCount} missing from Osmind. `
        }
        if (incompleteCount > 0) {
          message += `${incompleteCount} incomplete in Osmind.`
        }

        speak(message)
      } else if (command.toLowerCase().includes('fetch') || command.toLowerCase().includes('process')) {
        // Fetch and compare notes with variable days
        // Extract number of days from command (e.g., "fetch notes from last 10 days" or "process 7 days")
        const daysMatch = command.match(/(\d+)\s*day/i)
        const days = daysMatch ? parseInt(daysMatch[1]) : null

        response = await axios.post('/api/voice/fetch_notes', null, {
          params: days ? { days } : {}
        })

        if (response.data.success) {
          const message = response.data.message + '. This will run in the background.'
          speak(message)
        } else {
          speak('Failed to start the fetch process. Please try again.')
        }
      } else {
        speak("I didn't understand that command. Try saying 'search for patient', 'what are the statistics', or 'add tag to patient'.")
      }
    } catch (error) {
      console.error('Voice command error:', error)
      speak('Sorry, I encountered an error processing that command.')
    } finally {
      setIsProcessing(false)
    }
  }

  // Text-to-speech function using ElevenLabs
  const speak = async (text) => {
    try {
      // Stop any currently playing audio
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }

      const apiKey = import.meta.env.VITE_ELEVENLABS_API_KEY
      if (!apiKey) {
        console.error('ElevenLabs API key not found')
        return
      }

      // Use ElevenLabs v3 model with Eve voice (human-like expressive speech)
      const voiceId = 'MF3mGyEYCl7XYWbV9V6O' // Eve voice
      const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
        method: 'POST',
        headers: {
          'Accept': 'audio/mpeg',
          'Content-Type': 'application/json',
          'xi-api-key': apiKey
        },
        body: JSON.stringify({
          text,
          model_id: 'eleven_v3',
          voice_settings: {
            stability: 0.5,
            similarity_boost: 0.75,
            style: 0.5,
            use_speaker_boost: true
          }
        })
      })

      if (!response.ok) {
        throw new Error(`ElevenLabs API error: ${response.statusText}`)
      }

      // Convert response to audio blob
      const audioBlob = await response.blob()
      const audioUrl = URL.createObjectURL(audioBlob)

      // Create and play audio
      const audio = new Audio(audioUrl)
      audioRef.current = audio

      await audio.play()

      // Clean up URL after playback
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl)
        audioRef.current = null
      }

    } catch (error) {
      console.error('ElevenLabs TTS error:', error)
    }
  }

  // Handle listening state changes
  useEffect(() => {
    if (isListening && recognitionRef.current) {
      try {
        recognitionRef.current.start()
      } catch (e) {
        console.error('Failed to start recognition:', e)
      }
    } else if (!isListening && recognitionRef.current) {
      recognitionRef.current.stop()
      // Stop any playing audio
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
      setTranscript('')
    }
  }, [isListening])

  // Animation loop
  useEffect(() => {
    setBars(generateBars())
    setParticles(generateParticles())

    const animate = () => {
      setBars(generateBars())
      if (isListening) {
        setParticles(generateParticles())
      }
      animationRef.current = setTimeout(animate, 80)
    }
    animate()

    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current)
      }
    }
  }, [isListening])

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1.5rem',
      width: '100%'
    }}>
      <button
        onClick={onToggle}
        disabled={isProcessing}
        className="voice-button"
        style={{
          position: 'relative',
          width: '200px',
          height: '200px',
          borderRadius: '50%',
          border: 'none',
          background: isListening
            ? 'radial-gradient(circle, rgba(118, 75, 162, 0.9) 0%, rgba(102, 126, 234, 0.95) 50%, rgba(240, 147, 251, 0.9) 100%)'
            : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          cursor: isProcessing ? 'wait' : 'pointer',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: isListening
            ? '0 0 60px rgba(102, 126, 234, 0.8), 0 0 120px rgba(118, 75, 162, 0.5), inset 0 0 30px rgba(255, 255, 255, 0.1)'
            : '0 10px 40px rgba(102, 126, 234, 0.5)',
          transition: 'all 0.3s ease',
          animation: isListening ? 'pulse 1.5s ease-in-out infinite' : 'none',
          overflow: 'visible',
          opacity: isProcessing ? 0.7 : 1,
          zIndex: 1
        }}
      >
        {/* Microphone Icon */}
        <svg
          width="50"
          height="50"
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.4))',
            transition: 'transform 0.3s ease',
            transform: isListening ? 'scale(1.2)' : 'scale(1)',
            zIndex: 10,
            position: 'relative'
          }}
        >
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>

        {/* Radial Audio Visualizer Bars */}
        <div style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          borderRadius: '50%'
        }}>
          {bars.map((bar, index) => (
            <div
              key={index}
              style={{
                position: 'absolute',
                width: '4px',
                height: `${bar.height}%`,
                background: `linear-gradient(to top,
                  rgba(255, 255, 255, 0.95),
                  rgba(255, 255, 255, ${isListening ? 0.6 : 0.3})
                )`,
                borderRadius: '4px',
                transform: `rotate(${bar.rotation}deg) translateY(-50%)`,
                transformOrigin: 'center 100px',
                top: '50%',
                left: '50%',
                marginLeft: '-2px',
                transition: 'height 0.08s ease',
                boxShadow: isListening
                  ? '0 0 10px rgba(255, 255, 255, 0.9), 0 0 20px rgba(102, 126, 234, 0.7)'
                  : '0 0 6px rgba(255, 255, 255, 0.5)',
                transitionDelay: `${bar.delay}s`
              }}
            />
          ))}
        </div>

        {/* Floating Particles */}
        {isListening && particles.map((particle, index) => (
          <div
            key={index}
            style={{
              position: 'absolute',
              width: `${particle.size}px`,
              height: `${particle.size}px`,
              borderRadius: '50%',
              background: `radial-gradient(circle, rgba(255, 255, 255, ${particle.opacity}) 0%, transparent 70%)`,
              left: `calc(50% + ${particle.x}px)`,
              top: `calc(50% + ${particle.y}px)`,
              animation: `float ${particle.duration}s ease-in-out infinite`,
              boxShadow: `0 0 ${particle.size * 3}px rgba(255, 255, 255, ${particle.opacity * 0.8})`,
              pointerEvents: 'none'
            }}
          />
        ))}

        {/* Ripple effects when listening */}
        {isListening && (
          <>
            <div style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              border: '2px solid rgba(255, 255, 255, 0.4)',
              animation: 'ripple 2s ease-out infinite',
              pointerEvents: 'none'
            }} />
            <div style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              border: '2px solid rgba(255, 255, 255, 0.3)',
              animation: 'ripple 2s ease-out infinite 0.5s',
              pointerEvents: 'none'
            }} />
            <div style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              border: '2px solid rgba(255, 255, 255, 0.2)',
              animation: 'ripple 2s ease-out infinite 1s',
              pointerEvents: 'none'
            }} />
          </>
        )}

        {/* Inner glow */}
        {isListening && (
          <div style={{
            position: 'absolute',
            width: '70%',
            height: '70%',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(255, 255, 255, 0.15) 0%, transparent 70%)',
            animation: 'glow 2s ease-in-out infinite',
            pointerEvents: 'none'
          }} />
        )}
      </button>

      {/* Status Text */}
      <div style={{
        textAlign: 'center',
        color: 'var(--text-primary)',
        fontWeight: '600',
        fontSize: '1.1rem',
        minHeight: '28px'
      }}>
        {isProcessing ? (
          <div style={{ color: '#f093fb' }}>Processing...</div>
        ) : isListening ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            color: '#667eea'
          }}>
            <span style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              animation: 'blink 1.2s ease-in-out infinite',
              boxShadow: '0 0 10px rgba(102, 126, 234, 0.8)'
            }} />
            Listening...
          </div>
        ) : (
          'Click to Talk'
        )}
      </div>

      {/* Transcript Display */}
      {transcript && !isListening && (
        <div style={{
          fontSize: '0.875rem',
          color: 'var(--text-secondary)',
          textAlign: 'center',
          maxWidth: '300px',
          fontStyle: 'italic'
        }}>
          "{transcript}"
        </div>
      )}

      {/* Subtle hint text */}
      {showHint && !isListening && !transcript && (
        <div style={{
          fontSize: '0.875rem',
          color: 'var(--text-muted)',
          textAlign: 'center',
          maxWidth: '220px'
        }}>
          Ask about patients, stats, or manage tags
        </div>
      )}

      {/* CSS Animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% {
            transform: scale(1);
            box-shadow: 0 0 60px rgba(102, 126, 234, 0.8), 0 0 120px rgba(118, 75, 162, 0.5), inset 0 0 30px rgba(255, 255, 255, 0.1);
          }
          50% {
            transform: scale(1.06);
            box-shadow: 0 0 80px rgba(102, 126, 234, 0.9), 0 0 150px rgba(118, 75, 162, 0.6), inset 0 0 40px rgba(255, 255, 255, 0.15);
          }
        }

        @keyframes ripple {
          0% {
            transform: scale(1);
            opacity: 1;
          }
          100% {
            transform: scale(1.8);
            opacity: 0;
          }
        }

        @keyframes blink {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.2;
          }
        }

        @keyframes float {
          0%, 100% {
            transform: translate(0, 0);
          }
          25% {
            transform: translate(5px, -5px);
          }
          50% {
            transform: translate(-3px, -8px);
          }
          75% {
            transform: translate(-5px, -3px);
          }
        }

        @keyframes glow {
          0%, 100% {
            opacity: 0.3;
            transform: scale(1);
          }
          50% {
            opacity: 0.6;
            transform: scale(1.1);
          }
        }

        .voice-button:hover:not(:disabled) {
          transform: scale(1.05) !important;
          box-shadow: 0 15px 50px rgba(102, 126, 234, 0.6) !important;
        }

        .voice-button:active:not(:disabled) {
          transform: scale(0.98) !important;
        }
      `}</style>
    </div>
  )
}

export default VoiceButton
