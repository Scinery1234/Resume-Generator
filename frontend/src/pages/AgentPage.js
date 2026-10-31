import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { downloadBlob } from '../utils/fileDownload';
import './AgentPage.css';

// The four-phase Australian resume agent (see docs/RESUME_AGENT_SPEC.md):
// draft -> "Approve content?" -> Yes -> Phase 2 JSON, then the script runs and the .docx is checked.
// The server holds the rules and the gates; this page shows the conversation.

const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const STORE = 'resume-agent-v1';
const QUICK = { AWAITING_CONTENT_APPROVAL: 'Yes', EXECUTION_FAILED: 'Try again' };
// Replies that approve the content, which also builds the Word file (for the busy message only).
const APPROVAL = /^(y|yes|yep|yeah|approved?|looks good|proceed|go ahead|content approved|perfect|lgtm|try again|retry)\b/i;

const b64ToBlob = (b64, type) => new Blob([Uint8Array.from(atob(b64), c => c.charCodeAt(0))], { type });

async function post(url, body, config = {}) {
    const res = await api.post(url, body, { timeout: 300000, ...config });
    if (res.status >= 400) throw new Error(res.data?.detail || 'Something went wrong. Please try again.');
    return res.data;
}

const load = () => { try { return JSON.parse(sessionStorage.getItem(STORE)) || null; } catch { return null; } };
const save = v => { try { v ? sessionStorage.setItem(STORE, JSON.stringify(v)) : sessionStorage.removeItem(STORE); } catch { /* storage unavailable */ } };

function UploadButton({ id, label, busy, onText, onError }) {
    const pick = async e => {
        const file = e.target.files[0];
        e.target.value = '';
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) return onError('That file is over 5 MB. Try a smaller one, or paste the text.');
        busy(true);
        try {
            const form = new FormData();
            form.append('file', file);
            const d = await post('/api/agent/extract', form, { headers: { 'Content-Type': 'multipart/form-data' } });
            onText(d.text, file.name);
        } catch (err) { onError(err.message); }
        busy(false);
    };
    return (
        <label className="agent-upload" htmlFor={id}>
            <input id={id} type="file" accept=".pdf,.docx,.txt,.md" onChange={pick} />
            {label}
        </label>
    );
}

function AgentMessage({ m }) {
    if (m.role === 'user') return <div className="agent-msg agent-msg--user">{m.text}</div>;
    switch (m.kind) {
        case 'draft':
            return (
                <div className="agent-msg">
                    <p className="agent-label">Draft resume</p>
                    <pre className="agent-draft">{m.text}</pre>
                    {m.notes?.length > 0 && (
                        <div className="agent-notes">
                            <b>To confirm (proposed wording, not yet verified):</b>
                            <ul>{m.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
                        </div>
                    )}
                    <p className="agent-prompt">{m.prompt}</p>
                </div>
            );
        case 'questions':
            return (
                <div className="agent-msg">
                    <p>{m.text}</p>
                    <ol>{m.questions.map((q, i) => <li key={i}>{q}</li>)}</ol>
                </div>
            );
        case 'json':
            return (
                <div className="agent-msg">
                    <p className="agent-label">{m.heading}</p>
                    <pre className="agent-json">{m.json}</pre>
                </div>
            );
        case 'result':
            return (
                <div className={`agent-msg ${m.ok ? 'agent-msg--ok' : 'agent-msg--fail'}`}>
                    <p className="agent-prompt">{m.message}</p>
                    {m.ok && (
                        <div className="agent-actions">
                            <button className="btn-primary" onClick={() => downloadBlob(b64ToBlob(m.docx, DOCX), m.filename)}>Download {m.filename}</button>
                        </div>
                    )}
                    {!m.ok && <p>Reply “Try again” and I will correct the script and run it again.</p>}
                    {m.validation && (
                        <details>
                            <summary>Checks on the Word file ({m.validation.checks.filter(c => c.ok).length} of {m.validation.checks.length} passed)</summary>
                            <ul className="agent-checks">
                                {m.validation.checks.map((c, i) => <li key={i} className={c.ok ? 'ok' : 'bad'}>{c.ok ? '✓' : '✗'} {c.name}{c.detail && !c.ok ? `: ${c.detail}` : ''}</li>)}
                            </ul>
                            <p className="agent-small">{m.visual?.performed ? `Visual check: rendered ${m.visual.pages} page(s)${m.visual.problems.length ? `; ${m.visual.problems.join(' ')}` : ', no blank pages or stranded headings.'}` : m.visual?.reason}</p>
                        </details>
                    )}
                </div>
            );
        default:
            return <div className="agent-msg"><p>{m.text}</p></div>;
    }
}

const AgentPage = () => {
    const navigate = useNavigate();
    const saved = load();
    const [form, setForm] = useState(saved?.form || { materials: '', job_description: '', target_title: '', additional: '' });
    const [conv, setConv] = useState(saved?.conv || null); // {session, state, messages}
    const [reply, setReply] = useState('');
    const [busy, setBusy] = useState('');
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');
    const [note, setNote] = useState('');
    const [ai, setAi] = useState(true);
    const end = useRef(null);

    useEffect(() => { api.get('/api/agent/status').then(r => setAi(!!r.data?.ai)).catch(() => {}); }, []);
    // Keep the conversation across a refresh, without the large Word file.
    useEffect(() => save(conv ? { form, conv: { ...conv, messages: conv.messages.map(m => (m.docx ? { ...m, docx: '', ok: m.ok, stale: true } : m)) } } : { form }), [form, conv]);
    useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [conv?.messages.length, busy]);

    const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

    const start = async e => {
        e.preventDefault();
        if (form.materials.trim().length < 80) return setError('Add your current resume or career notes first: upload a file or paste your roles, dates and achievements.');
        setError(''); setBusy('Drafting your resume. This can take up to a minute.');
        try {
            const d = await post('/api/agent/start', form);
            setConv({ session: d.session, state: d.state, messages: d.messages.map(m => ({ role: 'agent', ...m })) });
        } catch (err) { setError(err.message); }
        setBusy('');
    };

    const send = async text => {
        const msg = (text ?? reply).trim();
        if (!msg || busy) return;
        const generating = conv.state !== 'DRAFTING' && APPROVAL.test(msg) && msg.split(/\s+/).length <= 4;
        setError(''); setReply('');
        setConv(c => ({ ...c, messages: [...c.messages, { role: 'user', text: msg }] }));
        setBusy(generating ? 'Building your Word resume and checking it…' : 'Working on it…');
        try {
            const d = await post('/api/agent/reply', { session: conv.session, message: msg });
            setConv(c => ({ session: d.session, state: d.state, messages: [...c.messages, ...d.messages.map(m => ({ role: 'agent', ...m }))] }));
        } catch (err) { setError(err.message); }
        setBusy('');
    };

    const startOver = () => { setConv(null); setReply(''); setError(''); };

    return (
        <div className="gen-page agent-page">
            <nav className="gen-nav">
                <button className="gen-nav__back" onClick={() => navigate('/')}>← Home</button>
                <span className="gen-nav__logo">Australian Resume Writer</span>
                {conv ? <button className="gen-nav__back" onClick={startOver}>Start over</button> : <span />}
            </nav>
            <main className="agent-main">
                {!ai && <p className="agent-error">The resume writer isn't switched on for this site yet (no Anthropic API key).</p>}
                {!conv && (
                    <form className="agent-card" onSubmit={start}>
                        <h1>Write my Australian resume</h1>
                        <p className="agent-small">You'll see a full draft first. Nothing goes into Word until you approve the content; once you reply Yes, the Word file is built and checked straight away. Everything comes from your own materials: nothing is invented.</p>

                        <div className="agent-field">
                            <div className="agent-field__head"><b>1. Your current resume or career notes</b>
                                <UploadButton id="up-cv" label={uploading ? 'Reading…' : 'Upload (PDF, Word, text)'} busy={setUploading} onError={setError}
                                    onText={(t, n) => { setForm(f => ({ ...f, materials: f.materials ? `${f.materials}\n\n${t}` : t })); setNote(`Added ${n}. Check the text below; PDFs can come out a little jumbled.`); }} />
                            </div>
                            <textarea rows={9} value={form.materials} onChange={set('materials')} placeholder="Roles, employers, dates, achievements, qualifications, certificates, LinkedIn text…" />
                        </div>

                        <div className="agent-field">
                            <div className="agent-field__head"><b>2. The job description (optional)</b>
                                <UploadButton id="up-jd" label="Upload the job ad (PDF, Word)" busy={setUploading} onError={setError}
                                    onText={(t, n) => { setForm(f => ({ ...f, job_description: t })); setNote(`Loaded the job description from ${n}.`); }} />
                            </div>
                            <textarea rows={6} value={form.job_description} onChange={set('job_description')} placeholder="Paste or upload the job ad or position description for a tailored resume." />
                        </div>

                        <label className="agent-field"><b>3. Target job title (optional)</b>
                            <input type="text" value={form.target_title} onChange={set('target_title')} placeholder="e.g. Operations Manager" maxLength={200} />
                        </label>
                        <label className="agent-field"><b>Anything else to include? (optional)</b>
                            <textarea rows={3} value={form.additional} onChange={set('additional')} placeholder="Work rights, licences, availability, a project not on your old resume…" />
                        </label>

                        {note && <p className="agent-small">{note}</p>}
                        {error && <p className="agent-error" role="alert">{error}</p>}
                        <button className="btn-primary" type="submit" disabled={!!busy || uploading}>{busy || 'Draft my resume'}</button>
                    </form>
                )}

                {conv && (
                    <div className="agent-conv">
                        {conv.messages.map((m, i) => (m.stale ? <div className="agent-msg" key={i}><p>{m.message}</p><p className="agent-small">Reply “Try again” to build the file again.</p></div> : <AgentMessage key={i} m={m} />))}
                        {busy && <p className="agent-busy" aria-live="polite">{busy}</p>}
                        {error && <p className="agent-error" role="alert">{error}</p>}
                        <form className="agent-reply" onSubmit={e => { e.preventDefault(); send(); }}>
                            {QUICK[conv.state] && <button type="button" className="btn-primary" disabled={!!busy} onClick={() => send(QUICK[conv.state])}>{QUICK[conv.state]}</button>}
                            <textarea rows={2} value={reply} onChange={e => setReply(e.target.value)} disabled={!!busy}
                                placeholder={conv.state === 'DRAFTING' ? 'Answer the questions here' : 'Type your reply or the amendments you want'}
                                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} />
                            <button type="submit" className="btn-secondary" disabled={!!busy || !reply.trim()}>Send</button>
                        </form>
                        <div ref={end} />
                    </div>
                )}
            </main>
        </div>
    );
};

export default AgentPage;
