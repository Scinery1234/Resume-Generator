import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import AuthPage from '../pages/AuthPage';
import { authAPI } from '../services/api';

// Mock the api module
jest.mock('../services/api', () => ({
    authAPI: {
        login:  jest.fn(),
        signup: jest.fn(),
    },
}));

// Mock react-router-dom's useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
    ...jest.requireActual('react-router-dom'),
    useNavigate: () => mockNavigate,
}));

const renderAuth = () =>
    render(
        <MemoryRouter>
            <AuthPage />
        </MemoryRouter>
    );

beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
});

describe('AuthPage – Sign In mode (default)', () => {
    test('renders Sign In heading and form', () => {
        renderAuth();
        expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/email/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/password/i)).toBeInTheDocument();
        expect(screen.queryByPlaceholderText(/full name/i)).not.toBeInTheDocument();
    });

    test('shows error on failed login', async () => {
        authAPI.login.mockRejectedValueOnce({
            response: { data: { detail: 'Invalid email or password' } },
        });
        renderAuth();
        await userEvent.type(screen.getByPlaceholderText(/email/i), 'bad@bad.com');
        await userEvent.type(screen.getByPlaceholderText(/password/i), 'wrongpass');
        fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
        await waitFor(() =>
            expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
        );
    });

    test('navigates to /wizard on successful login', async () => {
        authAPI.login.mockResolvedValueOnce({
            status: 'success', token: '3', user_id: 3,
        });
        renderAuth();
        await userEvent.type(screen.getByPlaceholderText(/email/i), 'user@test.com');
        await userEvent.type(screen.getByPlaceholderText(/password/i), 'pass123');
        fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
        await waitFor(() => {
            expect(localStorage.getItem('token')).toBe('3');
            expect(mockNavigate).toHaveBeenCalledWith('/wizard');
        });
    });
});

describe('AuthPage – Sign Up mode', () => {
    test('shows name field after switching to Sign Up', async () => {
        renderAuth();
        fireEvent.click(screen.getByRole('button', { name: /sign up/i }));
        expect(screen.getByPlaceholderText(/full name/i)).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: /sign up/i })).toBeInTheDocument();
    });

    test('calls signup with name, email, password', async () => {
        authAPI.signup.mockResolvedValueOnce({
            status: 'success', token: '10', user_id: 10,
        });
        renderAuth();
        fireEvent.click(screen.getByRole('button', { name: /sign up/i }));
        await userEvent.type(screen.getByPlaceholderText(/full name/i), 'Jane Smith');
        await userEvent.type(screen.getByPlaceholderText(/email/i), 'jane@test.com');
        await userEvent.type(screen.getByPlaceholderText(/password/i), 'secure123');
        fireEvent.click(screen.getByRole('button', { name: /sign up/i }));
        await waitFor(() => {
            expect(authAPI.signup).toHaveBeenCalledWith('Jane Smith', 'jane@test.com', 'secure123');
            expect(mockNavigate).toHaveBeenCalledWith('/wizard');
        });
    });

    test('displays error message on signup failure', async () => {
        authAPI.signup.mockRejectedValueOnce({
            response: { data: { detail: 'Email already registered' } },
        });
        renderAuth();
        fireEvent.click(screen.getByRole('button', { name: /sign up/i }));
        await userEvent.type(screen.getByPlaceholderText(/full name/i), 'Bob');
        await userEvent.type(screen.getByPlaceholderText(/email/i), 'bob@test.com');
        await userEvent.type(screen.getByPlaceholderText(/password/i), 'pass1234');
        fireEvent.click(screen.getByRole('button', { name: /sign up/i }));
        await waitFor(() =>
            expect(screen.getByText(/email already registered/i)).toBeInTheDocument()
        );
    });
});

describe('AuthPage – Guest mode', () => {
    test('clears existing auth and navigates to wizard', async () => {
        localStorage.setItem('token', 'stale-token');
        localStorage.setItem('userId', '42');
        renderAuth();

        fireEvent.click(screen.getByRole('button', { name: /continue as guest/i }));

        expect(localStorage.getItem('token')).toBeNull();
        expect(localStorage.getItem('userId')).toBeNull();
        expect(mockNavigate).toHaveBeenCalledWith('/wizard');
    });
});
