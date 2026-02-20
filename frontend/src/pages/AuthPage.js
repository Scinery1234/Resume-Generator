import React, { useState } from 'react';

const AuthPage = () => {
    const [isSignIn, setIsSignIn] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    const handleSubmit = (event) => {
        event.preventDefault();
        // Handle sign in or sign up logic here
        console.log(`Email: ${email}, Password: ${password}`);
    };

    return (
        <div>
            <h1>{isSignIn ? 'Sign In' : 'Sign Up'}</h1>
            <form onSubmit={handleSubmit}>
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
                />
                <button type="submit">
                    {isSignIn ? 'Sign In' : 'Sign Up'}
                </button>
            </form>
            <button onClick={() => setIsSignIn(!isSignIn)}>
                {isSignIn ? 'Switch to Sign Up' : 'Switch to Sign In'}
            </button>
        </div>
    );
};

export default AuthPage;