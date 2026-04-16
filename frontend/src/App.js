import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import WizardPage from './pages/WizardPage';
import MyResumesPage from './pages/MyResumesPage';
import PreviewPage from './pages/PreviewPage';
import BackendDebugger from './components/BackendDebugger';
import ErrorBoundary from './components/ErrorBoundary';

const App = () => {
    // Show debugger in production if API URL is set (helps diagnose issues)
    const showDebugger = process.env.NODE_ENV === 'production' && process.env.REACT_APP_API_URL;

    return (
        <ErrorBoundary>
            <Router>
                <Routes>
                    <Route path='/' element={<LandingPage />} />
                    <Route path='/auth' element={<AuthPage />} />
                    <Route path='/wizard' element={<WizardPage />} />
                    <Route path='/my-resumes' element={<MyResumesPage />} />
                    <Route path='/preview' element={<PreviewPage />} />
                </Routes>
                {showDebugger && <BackendDebugger />}
            </Router>
        </ErrorBoundary>
    );
};

export default App;
