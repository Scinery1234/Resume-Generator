import React, { useState } from 'react';

const WizardPage = () => {
    const steps = [
        'Step 1: Personal Information',
        'Step 2: Education',
        'Step 3: Work Experience',
        'Step 4: Skills',
        'Step 5: Review'
    ];

    const [currentStep, setCurrentStep] = useState(0);

    const handleNext = () => {
        setCurrentStep((prevStep) => Math.min(prevStep + 1, steps.length - 1));
    };

    const handlePrev = () => {
        setCurrentStep((prevStep) => Math.max(prevStep - 1, 0));
    };

    return (
        <div>
            <h1>{steps[currentStep]}</h1>
            <div>
                {currentStep > 0 && <button onClick={handlePrev}>Previous</button>}
                {currentStep < steps.length - 1 ? (
                    <button onClick={handleNext}>Next</button>
                ) : (
                    <button onClick={() => alert('Submit!')}>Submit</button>
                )}
            </div>
        </div>
    );
};

export default WizardPage;