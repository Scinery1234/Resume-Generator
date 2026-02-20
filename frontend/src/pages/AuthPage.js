import React, { useState } from 'react';
import './AuthPage.css';

const AuthPage = () => {
    const [isSignIn, setIsSignIn] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (isSignIn) {
            console.log('Sign in:', { email, password });
        } else {
            console.log('Sign up:', { name, email, password });
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-container">
                <h1>{isSignIn ? 'Sign In' : 'Sign Up'}</h1>
                <form onSubmit={handleSubmit} className="auth-form">
                    {!isSignIn && (
                        <input type="text" placeholder="Full Name" value={name} onChange={(e) => setName(e.target.value)} required />
                    )}
                    <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                    <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                    <button type="submit"> {isSignIn ? 'Sign In' : 'Sign Up'} </button>
                </form>
                <p className="toggle-text">
                    {isSignIn ? "Don't have an account? " : 'Already have an account? '}
                    <button type="button" className="toggle-button" onClick={() => setIsSignIn(!isSignIn)}>
                        {isSignIn ? 'Sign Up' : 'Sign In'}
                    </button>
                </p>
            </div>
        </div>
    );
};

export default AuthPage;