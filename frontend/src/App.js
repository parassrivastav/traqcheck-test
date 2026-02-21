import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import './App.css';

const API_BASE = 'http://localhost:5000';

const toTitleCase = (value) => {
  if (!value || value === 'Not found') return value;
  return value
    .toString()
    .toLowerCase()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const getInitials = (name) => {
  if (!name || name === 'Not found') return 'NA';
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
};

const resolveFileUrl = (fileUrl) => {
  if (!fileUrl) return '';
  if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) return fileUrl;
  return `${API_BASE}${fileUrl}`;
};

const isImageFile = (path = '') => {
  const lower = path.toLowerCase();
  return ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'].some((ext) => lower.endsWith(ext));
};

const isPdfFile = (path = '') => path.toLowerCase().endsWith('.pdf');

function App() {
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [documents, setDocuments] = useState([]);
  const [telegramUsername, setTelegramUsername] = useState('');
  const [toasts, setToasts] = useState([]);
  const [isLoadingCandidates, setIsLoadingCandidates] = useState(false);
  const [candidateFetchFailed, setCandidateFetchFailed] = useState(false);
  const [pendingDeleteCandidate, setPendingDeleteCandidate] = useState(null);

  const showToast = (message, type = 'success') => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 3600);
  };

  const showToastSequence = (messages, type = 'success') => {
    (messages || []).forEach((message, index) => {
      setTimeout(() => showToast(message, type), index * 600);
    });
  };

  const getCompanyTimeline = (candidate) => {
    if (!candidate) return [];
    const history = Array.isArray(candidate.company_history) ? candidate.company_history : [];
    const normalized = history
      .filter((item) => item && item.company)
      .map((item) => ({
        company: item.company,
        duration: item.duration || 'Duration not available',
        is_current: Boolean(item.is_current)
      }));

    const currentCompanies = normalized.filter((item) => item.is_current);
    const previousCompanies = normalized.filter((item) => !item.is_current);
    const timeline = [...currentCompanies, ...previousCompanies];

    if (timeline.length > 0) return timeline.slice(0, 3);
    if (candidate.company) {
      return [
        {
          company: candidate.company,
          duration: 'Duration not available',
          is_current: true
        }
      ];
    }
    return [];
  };

  const fetchCandidates = useCallback(async (isSilent = false) => {
    if (!isSilent) {
      setIsLoadingCandidates(true);
    }
    try {
      const response = await axios.get(`${API_BASE}/candidates`);
      console.log('API Call: GET /candidates', {}, 'Response:', response.data);
      setCandidates(response.data);
      setCandidateFetchFailed(false);
    } catch (error) {
      console.error('Error fetching candidates:', error);
      setCandidateFetchFailed(true);
      if (!isSilent) {
        showToast('Could not load dashboard. Retrying automatically...', 'error');
      }
      if (!isSilent) {
        setTimeout(() => fetchCandidates(true), 3000);
      }
    } finally {
      if (!isSilent) {
        setIsLoadingCandidates(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchCandidates();
    const intervalId = setInterval(() => {
      fetchCandidates(true);
    }, 12000);
    return () => clearInterval(intervalId);
  }, [fetchCandidates]);

  useEffect(() => {
    if (!selectedCandidate) {
      setTelegramUsername('');
      return;
    }
    setTelegramUsername(selectedCandidate.telegram_username || selectedCandidate.phone || '');
  }, [selectedCandidate]);

  const onDrop = async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('resume', file);

    try {
      const response = await axios.post(`${API_BASE}/candidates/upload`, formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });
      console.log('API Call: POST /candidates/upload', formData, 'Response:', response.data);
      showToastSequence(
        response.data.messages || [
          'Resume uploaded successfully',
          'Extraction successful',
          'Fields have been saved to DB'
        ],
        'success'
      );
      setUploadProgress(0);
      fetchCandidates();
    } catch (error) {
      console.error('Error uploading resume:', error);
      const backendError = error?.response?.data?.error;
      showToast(backendError || 'Error parsing the resume because extraction failed', 'error');
      setUploadProgress(0);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: '.pdf,.docx' });

  const selectCandidate = async (id) => {
    try {
      const response = await axios.get(`${API_BASE}/candidates/${id}`);
      console.log('API Call: GET /candidates/' + id, {}, 'Response:', response.data);
      setSelectedCandidate(response.data);

      // Fetch documents
      const docsResponse = await axios.get(`${API_BASE}/candidates/${id}/documents`);
      console.log('API Call: GET /candidates/' + id + '/documents', {}, 'Response:', docsResponse.data);
      setDocuments(docsResponse.data);
    } catch (error) {
      console.error('Error fetching candidate:', error);
    }
  };

  const requestDocuments = async () => {
    if (!selectedCandidate) return;
    try {
      const response = await axios.post(`${API_BASE}/candidates/${selectedCandidate.id}/request-documents`);
      console.log('API Call: POST /candidates/' + selectedCandidate.id + '/request-documents', {}, 'Response:', response.data);
      showToast(response.data.message || 'Mr Traqchecker has started document collection', 'success');
    } catch (error) {
      console.error('Error requesting documents:', error);
      showToast(error?.response?.data?.error || 'Error requesting documents', 'error');
    }
  };

  const updateTelegram = async (id) => {
    try {
      const response = await axios.post(`${API_BASE}/candidates/${id}/telegram`, { telegram_username: telegramUsername });
      console.log('API Call: POST /candidates/' + id + '/telegram', { telegram_username: telegramUsername }, 'Response:', response.data);
      showToast('Telegram username updated', 'success');
      setTelegramUsername('');
      fetchCandidates(); // Refresh
    } catch (error) {
      console.error('Error updating telegram:', error);
      showToast('Error updating telegram', 'error');
    }
  };

  const submitDocuments = async (panFile, aadhaarFile) => {
    if (!selectedCandidate || !panFile || !aadhaarFile) return;

    const formData = new FormData();
    formData.append('pan', panFile);
    formData.append('aadhaar', aadhaarFile);

    try {
      const response = await axios.post(
        `${API_BASE}/candidates/${selectedCandidate.id}/submit-documents`,
        formData
      );
      console.log(
        'API Call: POST /candidates/' + selectedCandidate.id + '/submit-documents',
        formData,
        'Response:',
        response.data
      );
      showToast('Documents submitted successfully', 'success');
      const docsResponse = await axios.get(`${API_BASE}/candidates/${selectedCandidate.id}/documents`);
      setDocuments(docsResponse.data);
    } catch (error) {
      console.error('Error submitting documents:', error);
      showToast('Error submitting documents', 'error');
    }
  };

  const requestDeleteCandidate = (candidate) => {
    setPendingDeleteCandidate(candidate);
  };

  const closeDeleteModal = () => {
    setPendingDeleteCandidate(null);
  };

  const confirmDeleteCandidate = async () => {
    if (!pendingDeleteCandidate) return;
    const deletingId = pendingDeleteCandidate.id;

    try {
      await axios.delete(`${API_BASE}/candidates/${deletingId}`);
      showToast('Candidate profile and resume deleted permanently', 'success');
      if (selectedCandidate && selectedCandidate.id === deletingId) {
        setSelectedCandidate(null);
        setDocuments([]);
      }
      setPendingDeleteCandidate(null);
      fetchCandidates(true);
    } catch (error) {
      console.error('Error deleting candidate:', error);
      showToast(error?.response?.data?.error || 'Failed to delete candidate profile', 'error');
    }
  };

  return (
    <div className="App">
      <div className="toast-stack">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.type}`}>
            {toast.message}
          </div>
        ))}
      </div>

      <header className="App-header">
        <h1>Traqcheckjobs.com</h1>
      </header>

      <div className="container">
        <div className="upload-section">
          <h2>Upload Resume</h2>
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
            <input {...getInputProps()} />
            {isDragActive ? (
              <p>Drop the resume here...</p>
            ) : (
              <p>Drag 'n' drop a resume file here, or click to select (PDF/DOCX)</p>
            )}
          </div>
          {uploadProgress > 0 && (
            <div className="progress-bar">
              <div className="progress" style={{ width: `${uploadProgress}%` }}></div>
              <span>{uploadProgress}%</span>
            </div>
          )}
        </div>

        <div className="dashboard">
          <h2>Candidate Dashboard</h2>
          {isLoadingCandidates && <p className="dashboard-meta">Loading candidates...</p>}
          {!isLoadingCandidates && candidateFetchFailed && (
            <p className="dashboard-meta error">Unable to fetch candidates right now. Auto-retrying.</p>
          )}
          {!isLoadingCandidates && !candidateFetchFailed && candidates.length === 0 && (
            <p className="dashboard-meta">No candidates available yet.</p>
          )}
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Company</th>
                <th>Extraction Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map(candidate => (
                <tr key={candidate.id}>
                  <td>{candidate.name}</td>
                  <td>{candidate.email}</td>
                  <td>{candidate.company}</td>
                  <td>{candidate.extraction_status}</td>
                  <td>
                    <button onClick={() => selectCandidate(candidate.id)}>View Profile</button>
                    <button
                      type="button"
                      className="danger-btn"
                      onClick={() => requestDeleteCandidate(candidate)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedCandidate && (
          <div className="profile-view">
            <div className="profile-header">
              <div className="candidate-avatar">{getInitials(selectedCandidate.name)}</div>
              <div className="profile-heading">
                <h2>{toTitleCase(selectedCandidate.name)}</h2>
                <p>{selectedCandidate.designation}</p>
              </div>
            </div>

            <div className="profile-details">
              <div className="detail-item">
                <span className="detail-label">Email</span>
                <span className="detail-value">{selectedCandidate.email}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Phone</span>
                <span className="detail-value">{selectedCandidate.phone}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Current Company</span>
                <span className="detail-value">{selectedCandidate.company}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Confidence Score</span>
                <span className="detail-value">{(selectedCandidate.confidence * 100).toFixed(1)}%</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Telegram</span>
                <span className="detail-value">{selectedCandidate.telegram_username || 'Not set'}</span>
              </div>
            </div>

            <div className="company-timeline">
              <h3>Employment Timeline</h3>
              <div className="timeline-list">
                {getCompanyTimeline(selectedCandidate).length > 0 ? (
                  getCompanyTimeline(selectedCandidate).map((item, index) => (
                    <div key={`${item.company}-${index}`} className="timeline-item">
                      <div className="timeline-item-head">
                        <span className="timeline-company">{item.company}</span>
                        <span className={`timeline-badge ${index === 0 ? 'current' : 'previous'}`}>
                          {index === 0 ? 'Current' : `Previous ${index}`}
                        </span>
                      </div>
                      <p className="timeline-duration">{item.duration || 'Duration not available'}</p>
                    </div>
                  ))
                ) : (
                  <p className="skills-empty">No employment history extracted yet</p>
                )}
              </div>
            </div>

            <div className="profile-skills">
              <h3>Core Skills</h3>
              <div className="skills-list">
                {(selectedCandidate.skills || []).length > 0 ? (
                  selectedCandidate.skills.map((skill, index) => (
                    <span key={`${skill}-${index}`} className="skill-chip">
                      {skill}
                    </span>
                  ))
                ) : (
                  <span className="skills-empty">No skills extracted yet</span>
                )}
              </div>
            </div>

            <div className="profile-actions">
              <input
                type="text"
                placeholder="Enter Telegram username or phone"
                onChange={(e) => setTelegramUsername(e.target.value)}
                value={telegramUsername}
              />
              <button onClick={() => updateTelegram(selectedCandidate.id)}>Update Telegram</button>
            </div>
            <button onClick={requestDocuments}>Ask Mr Traqchecker to Request Documents</button>
          </div>
        )}

        {selectedCandidate && (
          <div className="documents-section">
            <h2>Submitted Documents</h2>
            <div className="document-grid">
              {documents.map((doc) => {
                const fileSrc = resolveFileUrl(doc.file_url);
                return (
                  <div key={doc.id} className="document-card">
                    <div className="document-card-head">
                      <h4>{doc.type}</h4>
                      <span className={`doc-status ${doc.status === 'collected' ? 'ok' : 'pending'}`}>
                        {doc.status} {doc.status === 'collected' ? '✅' : ''}
                      </span>
                    </div>

                    {doc.path ? (
                      <div className="document-preview">
                        {isImageFile(doc.path) && <img src={fileSrc} alt={`${doc.type} document`} loading="lazy" />}
                        {isPdfFile(doc.path) && <iframe src={fileSrc} title={`${doc.type} preview`} />}
                        {!isImageFile(doc.path) && !isPdfFile(doc.path) && (
                          <a href={fileSrc} target="_blank" rel="noreferrer">
                            Open document
                          </a>
                        )}
                      </div>
                    ) : (
                      <p className="skills-empty">No file attached yet</p>
                    )}
                  </div>
                );
              })}
            </div>
            <h3>Submit Documents</h3>
            <DocumentUpload onSubmit={submitDocuments} />
          </div>
        )}
      </div>

      {pendingDeleteCandidate && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="delete-title">
          <div className="confirm-modal">
            <h3 id="delete-title">Delete Candidate Profile?</h3>
            <p>
              This will permanently delete <strong>{pendingDeleteCandidate.name}</strong>, their resume file, and
              related documents from the database.
            </p>
            <div className="modal-actions">
              <button type="button" className="secondary-btn" onClick={closeDeleteModal}>
                Cancel
              </button>
              <button type="button" className="danger-btn" onClick={confirmDeleteCandidate}>
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentUpload({ onSubmit }) {
  const [panFile, setPanFile] = useState(null);
  const [aadhaarFile, setAadhaarFile] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(panFile, aadhaarFile);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>PAN:</label>
        <input type="file" accept="image/*" onChange={(e) => setPanFile(e.target.files[0])} required />
      </div>
      <div>
        <label>Aadhaar:</label>
        <input type="file" accept="image/*" onChange={(e) => setAadhaarFile(e.target.files[0])} required />
      </div>
      <button type="submit">Submit Documents</button>
    </form>
  );
}

export default App;
