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
    const [activeTemplate, setActiveTemplate] = useState(result.template || 'modern');
    const [switchingTemplate, setSwitchingTemplate] = useState(false);

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
            const blob = await resumeAPI.downloadByFilename(result.filename);
            downloadBlob(blob, result.filename);
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

    const handleSwitchTemplate = async (templateId) => {
        if (templateId === activeTemplate || switchingTemplate || !result.resume_id) return;
        setSwitchingTemplate(true);
        try {
            const response = await resumeAPI.switchTemplate(
                result.resume_id,
                templateId,
                isGuest ? null : userId,
            );
            setActiveTemplate(templateId);
            if (onUpdate) onUpdate({ ...response, data: result.data });
        } catch (err) {
            setEditError(err.message || 'Failed to switch template.');
        } finally {
            setSwitchingTemplate(false);
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

            {/* ── Template switcher ── */}
            {result.resume_id && (
                <div className="gen-template-switcher">
                    <span className="gen-template-switcher__label">Layout:</span>
                    {TEMPLATES.map(t => (
                        <button
                            key={t.id}
                            type="button"
                            className={`gen-template-pill${activeTemplate === t.id ? ' gen-template-pill--active' : ''}`}
                            onClick={() => handleSwitchTemplate(t.id)}
                            disabled={switchingTemplate}
                            style={{ '--pill-color': t.preview.headingColor }}
                            aria-pressed={activeTemplate === t.id}
                        >
                            <span className="gen-template-pill__dot" style={{ background: t.preview.headingColor }} />
                            {t.name}
                            {switchingTemplate && activeTemplate !== t.id && ' '}
                        </button>
                    ))}
                    {switchingTemplate && (
                        <span className="gen-template-switcher__loading">Applying…</span>
                    )}
                </div>
            )}

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

// ── Template definitions ──────────────────────────────────────────────────────
// `preview` drives the TemplatePreviewMini component — every key maps to a real
// CSS value that matches the backend template config exactly.
const TEMPLATES = [
    {
        id: 'modern',
        name: 'Modern',
        description: 'Clean navy-blue design — polished and professional.',
        preview: {
            headingColor: '#1a375e',
            ruleColor:    '#1a375e',
            mutedColor:   '#445566',
            fontFamily:   "Calibri, 'Segoe UI', Arial, sans-serif",
            nameAlign:    'center',
            namePx:       14,
        },
    },
    {
        id: 'classic',
        name: 'Classic',
        description: 'Traditional serif format — timeless and formal.',
        preview: {
            headingColor: '#1a1a1a',
            ruleColor:    '#333333',
            mutedColor:   '#555555',
            fontFamily:   "Georgia, 'Times New Roman', serif",
            nameAlign:    'center',
            namePx:       13,
        },
    },
    {
        id: 'creative',
        name: 'Creative',
        description: 'Purple & teal accents — bold and contemporary.',
        preview: {
            headingColor: '#6b21a8',
            ruleColor:    '#0891b2',
            mutedColor:   '#4b5563',
            fontFamily:   "Calibri, 'Segoe UI', Arial, sans-serif",
            nameAlign:    'left',
            namePx:       16,
        },
    },
    {
        id: 'minimal',
        name: 'Minimal',
        description: 'Light-gray rules — understated and elegant.',
        preview: {
            headingColor: '#374151',
            ruleColor:    '#d1d5db',
            mutedColor:   '#6b7280',
            fontFamily:   "Calibri, 'Segoe UI', Arial, sans-serif",
            nameAlign:    'left',
            namePx:       14,
        },
    },
    {
        id: 'executive',
        name: 'Executive',
        description: 'Charcoal headings with amber-gold rules — sharp and authoritative.',
        preview: {
            headingColor: '#1c1c2e',
            ruleColor:    '#b45309',
            mutedColor:   '#525252',
            fontFamily:   "Calibri, 'Segoe UI', Arial, sans-serif",
            nameAlign:    'left',
            namePx:       15,
        },
    },
];

// ── Mini resume preview ───────────────────────────────────────────────────────
// Renders a miniature but fully styled resume at a size designed for the card.
// Uses inline styles pulled directly from the template's preview config, so
// heading colour, rule colour, font family, and name alignment are all accurate.
function PreviewSection({ label, p, children }) {
    return (
        <div style={{ marginBottom: 7 }}>
            <div style={{
                fontFamily: p.fontFamily, fontSize: 7, fontWeight: 700,
                color: p.headingColor, letterSpacing: '0.07em', marginBottom: 2,
            }}>
                {label}
            </div>
            <div style={{ borderTop: `1px solid ${p.ruleColor}`, marginBottom: 4 }} />
            {children}
        </div>
    );
}

function TemplatePreviewMini({ t }) {
    const p = t.preview;
    const body = { fontFamily: p.fontFamily, fontSize: 8, color: '#2a2a2a', lineHeight: 1.35 };
    const muted = { fontFamily: p.fontFamily, fontSize: 7, fontStyle: 'italic', color: p.mutedColor };
    const bold  = { fontFamily: p.fontFamily, fontSize: 8.5, fontWeight: 700, color: p.headingColor };

    return (
        <div style={{ padding: '13px 13px 10px', background: '#fff', fontFamily: p.fontFamily }}>
            {/* ── Name ── */}
            <div style={{
                fontSize: p.namePx, fontWeight: 700, color: p.headingColor,
                textAlign: p.nameAlign, letterSpacing: '0.04em', marginBottom: 2,
            }}>
                ALEX JOHNSON
            </div>

            {/* ── Contact ── */}
            <div style={{
                fontSize: 7, color: p.mutedColor,
                textAlign: p.nameAlign, marginBottom: 6,
            }}>
                0412 345 678 · alex@email.com · Sydney NSW
            </div>

            {/* ── Header rule ── */}
            <div style={{ borderTop: `1.5px solid ${p.ruleColor}`, marginBottom: 7 }} />

            {/* ── Professional Summary ── */}
            <PreviewSection label="PROFESSIONAL SUMMARY" p={p}>
                <div style={{ ...body, marginBottom: 0 }}>
                    Results-driven engineer with 6+ years delivering scalable web applications
                    and leading high-performing teams across the fintech sector.
                </div>
            </PreviewSection>

            {/* ── Work Experience ── */}
            <PreviewSection label="WORK EXPERIENCE" p={p}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                    <span style={bold}>Senior Software Engineer</span>
                    <span style={{ fontFamily: p.fontFamily, fontSize: 6.5, color: p.mutedColor }}>2021 – Present</span>
                </div>
                <div style={{ ...muted, marginBottom: 4 }}>Atlassian  |  Sydney NSW</div>
                <div style={{ ...body, paddingLeft: 8, marginBottom: 2 }}>• Led microservices platform for 2M+ daily users</div>
                <div style={{ ...body, paddingLeft: 8, marginBottom: 4 }}>• Reduced API response time by 40%</div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                    <span style={{ ...bold, fontSize: 8 }}>Software Engineer</span>
                    <span style={{ fontFamily: p.fontFamily, fontSize: 6.5, color: p.mutedColor }}>2018 – 2021</span>
                </div>
                <div style={{ ...muted, marginBottom: 4 }}>Canva  |  Sydney NSW</div>
                <div style={{ ...body, paddingLeft: 8, marginBottom: 2 }}>• Built real-time collaboration features for 5M+ users</div>
                <div style={{ ...body, paddingLeft: 8 }}>• Implemented test framework, cutting QA time by 35%</div>
            </PreviewSection>

            {/* ── Education ── */}
            <PreviewSection label="EDUCATION" p={p}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                    <span style={{ ...bold, fontSize: 8 }}>Bachelor of Computer Science</span>
                    <span style={{ fontFamily: p.fontFamily, fontSize: 6.5, color: p.mutedColor }}>2018</span>
                </div>
                <div style={{ ...muted }}>University of New South Wales</div>
            </PreviewSection>

            {/* ── Key Skills ── */}
            <PreviewSection label="KEY SKILLS" p={p}>
                <div style={{ ...body }}>
                    Python · TypeScript · React · AWS · Docker · CI/CD · Agile
                </div>
            </PreviewSection>
        </div>
    );
}

// ── Template carousel (shown before generation) ────────────────────────────
function TemplateCarousel({ selected, onChange }) {
    return (
        <div className="gen-panel gen-panel--carousel">
            <h2 className="gen-panel__title">
                <span className="gen-panel__icon">🎨</span>
                Resume Template
                <span className="gen-panel__hint">click to choose a layout</span>
            </h2>
            <div className="gen-carousel">
                {TEMPLATES.map(t => (
                    <button
                        key={t.id}
                        type="button"
                        className={`gen-carousel-card${selected === t.id ? ' gen-carousel-card--active' : ''}`}
                        onClick={() => onChange(t.id)}
                        aria-pressed={selected === t.id}
                        style={{ '--card-accent': t.preview.headingColor }}
                    >
                        <div className="gen-carousel-preview">
                            <TemplatePreviewMini t={t} />
                        </div>
                        <div className="gen-carousel-footer">
                            <div className="gen-carousel-dot" style={{ background: t.preview.headingColor }} />
                            <span className="gen-carousel-name">{t.name}</span>
                            {selected === t.id && <span className="gen-carousel-check">✓</span>}
                        </div>
                    </button>
                ))}
            </div>
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
    const [template, setTemplate]       = useState('modern');
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
        setError(''); // Clear previous errors
        try {
            const data = await resumeAPI.generate(files, jobDesc, additionalInfo, null, template);
            setResult({ ...data, template });
        } catch (err) {
            // Use the enhanced error message from the API interceptor
            let msg = err.message || 'Generation failed. Please try again.';
            
            // Additional specific error handling
            if (err.response?.status === 503) {
                msg = 'OpenAI API key is not configured. Please contact the administrator.';
            } else if (err.response?.status === 400) {
                msg = err.response?.data?.detail || msg;
            } else if (err.response?.status >= 500) {
                msg = 'Server error occurred. Please try again later.';
            } else if (!err.response && !err.message?.includes('Could not reach')) {
                msg = 'Could not reach the server. Please ensure the backend is running on http://localhost:8000';
            }
            
            setError(msg);
            console.error('Resume generation error:', err);
        } finally {
            setLoading(false);
        }
    };

    // ── Result screen ─────────────────────────────────────────────────────────
    if (result) {
        const handleResultUpdate = (updatedResult) => {
            setResult({
                ...result,
                preview_html: updatedResult.preview_html,
                data: updatedResult.data,
                prompt_count: updatedResult.prompt_count,
            });
        };
        
        return (
            <div className="gen-page">
                <nav className="gen-nav">
                    <button className="gen-nav__back" onClick={() => setResult(null)}>← Back</button>
                    <span className="gen-nav__logo">ResumeGen</span>
                    <span />
                </nav>
                <ResultView result={result} onReset={() => setResult(null)} onUpdate={handleResultUpdate} />
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

            {/* Template Carousel */}
            <TemplateCarousel selected={template} onChange={setTemplate} />

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
