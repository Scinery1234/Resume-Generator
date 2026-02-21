import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import './WizardPage.css';
import { resumeAPI } from '../services/api';

const WizardPage = () => {
    const history = useHistory();
    const steps = ['Personal Info', 'Education', 'Experience', 'Skills', 'Review'];
    const [currentStep, setCurrentStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [generatedResumeId, setGeneratedResumeId] = useState(null);

    // Form data state
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        phone: '',
        location: '',
        professional_summary: '',
        education: [],
        experience: [],
        key_skills: [],
        technical_skills: [],
        certifications: [],
        awards: []
    });

    // Current education/experience being edited
    const [currentEducation, setCurrentEducation] = useState({
        degree: '',
        institution: '',
        field: '',
        graduation_year: ''
    });

    const [currentExperience, setCurrentExperience] = useState({
        title: '',
        company: '',
        location: '',
        dates: '',
        description: '',
        bullets: []
    });

    const [currentBullet, setCurrentBullet] = useState('');

    const handleNext = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(currentStep + 1);
            setError('');
        }
    };

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
            setError('');
        }
    };

    const addEducation = () => {
        if (currentEducation.degree && currentEducation.institution) {
            setFormData({
                ...formData,
                education: [...formData.education, { ...currentEducation }]
            });
            setCurrentEducation({ degree: '', institution: '', field: '', graduation_year: '' });
        }
    };

    const removeEducation = (index) => {
        setFormData({
            ...formData,
            education: formData.education.filter((_, i) => i !== index)
        });
    };

    const addExperience = () => {
        if (currentExperience.title && currentExperience.company) {
            setFormData({
                ...formData,
                experience: [...formData.experience, { ...currentExperience }]
            });
            setCurrentExperience({
                title: '',
                company: '',
                location: '',
                dates: '',
                description: '',
                bullets: []
            });
        }
    };

    const removeExperience = (index) => {
        setFormData({
            ...formData,
            experience: formData.experience.filter((_, i) => i !== index)
        });
    };

    const addBullet = () => {
        if (currentBullet.trim()) {
            setCurrentExperience({
                ...currentExperience,
                bullets: [...currentExperience.bullets, currentBullet]
            });
            setCurrentBullet('');
        }
    };

    const removeBullet = (index) => {
        setCurrentExperience({
            ...currentExperience,
            bullets: currentExperience.bullets.filter((_, i) => i !== index)
        });
    };

    const addSkill = (skillType) => {
        const input = document.getElementById(`${skillType}-input`);
        if (input && input.value.trim()) {
            setFormData({
                ...formData,
                [skillType]: [...formData[skillType], input.value.trim()]
            });
            input.value = '';
        }
    };

    const removeSkill = (skillType, index) => {
        setFormData({
            ...formData,
            [skillType]: formData[skillType].filter((_, i) => i !== index)
        });
    };

    const handleGenerateResume = async () => {
        setLoading(true);
        setError('');

        // Validate required fields
        if (!formData.name || !formData.email || !formData.phone || !formData.location) {
            setError('Please fill in all personal information fields');
            setLoading(false);
            return;
        }

        if (!formData.professional_summary) {
            setError('Please provide a professional summary');
            setLoading(false);
            return;
        }

        try {
            const candidateData = {
                name: formData.name,
                contact: {
                    email: formData.email,
                    phone: formData.phone,
                    location: formData.location
                },
                professional_summary: formData.professional_summary,
                key_skills: formData.key_skills,
                technical_skills: formData.technical_skills,
                experience: formData.experience,
                education: formData.education,
                certifications: formData.certifications,
                awards: formData.awards
            };

            const userId = localStorage.getItem('userId');
            const response = await resumeAPI.generate(candidateData, userId ? parseInt(userId) : null);
            
            if (response.status === 'success') {
                setGeneratedResumeId(response.data.resume_id);
                alert('Resume generated successfully! You can download it now.');
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to generate resume. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async () => {
        if (!generatedResumeId) {
            setError('Please generate a resume first');
            return;
        }

        try {
            const blob = await resumeAPI.download(generatedResumeId);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${formData.name}_resume.docx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            setError('Failed to download resume. Please try again.');
        }
    };

    const progress = ((currentStep + 1) / steps.length) * 100;

    return (
        <div className="wizard-page">
            <div className="wizard-header">
                <h1>Resume Builder</h1>
                <button onClick={() => history.push('/')} className="home-btn">Home</button>
            </div>
            <div className="progress-container">
                <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                </div>
                <p className="progress-text">Step {currentStep + 1} of {steps.length}</p>
            </div>
            {error && <div className="error-message">{error}</div>}
            <div className="wizard-content">
                <aside className="wizard-sidebar">
                    <h3>Steps</h3>
                    <ul className="steps-list">
                        {steps.map((step, index) => (
                            <li 
                                key={index} 
                                className={`step ${currentStep === index ? 'active' : ''} ${currentStep > index ? 'completed' : ''}`} 
                                onClick={() => setCurrentStep(index)}
                            >
                                <span className="step-number">{index + 1}</span>
                                <span className="step-name">{step}</span>
                            </li>
                        ))}
                    </ul>
                </aside>
                <main className="wizard-main">
                    <h2>{steps[currentStep]}</h2>
                    <div className="form-section">
                        {currentStep === 0 && (
                            <form>
                                <input 
                                    type="text" 
                                    placeholder="Full Name *" 
                                    value={formData.name}
                                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                                    required
                                />
                                <input 
                                    type="email" 
                                    placeholder="Email *" 
                                    value={formData.email}
                                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                                    required
                                />
                                <input 
                                    type="tel" 
                                    placeholder="Phone *" 
                                    value={formData.phone}
                                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                                    required
                                />
                                <input 
                                    type="text" 
                                    placeholder="Location *" 
                                    value={formData.location}
                                    onChange={(e) => setFormData({...formData, location: e.target.value})}
                                    required
                                />
                                <textarea 
                                    placeholder="Professional Summary *" 
                                    value={formData.professional_summary}
                                    onChange={(e) => setFormData({...formData, professional_summary: e.target.value})}
                                    rows="5"
                                    required
                                />
                            </form>
                        )}
                        {currentStep === 1 && (
                            <div>
                                <div className="form-group">
                                    <input 
                                        type="text" 
                                        placeholder="Degree" 
                                        value={currentEducation.degree}
                                        onChange={(e) => setCurrentEducation({...currentEducation, degree: e.target.value})}
                                    />
                                    <input 
                                        type="text" 
                                        placeholder="Institution" 
                                        value={currentEducation.institution}
                                        onChange={(e) => setCurrentEducation({...currentEducation, institution: e.target.value})}
                                    />
                                    <input 
                                        type="text" 
                                        placeholder="Field of Study" 
                                        value={currentEducation.field}
                                        onChange={(e) => setCurrentEducation({...currentEducation, field: e.target.value})}
                                    />
                                    <input 
                                        type="text" 
                                        placeholder="Graduation Year" 
                                        value={currentEducation.graduation_year}
                                        onChange={(e) => setCurrentEducation({...currentEducation, graduation_year: e.target.value})}
                                    />
                                    <button type="button" onClick={addEducation} className="add-btn">Add Education</button>
                                </div>
                                <div className="list-items">
                                    {formData.education.map((edu, index) => (
                                        <div key={index} className="list-item">
                                            <span>{edu.degree} - {edu.institution}</span>
                                            <button onClick={() => removeEducation(index)} className="remove-btn">Remove</button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {currentStep === 2 && (
                            <div>
                                <div className="form-group">
                                    <input 
                                        type="text" 
                                        placeholder="Job Title" 
                                        value={currentExperience.title}
                                        onChange={(e) => setCurrentExperience({...currentExperience, title: e.target.value})}
                                    />
                                    <input 
                                        type="text" 
                                        placeholder="Company Name" 
                                        value={currentExperience.company}
                                        onChange={(e) => setCurrentExperience({...currentExperience, company: e.target.value})}
                                    />
                                    <input 
                                        type="text" 
                                        placeholder="Location" 
                                        value={currentExperience.location}
                                        onChange={(e) => setCurrentExperience({...currentExperience, location: e.target.value})}
                                    />
                                    <input 
                                        type="text" 
                                        placeholder="Dates (e.g., Jan 2020 - Present)" 
                                        value={currentExperience.dates}
                                        onChange={(e) => setCurrentExperience({...currentExperience, dates: e.target.value})}
                                    />
                                    <textarea 
                                        placeholder="Job Description" 
                                        value={currentExperience.description}
                                        onChange={(e) => setCurrentExperience({...currentExperience, description: e.target.value})}
                                        rows="3"
                                    />
                                    <div className="bullets-section">
                                        <input 
                                            type="text" 
                                            placeholder="Achievement/Bullet Point" 
                                            value={currentBullet}
                                            onChange={(e) => setCurrentBullet(e.target.value)}
                                            onKeyPress={(e) => e.key === 'Enter' && addBullet()}
                                        />
                                        <button type="button" onClick={addBullet} className="add-btn">Add Bullet</button>
                                        <div className="bullets-list">
                                            {currentExperience.bullets.map((bullet, index) => (
                                                <div key={index} className="bullet-item">
                                                    <span>• {bullet}</span>
                                                    <button onClick={() => removeBullet(index)} className="remove-btn">Remove</button>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <button type="button" onClick={addExperience} className="add-btn">Add Experience</button>
                                </div>
                                <div className="list-items">
                                    {formData.experience.map((exp, index) => (
                                        <div key={index} className="list-item">
                                            <span>{exp.title} at {exp.company}</span>
                                            <button onClick={() => removeExperience(index)} className="remove-btn">Remove</button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {currentStep === 3 && (
                            <div>
                                <div className="skills-section">
                                    <h3>Key Skills</h3>
                                    <div className="skill-input-group">
                                        <input 
                                            id="key_skills-input"
                                            type="text" 
                                            placeholder="Add a skill" 
                                            onKeyPress={(e) => e.key === 'Enter' && addSkill('key_skills')}
                                        />
                                        <button type="button" onClick={() => addSkill('key_skills')} className="add-btn">Add</button>
                                    </div>
                                    <div className="skills-list">
                                        {formData.key_skills.map((skill, index) => (
                                            <span key={index} className="skill-tag">
                                                {skill}
                                                <button onClick={() => removeSkill('key_skills', index)} className="remove-skill">×</button>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div className="skills-section">
                                    <h3>Technical Skills</h3>
                                    <div className="skill-input-group">
                                        <input 
                                            id="technical_skills-input"
                                            type="text" 
                                            placeholder="Add a technical skill" 
                                            onKeyPress={(e) => e.key === 'Enter' && addSkill('technical_skills')}
                                        />
                                        <button type="button" onClick={() => addSkill('technical_skills')} className="add-btn">Add</button>
                                    </div>
                                    <div className="skills-list">
                                        {formData.technical_skills.map((skill, index) => (
                                            <span key={index} className="skill-tag">
                                                {skill}
                                                <button onClick={() => removeSkill('technical_skills', index)} className="remove-skill">×</button>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div className="skills-section">
                                    <h3>Certifications</h3>
                                    <div className="skill-input-group">
                                        <input 
                                            id="certifications-input"
                                            type="text" 
                                            placeholder="Add a certification" 
                                            onKeyPress={(e) => e.key === 'Enter' && addSkill('certifications')}
                                        />
                                        <button type="button" onClick={() => addSkill('certifications')} className="add-btn">Add</button>
                                    </div>
                                    <div className="skills-list">
                                        {formData.certifications.map((cert, index) => (
                                            <span key={index} className="skill-tag">
                                                {cert}
                                                <button onClick={() => removeSkill('certifications', index)} className="remove-skill">×</button>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div className="skills-section">
                                    <h3>Awards</h3>
                                    <div className="skill-input-group">
                                        <input 
                                            id="awards-input"
                                            type="text" 
                                            placeholder="Add an award" 
                                            onKeyPress={(e) => e.key === 'Enter' && addSkill('awards')}
                                        />
                                        <button type="button" onClick={() => addSkill('awards')} className="add-btn">Add</button>
                                    </div>
                                    <div className="skills-list">
                                        {formData.awards.map((award, index) => (
                                            <span key={index} className="skill-tag">
                                                {award}
                                                <button onClick={() => removeSkill('awards', index)} className="remove-skill">×</button>
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                        {currentStep === 4 && (
                            <div className="review-section">
                                <h3>Review Your Resume</h3>
                                <div className="review-content">
                                    <p><strong>Name:</strong> {formData.name || 'Not provided'}</p>
                                    <p><strong>Email:</strong> {formData.email || 'Not provided'}</p>
                                    <p><strong>Phone:</strong> {formData.phone || 'Not provided'}</p>
                                    <p><strong>Location:</strong> {formData.location || 'Not provided'}</p>
                                    <p><strong>Professional Summary:</strong> {formData.professional_summary || 'Not provided'}</p>
                                    <p><strong>Education:</strong> {formData.education.length} entries</p>
                                    <p><strong>Experience:</strong> {formData.experience.length} entries</p>
                                    <p><strong>Skills:</strong> {formData.key_skills.length + formData.technical_skills.length} total</p>
                                </div>
                                <button 
                                    className="download-btn" 
                                    onClick={handleGenerateResume}
                                    disabled={loading}
                                >
                                    {loading ? 'Generating...' : 'Generate Resume'}
                                </button>
                                {generatedResumeId && (
                                    <button 
                                        className="download-btn" 
                                        onClick={handleDownload}
                                    >
                                        Download Resume
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                    <div className="wizard-nav">
                        <button onClick={handlePrev} disabled={currentStep === 0} className="btn btn-secondary">Previous</button>
                        {currentStep === steps.length - 1 ? (
                            <button onClick={handleGenerateResume} disabled={loading} className="btn btn-primary">
                                {loading ? 'Generating...' : 'Generate Resume'}
                            </button>
                        ) : (
                            <button onClick={handleNext} className="btn btn-primary">Next</button>
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
};

export default WizardPage;
