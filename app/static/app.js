const API_BASE = '/api';

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || 'Request failed');
  }

  return response.headers.get('Content-Type')?.includes('application/json') ? response.json() : response.text();
}

async function login(email, password) {
  return api('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

async function getSummary() {
  return api('/dashboard/summary');
}

async function getSessionToken() {
  return api('/assemblyai/session-token', { method: 'POST' });
}

window.InterviewaApp = { api, login, getSummary, getSessionToken };
