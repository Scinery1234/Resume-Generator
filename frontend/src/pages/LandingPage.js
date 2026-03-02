import React from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

const LandingPage = () => {
    const navigate = useNavigate();
    const token = localStorage.getItem('token');

    const handleGetStarted = () => {
        navigate(token ? '/wizard' : '/auth');
    };

    return (
        <div className="lp">
            {/* ── Navbar ── */}
            <nav className="lp-nav">
                <div className="lp-nav__inner">
                    <span className="lp-nav__logo">
                        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
                            <rect width="28" height="28" rx="8" fill="url(#logoGrad)"/>
                            <path d="M7 8h14M7 12h10M7 16h12M7 20h8" stroke="#fff" strokeWidth="2" strokeLinecap="round"/>
                            <defs>
                                <linearGradient id="logoGrad" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#0369a1"/>
                                    <stop offset="1" stopColor="#38bdf8"/>
                                </linearGradient>
                            </defs>
                        </svg>
                        ResumeGen
                    </span>
                    <ul className="lp-nav__links">
                        <li><a href="#features">Features</a></li>
                        <li><a href="#how-it-works">How it works</a></li>
                        <li><a href="#pricing">Pricing</a></li>
                    </ul>
                    <button
                        className="btn-primary lp-nav__cta"
                        onClick={() => navigate(token ? '/wizard' : '/auth')}
                    >
                        {token ? 'My Resumes' : 'Sign In'}
                    </button>
                </div>
            </nav>

            {/* ── Hero ── */}
            <header className="lp-hero" id="hero">
                <div className="lp-hero__bg-dots" aria-hidden="true" />
                <div className="lp-hero__inner">
                    <span className="lp-hero__badge">AI-Powered Resume Builder</span>
                    <h1 className="lp-hero__title">
                        Build a Resume That<br />
                        <span className="lp-hero__title-accent">Gets You Hired</span>
                    </h1>
                    <p className="lp-hero__subtitle">
                        Create a professional, tailored resume in minutes. No design skills needed —
                        just fill in your details and let our AI do the rest.
                    </p>
                    <div className="lp-hero__actions">
                        <button className="btn-primary lp-hero__btn-main" onClick={handleGetStarted}>
                            Get Started Free
                            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                                <path d="M3.75 9h10.5M9.75 4.5 14.25 9l-4.5 4.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                        </button>
                        <a href="#how-it-works" className="lp-hero__link">See how it works</a>
                    </div>
                    <p className="lp-hero__note">No credit card required · Free plan available</p>
                </div>
            </header>

            {/* ── Features ── */}
            <section className="lp-features" id="features">
                <div className="lp-section-inner">
                    <p className="lp-eyebrow">Why choose us</p>
                    <h2 className="lp-section-title">Everything you need to land the job</h2>
                    <div className="lp-features__grid">
                        {[
                            {
                                icon: (
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    </svg>
                                ),
                                title: 'Lightning Fast',
                                body: 'Go from blank page to polished resume in under 10 minutes with our guided step-by-step wizard.',
                            },
                            {
                                icon: (
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                        <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" strokeWidth="2"/>
                                        <path d="M8 12h8M8 8h5M8 16h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                                    </svg>
                                ),
                                title: 'Fully Customisable',
                                body: "Tailor every section — skills, experience, education — to match the exact role you're applying for.",
                            },
                            {
                                icon: (
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                        <path d="M12 3v12M8 11l4 4 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                        <path d="M3 19h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                                    </svg>
                                ),
                                title: 'Export as Word',
                                body: 'Download a professionally formatted .docx file, ready to email or upload to any job board.',
                            },
                            {
                                icon: (
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2"/>
                                        <path d="M12 8v4l3 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                                    </svg>
                                ),
                                title: 'Save Your Progress',
                                body: 'Your resumes are saved to your account so you can revisit, update, and re-download at any time.',
                            },
                            {
                                icon: (
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    </svg>
                                ),
                                title: 'AI-Enhanced Content',
                                body: "Our AI suggests impactful bullet points and summary text so your resume speaks the language recruiters love.",
                            },
                            {
                                icon: (
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    </svg>
                                ),
                                title: 'Secure & Private',
                                body: 'Your data is stored securely and never shared. You own your information — delete it any time.',
                            },
                        ].map((f, i) => (
                            <div key={i} className="lp-feature-card card">
                                <div className="lp-feature-card__icon">{f.icon}</div>
                                <h3 className="lp-feature-card__title">{f.title}</h3>
                                <p className="lp-feature-card__body">{f.body}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── How It Works ── */}
            <section className="lp-how" id="how-it-works">
                <div className="lp-section-inner">
                    <p className="lp-eyebrow">Simple process</p>
                    <h2 className="lp-section-title">Three steps to your next job</h2>
                    <div className="lp-how__steps">
                        {[
                            { n: '01', title: 'Create an account', body: 'Sign up for free in seconds — no credit card required.' },
                            { n: '02', title: 'Fill in your details', body: 'Work through our guided wizard: personal info, experience, education, and skills.' },
                            { n: '03', title: 'Download your resume', body: 'Generate a polished Word document and start applying with confidence.' },
                        ].map((s) => (
                            <div key={s.n} className="lp-how__step">
                                <span className="lp-how__step-num">{s.n}</span>
                                <h3 className="lp-how__step-title">{s.title}</h3>
                                <p className="lp-how__step-body">{s.body}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Pricing ── */}
            <section className="lp-pricing" id="pricing">
                <div className="lp-section-inner">
                    <p className="lp-eyebrow">Pricing</p>
                    <h2 className="lp-section-title">Start free, upgrade when ready</h2>
                    <div className="lp-pricing__grid">
                        {[
                            {
                                name: 'Free',
                                price: '$0',
                                period: 'forever',
                                desc: 'Perfect for getting started.',
                                features: ['1 resume', 'Basic template', 'Word export', 'Email support'],
                                highlighted: false,
                            },
                            {
                                name: 'Pro',
                                price: '$9',
                                period: 'per month',
                                desc: 'For serious job seekers.',
                                features: ['Unlimited resumes', 'All templates', 'AI enhancements', 'Priority support'],
                                highlighted: true,
                            },
                            {
                                name: 'Enterprise',
                                price: 'Custom',
                                period: '',
                                desc: 'For teams and organisations.',
                                features: ['Bulk generation', 'Custom branding', 'Dedicated account manager', 'SLA guarantee'],
                                highlighted: false,
                            },
                        ].map((p, i) => (
                            <div key={i} className={`lp-pricing-card card${p.highlighted ? ' lp-pricing-card--highlight' : ''}`}>
                                {p.highlighted && <span className="lp-pricing-card__badge">Most Popular</span>}
                                <h3 className="lp-pricing-card__name">{p.name}</h3>
                                <div className="lp-pricing-card__price">
                                    {p.price}
                                    {p.period && <span className="lp-pricing-card__period"> / {p.period}</span>}
                                </div>
                                <p className="lp-pricing-card__desc">{p.desc}</p>
                                <ul className="lp-pricing-card__features">
                                    {p.features.map((f, j) => (
                                        <li key={j}>
                                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                                                <path d="M3 8l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                            </svg>
                                            {f}
                                        </li>
                                    ))}
                                </ul>
                                <button
                                    className={p.highlighted ? 'btn-primary' : 'btn-secondary'}
                                    onClick={handleGetStarted}
                                >
                                    {p.highlighted ? 'Get started' : 'Choose plan'}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── Footer ── */}
            <footer className="lp-footer">
                <div className="lp-footer__inner">
                    <span className="lp-footer__logo">
                        <svg width="22" height="22" viewBox="0 0 28 28" fill="none" aria-hidden="true">
                            <rect width="28" height="28" rx="8" fill="rgba(255,255,255,.15)"/>
                            <path d="M7 8h14M7 12h10M7 16h12M7 20h8" stroke="#fff" strokeWidth="2" strokeLinecap="round"/>
                        </svg>
                        ResumeGen
                    </span>
                    <p className="lp-footer__copy">&copy; {new Date().getFullYear()} ResumeGen. All rights reserved.</p>
                    <nav className="lp-footer__links" aria-label="Footer nav">
                        <a href="#features">Features</a>
                        <a href="#pricing">Pricing</a>
                        <button onClick={() => navigate('/auth')} className="lp-footer__nav-btn">Sign In</button>
                    </nav>
                </div>
            </footer>
        </div>
    );
};

export default LandingPage;
