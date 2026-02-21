import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
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
  generate: async (candidateData, userId = null) => {
    const payload = { ...candidateData };
    if (userId) {
      payload.user_id = userId;
    }
    const response = await api.post('/api/generate-resume', payload);
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

export default api;
