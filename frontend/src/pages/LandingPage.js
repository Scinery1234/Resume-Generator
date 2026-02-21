import React from 'react';
import { useHistory } from 'react-router-dom';
import './LandingPage.css';

const LandingPage = () => {
    const history = useHistory();
    const token = localStorage.getItem('token');

    const handleGetStarted = () => {
        if (token) {
            history.push('/wizard');
        } else {
            history.push('/auth');
        }
    };

    return (
        <div>
            <nav className="navbar">
                <h1>Resume Generator</h1>
                <ul>
                    <li><a href="#hero">Home</a></li>
                    <li><a href="#features">Features</a></li>
                    <li><a href="#pricing">Pricing</a></li>
                    <li><a href="#contact">Contact</a></li>
                    {token ? (
                        <li><button onClick={() => history.push('/wizard')} className="nav-btn">My Resumes</button></li>
                    ) : (
                        <li><button onClick={() => history.push('/auth')} className="nav-btn">Sign In</button></li>
                    )}
                </ul>
            </nav>
            <header id="hero" className="hero-section">
                <h2>Create Your Perfect Resume</h2>
                <p>Get started with our easy-to-use tools and make your resume stand out.</p>
                <button className="cta-button" onClick={handleGetStarted}>Get Started</button>
            </header>
            <section id="features" className="features-grid">
                <h3>Features</h3>
                <div className="feature">
                    <h4>Easy to use</h4>
                    <p>Our interface is user-friendly and intuitive.</p>
                </div>
                <div className="feature">
                    <h4>Customization</h4>
                    <p>Modify templates to fit your style and needs.</p>
                </div>
                <div className="feature">
                    <h4>Save and Export</h4>
                    <p>Save your progress and export your resume in various formats.</p>
                </div>
            </section>
            <section id="pricing" className="pricing-cards">
                <h3>Pricing</h3>
                <div className="card">
                    <h4>Free</h4>
                    <p>Basic templates</p>
                    <button>Select</button>
                </div>
                <div className="card">
                    <h4>Pro</h4>
                    <p>All templates + Premium support</p>
                    <button>Select</button>
                </div>
                <div className="card">
                    <h4>Enterprise</h4>
                    <p>Custom solutions for businesses</p>
                    <button>Select</button>
                </div>
            </section>
        </div>
    );
};

export default LandingPage;