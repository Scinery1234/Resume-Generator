import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import './WizardPage.css';
import { resumeAPI } from '../services/api';

const MAX_FILES = 5;
const ACCEPTED_TYPES = ['.pdf', '.docx', '.doc', '.txt'];
const ACCEPTED_MIME = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'text/plain',
];

function fileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    if (ext === 'pdf')  return '📄';
    if (ext === 'docx' || ext === 'doc') return '📝';
    return '📃';
}

// ── Result view ──────────────────────────────────────────────────────────────
function ResultView({ result, onReset }) {
    const [downloading, setDownloading]   = useState(false);
    const [downloadError, setDownloadError] = useState('');

    const handleDownload = async () => {
        setDownloading(true);
        setDownloadError('');
        try {
            const blob = await resumeAPI.downloadByFilename(result.filename);
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href     = url;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch {
            setDownloadError('Download failed. Please try again.');
        } finally {
            setDownloading(false);
        }
    };

    return (
        <div className="gen-result">
            <div className="gen-result__header">
                <span className="gen-result__tick">✓</span>
                <div>
                    <h2>Your resume is ready!</h2>
                    <p>AI-generated and tailored to your job description. Download your .docx below.</p>
                </div>
            </div>

            {result.preview_html && (
                <div className="gen-preview-wrap">
                    <iframe
                        title="Resume Preview"
                        srcDoc={result.preview_html}
                        className="gen-preview-frame"
                        sandbox="allow-same-origin"
                    />
                </div>
            )}

            <div className="gen-result__actions">
                <button className="btn-download" onClick={handleDownload} disabled={downloading}>
                    {downloading ? 'Downloading…' : '⬇ Download .docx'}
                </button>
                <button className="btn-reset" onClick={onReset}>
                    ↺ Generate Another
                </button>
            </div>
            {downloadError && (
                <div className="gen-error" role="alert">{downloadError}</div>
            )}
        </div>
    );
}

// ── Main generator page ───────────────────────────────────────────────────────
const WizardPage = () => {
    const navigate      = useNavigate();
    const fileInputRef  = useRef(null);
    const [files, setFiles]             = useState([]);
    const [jobDesc, setJobDesc]         = useState('');
    const [isDragging, setIsDragging]   = useState(false);
    const [loading, setLoading]         = useState(false);
    const [error, setError]             = useState('');
    const [result, setResult]           = useState(null);

    // ── File handling ────────────────────────────────────────────────────────
    const addFiles = useCallback((newFiles) => {
        const accepted = Array.from(newFiles).filter(f => {
            const ext = '.' + f.name.split('.').pop().toLowerCase();
            return ACCEPTED_TYPES.includes(ext) || ACCEPTED_MIME.includes(f.type);
        });
        setFiles(prev => {
            const combined = [...prev, ...accepted];
            return combined.slice(0, MAX_FILES);
        });
    }, []);

    const removeFile = (index) => setFiles(prev => prev.filter((_, i) => i !== index));

    const onDragOver  = (e) => { e.preventDefault(); setIsDragging(true);  };
    const onDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
    const onDrop      = (e) => {
        e.preventDefault();
        setIsDragging(false);
        addFiles(e.dataTransfer.files);
    };
    const onFileInput = (e) => addFiles(e.target.files);

    // ── Generate ─────────────────────────────────────────────────────────────
    const handleGenerate = async () => {
        setError('');
        if (files.length === 0) {
            setError('Please upload at least one supporting document (e.g. your old resume).');
            return;
        }
        if (!jobDesc.trim()) {
            setError('Please paste the job description before generating.');
            return;
        }

        setLoading(true);
        try {
            const data = await resumeAPI.generate(files, jobDesc);
            setResult(data);
        } catch (err) {
            let msg;
            if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
                msg = 'The request timed out. The server may be starting up — please wait a moment and try again.';
            } else if (!err.response) {
                msg = 'Could not reach the server. Please check your connection and try again.';
            } else {
                msg = err.response?.data?.detail || 'Generation failed. Please try again.';
            }
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    // ── Result screen ─────────────────────────────────────────────────────────
    if (result) {
        return (
            <div className="gen-page">
                <nav className="gen-nav">
                    <button className="gen-nav__back" onClick={() => setResult(null)}>← Back</button>
                    <span className="gen-nav__logo">ResumeGen</span>
                    <span />
                </nav>
                <ResultView result={result} onReset={() => setResult(null)} />
            </div>
        );
    }

    // ── Input screen ──────────────────────────────────────────────────────────
    return (
        <div className="gen-page">
            {/* Nav */}
            <nav className="gen-nav">
                <button className="gen-nav__back" onClick={() => navigate('/')}>← Home</button>
                <span className="gen-nav__logo">ResumeGen</span>
                <span />
            </nav>

            {/* Hero */}
            <div className="gen-hero">
                <h1>Generate Your Resume with AI</h1>
                <p>
                    Upload up to {MAX_FILES} supporting documents (old resumes, LinkedIn exports, cover
                    letters) and paste the job description — our AI does the rest in seconds.
                </p>
            </div>

            {/* Main panels */}
            <div className="gen-panels">

                {/* Left — Upload */}
                <div className="gen-panel">
                    <h2 className="gen-panel__title">
                        <span className="gen-panel__icon">📁</span>
                        Supporting Documents
                        <span className="gen-panel__hint">up to {MAX_FILES} files</span>
                    </h2>

                    {/* Drop zone */}
                    <div
                        className={`gen-dropzone${isDragging ? ' gen-dropzone--active' : ''}${files.length >= MAX_FILES ? ' gen-dropzone--full' : ''}`}
                        onDragOver={onDragOver}
                        onDragLeave={onDragLeave}
                        onDrop={onDrop}
                        onClick={() => files.length < MAX_FILES && fileInputRef.current?.click()}
                        role="button"
                        aria-label="Upload documents"
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            accept=".pdf,.docx,.doc,.txt"
                            style={{ display: 'none' }}
                            onChange={onFileInput}
                        />
                        {files.length < MAX_FILES ? (
                            <>
                                <div className="gen-dropzone__icon">⬆</div>
                                <p className="gen-dropzone__label">
                                    {isDragging ? 'Drop files here' : 'Drop files here or click to browse'}
                                </p>
                                <p className="gen-dropzone__sub">PDF, DOCX, DOC, TXT accepted</p>
                            </>
                        ) : (
                            <p className="gen-dropzone__label">Maximum {MAX_FILES} files reached</p>
                        )}
                    </div>

                    {/* File list */}
                    {files.length > 0 && (
                        <ul className="gen-filelist">
                            {files.map((f, i) => (
                                <li key={i} className="gen-filelist__item">
                                    <span className="gen-filelist__icon">{fileIcon(f.name)}</span>
                                    <span className="gen-filelist__name" title={f.name}>{f.name}</span>
                                    <button
                                        className="gen-filelist__remove"
                                        onClick={() => removeFile(i)}
                                        aria-label={`Remove ${f.name}`}
                                    >
                                        ✕
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}

                    <p className="gen-panel__tip">
                        Tip: uploading your most recent resume and the target job description gives the
                        best results.
                    </p>
                </div>

                {/* Right — Job description */}
                <div className="gen-panel">
                    <h2 className="gen-panel__title">
                        <span className="gen-panel__icon">📋</span>
                        Job Description
                        <span className="gen-panel__hint">paste in full</span>
                    </h2>
                    <textarea
                        className="gen-jd-textarea"
                        placeholder="Paste the full job description here. The AI will tailor your resume specifically to match this role's requirements, keywords, and responsibilities."
                        value={jobDesc}
                        onChange={e => setJobDesc(e.target.value)}
                        rows={18}
                    />
                    <p className="gen-panel__tip">
                        Tip: include the complete posting — responsibilities, requirements, and preferred
                        qualifications — for the most targeted resume.
                    </p>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="gen-error" role="alert">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* Generate button */}
            <div className="gen-actions">
                <button
                    className="gen-btn-generate"
                    onClick={handleGenerate}
                    disabled={loading}
                >
                    {loading ? (
                        <>
                            <span className="gen-spinner" aria-hidden="true" />
                            Generating your resume…
                        </>
                    ) : (
                        <>✨ Generate My Resume</>
                    )}
                </button>
                {loading && (
                    <p className="gen-loading-note">
                        This usually takes 15–30 seconds. The AI is reading your documents and crafting
                        a tailored resume.
                    </p>
                )}
            </div>
        </div>
    );
};

export default WizardPage;
