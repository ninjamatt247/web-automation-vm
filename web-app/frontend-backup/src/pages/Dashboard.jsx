import { useState, useEffect } from 'react'
import axios from 'axios'
import VoiceButton from '../components/VoiceButton'

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterType, setFilterType] = useState('all')
  const [isVoiceActive, setIsVoiceActive] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [fetchingFreed, setFetchingFreed] = useState(false)
  const [fetchingOsmind, setFetchingOsmind] = useState(false)
  const [fetchMessage, setFetchMessage] = useState(null)

  useEffect(() => {
    fetchStats()
  }, [filterType])

  const fetchStats = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({ filter_type: filterType })
      const response = await axios.get(`/api/stats?${params}`)
      setStats(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to load statistics')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleFetchFromFreed = async () => {
    try {
      setFetchingFreed(true)
      setFetchMessage(null)
      const response = await axios.post('/api/fetch-from-freed', { days: 7 })
      setFetchMessage({
        type: 'success',
        text: response.data.message
      })
      // Refresh stats after a delay
      setTimeout(() => {
        fetchStats()
      }, 5000)
    } catch (err) {
      setFetchMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to fetch from Freed.ai'
      })
      console.error(err)
    } finally {
      setFetchingFreed(false)
    }
  }

  const handleFetchFromOsmind = async () => {
    try {
      setFetchingOsmind(true)
      setFetchMessage(null)
      const response = await axios.post('/api/fetch-from-osmind')
      setFetchMessage({
        type: 'success',
        text: response.data.message
      })
      // Refresh stats after a delay
      setTimeout(() => {
        fetchStats()
      }, 5000)
    } catch (err) {
      setFetchMessage({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to fetch from Osmind'
      })
      console.error(err)
    } finally {
      setFetchingOsmind(false)
    }
  }

  if (loading) {
    return (
      <div className="page">
        <div className="loading">
          <div className="spinner"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page">
        <div className="error">{error}</div>
      </div>
    )
  }

  return (
    <div className="page">
      <h1 className="page-title">Dashboard</h1>

      <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <label className="form-label" style={{ marginBottom: 0 }}>Filter by:</label>
        <select
          className="form-control"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          style={{
            minWidth: '150px',
            width: 'auto',
            display: 'inline-block'
          }}
        >
          <option value="all">All Time</option>
          <option value="week">Last Week</option>
          <option value="month">Last Month</option>
        </select>
        <button
          className="btn btn-primary"
          onClick={fetchStats}
          style={{ marginLeft: 'auto' }}
        >
          Refresh
        </button>
      </div>

      {stats && (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Processed Notes</h3>
              <div className="stat-value">{stats.total_processed || 0}</div>
            </div>

            {stats.total_in_freed !== undefined && (
              <div className="stat-card success">
                <h3>Notes in Freed.ai</h3>
                <div className="stat-value">{stats.total_in_freed}</div>
              </div>
            )}

            {stats.complete_in_osmind !== undefined && (
              <div className="stat-card success">
                <h3>Complete in Osmind</h3>
                <div className="stat-value">{stats.complete_in_osmind}</div>
              </div>
            )}

            {stats.missing_from_osmind !== undefined && (
              <div className="stat-card danger">
                <h3>Missing from Osmind</h3>
                <div className="stat-value">{stats.missing_from_osmind}</div>
              </div>
            )}

            {stats.incomplete_in_osmind !== undefined && (
              <div className="stat-card warning">
                <h3>Incomplete in Osmind</h3>
                <div className="stat-value">{stats.incomplete_in_osmind}</div>
              </div>
            )}

            {stats.to_process !== undefined && (
              <div className="stat-card">
                <h3>Notes to Process</h3>
                <div className="stat-value">{stats.to_process}</div>
              </div>
            )}
          </div>

          {stats.comparison_timestamp && (
            <div style={{ marginTop: '1rem', color: '#666', fontSize: '0.9rem' }}>
              Last comparison: {new Date(stats.comparison_timestamp).toLocaleString()}
            </div>
          )}

          {/* Voice Assistant Button */}
          <div style={{
            marginTop: '3rem',
            display: 'flex',
            justifyContent: 'center'
          }}>
            <button
              className="btn btn-primary"
              onClick={() => setIsModalOpen(true)}
              style={{
                padding: '1rem 2rem',
                fontSize: '1.1rem',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)'
              }}
            >
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
              Open Voice Assistant
            </button>
          </div>

          {fetchMessage && (
            <div style={{
              marginTop: '1.5rem',
              padding: '1rem',
              borderRadius: '8px',
              background: fetchMessage.type === 'success' ? '#d4edda' : '#f8d7da',
              color: fetchMessage.type === 'success' ? '#155724' : '#721c24',
              border: `1px solid ${fetchMessage.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`
            }}>
              {fetchMessage.text}
            </div>
          )}

          <div style={{ marginTop: '2rem' }}>
            <h2 style={{ marginBottom: '1rem' }}>Data Sync</h2>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
              <button
                className="btn btn-primary"
                onClick={handleFetchFromFreed}
                disabled={fetchingFreed}
                style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                {fetchingFreed ? (
                  <>
                    <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></div>
                    Fetching from Freed.ai...
                  </>
                ) : (
                  <>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Pull from Freed.ai
                  </>
                )}
              </button>
              <button
                className="btn btn-primary"
                onClick={handleFetchFromOsmind}
                disabled={fetchingOsmind}
                style={{
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                {fetchingOsmind ? (
                  <>
                    <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></div>
                    Fetching from Osmind...
                  </>
                ) : (
                  <>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Verify Osmind Data
                  </>
                )}
              </button>
            </div>

            <h2 style={{ marginBottom: '1rem' }}>Quick Actions</h2>
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={() => window.location.href = '/notes'}>
                View All Notes
              </button>
              <button className="btn btn-primary" onClick={() => window.location.href = '/comparison'}>
                View Comparison
              </button>
              <button className="btn btn-success" onClick={() => window.location.href = '/process'}>
                Process New Note
              </button>
            </div>
          </div>
        </>
      )}

      {/* Voice Assistant Modal */}
      {isModalOpen && (
        <>
          {/* Backdrop */}
          <div
            onClick={() => {
              setIsModalOpen(false)
              setIsVoiceActive(false)
            }}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              animation: 'fadeIn 0.3s ease'
            }}
          >
            {/* Modal Content */}
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                position: 'relative',
                width: '90%',
                maxWidth: '700px',
                maxHeight: '85vh',
                overflowY: 'auto',
                padding: '2.5rem',
                background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '20px',
                border: '1px solid rgba(102, 126, 234, 0.2)',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '1.5rem',
                animation: 'slideUp 0.3s ease'
              }}
            >
              {/* Close Button */}
              <button
                onClick={() => {
                  setIsModalOpen(false)
                  setIsVoiceActive(false)
                }}
                style={{
                  position: 'absolute',
                  top: '1.5rem',
                  right: '1.5rem',
                  background: 'transparent',
                  border: 'none',
                  fontSize: '1.75rem',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  width: '40px',
                  height: '40px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  e.currentTarget.style.color = 'var(--text-primary)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.color = 'var(--text-secondary)'
                }}
              >
                ×
              </button>

              {/* Header */}
              <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
                <h2 style={{
                  margin: 0,
                  fontSize: '2rem',
                  fontWeight: '700',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}>
                  Voice Assistant
                </h2>
                <p style={{
                  margin: '0.75rem 0 0 0',
                  color: 'var(--text-secondary)',
                  fontSize: '1.05rem',
                  lineHeight: '1.5'
                }}>
                  Talk to your AI assistant to search patients, check stats, and manage data
                </p>
              </div>

              {/* Voice Button */}
              <VoiceButton
                isListening={isVoiceActive}
                onToggle={() => setIsVoiceActive(!isVoiceActive)}
                showHint={false}
              />

              {/* Example Commands */}
              {isVoiceActive && (
                <div style={{
                  padding: '1.75rem',
                  background: 'rgba(102, 126, 234, 0.08)',
                  borderRadius: '16px',
                  border: '1px solid rgba(102, 126, 234, 0.15)',
                  maxWidth: '550px',
                  width: '100%',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
                }}>
                  <div style={{
                    color: 'var(--text-secondary)',
                    fontSize: '0.875rem',
                    textAlign: 'center'
                  }}>
                    <strong style={{
                      color: 'var(--text-primary)',
                      display: 'block',
                      marginBottom: '1rem',
                      fontSize: '1rem',
                      fontWeight: '600'
                    }}>
                      Try saying:
                    </strong>
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.5rem',
                      fontSize: '0.9rem'
                    }}>
                      <span style={{ padding: '0.25rem' }}>"Search for patients named John"</span>
                      <span style={{ padding: '0.25rem' }}>"What are the statistics?"</span>
                      <span style={{ padding: '0.25rem' }}>"What notes need to be done?"</span>
                      <span style={{ padding: '0.25rem' }}>"Fetch notes from last 10 days"</span>
                      <span style={{ padding: '0.25rem' }}>"Add urgent tag to Danny Handley"</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Modal Animations */}
          <style>{`
            @keyframes fadeIn {
              from {
                opacity: 0;
              }
              to {
                opacity: 1;
              }
            }

            @keyframes slideUp {
              from {
                opacity: 0;
                transform: translateY(30px);
              }
              to {
                opacity: 1;
                transform: translateY(0);
              }
            }
          `}</style>
        </>
      )}
    </div>
  )
}

export default Dashboard
