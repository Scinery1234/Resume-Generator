import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { resumeAPI } from '../services/api';
import { downloadBlob } from '../utils/fileDownload';
import './MyResumesPage.css';

const MyResumesPage = () => {
    const navigate = useNavigate();
    const [resumes, setResumes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const userId = localStorage.getItem('userId');
    const token = localStorage.getItem('token');

    useEffect(() => {
        if (!token || !userId) {
            navigate('/auth');
            return;
        }
        loadResumes();
    }, [userId, token, navigate]);

    const loadResumes = async () => {
        try {
            setLoading(true);
            setError('');
            const response = await resumeAPI.getAll(userId);
            if (response.status === 'success') {
                setResumes(response.resumes || []);
            } else {
                setError('Failed to load resumes');
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load resumes. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async (resume) => {
        try {
            let blob, filename;
            if (resume.filename) {
                blob = await resumeAPI.downloadByFilename(resume.filename);
                filename = resume.filename;
            } else if (resume.id) {
                blob = await resumeAPI.download(resume.id);
                filename = resume.name || 'resume.docx';
            } else {
                setError('No download source available for this resume');
                return;
            }
            downloadBlob(blob, filename);
        } catch (err) {
            setError(err.message || 'Download failed. Please try again.');
        }
    };

    const handleDelete = async (resumeId) => {
        if (!window.confirm('Are you sure you want to delete this resume?')) {
            return;
        }
        try {
            await resumeAPI.delete(resumeId);
            loadResumes(); // Reload list
        } catch (err) {
            alert('Failed to delete resume. Please try again.');
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('userId');
        window.dispatchEvent(new Event('storage'));
        navigate('/');
    };

    if (loading) {
        return (
            <div className="my-resumes-page">
                <div className="my-resumes-container">
                    <div className="loading">Loading your resumes...</div>
                </div>
            </div>
        );
    }

    return (
        <div className="my-resumes-page">
            <nav className="my-resumes-nav">
                <div className="my-resumes-nav__inner">
                    <span className="my-resumes-nav__logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
                        ResumeGen
                    </span>
                    <div className="my-resumes-nav__actions">
                        <button className="btn-secondary" onClick={() => navigate('/wizard')}>
                            + Create New Resume
                        </button>
                        <button className="btn-secondary" onClick={handleLogout}>
                            Sign Out
                        </button>
                    </div>
                </div>
            </nav>

            <div className="my-resumes-container">
                <h1>My Resumes</h1>
                
                {error && (
                    <div className="error-message" role="alert">
                        {error}
                    </div>
                )}

                {resumes.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state__icon">📄</div>
                        <h2>No resumes yet</h2>
                        <p>Create your first resume to get started!</p>
                        <button className="btn-primary" onClick={() => navigate('/wizard')}>
                            Create Resume
                        </button>
                    </div>
                ) : (
                    <div className="resumes-grid">
                        {resumes.map((resume) => (
                            <div key={resume.id} className="resume-card">
                                <div className="resume-card__header">
                                    <h3>{resume.name || 'Untitled Resume'}</h3>
                                    {resume.created_at && (
                                        <span className="resume-card__date">
                                            {new Date(resume.created_at).toLocaleDateString()}
                                        </span>
                                    )}
                                </div>
                                {resume.contact_info && (
                                    <div className="resume-card__info">
                                        <p>{resume.contact_info}</p>
                                    </div>
                                )}
                                <div className="resume-card__actions">
                                    <button 
                                        className="btn-primary" 
                                        onClick={() => handleDownload(resume)}
                                    >
                                        ⬇ Download
                                    </button>
                                    <button 
                                        className="btn-secondary" 
                                        onClick={() => handleDelete(resume.id)}
                                    >
                                        🗑 Delete
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default MyResumesPage;
