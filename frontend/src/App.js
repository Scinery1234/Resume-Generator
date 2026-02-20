import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import WizardPage from './pages/WizardPage';

const App = () => {
  return (
    <Router>
      <Switch>
        <Route path='/' exact component={LandingPage} />
        <Route path='/auth' component={AuthPage} />
        <Route path='/wizard' component={WizardPage} />
      </Switch>
    </Router>
  );
};

export default App;