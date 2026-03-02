import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import WizardPage from './pages/WizardPage';
import DiagnosticPage from './pages/DiagnosticPage';
import BackendDebugger from './components/BackendDebugger';

const App = () => {
    // Show debugger in production if API URL is set (helps diagnose issues)
    const showDebugger = process.env.NODE_ENV === 'production' && process.env.REACT_APP_API_URL;
    
    return (
        <Router>
            <Routes>
                <Route path='/' element={<LandingPage />} />
                <Route path='/auth' element={<AuthPage />} />
                <Route path='/wizard' element={<WizardPage />} />
                <Route path='/diagnostic' element={<DiagnosticPage />} />
            </Routes>
            {showDebugger && <BackendDebugger />}
        </Router>
    );
};

export default App;
