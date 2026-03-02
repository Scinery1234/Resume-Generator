import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import WizardPage from '../pages/WizardPage';
import { resumeAPI } from '../services/api';

jest.mock('../services/api', () => ({
    resumeAPI: {
        generate:         jest.fn(),
        preview:          jest.fn(),
        downloadByFilename: jest.fn(),
        download:         jest.fn(),
    },
}));

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
    ...jest.requireActual('react-router-dom'),
    useNavigate: () => mockNavigate,
}));

// preview returns minimal HTML by default
beforeEach(() => {
    jest.clearAllMocks();
    resumeAPI.preview.mockResolvedValue('<html><body>Preview</body></html>');
    localStorage.clear();
});

const renderWizard = () =>
    render(
        <MemoryRouter>
            <WizardPage />
        </MemoryRouter>
    );

// ── Step rendering ────────────────────────────────────────────────────────
describe('Step 0 – Personal Info', () => {
    test('renders all required personal info fields', () => {
        renderWizard();
        expect(screen.getByPlaceholderText(/jane smith/i)).toBeInTheDocument(); // name
        expect(screen.getByPlaceholderText(/jane\.smith@email\.com/i)).toBeInTheDocument(); // email
        expect(screen.getByPlaceholderText(/0412 345 678/i)).toBeInTheDocument(); // phone
        expect(screen.getByPlaceholderText(/melbourne, vic/i)).toBeInTheDocument(); // location
        expect(screen.getByPlaceholderText(/linkedin\.com/i)).toBeInTheDocument(); // linkedin
        expect(screen.getByRole('textbox', { name: /professional summary/i })).toBeInTheDocument();
    });

    test('shows validation error when required fields are empty', async () => {
        renderWizard();
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() =>
            expect(screen.getByRole('alert')).toHaveTextContent(/full name is required/i)
        );
    });

    test('shows validation error for missing professional summary', async () => {
        renderWizard();
        await userEvent.type(screen.getByPlaceholderText(/jane smith/i), 'Test User');
        await userEvent.type(screen.getByPlaceholderText(/jane\.smith@email\.com/i), 'test@test.com');
        await userEvent.type(screen.getByPlaceholderText(/0412/i), '0412000000');
        await userEvent.type(screen.getByPlaceholderText(/melbourne/i), 'Sydney, NSW');
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() =>
            expect(screen.getByRole('alert')).toHaveTextContent(/professional summary is required/i)
        );
    });

    test('advances to step 2 when all required fields are filled', async () => {
        renderWizard();
        await userEvent.type(screen.getByPlaceholderText(/jane smith/i), 'Jane Smith');
        await userEvent.type(screen.getByPlaceholderText(/jane\.smith@email\.com/i), 'jane@test.com');
        await userEvent.type(screen.getByPlaceholderText(/0412/i), '0412345678');
        await userEvent.type(screen.getByPlaceholderText(/melbourne/i), 'Brisbane, QLD');
        await userEvent.type(
            screen.getByRole('textbox', { name: /professional summary/i }),
            'Experienced developer with 5 years in fintech.'
        );
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() =>
            expect(screen.getByText(/step 2 of 5/i)).toBeInTheDocument()
        );
    });
});

describe('Step 1 – Education', () => {
    const goToStep1 = async () => {
        renderWizard();
        await userEvent.type(screen.getByPlaceholderText(/jane smith/i), 'Jane Smith');
        await userEvent.type(screen.getByPlaceholderText(/jane\.smith@email\.com/i), 'j@j.com');
        await userEvent.type(screen.getByPlaceholderText(/0412/i), '0400000000');
        await userEvent.type(screen.getByPlaceholderText(/melbourne/i), 'Perth, WA');
        await userEvent.type(screen.getByRole('textbox', { name: /professional summary/i }), 'Summary text here.');
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() => expect(screen.getByText(/step 2 of 5/i)).toBeInTheDocument());
    };

    test('renders education form fields', async () => {
        await goToStep1();
        expect(screen.getByPlaceholderText(/bachelor of computer science/i)).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/university of melbourne/i)).toBeInTheDocument();
    });

    test('validates degree and institution are required', async () => {
        await goToStep1();
        fireEvent.click(screen.getByRole('button', { name: /\+ add education/i }));
        await waitFor(() =>
            expect(screen.getByRole('alert')).toHaveTextContent(/degree and institution are required/i)
        );
    });

    test('adds an education entry to the list', async () => {
        await goToStep1();
        await userEvent.type(screen.getByPlaceholderText(/bachelor of computer science/i), 'B.Sc. Computer Science');
        await userEvent.type(screen.getByPlaceholderText(/university of melbourne/i), 'University of Sydney');
        await userEvent.type(screen.getByPlaceholderText(/software engineering/i), 'Software Engineering');
        await userEvent.type(screen.getByPlaceholderText(/2020/i), '2022');
        fireEvent.click(screen.getByRole('button', { name: /\+ add education/i }));
        await waitFor(() => {
            expect(screen.getByText(/b\.sc\. computer science/i)).toBeInTheDocument();
            expect(screen.getByText(/university of sydney/i)).toBeInTheDocument();
        });
    });

    test('removes an education entry', async () => {
        await goToStep1();
        await userEvent.type(screen.getByPlaceholderText(/bachelor of computer science/i), 'MBA');
        await userEvent.type(screen.getByPlaceholderText(/university of melbourne/i), 'RMIT');
        fireEvent.click(screen.getByRole('button', { name: /\+ add education/i }));
        await waitFor(() => expect(screen.getByText(/mba/i)).toBeInTheDocument());
        fireEvent.click(screen.getByRole('button', { name: /remove mba/i }));
        await waitFor(() => expect(screen.queryByText(/mba/i)).not.toBeInTheDocument());
    });
});

describe('Step 3 – Skills', () => {
    const goToSkillsStep = async () => {
        renderWizard();
        // Step 0
        await userEvent.type(screen.getByPlaceholderText(/jane smith/i), 'Test');
        await userEvent.type(screen.getByPlaceholderText(/jane\.smith@email\.com/i), 'a@b.com');
        await userEvent.type(screen.getByPlaceholderText(/0412/i), '0400000000');
        await userEvent.type(screen.getByPlaceholderText(/melbourne/i), 'Darwin, NT');
        await userEvent.type(screen.getByRole('textbox', { name: /professional summary/i }), 'Summary.');
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() => expect(screen.getByText(/step 2 of 5/i)).toBeInTheDocument());
        // Step 1 – skip (no required fields)
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() => expect(screen.getByText(/step 3 of 5/i)).toBeInTheDocument());
        // Step 2 – skip
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() => expect(screen.getByText(/step 4 of 5/i)).toBeInTheDocument());
    };

    test('adds a key skill tag', async () => {
        await goToSkillsStep();
        const input = screen.getByLabelText(/^add key skills$/i);
        await userEvent.type(input, 'Python');
        fireEvent.click(screen.getByRole('button', { name: /add key skills item/i }));
        await waitFor(() => expect(screen.getByText('Python')).toBeInTheDocument());
    });

    test('adds a skill on Enter key', async () => {
        await goToSkillsStep();
        const input = screen.getByLabelText(/^add key skills$/i);
        await userEvent.type(input, 'React{enter}');
        await waitFor(() => expect(screen.getByText('React')).toBeInTheDocument());
    });

    test('removes a skill tag', async () => {
        await goToSkillsStep();
        const input = screen.getByLabelText(/^add key skills$/i);
        await userEvent.type(input, 'Docker');
        fireEvent.click(screen.getByRole('button', { name: /add key skills item/i }));
        await waitFor(() => expect(screen.getByText('Docker')).toBeInTheDocument());
        fireEvent.click(screen.getByRole('button', { name: /remove docker/i }));
        await waitFor(() => expect(screen.queryByText('Docker')).not.toBeInTheDocument());
    });
});

describe('Step 4 – Preview & Export', () => {
    const goToPreviewStep = async () => {
        renderWizard();
        // Quickly navigate through all steps
        await userEvent.type(screen.getByPlaceholderText(/jane smith/i), 'Preview User');
        await userEvent.type(screen.getByPlaceholderText(/jane\.smith@email\.com/i), 'p@u.com');
        await userEvent.type(screen.getByPlaceholderText(/0412/i), '0400000000');
        await userEvent.type(screen.getByPlaceholderText(/melbourne/i), 'Adelaide, SA');
        await userEvent.type(screen.getByRole('textbox', { name: /professional summary/i }), 'Summary here.');
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() => expect(screen.getByText(/step 2 of 5/i)).toBeInTheDocument());
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() => expect(screen.getByText(/step 3 of 5/i)).toBeInTheDocument());
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() => expect(screen.getByText(/step 4 of 5/i)).toBeInTheDocument());
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
        await waitFor(() => expect(screen.getByText(/step 5 of 5/i)).toBeInTheDocument());
    };

    test('calls resumeAPI.preview when entering preview step', async () => {
        await goToPreviewStep();
        await waitFor(() => expect(resumeAPI.preview).toHaveBeenCalledTimes(1));
    });

    test('shows Generate DOCX button on preview step', async () => {
        await goToPreviewStep();
        expect(screen.getByRole('button', { name: /generate docx/i })).toBeInTheDocument();
    });

    test('shows Download DOCX after successful generation', async () => {
        resumeAPI.generate.mockResolvedValueOnce({
            status: 'success',
            data: { filename: 'preview_user_resume.docx', resume_id: null },
        });
        await goToPreviewStep();
        fireEvent.click(screen.getByRole('button', { name: /generate docx/i }));
        await waitFor(() =>
            expect(screen.getByRole('button', { name: /download docx/i })).toBeInTheDocument()
        );
    });

    test('shows error on generate failure', async () => {
        resumeAPI.generate.mockRejectedValueOnce({
            response: { data: { detail: 'Server error' } },
        });
        await goToPreviewStep();
        fireEvent.click(screen.getByRole('button', { name: /generate docx/i }));
        await waitFor(() =>
            expect(screen.getByRole('alert')).toHaveTextContent(/server error/i)
        );
    });

    test('renders preview iframe when preview HTML loads', async () => {
        await goToPreviewStep();
        await waitFor(() =>
            expect(screen.getByTitle('Resume Preview')).toBeInTheDocument()
        );
    });
});

describe('Navigation', () => {
    test('Previous button is disabled on step 1', () => {
        renderWizard();
        expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
    });

    test('Home button navigates to /', () => {
        renderWizard();
        fireEvent.click(screen.getByRole('button', { name: /back to home/i }));
        expect(mockNavigate).toHaveBeenCalledWith('/');
    });

    test('clicking a sidebar step navigates directly', async () => {
        renderWizard();
        // Click on "Education" in sidebar (index 1)
        const sidebar = screen.getByRole('complementary');
        const educationStep = within(sidebar).getByText('Education');
        fireEvent.click(educationStep);
        await waitFor(() => expect(screen.getByText(/step 2 of 5/i)).toBeInTheDocument());
    });
});
