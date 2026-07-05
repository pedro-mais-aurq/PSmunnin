import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { 'Content-Type': 'application/json' },
});

export const createSearch = (payload) => api.post('/searches', payload).then(r => r.data);
export const listSearches = () => api.get('/searches').then(r => r.data);
export const getSearch = (id) => api.get(`/searches/${id}`).then(r => r.data);
export const deleteSearch = (id) => api.delete(`/searches/${id}`).then(r => r.data);
export const getLead = (id) => api.get(`/leads/${id}`).then(r => r.data);
export const generateMessage = (id, channel = 'email') =>
  api.get(`/leads/${id}/message`, { params: { channel } }).then(r => r.data);
