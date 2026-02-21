import React, { useState } from 'react';
import { useHistory } from 'react-router-dom';
import './AuthPage.css';
import { authAPI } from '../services/api';

const AuthPage = () => {
    const history = useHistory();
    const [isSignIn, setIsSignIn] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        
        try {
            let response;
            if (isSignIn) {
                response = await authAPI.login(email, password);
            } else {
                response = await authAPI.signup(name, email, password);
            }
            
            if (response.status === 'success') {
                // Store token and user ID
                localStorage.setItem('token', response.token);
                localStorage.setItem('userId', response.user_id);
                // Redirect to wizard
                history.push('/wizard');
            }
        } catch (err) {
            setError(err.response?.data?.detail || 'An error occurred. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-container">
                <h1>{isSignIn ? 'Sign In' : 'Sign Up'}</h1>
                {error && <div className="error-message">{error}</div>}
                <form onSubmit={handleSubmit} className="auth-form">
                    {!isSignIn && (
                        <input 
                            type="text" 
                            placeholder="Full Name" 
                            value={name} 
                            onChange={(e) => setName(e.target.value)} 
                            required 
                        />
                    )}
                    <input 
                        type="email" 
                        placeholder="Email" 
                        value={email} 
                        onChange={(e) => setEmail(e.target.value)} 
                        required 
                    />
                    <input 
                        type="password" 
                        placeholder="Password" 
                        value={password} 
                        onChange={(e) => setPassword(e.target.value)} 
                        required 
                        minLength={6}
                    />
                    <button type="submit" disabled={loading}>
                        {loading ? 'Processing...' : (isSignIn ? 'Sign In' : 'Sign Up')}
                    </button>
                </form>
                <p className="toggle-text">
                    {isSignIn ? "Don't have an account? " : 'Already have an account? '}
                    <button 
                        type="button" 
                        className="toggle-button" 
                        onClick={() => {
                            setIsSignIn(!isSignIn);
                            setError('');
                        }}
                    >
                        {isSignIn ? 'Sign Up' : 'Sign In'}
                    </button>
                </p>
            </div>
        </div>
    );
};

export default AuthPage;
