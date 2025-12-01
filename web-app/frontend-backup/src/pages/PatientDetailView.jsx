import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import NoteDetailModal from '../components/NoteDetailModal'
import NotePreviewModal from '../components/NotePreviewModal'

function PatientDetailView() {
  const { patientName } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [patientHistory, setPatientHistory] = useState([])
  const [statusChanges, setStatusChanges] = useState([])
  const [patientTags, setPatientTags] = useState([])
  const [selectedNote, setSelectedNote] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [notesToPreview, setNotesToPreview] = useState([])
  const [notification, setNotification] = useState('')
  const [newTagName, setNewTagName] = useState('')
  const [showTagInput, setShowTagInput] = useState(false)

  useEffect(() => {
    if (patientName) {
      fetchPatientData()
    }
  }, [patientName])

  const fetchPatientData = async () => {
    try {
      setLoading(true)

      // Fetch patient history, status changes, and tags in parallel
      const [historyRes, statusRes, tagsRes] = await Promise.all([
        axios.get(`/api/patients/${encodeURIComponent(patientName)}/history`),
        axios.get(`/api/patients/${encodeURIComponent(patientName)}/status-changes`),
        axios.get(`/api/patients/${encodeURIComponent(patientName)}/tags`)
      ])

      setPatientHistory(historyRes.data.history || [])
      setStatusChanges(statusRes.data.changes || [])
      setPatientTags(tagsRes.data.tags || [])
      setError(null)
    } catch (err) {
      console.error('Failed to fetch patient data:', err)
      setError('Failed to load patient information')
    } finally {
      setLoading(false)
    }
  }

  const handleBackClick = () => {
    navigate('/comparison')
  }

  const handleNoteClick = (note) => {
    setSelectedNote(note)
    setModalOpen(true)
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    setSelectedNote(null)
  }

  const handleUploadNote = (note) => {
    setNotesToPreview([note])
    setShowPreviewModal(true)
  }

  const handleConfirmUpload = async (editedNotes) => {
    setShowPreviewModal(false)

    try {
      setNotification(`Uploading note to Osmind...`)

      const response = await axios.post('/api/upload-to-osmind', {
        patient_names: [patientName]
      })

      const results = response.data.results
      let message = `Upload complete! ${results.success} successful`
      if (results.failure > 0) message += `, ${results.failure} failed`
      if (results.flagged > 0) message += `, ${results.flagged} flagged`

      setNotification(message)
      setTimeout(() => setNotification(''), 5000)

      // Refresh patient data
      fetchPatientData()
    } catch (err) {
      console.error('Failed to upload note:', err)
      setNotification(`Error: ${err.response?.data?.detail || 'Failed to upload note'}`)
      setTimeout(() => setNotification(''), 5000)
    }
  }

  const handleCancelPreview = () => {
    setShowPreviewModal(false)
    setNotesToPreview([])
  }

  const handleAddTag = async () => {
    if (!newTagName.trim()) return

    try {
      await axios.post(`/api/patients/${encodeURIComponent(patientName)}/tags`, null, {
        params: {
          tag_name: newTagName.trim(),
          color: '#3b82f6'
        }
      })

      setNewTagName('')
      setShowTagInput(false)
      setNotification('Tag added successfully')
      setTimeout(() => setNotification(''), 3000)

      // Refresh tags
      const tagsRes = await axios.get(`/api/patients/${encodeURIComponent(patientName)}/tags`)
      setPatientTags(tagsRes.data.tags || [])
    } catch (err) {
      console.error('Failed to add tag:', err)
      setNotification('Failed to add tag')
      setTimeout(() => setNotification(''), 3000)
    }
  }

  const handleRemoveTag = async (tagName) => {
    try {
      await axios.delete(`/api/patients/${encodeURIComponent(patientName)}/tags/${encodeURIComponent(tagName)}`)

      setNotification('Tag removed successfully')
      setTimeout(() => setNotification(''), 3000)

      // Refresh tags
      const tagsRes = await axios.get(`/api/patients/${encodeURIComponent(patientName)}/tags`)
      setPatientTags(tagsRes.data.tags || [])
    } catch (err) {
      console.error('Failed to remove tag:', err)
      setNotification('Failed to remove tag')
      setTimeout(() => setNotification(''), 3000)
    }
  }

  const getStatusBadgeClass = (status) => {
    if (status === 'complete') return 'badge badge-success'
    if (status === 'incomplete') return 'badge badge-warning'
    return 'badge badge-danger'
  }

  const getStatusLabel = (note) => {
    if (note.in_osmind && note.has_freed_content) return 'complete'
    if (note.in_osmind && !note.has_freed_content) return 'incomplete'
    return 'missing'
  }

  const getStatusBadge = (note) => {
    const status = getStatusLabel(note)
    if (status === 'complete') return <span className="badge badge-success">Complete</span>
    if (status === 'incomplete') return <span className="badge badge-warning">Incomplete</span>
    return <span className="badge badge-danger">Missing</span>
  }

  // Get the latest note for header display
  const latestNote = patientHistory.length > 0 ? patientHistory[0] : null
  const latestStatus = latestNote ? getStatusLabel(latestNote) : 'unknown'

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading patient information...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">{error}</div>
        <button className="btn btn-primary" onClick={handleBackClick}>
          ← Back to Comparison
        </button>
      </div>
    )
  }

  return (
    <div className="patient-detail-view">
      {/* Notification */}
      {notification && (
        <div className="notification-banner">
          {notification}
        </div>
      )}

      {/* Back Button */}
      <button
        className="btn btn-secondary"
        onClick={handleBackClick}
        style={{ marginBottom: '1.5rem' }}
      >
        ← Back to Comparison
      </button>

      {/* Patient Header */}
      <div className="patient-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div>
            <h1 style={{ marginBottom: '0.5rem' }}>{patientName}</h1>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <span className={getStatusBadgeClass(latestStatus)}>
                Latest Status: {latestStatus.charAt(0).toUpperCase() + latestStatus.slice(1)}
              </span>
              <span className="badge" style={{ backgroundColor: 'var(--accent-blue)' }}>
                {patientHistory.length} Note{patientHistory.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {latestNote && !latestNote.in_osmind && (
              <button
                className="btn btn-success"
                onClick={() => handleUploadNote(latestNote)}
              >
                📤 Upload Latest Note
              </button>
            )}
          </div>
        </div>

        {/* Tags Section */}
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <strong>Tags:</strong>
            <button
              className="add-tag-btn"
              onClick={() => setShowTagInput(!showTagInput)}
              style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
            >
              + Add Tag
            </button>
          </div>

          {showTagInput && (
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <input
                type="text"
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
                placeholder="Enter tag name..."
                className="form-control"
                style={{ maxWidth: '200px' }}
              />
              <button className="btn btn-primary" onClick={handleAddTag}>Add</button>
              <button className="btn btn-secondary" onClick={() => setShowTagInput(false)}>Cancel</button>
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {patientTags.length === 0 && !showTagInput && (
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No tags yet</span>
            )}
            {patientTags.map((tag, index) => (
              <span
                key={index}
                className="badge"
                style={{
                  backgroundColor: tag.color || '#3b82f6',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem'
                }}
              >
                {tag.name}
                <button
                  onClick={() => handleRemoveTag(tag.name)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'inherit',
                    cursor: 'pointer',
                    padding: '0',
                    marginLeft: '0.25rem',
                    fontSize: '1.1rem',
                    lineHeight: '1'
                  }}
                  title="Remove tag"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Status Changes Timeline */}
      {statusChanges.length > 0 && (
        <div className="status-changes-section" style={{ marginTop: '2rem' }}>
          <h2 style={{ marginBottom: '1rem' }}>Status History</h2>
          <div className="timeline">
            {statusChanges.map((change, index) => (
              <div key={index} className="timeline-item">
                <div className="timeline-marker" style={{
                  backgroundColor: change.new_status === 'complete' ? '#10b981' :
                                 change.new_status === 'incomplete' ? '#f59e0b' : '#ef4444'
                }}></div>
                <div className="timeline-content">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <span className={getStatusBadgeClass(change.old_status)}>
                        {change.old_status}
                      </span>
                      <span style={{ margin: '0 0.5rem' }}>→</span>
                      <span className={getStatusBadgeClass(change.new_status)}>
                        {change.new_status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      {new Date(change.changed_at).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    Comparison ID: {change.comparison_id}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Note History */}
      <div className="note-history-section" style={{ marginTop: '2rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>Note History</h2>

        {patientHistory.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <div className="empty-state-title">No notes found</div>
            <div className="empty-state-description">
              No historical notes available for this patient.
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {patientHistory.map((note, index) => (
              <div
                key={index}
                className="note-card"
                onClick={() => handleNoteClick(note)}
                style={{ cursor: 'pointer' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <strong style={{ fontSize: '1.1rem' }}>
                        Visit: {note.visit_date || 'Unknown Date'}
                      </strong>
                      {getStatusBadge(note)}
                      {note.is_signed && (
                        <span className="badge" style={{ backgroundColor: '#10b981' }}>Signed</span>
                      )}
                    </div>

                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                      Comparison: {new Date(note.comparison_timestamp).toLocaleString()}
                    </div>

                    {note.note_text && (
                      <div style={{
                        fontSize: '0.9rem',
                        color: 'var(--text-secondary)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        marginTop: '0.5rem'
                      }}>
                        {note.note_text}
                      </div>
                    )}
                  </div>

                  <div style={{ fontSize: '1.5rem', color: 'var(--text-secondary)' }}>›</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      {modalOpen && (
        <NoteDetailModal
          note={selectedNote}
          onClose={handleCloseModal}
          onUploadComplete={fetchPatientData}
        />
      )}
      {showPreviewModal && (
        <NotePreviewModal
          notes={notesToPreview}
          onConfirm={handleConfirmUpload}
          onCancel={handleCancelPreview}
        />
      )}
    </div>
  )
}

export default PatientDetailView
