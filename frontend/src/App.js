import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import WizardPage from './pages/WizardPage';

const App = () => {
    return (
        <Router>
            <Routes>
                <Route path='/' element={<LandingPage />} />
                <Route path='/auth' element={<AuthPage />} />
                <Route path='/wizard' element={<WizardPage />} />
            </Routes>
        </Router>
    );
};

export default App;
