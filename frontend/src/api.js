const BASE = import.meta.env.VITE_API_URL ?? '';

async function req(path, options = {}) {
  const res = await fetch(BASE + path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  getOptions: () => req('/meta/options'),

  listVideos: (params = {}) => {
    const q = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v))
    );
    return req(`/videos/?${q}`);
  },

  getVideo: (id) => req(`/videos/${id}`),

  createVideo: (data) =>
    req('/videos/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  updateVideo: (id, data) =>
    req(`/videos/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),

  deleteVideo: (id) => req(`/videos/${id}`, { method: 'DELETE' }),

  uploadCsv: (file) => {
    const form = new FormData();
    form.append('file', file);
    return req('/upload/', { method: 'POST', body: form });
  },
};
