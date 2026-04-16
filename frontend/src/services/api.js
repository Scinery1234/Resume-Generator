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
  // Primary: generate from uploaded documents + job description + additional info
  generate: async (files, jobDescription, additionalInfo = '', userId = null, template = 'modern') => {
    try {
      console.log('🚀 Starting resume generation...', {
        filesCount: files.length,
        template,
        apiUrl: API_BASE_URL,
        fullUrl: `${API_BASE_URL}/api/generate`
      });

      const formData = new FormData();
      files.forEach(f => {
        console.log('📎 Adding file:', f.name, f.type, f.size);
        formData.append('files', f);
      });
      formData.append('job_description', jobDescription);
      if (additionalInfo && additionalInfo.trim()) {
        const trimmedInfo = additionalInfo.trim();
        console.log('📝 Sending additional info:', trimmedInfo.substring(0, 100) + (trimmedInfo.length > 100 ? '...' : ''));
        formData.append('additional_info', trimmedInfo);
      } else {
        console.log('📝 No additional info provided');
      }
      formData.append('template', template || 'modern');
      if (userId) {
        formData.append('user_id', userId);
      }
      
      // Test backend connectivity first
      console.log('🔍 Testing backend connectivity...');
      try {
        const healthCheck = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          mode: 'cors',
        });
        console.log('✅ Health check:', healthCheck.status, healthCheck.statusText);
        if (!healthCheck.ok) {
          throw new Error(`Backend health check failed: ${healthCheck.status}`);
        }
      } catch (healthError) {
        console.error('❌ Health check failed:', healthError);
        throw new Error(`Cannot reach backend: ${healthError.message}. Backend may be sleeping or unreachable.`);
      }
      
      // Use fetch directly for FormData to avoid axios issues with multipart
      console.log('📤 Sending POST request to /api/generate...');
      const response = await fetch(`${API_BASE_URL}/api/generate`, {
        method: 'POST',
        body: formData,
        mode: 'cors',
        credentials: 'omit',
        // Don't set Content-Type - browser will set it with boundary
      });
      
      console.log('📥 Response received:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Response error:', errorText);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { detail: errorText || `HTTP ${response.status}` };
        }
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('✅ Generation successful:', result);
      // Unwrap standardize_response envelope { status, data: {...} } if present,
      // so callers always receive a flat object with filename/preview_html/resume_id
      // at the top level.
      return (result && result.status === 'success' && result.data) ? result.data : result;
    } catch (error) {
      // Enhanced error handling
      console.error('❌ Generate error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack,
        apiUrl: API_BASE_URL
      });
      
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Failed to fetch - This usually means CORS is blocking the request or backend is unreachable. Check backend CORS_ORIGINS includes your Vercel domain.');
      }
      
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        throw new Error(`Cannot connect to backend at ${API_BASE_URL}. Backend may be sleeping (Render free tier) or CORS is blocking the request.`);
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
  
  editWithPrompt: async (resumeId, prompt, userId = null) => {
    const formData = new FormData();
    formData.append('prompt', prompt);
    if (userId) formData.append('user_id', userId);
    const response = await fetch(`${API_BASE_URL}/api/resumes/${resumeId}/edit`, {
      method: 'POST',
      body: formData,
      mode: 'cors',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      throw new Error(error.detail || `Server error: ${response.status}`);
    }
    return await response.json();
  },
  
  updateInline: async (resumeId, resumeData, userId) => {
    const response = await api.put(`/api/resumes/${resumeId}/update`, {
      resume_data: resumeData,
      user_id: userId,
    }, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    const result = response.data;
    // Unwrap standardize_response envelope if present
    return (result && result.status === 'success' && result.data) ? result.data : result;
  },
  
  switchTemplate: async (resumeId, templateId, userId = null) => {
    const formData = new FormData();
    formData.append('template_id', templateId);
    if (userId) formData.append('user_id', userId);
    const response = await fetch(`${API_BASE_URL}/api/resumes/${resumeId}/switch-template`, {
      method: 'POST',
      body: formData,
      mode: 'cors',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      throw new Error(error.detail || `Server error: ${response.status}`);
    }
    return await response.json();
  },

  getPromptInfo: async (userId) => {
    const response = await api.get(`/api/users/${userId}/prompt-info`);
    return response.data;
  },
};

export const templateAPI = {
  getAll: async () => {
    const response = await api.get('/api/templates');
    return response.data;
  },

  getPreviews: async () => {
    const response = await api.get('/api/templates/previews');
    return response.data;  // { modern: '<html>…', classic: '<html>…', … }
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
