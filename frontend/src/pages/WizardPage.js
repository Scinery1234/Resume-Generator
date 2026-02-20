import React, { useState } from 'react';
import './WizardPage.css';

const WizardPage = () => {
    const steps = ['Personal Info', 'Education', 'Experience', 'Skills', 'Review'];
    const [currentStep, setCurrentStep] = useState(0);

    const handleNext = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(currentStep + 1);
        }
    };

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        }
    };

    const progress = ((currentStep + 1) / steps.length) * 100;

    return (
        <div className="wizard-page">
            <div className="wizard-header">
                <h1>Resume Builder</h1>
            </div>
            <div className="progress-container">
                <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                </div>
                <p className="progress-text">Step {currentStep + 1} of {steps.length}</p>
            </div>
            <div className="wizard-content">
                <aside className="wizard-sidebar">
                    <h3>Steps</h3>
                    <ul className="steps-list">
                        {steps.map((step, index) => (
                            <li key={index} className={`step ${currentStep === index ? 'active' : ''} ${currentStep > index ? 'completed' : ''}`} onClick={() => setCurrentStep(index)}>
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
                                <input type="text" placeholder="Full Name" />
                                <input type="email" placeholder="Email" />
                                <input type="tel" placeholder="Phone" />
                                <textarea placeholder="Professional Summary"></textarea>
                            </form>
                        )}
                        {currentStep === 1 && (
                            <form>
                                <input type="text" placeholder="School/University" />
                                <input type="text" placeholder="Degree" />
                                <input type="text" placeholder="Field of Study" />
                            </form>
                        )}
                        {currentStep === 2 && (
                            <form>
                                <input type="text" placeholder="Company Name" />
                                <input type="text" placeholder="Job Title" />
                                <textarea placeholder="Job Description"></textarea>
                            </form>
                        )}
                        {currentStep === 3 && (
                            <form>
                                <input type="text" placeholder="Skill 1" />
                                <input type="text" placeholder="Skill 2" />
                                <input type="text" placeholder="Skill 3" />
                            </form>
                        )}
                        {currentStep === 4 && (
                            <div className="review-section">
                                <h3>Review Your Resume</h3>
                                <p>Your resume information will be displayed here for review.</p>
                                <button className="download-btn">Download PDF</button>
                            </div>
                        )}
                    </div>
                    <div className="wizard-nav">
                        <button onClick={handlePrev} disabled={currentStep === 0} className="btn btn-secondary"> Previous </button>
                        <button onClick={handleNext} disabled={currentStep === steps.length - 1} className="btn btn-primary"> Next </button>
                    </div>
                </main>
            </div>
        </div>
    );
};

export default WizardPage;