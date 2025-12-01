import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import NoteDetailModal from '../components/NoteDetailModal'
import NotePreviewModal from '../components/NotePreviewModal'

function ComparisonView() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('all')
  const [filterType, setFilterType] = useState('all')
  const [copyNotification, setCopyNotification] = useState('')
  const [showTagInput, setShowTagInput] = useState(null)
  const [newTagName, setNewTagName] = useState('')
  const [selectedNote, setSelectedNote] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedItems, setSelectedItems] = useState([])
  const [bulkTagName, setBulkTagName] = useState('')
  const [showBulkTagInput, setShowBulkTagInput] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [notesToPreview, setNotesToPreview] = useState([])

  useEffect(() => {
    fetchComparison()
  }, [filterType])

  const fetchComparison = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({ filter_type: filterType })
      const response = await axios.get(`/api/comparison/details?${params}`)
      setData(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to load comparison results')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleCardClick = (item, event) => {
    // Don't open modal if clicking on tag elements or checkbox
    if (event.target.closest('.tag') ||
        event.target.closest('.add-tag-btn') ||
        event.target.closest('.selection-checkbox')) {
      return
    }

    setSelectedNote(item)
    setModalOpen(true)
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    setSelectedNote(null)
  }

  const handleCheckboxChange = (patientName, event) => {
    event.stopPropagation()
    setSelectedItems(prev => {
      if (prev.includes(patientName)) {
        return prev.filter(name => name !== patientName)
      } else {
        return [...prev, patientName]
      }
    })
  }

  const handleSelectAll = (items) => {
    const allNames = items.map(item => item.patient_name)
    setSelectedItems(allNames)
  }

  const handleDeselectAll = () => {
    setSelectedItems([])
  }

  const handleBulkTag = async () => {
    if (!bulkTagName.trim() || selectedItems.length === 0) return

    try {
      for (const patientName of selectedItems) {
        await axios.post(`/api/patients/${encodeURIComponent(patientName)}/tags`, null, {
          params: {
            tag_name: bulkTagName.trim(),
            color: '#3b82f6'
          }
        })
      }
      setBulkTagName('')
      setShowBulkTagInput(false)
      setSelectedItems([])
      fetchComparison()
      setCopyNotification(`Tag added to ${selectedItems.length} patients`)
      setTimeout(() => setCopyNotification(''), 3000)
    } catch (err) {
      console.error('Failed to add bulk tags:', err)
      setCopyNotification('Failed to add tags')
      setTimeout(() => setCopyNotification(''), 3000)
    }
  }

  const handleBulkExport = () => {
    if (selectedItems.length === 0) return

    const allItems = [...(data?.complete || []), ...(data?.missing || []), ...(data?.incomplete || [])]
    const selectedData = allItems.filter(item => selectedItems.includes(item.patient_name))

    const csvContent = [
      ['Patient Name', 'Visit Date', 'Status', 'In Freed', 'In Osmind', 'Has Content', 'Signed'].join(','),
      ...selectedData.map(item => [
        item.patient_name,
        item.visit_date,
        item.in_osmind && item.has_freed_content ? 'Complete' : item.in_osmind ? 'Incomplete' : 'Missing',
        item.in_freed ? 'Yes' : 'No',
        item.in_osmind ? 'Yes' : 'No',
        item.has_freed_content ? 'Yes' : 'No',
        item.is_signed ? 'Yes' : 'No'
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `comparison-export-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)

    setCopyNotification(`Exported ${selectedItems.length} records`)
    setTimeout(() => setCopyNotification(''), 3000)
  }

  const handleBulkUpload = () => {
    if (selectedItems.length === 0) return

    // Get full note data for selected items
    const allItems = [...(data?.complete || []), ...(data?.missing || []), ...(data?.incomplete || [])]
    const selectedNotes = allItems.filter(item => selectedItems.includes(item.patient_name))

    // Show preview modal
    setNotesToPreview(selectedNotes)
    setShowPreviewModal(true)
  }

  const handleConfirmUpload = async (editedNotes) => {
    // Close preview modal
    setShowPreviewModal(false)

    try {
      // Show loading state
      setCopyNotification(`Uploading ${editedNotes.length} note(s) to Osmind...`)

      // Prepare notes with edited content
      const notesToUpload = editedNotes.map(note => ({
        patient_name: note.patient_name,
        visit_date: note.visit_date,
        cleaned_note: note.editedContent
      }))

      // Call API endpoint with edited notes
      const response = await axios.post('/api/upload-to-osmind', {
        patient_names: editedNotes.map(n => n.patient_name)
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

      // Clear selections and refresh data
      setSelectedItems([])
      fetchComparison()
      setCopyNotification('Upload complete!')
      setTimeout(() => setCopyNotification(''), 3000)

    } catch (err) {
      console.error('Failed to upload notes:', err)
      const errorMsg = err.response?.data?.detail || 'Failed to upload notes'
      setCopyNotification(`Error: ${errorMsg}`)
      setTimeout(() => setCopyNotification(''), 5000)
    }
  }

  const handleCancelPreview = () => {
    setShowPreviewModal(false)
    setNotesToPreview([])
  }

  const applyFilters = (items) => {
    let filtered = [...items]

    // Apply search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim()
      filtered = filtered.filter(item =>
        item.patient_name.toLowerCase().includes(query) ||
        item.visit_date.toLowerCase().includes(query)
      )
    }

    return filtered
  }

  const handleClearFilters = () => {
    setSearchQuery('')
    setStatusFilter('all')
    setFilterType('all')
  }

  const handleAddTag = async (patientName, index) => {
    if (!newTagName.trim()) return

    try {
      await axios.post(`/api/patients/${encodeURIComponent(patientName)}/tags`, null, {
        params: {
          tag_name: newTagName.trim(),
          color: '#3b82f6'
        }
      })
      setNewTagName('')
      setShowTagInput(null)
      fetchComparison() // Refresh data
      setCopyNotification(`Tag added successfully`)
      setTimeout(() => setCopyNotification(''), 3000)
    } catch (err) {
      console.error('Failed to add tag:', err)
      setCopyNotification('Failed to add tag')
      setTimeout(() => setCopyNotification(''), 3000)
    }
  }

  const handleRemoveTag = async (patientName, tagName) => {
    try {
      await axios.delete(`/api/patients/${encodeURIComponent(patientName)}/tags/${encodeURIComponent(tagName)}`)
      fetchComparison() // Refresh data
      setCopyNotification(`Tag removed`)
      setTimeout(() => setCopyNotification(''), 3000)
    } catch (err) {
      console.error('Failed to remove tag:', err)
      setCopyNotification('Failed to remove tag')
      setTimeout(() => setCopyNotification(''), 3000)
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

  const renderItems = (items, status) => {
    // Apply filters
    const filteredItems = applyFilters(items)

    if (filteredItems.length === 0) {
      return (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <div className="empty-state-title">
            {items.length === 0 ? 'No notes in this category' : 'No results found'}
          </div>
          <div className="empty-state-description">
            {items.length === 0 ? (
              <>
                {status === 'complete' && 'No complete notes found for this time period.'}
                {status === 'missing' && 'Great! All notes are in Osmind.'}
                {status === 'incomplete' && 'No incomplete notes found.'}
              </>
            ) : (
              'Try adjusting your search or filters.'
            )}
          </div>
        </div>
      )
    }

    const selectedInCategory = filteredItems.filter(item => selectedItems.includes(item.patient_name)).length

    return (
      <>
        {/* Selection Controls */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={() => handleSelectAll(filteredItems)}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            Select All ({filteredItems.length})
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleDeselectAll}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            Deselect All
          </button>
          {selectedInCategory > 0 && (
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              {selectedInCategory} selected
            </span>
          )}
        </div>

        <div className="comparison-grid">
          {filteredItems.map((item, index) => (
          <div
            key={index}
            className={`comparison-item ${status}`}
            onClick={(e) => handleCardClick(item, e)}
            style={{
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              position: 'relative'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            {/* Checkbox */}
            <div className="selection-checkbox" style={{ position: 'absolute', top: '1rem', right: '1rem' }}>
              <input
                type="checkbox"
                checked={selectedItems.includes(item.patient_name)}
                onChange={(e) => handleCheckboxChange(item.patient_name, e)}
                onClick={(e) => e.stopPropagation()}
                style={{
                  width: '18px',
                  height: '18px',
                  cursor: 'pointer',
                  accentColor: 'var(--accent-blue)'
                }}
              />
            </div>

            <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)', paddingRight: '2rem' }}>
              <Link
                to={`/patient/${encodeURIComponent(item.patient_name)}`}
                className="patient-name-link"
                onClick={(e) => e.stopPropagation()}
              >
                {item.patient_name}
              </Link>
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Date: {item.visit_date}
            </div>
            <div style={{ marginTop: '0.5rem' }}>
              <span className={`badge badge-${status === 'complete' ? 'success' : status === 'incomplete' ? 'warning' : 'danger'}`}>
                {status === 'complete' ? 'Complete' : status === 'incomplete' ? 'Incomplete' : 'Missing'}
              </span>
            </div>

            {/* Tags Section */}
            {item.tags && item.tags.length > 0 && (
              <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                {item.tags.map((tag, tagIndex) => (
                  <span
                    key={tagIndex}
                    className="tag"
                    style={{
                      backgroundColor: tag.color || '#3b82f6',
                      color: 'white',
                      padding: '0.15rem 0.4rem',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem'
                    }}
                  >
                    {tag.name}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRemoveTag(item.patient_name, tag.name)
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'white',
                        cursor: 'pointer',
                        padding: '0',
                        fontSize: '0.8rem',
                        fontWeight: 'bold'
                      }}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Add Tag Button */}
            <div style={{ marginTop: '0.5rem' }}>
              {showTagInput === index ? (
                <div style={{ display: 'flex', gap: '0.25rem' }} onClick={(e) => e.stopPropagation()}>
                  <input
                    type="text"
                    value={newTagName}
                    onChange={(e) => setNewTagName(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleAddTag(item.patient_name, index)
                      }
                    }}
                    placeholder="Tag name"
                    style={{
                      flex: 1,
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.75rem',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
                    }}
                    autoFocus
                  />
                  <button
                    onClick={() => handleAddTag(item.patient_name, index)}
                    style={{
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.75rem',
                      backgroundColor: '#3b82f6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Add
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setShowTagInput(null)
                      setNewTagName('')
                    }}
                    style={{
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.75rem',
                      backgroundColor: '#6c757d',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  className="add-tag-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    setShowTagInput(index)
                    setNewTagName('')
                  }}
                  style={{
                    padding: '0.25rem 0.5rem',
                    fontSize: '0.75rem',
                    backgroundColor: '#f8f9fa',
                    color: '#666',
                    border: '1px dashed #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  + Add Tag
                </button>
              )}
            </div>

            <div style={{
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              marginTop: '0.5rem',
              fontStyle: 'italic'
            }}>
              Click for details
            </div>
          </div>
        ))}
      </div>
      </>
    )
  }

  return (
    <div className="page">
      <h1 className="page-title">Freed.ai vs Osmind Comparison</h1>

      {copyNotification && (
        <div className={`toast ${copyNotification.includes('Failed') || copyNotification.includes('failed') ? 'toast-error' : 'toast-success'}`}>
          <span style={{ fontSize: '1.25rem' }}>
            {copyNotification.includes('Failed') || copyNotification.includes('failed') ? '❌' : '✅'}
          </span>
          <span>{copyNotification}</span>
        </div>
      )}

      {/* Bulk Action Toolbar */}
      {selectedItems.length > 0 && (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '1rem 1.5rem',
          marginBottom: '1.5rem',
          display: 'flex',
          gap: '1rem',
          alignItems: 'center',
          flexWrap: 'wrap',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
        }}>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
            {selectedItems.length} item{selectedItems.length > 1 ? 's' : ''} selected
          </div>
          <div style={{ flex: 1 }} />
          {!showBulkTagInput ? (
            <button
              className="btn btn-secondary"
              onClick={() => setShowBulkTagInput(true)}
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
            >
              🏷️ Add Tag
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                value={bulkTagName}
                onChange={(e) => setBulkTagName(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') handleBulkTag()
                }}
                placeholder="Tag name"
                style={{
                  padding: '0.5rem 1rem',
                  fontSize: '0.875rem',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  background: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                  minWidth: '150px'
                }}
                autoFocus
              />
              <button
                className="btn btn-primary"
                onClick={handleBulkTag}
                style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
              >
                Add
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setShowBulkTagInput(false)
                  setBulkTagName('')
                }}
                style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
              >
                Cancel
              </button>
            </div>
          )}
          <button
            className="btn btn-secondary"
            onClick={handleBulkExport}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            📊 Export CSV
          </button>
          <button
            className="btn btn-success"
            onClick={handleBulkUpload}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            ⬆️ Upload to Osmind
          </button>
        </div>
      )}

      {/* Filters Section */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Search Input */}
          <div style={{ flex: '1 1 250px', minWidth: '250px' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search by patient name or date..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                fontSize: '0.875rem',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)'
              }}
            />
          </div>

          {/* Status Filter */}
          <div style={{ flex: '0 0 auto' }}>
            <label className="form-label" style={{ marginBottom: 0, marginRight: '0.5rem', display: 'inline' }}>
              Status:
            </label>
            <select
              className="form-control"
              value={statusFilter}
              onChange={(e) => {
                const newStatus = e.target.value
                setStatusFilter(newStatus)
                setActiveTab(newStatus)  // Sync with tab selection
              }}
              style={{
                minWidth: '150px',
                width: 'auto',
                display: 'inline-block'
              }}
            >
              <option value="all">All Statuses</option>
              <option value="complete">Complete</option>
              <option value="missing">Missing</option>
              <option value="incomplete">Incomplete</option>
            </select>
          </div>

          {/* Date Filter */}
          <div style={{ flex: '0 0 auto' }}>
            <label className="form-label" style={{ marginBottom: 0, marginRight: '0.5rem', display: 'inline' }}>
              Date:
            </label>
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
          </div>

          {/* Clear Filters Button */}
          {(searchQuery || statusFilter !== 'all' || filterType !== 'all') && (
            <button
              className="btn btn-secondary"
              onClick={handleClearFilters}
              style={{ padding: '0.75rem 1rem', fontSize: '0.875rem' }}
            >
              Clear Filters
            </button>
          )}

          {/* Refresh Button */}
          <button
            className="btn btn-primary"
            onClick={fetchComparison}
            style={{ padding: '0.75rem 1rem', fontSize: '0.875rem', marginLeft: 'auto' }}
          >
            Refresh
          </button>
        </div>
      </div>

      {data && (
        <>
          <div className="stats-grid">
            <div className="stat-card success">
              <h3>Complete</h3>
              <div className="stat-value">{data.counts.complete}</div>
            </div>
            <div className="stat-card danger">
              <h3>Missing</h3>
              <div className="stat-value">{data.counts.missing}</div>
            </div>
            <div className="stat-card warning">
              <h3>Incomplete</h3>
              <div className="stat-value">{data.counts.incomplete}</div>
            </div>
            <div className="stat-card">
              <h3>Total</h3>
              <div className="stat-value">{data.counts.total}</div>
            </div>
          </div>

          <div className="tabs">
            <button
              className={`tab ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('all')
                setStatusFilter('all')
              }}
            >
              All ({data.counts.total})
            </button>
            <button
              className={`tab ${activeTab === 'complete' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('complete')
                setStatusFilter('complete')
              }}
            >
              Complete ({data.counts.complete})
            </button>
            <button
              className={`tab ${activeTab === 'missing' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('missing')
                setStatusFilter('missing')
              }}
            >
              Missing ({data.counts.missing})
            </button>
            <button
              className={`tab ${activeTab === 'incomplete' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('incomplete')
                setStatusFilter('incomplete')
              }}
            >
              Incomplete ({data.counts.incomplete})
            </button>
          </div>

          {activeTab === 'all' && (
            <>
              <h3 style={{ marginBottom: '1rem', color: 'var(--accent-emerald)' }}>Complete in Osmind</h3>
              {renderItems(data.complete, 'complete')}

              <h3 style={{ marginTop: '2rem', marginBottom: '1rem', color: 'var(--accent-red)' }}>Missing from Osmind</h3>
              {renderItems(data.missing, 'missing')}

              <h3 style={{ marginTop: '2rem', marginBottom: '1rem', color: 'var(--accent-amber)' }}>Incomplete in Osmind</h3>
              {renderItems(data.incomplete, 'incomplete')}
            </>
          )}

          {activeTab === 'complete' && renderItems(data.complete, 'complete')}
          {activeTab === 'missing' && renderItems(data.missing, 'missing')}
          {activeTab === 'incomplete' && renderItems(data.incomplete, 'incomplete')}
        </>
      )}

      {modalOpen && <NoteDetailModal note={selectedNote} onClose={handleCloseModal} onUploadComplete={fetchComparison} />}
      {showPreviewModal && <NotePreviewModal notes={notesToPreview} onConfirm={handleConfirmUpload} onCancel={handleCancelPreview} />}
    </div>
  )
}

export default ComparisonView
