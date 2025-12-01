import { useState, useEffect } from 'react'
import '../App.css'

function NotePreviewModal({ notes, onConfirm, onCancel }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [editedNotes, setEditedNotes] = useState([])

  useEffect(() => {
    // Initialize edited notes with original content
    if (notes && notes.length > 0) {
      setEditedNotes(notes.map(note => ({
        ...note,
        editedContent: note.note_text || note.raw_note || note.cleaned_note || ''
      })))
    }
  }, [notes])

  if (!notes || notes.length === 0 || editedNotes.length === 0) return null

  const currentNote = editedNotes[currentIndex]
  const isLastNote = currentIndex === editedNotes.length - 1
  const isFirstNote = currentIndex === 0

  const handleContentChange = (e) => {
    const updatedNotes = [...editedNotes]
    updatedNotes[currentIndex].editedContent = e.target.value
    setEditedNotes(updatedNotes)
  }

  const handleNext = () => {
    if (!isLastNote) {
      setCurrentIndex(currentIndex + 1)
    }
  }

  const handlePrevious = () => {
    if (!isFirstNote) {
      setCurrentIndex(currentIndex - 1)
    }
  }

  const handleConfirm = () => {
    // Pass edited notes back to parent
    onConfirm(editedNotes)
  }

  const characterCount = currentNote.editedContent?.length || 0
  const wordCount = currentNote.editedContent?.trim().split(/\s+/).filter(w => w.length > 0).length || 0

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '900px' }}
      >
        <div className="modal-header">
          <div>
            <h2 style={{ marginBottom: '0.5rem' }}>
              Review Note Before Upload
              {editedNotes.length > 1 && (
                <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginLeft: '1rem' }}>
                  ({currentIndex + 1} of {editedNotes.length})
                </span>
              )}
            </h2>
            <div style={{ fontSize: '0.9rem', color: '#666' }}>
              Patient: <strong>{currentNote.patient_name}</strong> | Visit Date: <strong>{currentNote.visit_date}</strong>
            </div>
          </div>
          <button className="modal-close" onClick={onCancel}>×</button>
        </div>

        <div className="modal-body">
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <label style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                Note Content
              </label>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {characterCount.toLocaleString()} characters | {wordCount.toLocaleString()} words
              </div>
            </div>
            <textarea
              value={currentNote.editedContent}
              onChange={handleContentChange}
              style={{
                width: '100%',
                minHeight: '400px',
                padding: '1rem',
                fontSize: '0.9rem',
                fontFamily: 'monospace',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                resize: 'vertical',
                lineHeight: '1.6'
              }}
              placeholder="Enter note content..."
            />
            <div style={{
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              marginTop: '0.5rem',
              fontStyle: 'italic'
            }}>
              💡 You can edit the note text before uploading. Changes will only affect this upload.
            </div>
          </div>

          {/* Show warning if note is empty */}
          {!currentNote.editedContent?.trim() && (
            <div style={{
              padding: '1rem',
              background: 'rgba(234, 179, 8, 0.1)',
              border: '1px solid rgba(234, 179, 8, 0.3)',
              borderRadius: '8px',
              marginBottom: '1rem'
            }}>
              <strong style={{ color: '#eab308' }}>⚠️ Warning:</strong> Note content is empty
            </div>
          )}

          {/* Original metadata */}
          <div style={{
            padding: '1rem',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            fontSize: '0.85rem'
          }}>
            <div style={{ marginBottom: '0.5rem', fontWeight: 600 }}>Note Details:</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <div><strong>In Freed:</strong> {currentNote.in_freed ? 'Yes' : 'No'}</div>
              <div><strong>In Osmind:</strong> {currentNote.in_osmind ? 'Yes' : 'No'}</div>
              <div><strong>Has Content:</strong> {currentNote.has_freed_content ? 'Yes' : 'No'}</div>
              <div><strong>Is Signed:</strong> {currentNote.is_signed ? 'Yes' : 'No'}</div>
            </div>
          </div>
        </div>

        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {/* Navigation buttons for bulk uploads */}
            {editedNotes.length > 1 && (
              <>
                <button
                  className="btn btn-secondary"
                  onClick={handlePrevious}
                  disabled={isFirstNote}
                  style={{ opacity: isFirstNote ? 0.5 : 1 }}
                >
                  ← Previous
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={handleNext}
                  disabled={isLastNote}
                  style={{ opacity: isLastNote ? 0.5 : 1 }}
                >
                  Next →
                </button>
              </>
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button
              className="btn btn-success"
              onClick={handleConfirm}
              disabled={!currentNote.editedContent?.trim()}
              style={{ opacity: !currentNote.editedContent?.trim() ? 0.5 : 1 }}
            >
              {editedNotes.length > 1 ? `Confirm & Upload ${editedNotes.length} Notes` : 'Confirm & Upload'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NotePreviewModal
