import React, { useState, useEffect } from 'react';
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

function App() {
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [documents, setDocuments] = useState([]);
  const [telegramUsername, setTelegramUsername] = useState('');

  useEffect(() => {
    fetchCandidates();
  }, []);

  const fetchCandidates = async () => {
    try {
      const response = await axios.get(`${API_BASE}/candidates`);
      console.log('API Call: GET /candidates', {}, 'Response:', response.data);
      setCandidates(response.data);
    } catch (error) {
      console.error('Error fetching candidates:', error);
    }
  };

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
      alert('Resume uploaded successfully!');
      setUploadProgress(0);
      fetchCandidates();
    } catch (error) {
      console.error('Error uploading resume:', error);
      alert('Error uploading resume');
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
      alert('Document request sent: ' + response.data.message);
    } catch (error) {
      console.error('Error requesting documents:', error);
      alert('Error requesting documents');
    }
  };

  const updateTelegram = async (id) => {
    try {
      const response = await axios.post(`${API_BASE}/candidates/${id}/telegram`, { telegram_username: telegramUsername });
      console.log('API Call: POST /candidates/' + id + '/telegram', { telegram_username: telegramUsername }, 'Response:', response.data);
      alert('Telegram username updated!');
      setTelegramUsername('');
      fetchCandidates(); // Refresh
    } catch (error) {
      console.error('Error updating telegram:', error);
      alert('Error updating telegram');
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
      alert('Documents submitted successfully!');
      const docsResponse = await axios.get(`${API_BASE}/candidates/${selectedCandidate.id}/documents`);
      setDocuments(docsResponse.data);
    } catch (error) {
      console.error('Error submitting documents:', error);
      alert('Error submitting documents');
    }
  };

  return (
    <div className="App">
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
                placeholder="Enter Telegram username"
                onChange={(e) => setTelegramUsername(e.target.value)}
                value={telegramUsername}
              />
              <button onClick={() => updateTelegram(selectedCandidate.id)}>Update Telegram</button>
            </div>
            <button onClick={requestDocuments}>Request Documents</button>
          </div>
        )}

        {selectedCandidate && (
          <div className="documents-section">
            <h2>Submitted Documents</h2>
            <ul>
              {documents.map((doc, index) => (
                <li key={index}>{doc.type}: {doc.status} {doc.status === 'collected' && '✅'}</li>
              ))}
            </ul>
            <h3>Submit Documents</h3>
            <DocumentUpload onSubmit={submitDocuments} />
          </div>
        )}
      </div>
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
