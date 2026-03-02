import axios from 'axios';

// In development the CRA proxy (package.json "proxy") forwards /api/* to localhost:8000.
// In production set REACT_APP_API_URL to the backend's public URL.
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

// Log API URL to help debug (in both dev and prod)
console.log('🔗 API Base URL:', API_BASE_URL || '(empty - using proxy in dev)');
if (!API_BASE_URL && process.env.NODE_ENV === 'production') {
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
  // Ensure credentials are included for CORS
  withCredentials: false, // Set to false if CORS_ORIGINS uses "*"
});

// Log request configuration for debugging
api.interceptors.request.use((config) => {
  console.log('📤 API Request:', {
    method: config.method?.toUpperCase(),
    url: config.url,
    baseURL: config.baseURL,
    fullURL: (config.baseURL || '') + (config.url || ''),
    headers: config.headers
  });
  return config;
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
    // Enhanced error handling with detailed logging
    console.error('❌ API Error:', {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      url: error.config?.url,
      baseURL: error.config?.baseURL,
      fullURL: error.config?.baseURL + error.config?.url
    });
    
    if (error.code === 'ECONNABORTED') {
      error.message = 'Request timeout - the server may be processing. Please try again.';
    } else if (error.code === 'ERR_NETWORK' || !error.response) {
      const baseURL = error.config?.baseURL || API_BASE_URL;
      error.message = `Could not reach the server at ${baseURL}. Please check your connection and verify REACT_APP_API_URL is set correctly.`;
    } else if (error.response?.status === 503) {
      error.message = error.response?.data?.detail || 'Service temporarily unavailable. Please try again.';
    } else if (error.response?.status === 0) {
      error.message = 'CORS error or server unreachable. Check backend CORS settings and ensure backend is running.';
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
      
      // Don't set Content-Type header - let browser set it with boundary
      // This is critical for multipart/form-data requests
      const response = await api.post('/api/generate', formData, {
        timeout: 180000, // 3 minutes for AI generation
        headers: {
          // Let axios/browser set Content-Type with boundary for multipart
        },
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

// Health check utility with detailed logging
export const healthCheck = async () => {
  try {
    console.log('🏥 Checking backend health at:', API_BASE_URL + '/health');
    const response = await api.get('/health', { timeout: 10000 });
    console.log('✅ Backend health check passed:', response.status);
    return response.status === 200;
  } catch (error) {
    console.error('❌ Backend health check failed:', {
      message: error.message,
      code: error.code,
      url: API_BASE_URL + '/health'
    });
    return false;
  }
};

export default api;
