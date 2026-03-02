import axios from 'axios';

// In development the CRA proxy (package.json "proxy") forwards /api/* to localhost:8000.
// In production set REACT_APP_API_URL to the backend's public URL.
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

// Log API URL in development to help debug
if (process.env.NODE_ENV === 'development') {
  console.log('API Base URL:', API_BASE_URL || 'Using proxy (package.json)');
}

// Warn if API URL is not set in production
if (process.env.NODE_ENV === 'production' && !API_BASE_URL) {
  console.error('⚠️ REACT_APP_API_URL is not set! API calls will fail.');
  console.error('Set REACT_APP_API_URL in Vercel Environment Variables.');
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000, // 3 minutes — covers Render cold-start + OpenAI generation time
  headers: {
    'Content-Type': 'application/json',
  },
  // Add error handling
  validateStatus: function (status) {
    return status < 500; // Don't throw for 4xx errors
  },
});

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Enhanced error handling
    if (error.code === 'ECONNABORTED') {
      error.message = 'Request timeout - the server may be processing. Please try again.';
    } else if (error.code === 'ERR_NETWORK' || !error.response) {
      error.message = 'Could not reach the server. Please check your connection and try again.';
    } else if (error.response?.status === 503) {
      error.message = error.response?.data?.detail || 'Service temporarily unavailable. Please try again.';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  signup: async (name, email, password) => {
    const response = await api.post('/api/auth/signup', { name, email, password });
    return response.data;
  },
  
  login: async (email, password) => {
    const response = await api.post('/api/auth/login', { email, password });
    return response.data;
  },
};

export const resumeAPI = {
  // Primary: generate from uploaded documents + job description
  generate: async (files, jobDescription) => {
    try {
      const formData = new FormData();
      files.forEach(f => formData.append('files', f));
      formData.append('job_description', jobDescription);
      const response = await api.post('/api/generate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000, // 3 minutes for AI generation
      });
      
      // Check for error responses
      if (response.status >= 400) {
        throw new Error(response.data?.detail || `Server error: ${response.status}`);
      }
      
      return response.data;
    } catch (error) {
      // Re-throw with enhanced error message if not already set
      if (!error.message || error.message === 'Network Error') {
        throw new Error('Could not reach the server. Please check your connection and try again.');
      }
      throw error;
    }
  },

  // Legacy: generate from structured candidate data (wizard)
  generateFromData: async (candidateData, userId = null) => {
    const payload = { ...candidateData };
    if (userId) payload.user_id = userId;
    const response = await api.post('/api/generate-resume', payload);
    return response.data;
  },

  preview: async (candidateData) => {
    const response = await api.post('/api/preview-resume', candidateData, {
      responseType: 'text',
    });
    return response.data;
  },
  
  getAll: async (userId) => {
    const response = await api.get(`/api/resumes`, { params: { user_id: userId } });
    return response.data;
  },
  
  download: async (resumeId) => {
    const response = await api.get(`/api/resumes/${resumeId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadByFilename: async (filename) => {
    const response = await api.get(`/api/resumes/download-file/${filename}`, {
      responseType: 'blob',
    });
    return response.data;
  },
  
  delete: async (resumeId) => {
    const response = await api.delete(`/api/resumes/${resumeId}`);
    return response.data;
  },
};

export const templateAPI = {
  getAll: async () => {
    const response = await api.get('/api/templates');
    return response.data;
  },
};

// Health check utility
export const healthCheck = async () => {
  try {
    const response = await api.get('/health', { timeout: 5000 });
    return response.status === 200;
  } catch (error) {
    return false;
  }
};

export default api;
