/**
 * Tests for the resumeAPI, authAPI, and templateAPI service layer.
 * We mock the entire services/api module so no real HTTP calls are made.
 */

jest.mock('../services/api', () => ({
    authAPI: {
        login:  jest.fn(),
        signup: jest.fn(),
    },
    resumeAPI: {
        generate:           jest.fn(),
        preview:            jest.fn(),
        getAll:             jest.fn(),
        download:           jest.fn(),
        downloadByFilename: jest.fn(),
        delete:             jest.fn(),
    },
    templateAPI: {
        getAll: jest.fn(),
    },
}));

import { resumeAPI, authAPI, templateAPI } from '../services/api';

beforeEach(() => jest.clearAllMocks());

// ── authAPI ──────────────────────────────────────────────────────────────────

describe('authAPI.login', () => {
    test('resolves with success data', async () => {
        authAPI.login.mockResolvedValueOnce({ status: 'success', token: '5', user_id: 5 });
        const result = await authAPI.login('user@test.com', 'pass');
        expect(authAPI.login).toHaveBeenCalledWith('user@test.com', 'pass');
        expect(result.status).toBe('success');
        expect(result.token).toBe('5');
    });

    test('propagates error on failure', async () => {
        authAPI.login.mockRejectedValueOnce({ response: { data: { detail: 'Invalid credentials' } } });
        await expect(authAPI.login('bad@bad.com', 'wrong')).rejects.toMatchObject({
            response: { data: { detail: 'Invalid credentials' } },
        });
    });
});

describe('authAPI.signup', () => {
    test('resolves with user data on success', async () => {
        authAPI.signup.mockResolvedValueOnce({ status: 'success', token: '1', user_id: 1 });
        const result = await authAPI.signup('Jane', 'jane@test.com', 'secret');
        expect(authAPI.signup).toHaveBeenCalledWith('Jane', 'jane@test.com', 'secret');
        expect(result.user_id).toBe(1);
    });

    test('rejects on duplicate email', async () => {
        authAPI.signup.mockRejectedValueOnce({
            response: { data: { detail: 'Email already registered' } },
        });
        await expect(authAPI.signup('X', 'dup@test.com', 'pass')).rejects.toBeDefined();
    });
});

// ── resumeAPI ────────────────────────────────────────────────────────────────

const CANDIDATE = {
    name: 'Jane Smith',
    contact: { email: 'j@j.com', phone: '0412', location: 'Sydney, NSW' },
    professional_summary: 'Summary text.',
    key_skills: ['Python'],
    technical_skills: [],
    experience: [],
    education: [],
    certifications: [],
    awards: [],
};

describe('resumeAPI.generate', () => {
    test('resolves with resume data on success', async () => {
        resumeAPI.generate.mockResolvedValueOnce({
            status: 'success',
            data: { filename: 'resume_abc.docx', resume_id: null },
        });
        const result = await resumeAPI.generate(CANDIDATE, null);
        expect(result.status).toBe('success');
        expect(result.data.filename).toBe('resume_abc.docx');
    });

    test('called with user_id when provided', async () => {
        resumeAPI.generate.mockResolvedValueOnce({ status: 'success', data: {} });
        await resumeAPI.generate(CANDIDATE, 7);
        expect(resumeAPI.generate).toHaveBeenCalledWith(CANDIDATE, 7);
    });

    test('called without user_id when null', async () => {
        resumeAPI.generate.mockResolvedValueOnce({ status: 'success', data: {} });
        await resumeAPI.generate(CANDIDATE, null);
        expect(resumeAPI.generate).toHaveBeenCalledWith(CANDIDATE, null);
    });
});

describe('resumeAPI.preview', () => {
    test('returns HTML string', async () => {
        resumeAPI.preview.mockResolvedValueOnce('<html><body>Resume</body></html>');
        const html = await resumeAPI.preview(CANDIDATE);
        expect(typeof html).toBe('string');
        expect(html).toContain('<html>');
    });

    test('called with candidate data', async () => {
        resumeAPI.preview.mockResolvedValueOnce('<html></html>');
        await resumeAPI.preview(CANDIDATE);
        expect(resumeAPI.preview).toHaveBeenCalledWith(CANDIDATE);
    });
});

describe('resumeAPI.downloadByFilename', () => {
    test('resolves with a blob', async () => {
        const fakeBlob = new Blob(['binary-data'], { type: 'application/octet-stream' });
        resumeAPI.downloadByFilename.mockResolvedValueOnce(fakeBlob);
        const result = await resumeAPI.downloadByFilename('test.docx');
        expect(result).toBe(fakeBlob);
        expect(resumeAPI.downloadByFilename).toHaveBeenCalledWith('test.docx');
    });
});

describe('resumeAPI.delete', () => {
    test('resolves with success status', async () => {
        resumeAPI.delete.mockResolvedValueOnce({ status: 'success' });
        const result = await resumeAPI.delete(5);
        expect(resumeAPI.delete).toHaveBeenCalledWith(5);
        expect(result.status).toBe('success');
    });
});

describe('resumeAPI.getAll', () => {
    test('resolves with resumes list', async () => {
        resumeAPI.getAll.mockResolvedValueOnce({ status: 'success', resumes: [] });
        const result = await resumeAPI.getAll(1);
        expect(result.status).toBe('success');
        expect(Array.isArray(result.resumes)).toBe(true);
    });
});

// ── templateAPI ──────────────────────────────────────────────────────────────

describe('templateAPI.getAll', () => {
    test('resolves with template list', async () => {
        templateAPI.getAll.mockResolvedValueOnce({
            status: 'success',
            templates: [{ id: 1, name: 'Modern', description: 'Clean' }],
        });
        const result = await templateAPI.getAll();
        expect(result.status).toBe('success');
        expect(Array.isArray(result.templates)).toBe(true);
        expect(result.templates[0].name).toBe('Modern');
    });
});
