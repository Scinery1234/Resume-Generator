import React from 'react';
import './LandingPage.css';

const LandingPage = () => {
  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="navbar">
        <h1>Resume Generator</h1>
        <ul>
          <li>Home</li>
          <li>Features</li>
          <li>Pricing</li>
          <li>Contact</li>
        </ul>
      </nav>

      {/* Hero Section */}
      <header className="hero">
        <h2>Create Your Resume in Minutes</h2>
        <p>Quick, easy, and professional resume building.</p>
        <button>Get Started</button>
      </header>

      {/* Features Grid */}
      <section className="features">
        <h3>Features</h3>
        <div className="features-grid">
          <div className="feature-card">
            <h4>Customizable Templates</h4>
            <p>Choose from various templates that fit your style.</p>
          </div>
          <div className="feature-card">
            <h4>Easy Editing</h4>
            <p>Intuitive editor that makes resume editing a breeze.</p>
          </div>
          <div className="feature-card">
            <h4>Download Options</h4>
            <p>Download your resume in PDF or Word format.</p>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pricing">
        <h3>Pricing</h3>
        <div className="pricing-cards">
          <div className="pricing-card">
            <h4>Free</h4>
            <p>Basic features at no cost.</p>
          </div>
          <div className="pricing-card">
            <h4>Pro</h4>
            <p>$9.99/month for advanced features.</p>
          </div>
          <div className="pricing-card">
            <h4>Enterprise</h4>
            <p>Contact us for custom solutions.</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer>
        <p>© 2026 Resume Generator. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default LandingPage;