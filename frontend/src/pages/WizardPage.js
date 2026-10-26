import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './WizardPage.css';
import { resumeAPI } from '../services/api';
import { downloadBlob } from '../utils/fileDownload';

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

// ── Generation mode badge ────────────────────────────────────────────────────
const MODE_LABELS = {
    customisation: { text: 'Tailored to Job Description', color: '#0369a1' },
    minimal_jd:    { text: 'Role-Signal Mode',            color: '#0891b2' },
    general:       { text: 'General Resume',              color: '#64748b' },
};

function GenerationModeBadge({ mode }) {
    const info = MODE_LABELS[mode] || { text: 'Generated', color: '#64748b' };
    return (
        <span className="gen-mode-badge" style={{ background: info.color }}>
            {info.text}
        </span>
    );
}

// ── Result view ──────────────────────────────────────────────────────────────
const GUEST_MAX_EDITS = 3;
const PAID_MAX_EDITS  = 50;

function ResultView({ result, onReset, onUpdate }) {
    const [downloading, setDownloading] = useState(false);
    const [downloadError, setDownloadError] = useState('');
    const [editPrompt, setEditPrompt] = useState('');
    const [editing, setEditing] = useState(false);
    const [editError, setEditError] = useState('');
    const [promptInfo, setPromptInfo] = useState(null);
    const [isEditingInline, setIsEditingInline] = useState(false);
    const [jsonText, setJsonText] = useState(() => JSON.stringify(result.data || {}, null, 2));

    const userId = localStorage.getItem('userId');
    const token  = localStorage.getItem('token');
    const isGuest = !token || !userId;

    // Load prompt info for logged-in users; update JSON when result data changes
    useEffect(() => {
        if (!isGuest && userId && result.resume_id) {
            resumeAPI.getPromptInfo(userId)
                .then(info => setPromptInfo(info))
                .catch(err => console.error('Failed to load prompt info:', err));
        }
        if (result.data) {
            setJsonText(JSON.stringify(result.data, null, 2));
        }
    }, [isGuest, userId, result.resume_id, result.data]);

    // Derive remaining edits for display
    const editsUsed      = promptInfo ? promptInfo.prompt_count      : 0;
    const editsMax       = isGuest ? GUEST_MAX_EDITS : (promptInfo ? promptInfo.max_prompts : GUEST_MAX_EDITS);
    const editsRemaining = isGuest
        ? (promptInfo ? promptInfo.remaining_prompts : GUEST_MAX_EDITS)
        : (promptInfo ? promptInfo.remaining_prompts : null);
    const editsExhausted = editsRemaining !== null && editsRemaining <= 0;

    const handleDownload = async () => {
        setDownloading(true);
        setDownloadError('');
        try {
            if (!result.resume_id) {
                throw new Error('Resume ID missing — please regenerate your resume.');
            }
            const blob = await resumeAPI.download(result.resume_id);
            const safeName = (result.data?.name || 'resume').replace(/\s+/g, '_');
            downloadBlob(blob, `${safeName}.docx`);
        } catch (err) {
            setDownloadError(err.message || 'Download failed. Please try again.');
        } finally {
            setDownloading(false);
        }
    };

    const handleEditWithPrompt = async () => {
        if (!editPrompt.trim()) return;
        if (!result.resume_id) {
            setEditError('Resume ID missing — please regenerate your resume.');
            return;
        }

        setEditing(true);
        setEditError('');
        try {
            const response = await resumeAPI.editWithPrompt(
                result.resume_id,
                editPrompt,
                isGuest ? null : userId,
            );
            if (onUpdate) onUpdate(response);
            setEditPrompt('');
            setPromptInfo(response);  // server returns prompt_count / max_prompts / remaining_prompts
        } catch (err) {
            setEditError(err.message || 'Failed to edit resume. Please try again.');
        } finally {
            setEditing(false);
        }
    };

    const handleInlineEdit = async () => {
        if (!result.resume_id) {
            setEditError('Resume ID missing — please regenerate your resume.');
            return;
        }

        let parsedData;
        try {
            parsedData = JSON.parse(jsonText);
        } catch {
            setEditError('Invalid JSON. Please check your syntax.');
            return;
        }

        setEditing(true);
        setEditError('');
        try {
            const response = await resumeAPI.updateInline(result.resume_id, parsedData, userId);
            if (onUpdate) {
                onUpdate({ ...response, preview_html: response.preview_html, data: response.data });
            }
            setIsEditingInline(false);
        } catch (err) {
            setEditError(err.response?.data?.detail || err.message || 'Failed to update resume. Please try again.');
        } finally {
            setEditing(false);
        }
    };

    return (
        <div className="gen-result">
            <div className="gen-result__header">
                <span className="gen-result__tick">✓</span>
                <div>
                    <h2>Your resume is ready!</h2>
                    <p>
                        <GenerationModeBadge mode={result.generation_mode} />
                        {' '}Download your .docx below.
                    </p>
                </div>
            </div>

            {/* Edit-quota banner */}
            {promptInfo && (
                <div className="gen-prompt-info">
                    <span>Edits used: {promptInfo.prompt_count} / {promptInfo.max_prompts}</span>
                    {editsExhausted && isGuest && (
                        <a className="btn-upgrade" href="/signup">
                            Sign up for 50 edits
                        </a>
                    )}
                    {editsExhausted && !isGuest && (
                        <a className="btn-upgrade" href="/pricing">
                            Upgrade to Pro for more edits
                        </a>
                    )}
                </div>
            )}

            {/* Guest first-use nudge (only before they've used any edits) */}
            {isGuest && !promptInfo && (
                <div className="gen-guest-notice">
                    <strong>Free edits:</strong> You can edit this resume up to {GUEST_MAX_EDITS} times without an account.
                    <a href="/signup" className="gen-guest-notice__link">Sign up</a> for {PAID_MAX_EDITS} edits.
                </div>
            )}

            {result.preview_html && (
                <div className="gen-preview-wrap">
                    {isEditingInline ? (
                        <div className="gen-inline-editor">
                            <textarea
                                className="gen-edit-textarea"
                                value={jsonText}
                                onChange={(e) => setJsonText(e.target.value)}
                                rows={20}
                            />
                            {jsonText && (() => {
                                try { JSON.parse(jsonText); return null; }
                                catch { return <div className="gen-json-error">⚠️ Invalid JSON syntax</div>; }
                            })()}
                            <div className="gen-edit-actions">
                                <button className="btn-save" onClick={handleInlineEdit} disabled={editing}>
                                    {editing ? 'Saving...' : 'Save Changes'}
                                </button>
                                <button className="btn-cancel" onClick={() => {
                                    setIsEditingInline(false);
                                    setJsonText(JSON.stringify(result.data || {}, null, 2));
                                }}>
                                    Cancel
                                </button>
                            </div>
                        </div>
                    ) : (
                        <iframe
                            key={result.filename}
                            title="Resume Preview"
                            srcDoc={result.preview_html}
                            className="gen-preview-frame"
                            sandbox="allow-same-origin"
                        />
                    )}
                </div>
            )}

            {result.resume_id && (
                <div className="gen-edit-section">
                    <h3>
                        Edit Your Resume
                        {editsRemaining !== null && (
                            <span className="gen-edit-section__quota">
                                {editsRemaining} edit{editsRemaining !== 1 ? 's' : ''} remaining
                            </span>
                        )}
                    </h3>
                    <div className="gen-edit-prompt">
                        <textarea
                            className="gen-edit-input"
                            placeholder="Describe a change (e.g. 'Make the summary more concise', 'Add Python to skills')"
                            value={editPrompt}
                            onChange={(e) => setEditPrompt(e.target.value)}
                            rows={2}
                            disabled={editing || editsExhausted}
                        />
                        <button
                            className="btn-edit-prompt"
                            onClick={handleEditWithPrompt}
                            disabled={editing || !editPrompt.trim() || editsExhausted}
                        >
                            {editing ? 'Editing...' : '✨ Apply Edit'}
                        </button>
                    </div>
                    {!isGuest && (
                        <button
                            className="btn-edit-inline"
                            onClick={() => setIsEditingInline(true)}
                            disabled={editing}
                        >
                            📝 Edit Inline (JSON)
                        </button>
                    )}
                    {editError && <div className="gen-error" role="alert">{editError}</div>}
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
            {downloadError && <div className="gen-error" role="alert">{downloadError}</div>}
        </div>
    );
}

// ── Main generator page ───────────────────────────────────────────────────────
const WizardPage = () => {
    const navigate      = useNavigate();
    const fileInputRef  = useRef(null);
    const [files, setFiles]             = useState([]);
    const [jobDesc, setJobDesc]         = useState('');
    const [additionalInfo, setAdditionalInfo] = useState('');
    const [isDragging, setIsDragging]     = useState(false);
    const [loading, setLoading]           = useState(false);
    const [error, setError]               = useState('');
    const [result, setResult]             = useState(null);

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
        setLoading(true);
        setError(''); // Clear previous errors
        try {
            const savedToken = localStorage.getItem('token');
            const savedUserId = localStorage.getItem('userId');
            const activeUserId = (savedToken && savedUserId) ? parseInt(savedUserId, 10) : null;
            const data = await resumeAPI.generate(files, jobDesc, additionalInfo, activeUserId);
            setResult(data);
        } catch (err) {
            const msg = err.response?.data?.detail || err.message || 'Generation failed. Please try again.';
            setError(msg);
            console.error('Resume generation error:', err);
        } finally {
            setLoading(false);
        }
    };

    // ── Result screen ─────────────────────────────────────────────────────────
    if (result) {
        const handleResultUpdate = (updatedResult) => {
            setResult(prev => ({
                ...prev,
                ...(updatedResult.preview_html  !== undefined && { preview_html:  updatedResult.preview_html }),
                ...(updatedResult.data          !== undefined && { data:          updatedResult.data }),
                ...(updatedResult.filename      !== undefined && { filename:      updatedResult.filename }),
                ...(updatedResult.prompt_count  !== undefined && { prompt_count:  updatedResult.prompt_count }),
            }));
        };

        return (
            <div className="gen-page">
                <nav className="gen-nav">
                    <button className="gen-nav__back" onClick={() => setResult(null)}>← Back</button>
                    <span className="gen-nav__logo">ResumeGen</span>
                    <span />
                </nav>
                <ResultView
                    result={result}
                    onReset={() => setResult(null)}
                    onUpdate={handleResultUpdate}
                />
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
                <h1>Australian Resume Generator</h1>
                <p>
                    Upload your existing resume and paste the job description. Our AI tailors every
                    section to the role — Australian English, ATS-ready, ready to download in 30 seconds.
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
                        rows={12}
                    />
                    <p className="gen-panel__tip">
                        Tip: include the complete posting — responsibilities, requirements, and preferred
                        qualifications — for the most targeted resume.
                    </p>
                </div>
            </div>

            {/* Additional Information Panel */}
            <div className="gen-panel gen-panel--full">
                <h2 className="gen-panel__title">
                    <span className="gen-panel__icon">📝</span>
                    Additional Information
                    <span className="gen-panel__hint">optional</span>
                </h2>
                <textarea
                    className="gen-jd-textarea"
                    placeholder="Provide any additional information that will help tailor your resume: responses to job criteria, specific examples of experience relevant to the role, achievements, projects, or any other details you'd like to highlight..."
                    value={additionalInfo}
                    onChange={e => setAdditionalInfo(e.target.value)}
                    rows={6}
                />
                <p className="gen-panel__tip">
                    Tip: Include specific examples, achievements, or responses to selection criteria that directly relate to the job description.
                </p>
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
