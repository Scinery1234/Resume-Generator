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

function ResultView({ result, onReset, onUpdate, activeTemplate, switchingTemplate, onSwitchTemplate }) {
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
                            onClick={() => onSwitchTemplate(t.id)}
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
// Three structural layouts:
//   A – single column  (classic, minimal)
//   B – two-column sidebar  (modern, executive)
//   C – full-width header band  (creative)
const TEMPLATES = [
    {
        id: 'modern',
        name: 'Modern',
        description: 'Navy sidebar with contact & skills panel — polished and professional.',
        layout: 'B',
        preview: {
            headingColor: '#1a375e',
            ruleColor:    '#1a375e',
            mutedColor:   '#445566',
            fontFamily:   "Calibri, 'Segoe UI', Arial, sans-serif",
            nameAlign:    'left',
            namePx:       13,
            sidebarBg:    '#1a375e',
            sidebarText:  '#e8f0f8',
            sidebarRule:  '#4a7aae',
        },
    },
    {
        id: 'classic',
        name: 'Classic',
        description: 'Traditional serif single-column — timeless and formal.',
        layout: 'A',
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
        description: 'Purple header band with teal accents — bold and contemporary.',
        layout: 'C',
        preview: {
            headingColor: '#6b21a8',
            ruleColor:    '#0891b2',
            mutedColor:   '#4b5563',
            fontFamily:   "Calibri, 'Segoe UI', Arial, sans-serif",
            nameAlign:    'left',
            namePx:       14,
            headerBg:     '#6b21a8',
            headerText:   '#ffffff',
        },
    },
    {
        id: 'minimal',
        name: 'Minimal',
        description: 'Light-gray rules, single column — understated and elegant.',
        layout: 'A',
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
        description: 'Charcoal sidebar with amber-gold rules — sharp and authoritative.',
        layout: 'B',
        preview: {
            headingColor: '#1c1c2e',
            ruleColor:    '#b45309',
            mutedColor:   '#525252',
            fontFamily:   "Calibri, 'Segoe UI', Arial, sans-serif",
            nameAlign:    'left',
            namePx:       13,
            sidebarBg:    '#1c1c2e',
            sidebarText:  '#f0f0f0',
            sidebarRule:  '#b45309',
        },
    },
];

// ── Mini resume preview helpers ───────────────────────────────────────────────

/** Section heading + rule used inside Layout A and C mini previews. */
function PreviewSection({ label, p, children }) {
    return (
        <div style={{ marginBottom: 6 }}>
            <div style={{
                fontFamily: p.fontFamily, fontSize: 6.5, fontWeight: 700,
                color: p.headingColor, letterSpacing: '0.07em', marginBottom: 2,
            }}>
                {label}
            </div>
            <div style={{ borderTop: `1px solid ${p.ruleColor}`, marginBottom: 3 }} />
            {children}
        </div>
    );
}

/** Section heading + rule used inside the Layout B sidebar. */
function SidebarSection({ label, p, children }) {
    return (
        <div style={{ marginBottom: 8 }}>
            <div style={{
                fontSize: 6, fontWeight: 700, color: p.sidebarText,
                letterSpacing: '0.1em', marginBottom: 2,
            }}>
                {label}
            </div>
            <div style={{ borderTop: `1px solid ${p.sidebarRule}`, marginBottom: 4 }} />
            {children}
        </div>
    );
}

/** Layout A mini preview – single column */
function PreviewMiniA({ p }) {
    const body  = { fontFamily: p.fontFamily, fontSize: 7.5, color: '#2a2a2a', lineHeight: 1.35 };
    const muted = { fontFamily: p.fontFamily, fontSize: 6.5, fontStyle: 'italic', color: p.mutedColor };
    const bold  = { fontFamily: p.fontFamily, fontSize: 8, fontWeight: 700, color: p.headingColor };

    return (
        <div style={{ padding: '12px 12px 8px', background: '#fff', fontFamily: p.fontFamily }}>
            <div style={{ fontSize: p.namePx, fontWeight: 700, color: p.headingColor,
                textAlign: p.nameAlign, letterSpacing: '0.04em', marginBottom: 2 }}>
                ALEX JOHNSON
            </div>
            <div style={{ fontSize: 6.5, color: p.mutedColor, textAlign: p.nameAlign, marginBottom: 5 }}>
                0412 345 678 · alex@email.com · Sydney NSW
            </div>
            <div style={{ borderTop: `1.5px solid ${p.ruleColor}`, marginBottom: 6 }} />

            <PreviewSection label="PROFESSIONAL SUMMARY" p={p}>
                <div style={{ ...body }}>
                    Results-driven engineer with 6+ years delivering scalable web applications
                    and leading high-performing teams.
                </div>
            </PreviewSection>

            <PreviewSection label="WORK EXPERIENCE" p={p}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                    <span style={bold}>Senior Software Engineer</span>
                    <span style={{ fontSize: 6, color: p.mutedColor }}>2021 – Present</span>
                </div>
                <div style={{ ...muted, marginBottom: 3 }}>Atlassian  |  Sydney NSW</div>
                <div style={{ ...body, paddingLeft: 7, marginBottom: 1 }}>• Led microservices platform for 2M+ users</div>
                <div style={{ ...body, paddingLeft: 7, marginBottom: 4 }}>• Reduced API response time by 40%</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                    <span style={{ ...bold, fontSize: 7.5 }}>Software Engineer</span>
                    <span style={{ fontSize: 6, color: p.mutedColor }}>2018 – 2021</span>
                </div>
                <div style={{ ...muted, marginBottom: 3 }}>Canva  |  Sydney NSW</div>
                <div style={{ ...body, paddingLeft: 7 }}>• Built real-time collaboration for 5M+ users</div>
            </PreviewSection>

            <PreviewSection label="EDUCATION" p={p}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                    <span style={{ ...bold, fontSize: 7.5 }}>Bachelor of Computer Science</span>
                    <span style={{ fontSize: 6, color: p.mutedColor }}>2018</span>
                </div>
                <div style={{ ...muted }}>University of New South Wales</div>
            </PreviewSection>

            <PreviewSection label="KEY SKILLS" p={p}>
                <div style={{ ...body }}>Python · TypeScript · React · AWS · Docker</div>
            </PreviewSection>
        </div>
    );
}

/** Layout B mini preview – two-column sidebar with full-width header */
function PreviewMiniB({ p }) {
    const sbItem = { fontSize: 6.5, color: p.sidebarText, marginBottom: 2, lineHeight: 1.3, wordBreak: 'break-all' };
    const body   = { fontFamily: p.fontFamily, fontSize: 7.5, color: '#2a2a2a', lineHeight: 1.35 };
    const muted  = { fontFamily: p.fontFamily, fontSize: 6.5, fontStyle: 'italic', color: p.mutedColor };
    const bold   = { fontFamily: p.fontFamily, fontSize: 8, fontWeight: 700, color: p.headingColor };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', background: '#fff', fontFamily: p.fontFamily, minHeight: '100%' }}>
            {/* ── Full-width name header ── */}
            <div style={{ background: p.sidebarBg, padding: '8px 10px 7px 9px', flexShrink: 0 }}>
                <div style={{ fontSize: p.namePx, fontWeight: 700, color: p.sidebarText,
                    letterSpacing: '0.03em', lineHeight: 1.1 }}>
                    ALEX JOHNSON
                </div>
                <div style={{ fontSize: 6.5, color: p.sidebarText, opacity: 0.82,
                    marginTop: 3, letterSpacing: '0.04em' }}>
                    Senior Software Engineer  ·  Atlassian  ·  Sydney NSW
                </div>
            </div>

            {/* ── Body row ── */}
            <div style={{ display: 'flex', flex: 1 }}>
            {/* ── Sidebar ── */}
            <div style={{ width: '33%', background: p.sidebarBg, padding: '7px 7px 12px 9px', flexShrink: 0, overflow: 'hidden' }}>
                <SidebarSection label="CONTACT" p={p}>
                    <div style={sbItem}>0412 345 678</div>
                    <div style={sbItem}>alex@email.com</div>
                    <div style={sbItem}>Sydney NSW</div>
                </SidebarSection>

                <SidebarSection label="KEY SKILLS" p={p}>
                    {['Python', 'TypeScript', 'React', 'AWS', 'Docker'].map(s => (
                        <div key={s} style={sbItem}>  {s}</div>
                    ))}
                </SidebarSection>

                <SidebarSection label="EDUCATION" p={p}>
                    <div style={{ ...sbItem, fontWeight: 600 }}>B. Computer Science</div>
                    <div style={{ ...sbItem, fontStyle: 'italic', opacity: 0.85, fontSize: 6 }}>UNSW · 2018</div>
                </SidebarSection>
            </div>

            {/* ── Main ── */}
            <div style={{ flex: 1, padding: '7px 9px 8px 8px', minWidth: 0 }}>
                <div style={{ marginBottom: 6 }}>
                    <div style={{ fontSize: 6.5, fontWeight: 700, color: p.headingColor, letterSpacing: '0.07em', marginBottom: 2 }}>
                        PROFESSIONAL SUMMARY
                    </div>
                    <div style={{ borderTop: `1px solid ${p.ruleColor}`, marginBottom: 3 }} />
                    <div style={{ ...body }}>Results-driven engineer with 6+ years delivering scalable web applications.</div>
                </div>

                <div>
                    <div style={{ fontSize: 6.5, fontWeight: 700, color: p.headingColor, letterSpacing: '0.07em', marginBottom: 2 }}>
                        WORK EXPERIENCE
                    </div>
                    <div style={{ borderTop: `1px solid ${p.ruleColor}`, marginBottom: 3 }} />
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                        <span style={bold}>Senior Software Engineer</span>
                        <span style={{ fontSize: 6, color: p.mutedColor }}>2021–Present</span>
                    </div>
                    <div style={{ ...muted, marginBottom: 2 }}>Atlassian  |  Sydney NSW</div>
                    <div style={{ ...body, paddingLeft: 7, marginBottom: 1 }}>• Led microservices for 2M+ users</div>
                    <div style={{ ...body, paddingLeft: 7, marginBottom: 4 }}>• Reduced API time by 40%</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                        <span style={{ ...bold, fontSize: 7.5 }}>Software Engineer</span>
                        <span style={{ fontSize: 6, color: p.mutedColor }}>2018–2021</span>
                    </div>
                    <div style={{ ...muted, marginBottom: 2 }}>Canva  |  Sydney NSW</div>
                    <div style={{ ...body, paddingLeft: 7 }}>• Built real-time collaboration for 5M+ users</div>
                </div>
            </div>
            </div>{/* end body-row */}
        </div>
    );
}

/** Layout C mini preview – full-width header band */
function PreviewMiniC({ p }) {
    const body  = { fontFamily: p.fontFamily, fontSize: 7.5, color: '#2a2a2a', lineHeight: 1.35 };
    const muted = { fontFamily: p.fontFamily, fontSize: 6.5, fontStyle: 'italic', color: p.mutedColor };
    const bold  = { fontFamily: p.fontFamily, fontSize: 8, fontWeight: 700, color: p.headingColor };

    return (
        <div style={{ background: '#fff', fontFamily: p.fontFamily }}>
            {/* ── Header band ── */}
            <div style={{ background: p.headerBg, padding: '10px 12px 8px' }}>
                <div style={{ fontSize: p.namePx, fontWeight: 700, color: p.headerText,
                    letterSpacing: '0.04em', marginBottom: 3 }}>
                    ALEX JOHNSON
                </div>
                <div style={{ fontSize: 6.5, color: 'rgba(255,255,255,0.85)' }}>
                    0412 345 678 · alex@email.com · Sydney NSW
                </div>
            </div>

            {/* ── Body ── */}
            <div style={{ padding: '8px 12px 8px' }}>
                <PreviewSection label="PROFESSIONAL SUMMARY" p={p}>
                    <div style={{ ...body }}>
                        Results-driven engineer with 6+ years delivering scalable web applications
                        and leading high-performing teams.
                    </div>
                </PreviewSection>

                <PreviewSection label="WORK EXPERIENCE" p={p}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                        <span style={bold}>Senior Software Engineer</span>
                        <span style={{ fontSize: 6, color: p.mutedColor }}>2021 – Present</span>
                    </div>
                    <div style={{ ...muted, marginBottom: 3 }}>Atlassian  |  Sydney NSW</div>
                    <div style={{ ...body, paddingLeft: 7, marginBottom: 1 }}>• Led microservices for 2M+ daily users</div>
                    <div style={{ ...body, paddingLeft: 7, marginBottom: 4 }}>• Reduced API response time by 40%</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 1 }}>
                        <span style={{ ...bold, fontSize: 7.5 }}>Software Engineer</span>
                        <span style={{ fontSize: 6, color: p.mutedColor }}>2018 – 2021</span>
                    </div>
                    <div style={{ ...muted, marginBottom: 3 }}>Canva  |  Sydney NSW</div>
                    <div style={{ ...body, paddingLeft: 7 }}>• Built real-time collaboration for 5M+ users</div>
                </PreviewSection>

                <PreviewSection label="KEY SKILLS" p={p}>
                    <div style={{ ...body }}>Python · TypeScript · React · AWS · Docker</div>
                </PreviewSection>
            </div>
        </div>
    );
}

/** Dispatch to the correct mini preview component based on template layout. */
function TemplatePreviewMini({ t }) {
    if (t.layout === 'B') return <PreviewMiniB p={t.preview} />;
    if (t.layout === 'C') return <PreviewMiniC p={t.preview} />;
    return <PreviewMiniA p={t.preview} />;
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
    const [isDragging, setIsDragging]     = useState(false);
    const [loading, setLoading]           = useState(false);
    const [error, setError]               = useState('');
    const [result, setResult]             = useState(null);
    const [activeTemplate, setActiveTemplate]     = useState('modern');
    const [switchingTemplate, setSwitchingTemplate] = useState(false);

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
            const data = await resumeAPI.generate(files, jobDesc, additionalInfo, null, template);
            setActiveTemplate(template);
            setResult({ ...data, template });
        } catch (err) {
            const msg = err.response?.data?.detail || 'Generation failed. Please try again.';
            setError(msg);
            console.error('Resume generation error:', err);
        } finally {
            setLoading(false);
        }
    };

    // ── Template switching — lives in the parent so setResult is called directly
    const handleSwitchTemplate = async (templateId) => {
        if (!result || templateId === activeTemplate || switchingTemplate || !result.resume_id) return;
        const userId = localStorage.getItem('userId');
        const isGuest = !localStorage.getItem('token') || !userId;
        setSwitchingTemplate(true);
        try {
            const response = await resumeAPI.switchTemplate(
                result.resume_id,
                templateId,
                isGuest ? null : userId,
            );
            setActiveTemplate(templateId);
            setResult(prev => ({
                ...prev,
                preview_html: response.preview_html,
                filename:     response.filename,
            }));
        } catch (err) {
            // Error is surfaced via setSwitchError which ResultView displays
            console.error('Template switch failed:', err);
        } finally {
            setSwitchingTemplate(false);
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
                    activeTemplate={activeTemplate}
                    switchingTemplate={switchingTemplate}
                    onSwitchTemplate={handleSwitchTemplate}
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
