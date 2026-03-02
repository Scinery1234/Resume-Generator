import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './WizardPage.css';
import { resumeAPI } from '../services/api';

const STEPS = ['Personal Info', 'Education', 'Experience', 'Skills', 'Preview & Export'];

const EMPTY_EDUCATION = { degree: '', institution: '', field: '', graduation_year: '' };
const EMPTY_EXPERIENCE = { title: '', company: '', location: '', dates: '', description: '', bullets: [] };

const WizardPage = () => {
    const navigate = useNavigate();
    const [currentStep, setCurrentStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [error, setError] = useState('');
    const [generatedFilename, setGeneratedFilename] = useState(null);
    const [previewHtml, setPreviewHtml] = useState('');

    const [formData, setFormData] = useState({
        name: '',
        email: '',
        phone: '',
        location: '',
        linkedin: '',
        professional_summary: '',
        education: [],
        experience: [],
        key_skills: [],
        technical_skills: [],
        certifications: [],
        awards: [],
    });

    const [currentEducation, setCurrentEducation] = useState({ ...EMPTY_EDUCATION });
    const [currentExperience, setCurrentExperience] = useState({ ...EMPTY_EXPERIENCE });
    const [currentBullet, setCurrentBullet] = useState('');

    // Track skill input values via refs so we don't fight React for uncontrolled inputs
    const skillInputRefs = {
        key_skills:     useRef(null),
        technical_skills: useRef(null),
        certifications: useRef(null),
        awards:         useRef(null),
    };

    // ── Step navigation ─────────────────────────────────────────────────
    const handleNext = () => {
        const validationError = validateStep(currentStep);
        if (validationError) { setError(validationError); return; }
        setError('');
        setCurrentStep(s => s + 1);
    };

    const handlePrev = () => {
        setError('');
        setCurrentStep(s => s - 1);
    };

    const goToStep = (index) => {
        setError('');
        setCurrentStep(index);
    };

    // ── Validation ──────────────────────────────────────────────────────
    const validateStep = (step) => {
        if (step === 0) {
            if (!formData.name.trim())  return 'Full name is required.';
            if (!formData.email.trim()) return 'Email address is required.';
            if (!formData.phone.trim()) return 'Phone number is required.';
            if (!formData.location.trim()) return 'Location / suburb is required.';
            if (!formData.professional_summary.trim())
                return 'A professional summary is required.';
        }
        return '';
    };

    // ── Build API payload ────────────────────────────────────────────────
    const buildPayload = useCallback(() => ({
        name: formData.name,
        contact: {
            email: formData.email,
            phone: formData.phone,
            location: formData.location,
            ...(formData.linkedin ? { linkedin: formData.linkedin } : {}),
        },
        professional_summary: formData.professional_summary,
        key_skills:       formData.key_skills,
        technical_skills: formData.technical_skills,
        experience:       formData.experience,
        education:        formData.education,
        certifications:   formData.certifications,
        awards:           formData.awards,
    }), [formData]);

    // ── Auto-fetch preview when entering step 4 ─────────────────────────
    useEffect(() => {
        if (currentStep !== 4) return;
        let cancelled = false;
        const fetch = async () => {
            setPreviewLoading(true);
            setPreviewHtml('');
            try {
                const html = await resumeAPI.preview(buildPayload());
                if (!cancelled) setPreviewHtml(html);
            } catch {
                if (!cancelled) setPreviewHtml('');
            } finally {
                if (!cancelled) setPreviewLoading(false);
            }
        };
        fetch();
        return () => { cancelled = true; };
    }, [currentStep, buildPayload]);

    // ── Education ────────────────────────────────────────────────────────
    const addEducation = () => {
        if (!currentEducation.degree.trim() || !currentEducation.institution.trim()) {
            setError('Degree and institution are required to add an education entry.');
            return;
        }
        setFormData(fd => ({ ...fd, education: [...fd.education, { ...currentEducation }] }));
        setCurrentEducation({ ...EMPTY_EDUCATION });
        setError('');
    };

    const removeEducation = (index) =>
        setFormData(fd => ({ ...fd, education: fd.education.filter((_, i) => i !== index) }));

    // ── Experience ───────────────────────────────────────────────────────
    const addExperience = () => {
        if (!currentExperience.title.trim() || !currentExperience.company.trim()) {
            setError('Job title and company are required to add an experience entry.');
            return;
        }
        setFormData(fd => ({ ...fd, experience: [...fd.experience, { ...currentExperience }] }));
        setCurrentExperience({ ...EMPTY_EXPERIENCE });
        setCurrentBullet('');
        setError('');
    };

    const removeExperience = (index) =>
        setFormData(fd => ({ ...fd, experience: fd.experience.filter((_, i) => i !== index) }));

    const addBullet = () => {
        if (!currentBullet.trim()) return;
        setCurrentExperience(ce => ({ ...ce, bullets: [...ce.bullets, currentBullet.trim()] }));
        setCurrentBullet('');
    };

    const removeBullet = (index) =>
        setCurrentExperience(ce => ({ ...ce, bullets: ce.bullets.filter((_, i) => i !== index) }));

    // ── Skills (tag-style) ────────────────────────────────────────────────
    const addSkill = (skillType) => {
        const ref = skillInputRefs[skillType];
        if (!ref.current || !ref.current.value.trim()) return;
        const val = ref.current.value.trim();
        setFormData(fd => ({ ...fd, [skillType]: [...fd[skillType], val] }));
        ref.current.value = '';
    };

    const removeSkill = (skillType, index) =>
        setFormData(fd => ({ ...fd, [skillType]: fd[skillType].filter((_, i) => i !== index) }));

    const handleSkillKeyDown = (e, skillType) => {
        if (e.key === 'Enter') { e.preventDefault(); addSkill(skillType); }
    };

    // ── Generate / Download ──────────────────────────────────────────────
    const handleGenerateResume = async () => {
        setLoading(true);
        setError('');
        try {
            const payload = buildPayload();
            const userId = localStorage.getItem('userId');
            const response = await resumeAPI.generate(payload, userId ? parseInt(userId) : null);
            if (response.status === 'success') {
                setGeneratedFilename(response.data.filename);
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to generate resume. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async () => {
        if (!generatedFilename) { await handleGenerateResume(); return; }
        try {
            const blob = await resumeAPI.downloadByFilename(generatedFilename);
            const url  = window.URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href     = url;
            a.download = `${formData.name.replace(/\s+/g, '_')}_resume.docx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch {
            setError('Failed to download resume. Please try again.');
        }
    };

    const progress = ((currentStep + 1) / STEPS.length) * 100;

    // ── Render helpers ────────────────────────────────────────────────────
    const SkillSection = ({ title, type, placeholder }) => (
        <div className="skills-section">
            <h3 className="skill-group-title">{title}</h3>
            <div className="skill-input-group">
                <input
                    ref={skillInputRefs[type]}
                    type="text"
                    placeholder={placeholder}
                    onKeyDown={(e) => handleSkillKeyDown(e, type)}
                    aria-label={`Add ${title}`}
                />
                <button
                    type="button"
                    onClick={() => addSkill(type)}
                    className="add-btn"
                    aria-label={`Add ${title} item`}
                >
                    Add
                </button>
            </div>
            <div className="skills-list" role="list">
                {formData[type].map((item, i) => (
                    <span key={i} className="skill-tag" role="listitem">
                        {item}
                        <button
                            onClick={() => removeSkill(type, i)}
                            className="remove-skill"
                            aria-label={`Remove ${item}`}
                        >×</button>
                    </span>
                ))}
            </div>
        </div>
    );

    return (
        <div className="wizard-page">
            {/* ── Header ── */}
            <div className="wizard-header">
                <button onClick={() => navigate('/')} className="home-btn" aria-label="Back to home">
                    ← Home
                </button>
                <h1 className="wizard-title">Resume Builder</h1>
                <div style={{ width: '80px' }} /> {/* spacer */}
            </div>

            {/* ── Progress bar ── */}
            <div className="progress-container" aria-label={`Step ${currentStep + 1} of ${STEPS.length}`}>
                <div className="progress-bar" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
                    <div className="progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <p className="progress-text">Step {currentStep + 1} of {STEPS.length} — {STEPS[currentStep]}</p>
            </div>

            {error && <div className="error-message" role="alert">{error}</div>}

            <div className="wizard-content">
                {/* ── Sidebar ── */}
                <aside className="wizard-sidebar" aria-label="Steps navigation">
                    <ul className="steps-list" role="list">
                        {STEPS.map((step, index) => (
                            <li
                                key={index}
                                className={`step${currentStep === index ? ' active' : ''}${currentStep > index ? ' completed' : ''}`}
                                onClick={() => goToStep(index)}
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => e.key === 'Enter' && goToStep(index)}
                                aria-current={currentStep === index ? 'step' : undefined}
                            >
                                <span className="step-number" aria-hidden="true">
                                    {currentStep > index ? '✓' : index + 1}
                                </span>
                                <span className="step-name">{step}</span>
                            </li>
                        ))}
                    </ul>
                </aside>

                {/* ── Main content ── */}
                <main className="wizard-main">
                    <h2 className="step-heading">{STEPS[currentStep]}</h2>

                    {/* ── Step 0: Personal Info ── */}
                    {currentStep === 0 && (
                        <form className="form-fields" onSubmit={(e) => e.preventDefault()}>
                            <label className="field-label">
                                Full Name <span className="required">*</span>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData(fd => ({ ...fd, name: e.target.value }))}
                                    placeholder="e.g. Jane Smith"
                                    autoComplete="name"
                                />
                            </label>
                            <label className="field-label">
                                Email Address <span className="required">*</span>
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData(fd => ({ ...fd, email: e.target.value }))}
                                    placeholder="e.g. jane.smith@email.com"
                                    autoComplete="email"
                                />
                            </label>
                            <label className="field-label">
                                Phone Number <span className="required">*</span>
                                <input
                                    type="tel"
                                    value={formData.phone}
                                    onChange={(e) => setFormData(fd => ({ ...fd, phone: e.target.value }))}
                                    placeholder="e.g. 0412 345 678"
                                    autoComplete="tel"
                                />
                            </label>
                            <label className="field-label">
                                Location <span className="required">*</span>
                                <input
                                    type="text"
                                    value={formData.location}
                                    onChange={(e) => setFormData(fd => ({ ...fd, location: e.target.value }))}
                                    placeholder="e.g. Melbourne, VIC"
                                    autoComplete="address-level2"
                                />
                            </label>
                            <label className="field-label">
                                LinkedIn Profile <span className="optional">(optional)</span>
                                <input
                                    type="text"
                                    value={formData.linkedin}
                                    onChange={(e) => setFormData(fd => ({ ...fd, linkedin: e.target.value }))}
                                    placeholder="e.g. linkedin.com/in/janesmith"
                                    autoComplete="url"
                                />
                            </label>
                            <label className="field-label">
                                Professional Summary <span className="required">*</span>
                                <span className="field-hint">2–4 sentences summarising your experience and key strengths.</span>
                                <textarea
                                    value={formData.professional_summary}
                                    onChange={(e) => setFormData(fd => ({ ...fd, professional_summary: e.target.value }))}
                                    placeholder="e.g. Experienced software engineer with 5+ years building scalable web applications in the Australian financial sector…"
                                    rows={5}
                                />
                            </label>
                        </form>
                    )}

                    {/* ── Step 1: Education ── */}
                    {currentStep === 1 && (
                        <div>
                            <div className="entry-form card-form">
                                <h3 className="entry-form-title">Add Education</h3>
                                <label className="field-label">
                                    Degree / Qualification <span className="required">*</span>
                                    <input
                                        type="text"
                                        value={currentEducation.degree}
                                        onChange={(e) => setCurrentEducation(ce => ({ ...ce, degree: e.target.value }))}
                                        placeholder="e.g. Bachelor of Computer Science"
                                    />
                                </label>
                                <label className="field-label">
                                    Field of Study
                                    <input
                                        type="text"
                                        value={currentEducation.field}
                                        onChange={(e) => setCurrentEducation(ce => ({ ...ce, field: e.target.value }))}
                                        placeholder="e.g. Software Engineering"
                                    />
                                </label>
                                <label className="field-label">
                                    Institution <span className="required">*</span>
                                    <input
                                        type="text"
                                        value={currentEducation.institution}
                                        onChange={(e) => setCurrentEducation(ce => ({ ...ce, institution: e.target.value }))}
                                        placeholder="e.g. University of Melbourne"
                                    />
                                </label>
                                <label className="field-label">
                                    Graduation Year
                                    <input
                                        type="text"
                                        value={currentEducation.graduation_year}
                                        onChange={(e) => setCurrentEducation(ce => ({ ...ce, graduation_year: e.target.value }))}
                                        placeholder="e.g. 2020"
                                    />
                                </label>
                                <button type="button" onClick={addEducation} className="add-btn">
                                    + Add Education
                                </button>
                            </div>
                            <div className="list-items" role="list">
                                {formData.education.map((edu, index) => (
                                    <div key={index} className="list-item" role="listitem">
                                        <div>
                                            <strong>{edu.degree}{edu.field ? ` — ${edu.field}` : ''}</strong>
                                            <div className="list-item-sub">{edu.institution} {edu.graduation_year ? `(${edu.graduation_year})` : ''}</div>
                                        </div>
                                        <button onClick={() => removeEducation(index)} className="remove-btn" aria-label={`Remove ${edu.degree}`}>
                                            Remove
                                        </button>
                                    </div>
                                ))}
                            </div>
                            {formData.education.length === 0 && (
                                <p className="empty-hint">No education entries added yet. Fill in the form above and click "Add Education".</p>
                            )}
                        </div>
                    )}

                    {/* ── Step 2: Experience ── */}
                    {currentStep === 2 && (
                        <div>
                            <div className="entry-form card-form">
                                <h3 className="entry-form-title">Add Work Experience</h3>
                                <label className="field-label">
                                    Job Title <span className="required">*</span>
                                    <input
                                        type="text"
                                        value={currentExperience.title}
                                        onChange={(e) => setCurrentExperience(ce => ({ ...ce, title: e.target.value }))}
                                        placeholder="e.g. Senior Software Engineer"
                                    />
                                </label>
                                <label className="field-label">
                                    Company / Organisation <span className="required">*</span>
                                    <input
                                        type="text"
                                        value={currentExperience.company}
                                        onChange={(e) => setCurrentExperience(ce => ({ ...ce, company: e.target.value }))}
                                        placeholder="e.g. ANZ Bank"
                                    />
                                </label>
                                <label className="field-label">
                                    Location
                                    <input
                                        type="text"
                                        value={currentExperience.location}
                                        onChange={(e) => setCurrentExperience(ce => ({ ...ce, location: e.target.value }))}
                                        placeholder="e.g. Melbourne, VIC"
                                    />
                                </label>
                                <label className="field-label">
                                    Dates
                                    <input
                                        type="text"
                                        value={currentExperience.dates}
                                        onChange={(e) => setCurrentExperience(ce => ({ ...ce, dates: e.target.value }))}
                                        placeholder="e.g. Jan 2020 – Present"
                                    />
                                </label>
                                <label className="field-label">
                                    Role Description <span className="optional">(optional if adding bullets)</span>
                                    <textarea
                                        value={currentExperience.description}
                                        onChange={(e) => setCurrentExperience(ce => ({ ...ce, description: e.target.value }))}
                                        placeholder="Brief overview of your responsibilities…"
                                        rows={3}
                                    />
                                </label>

                                <div className="bullets-section">
                                    <label className="field-label">
                                        Key Achievements / Bullet Points
                                        <span className="field-hint">Use action verbs and quantify results where possible.</span>
                                    </label>
                                    <div className="skill-input-group">
                                        <input
                                            type="text"
                                            value={currentBullet}
                                            onChange={(e) => setCurrentBullet(e.target.value)}
                                            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addBullet(); } }}
                                            placeholder="e.g. Reduced deployment time by 40% through CI/CD optimisation"
                                            aria-label="Add achievement bullet"
                                        />
                                        <button type="button" onClick={addBullet} className="add-btn">Add</button>
                                    </div>
                                    <div className="bullets-list">
                                        {currentExperience.bullets.map((bullet, i) => (
                                            <div key={i} className="bullet-item">
                                                <span>• {bullet}</span>
                                                <button onClick={() => removeBullet(i)} className="remove-btn" aria-label={`Remove bullet`}>×</button>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <button type="button" onClick={addExperience} className="add-btn add-entry-btn">
                                    + Add Experience
                                </button>
                            </div>

                            <div className="list-items" role="list">
                                {formData.experience.map((exp, index) => (
                                    <div key={index} className="list-item" role="listitem">
                                        <div>
                                            <strong>{exp.title}</strong>
                                            <div className="list-item-sub">{exp.company}{exp.location ? `, ${exp.location}` : ''} {exp.dates ? `· ${exp.dates}` : ''}</div>
                                        </div>
                                        <button onClick={() => removeExperience(index)} className="remove-btn" aria-label={`Remove ${exp.title}`}>
                                            Remove
                                        </button>
                                    </div>
                                ))}
                            </div>
                            {formData.experience.length === 0 && (
                                <p className="empty-hint">No experience entries added yet. Fill in the form above and click "Add Experience".</p>
                            )}
                        </div>
                    )}

                    {/* ── Step 3: Skills ── */}
                    {currentStep === 3 && (
                        <div className="skills-step">
                            <SkillSection title="Key Skills" type="key_skills" placeholder="e.g. Project Management" />
                            <SkillSection title="Technical Skills" type="technical_skills" placeholder="e.g. Python, React, AWS" />
                            <SkillSection title="Certifications" type="certifications" placeholder="e.g. AWS Certified Solutions Architect" />
                            <SkillSection title="Awards & Recognition" type="awards" placeholder="e.g. Employee of the Year 2023" />
                        </div>
                    )}

                    {/* ── Step 4: Preview & Export ── */}
                    {currentStep === 4 && (
                        <div className="preview-step">
                            <div className="preview-actions">
                                <button
                                    className="btn btn-primary"
                                    onClick={handleGenerateResume}
                                    disabled={loading}
                                >
                                    {loading ? 'Generating…' : generatedFilename ? '↺ Re-generate DOCX' : 'Generate DOCX'}
                                </button>
                                {generatedFilename && (
                                    <button className="btn btn-success" onClick={handleDownload}>
                                        ↓ Download DOCX
                                    </button>
                                )}
                            </div>

                            <div className="preview-container">
                                {previewLoading && (
                                    <div className="preview-loading">
                                        <div className="spinner" aria-label="Loading preview" />
                                        <p>Loading preview…</p>
                                    </div>
                                )}
                                {!previewLoading && previewHtml && (
                                    <iframe
                                        className="preview-iframe"
                                        title="Resume Preview"
                                        srcDoc={previewHtml}
                                        sandbox="allow-same-origin"
                                        aria-label="Resume document preview"
                                    />
                                )}
                                {!previewLoading && !previewHtml && (
                                    <div className="preview-empty">
                                        <p>Preview unavailable. Please ensure the backend is running.</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* ── Navigation ── */}
                    <div className="wizard-nav">
                        <button
                            onClick={handlePrev}
                            disabled={currentStep === 0}
                            className="btn btn-secondary"
                        >
                            ← Previous
                        </button>
                        {currentStep < STEPS.length - 1 && (
                            <button onClick={handleNext} className="btn btn-primary">
                                Next →
                            </button>
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
};

export default WizardPage;
