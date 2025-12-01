import { useState } from 'react'
import axios from 'axios'
import NotePreviewModal from './NotePreviewModal'
import '../App.css'

function NoteDetailModal({ note, onClose, onUploadComplete }) {
  const [copied, setCopied] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [showPreview, setShowPreview] = useState(false)

  if (!note) return null

  const handleCopyNote = () => {
    const noteText = note.note_text || note.raw_note || 'No note text available'
    navigator.clipboard.writeText(noteText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleUploadClick = () => {
    // Show preview modal
    setShowPreview(true)
  }

  const handleConfirmUpload = async (editedNotes) => {
    setShowPreview(false)

    try {
      setUploading(true)

      // Call API endpoint
      const response = await axios.post('/api/upload-to-osmind', {
        patient_names: [note.patient_name]
      })

      // Show success message
      const results = response.data.results
      const successCount = results.success
      const failureCount = results.failure
      const flaggedCount = results.flagged

      let message = `Upload complete!\n\n`
      message += `✅ ${successCount} successful\n`
      if (failureCount > 0) {
        message += `❌ ${failureCount} failed\n`
      }
      if (flaggedCount > 0) {
        message += `⚠️ ${flaggedCount} flagged for review`
      }

      alert(message)

      // Notify parent to refresh data
      if (onUploadComplete) {
        onUploadComplete()
      }

      // Close modal
      onClose()

    } catch (err) {
      console.error('Failed to upload note:', err)
      const errorMsg = err.response?.data?.detail || 'Failed to upload note'
      alert(`Error: ${errorMsg}`)
    } finally {
      setUploading(false)
    }
  }

  const handleCancelPreview = () => {
    setShowPreview(false)
  }

  const getStatusBadge = () => {
    if (note.in_osmind && note.has_freed_content) {
      return <span className="badge badge-success">Complete in Osmind</span>
    } else if (note.in_osmind && !note.has_freed_content) {
      return <span className="badge badge-warning">Incomplete in Osmind</span>
    } else {
      return <span className="badge badge-danger">Missing from Osmind</span>
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h2 style={{ marginBottom: '0.5rem' }}>{note.patient_name}</h2>
            <div style={{ fontSize: '0.9rem', color: '#666' }}>
              Visit Date: {note.visit_date}
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ marginBottom: '0.75rem' }}>Status</h3>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {getStatusBadge()}
              {note.in_freed && <span className="badge" style={{ backgroundColor: '#3b82f6' }}>In Freed.ai</span>}
              {note.is_signed && <span className="badge" style={{ backgroundColor: '#10b981' }}>Signed</span>}
            </div>
          </div>

          {(note.note_text || note.raw_note) && (
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <h3>Note Content</h3>
                <button
                  className="btn btn-secondary"
                  onClick={handleCopyNote}
                  style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
                >
                  {copied ? '✓ Copied!' : 'Copy Note'}
                </button>
              </div>
              <div className="note-content-box">
                {note.note_text || note.raw_note}
              </div>
            </div>
          )}

          {note.cleaned_note && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ marginBottom: '0.75rem' }}>Processed Note (OpenAI)</h3>
              <div className="note-content-box">
                {note.cleaned_note}
              </div>
            </div>
          )}

          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ marginBottom: '0.75rem' }}>Details</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.9rem' }}>
              <div>
                <strong>In Freed.ai:</strong> {note.in_freed ? 'Yes' : 'No'}
              </div>
              <div>
                <strong>In Osmind:</strong> {note.in_osmind ? 'Yes' : 'No'}
              </div>
              <div>
                <strong>Has Freed Content:</strong> {note.has_freed_content ? 'Yes' : 'No'}
              </div>
              <div>
                <strong>Is Signed:</strong> {note.is_signed ? 'Yes' : 'No'}
              </div>
              {note.note_length_freed > 0 && (
                <div>
                  <strong>Note Length:</strong> {note.note_length_freed} characters
                </div>
              )}
              {note.actual_date && (
                <div>
                  <strong>Actual Date:</strong> {note.actual_date}
                </div>
              )}
            </div>
          </div>

          {note.tags && note.tags.length > 0 && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ marginBottom: '0.75rem' }}>Tags</h3>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {note.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="badge"
                    style={{ backgroundColor: tag.color || '#3b82f6' }}
                  >
                    {tag.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
          {!note.in_osmind && (
            <button
              className="btn btn-success"
              onClick={handleUploadClick}
              disabled={uploading}
            >
              {uploading ? 'Uploading...' : 'Upload to Osmind'}
            </button>
          )}
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <NotePreviewModal
          notes={[note]}
          onConfirm={handleConfirmUpload}
          onCancel={handleCancelPreview}
        />
      )}
    </div>
  )
}

export default NoteDetailModal
