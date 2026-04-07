import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { templateAPI } from '../services/api';
import './PreviewPage.css';

const TEMPLATE_META = [
    { id: 'modern',    name: 'Modern',    color: '#1a375e', desc: 'Navy sidebar — polished and professional' },
    { id: 'classic',   name: 'Classic',   color: '#1a1a1a', desc: 'Serif single-column — timeless and formal' },
    { id: 'creative',  name: 'Creative',  color: '#6b21a8', desc: 'Purple header band — bold and contemporary' },
    { id: 'minimal',   name: 'Minimal',   color: '#374151', desc: 'Clean single-column — understated and elegant' },
    { id: 'executive', name: 'Executive', color: '#b45309', desc: 'Charcoal sidebar — sharp and authoritative' },
];

export default function PreviewPage() {
    const navigate = useNavigate();
    const [previews, setPreviews]     = useState({});
    const [loading, setLoading]       = useState(true);
    const [error, setError]           = useState('');
    const [active, setActive]         = useState('modern');

    useEffect(() => {
        templateAPI.getPreviews()
            .then(data => {
                setPreviews(data);
                setLoading(false);
            })
            .catch(err => {
                setError('Could not load template previews. Is the backend running?');
                setLoading(false);
                console.error(err);
            });
    }, []);

    const activeMeta = TEMPLATE_META.find(t => t.id === active) || TEMPLATE_META[0];

    return (
        <div className="pp">
            {/* ── Nav ── */}
            <nav className="pp-nav">
                <div className="pp-nav__inner">
                    <button className="pp-nav__logo" onClick={() => navigate('/')}>
                        <svg width="26" height="26" viewBox="0 0 28 28" fill="none" aria-hidden="true">
                            <rect width="28" height="28" rx="8" fill="url(#ppLogoGrad)"/>
                            <path d="M7 8h14M7 12h10M7 16h12M7 20h8" stroke="#fff" strokeWidth="2" strokeLinecap="round"/>
                            <defs>
                                <linearGradient id="ppLogoGrad" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#0369a1"/>
                                    <stop offset="1" stopColor="#38bdf8"/>
                                </linearGradient>
                            </defs>
                        </svg>
                        ResumeGen
                    </button>
                    <button className="pp-nav__cta btn-primary" onClick={() => navigate('/wizard')}>
                        Try It Free
                    </button>
                </div>
            </nav>

            {/* ── Hero ── */}
            <header className="pp-hero">
                <h1 className="pp-hero__title">Resume Templates</h1>
                <p className="pp-hero__sub">
                    Five professionally designed layouts — each rendered with real content so you can see exactly what your resume will look like.
                </p>
            </header>

            {/* ── Template tabs ── */}
            <div className="pp-tabs" role="tablist" aria-label="Resume templates">
                {TEMPLATE_META.map(t => (
                    <button
                        key={t.id}
                        role="tab"
                        aria-selected={active === t.id}
                        className={`pp-tab${active === t.id ? ' pp-tab--active' : ''}`}
                        style={{ '--tab-color': t.color }}
                        onClick={() => setActive(t.id)}
                    >
                        <span className="pp-tab__dot" style={{ background: t.color }} />
                        {t.name}
                    </button>
                ))}
            </div>

            {/* ── Description strip ── */}
            <div className="pp-desc-strip" style={{ borderColor: activeMeta.color }}>
                <span className="pp-desc-strip__name" style={{ color: activeMeta.color }}>
                    {activeMeta.name}
                </span>
                <span className="pp-desc-strip__sep">—</span>
                <span className="pp-desc-strip__text">{activeMeta.desc}</span>
                <button
                    className="pp-desc-strip__cta btn-primary"
                    onClick={() => navigate('/wizard')}
                >
                    Use This Template
                </button>
            </div>

            {/* ── Preview frame ── */}
            <main className="pp-stage" role="tabpanel">
                {loading && (
                    <div className="pp-loading">
                        <div className="pp-loading__spinner" />
                        <p>Loading previews…</p>
                    </div>
                )}

                {error && (
                    <div className="pp-error">
                        <p>{error}</p>
                        <button className="btn-primary" onClick={() => navigate('/wizard')}>
                            Go to Wizard
                        </button>
                    </div>
                )}

                {!loading && !error && previews[active] && (
                    <div className="pp-frame-wrap">
                        <iframe
                            key={active}
                            title={`${activeMeta.name} template preview`}
                            srcDoc={previews[active]}
                            className="pp-frame"
                            sandbox="allow-same-origin"
                        />
                    </div>
                )}
            </main>

            {/* ── Footer CTA ── */}
            <section className="pp-footer-cta">
                <h2>Ready to build your resume?</h2>
                <p>Upload your existing resume (or start from scratch) and let AI tailor it to any job description.</p>
                <div className="pp-footer-cta__actions">
                    <button className="btn-primary pp-footer-cta__btn" onClick={() => navigate('/wizard')}>
                        Get Started Free
                    </button>
                    <button className="pp-footer-cta__link" onClick={() => navigate('/')}>
                        Learn more
                    </button>
                </div>
            </section>
        </div>
    );
}
