// ══════════════════════════════════════════
//  AniVault — storage.js
//  Talks to the Flask + SQLite backend instead
//  of localStorage. Same method names as before,
//  but every method is now async.
// ══════════════════════════════════════════

const API_BASE = 'http://localhost:5000/api';

async function req(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  const contentType = res.headers.get('content-type') || '';
  return contentType.includes('application/json') ? res.json() : res.text();
}

const AniStorage = {
  // ── List ──────────────────────────────
  async loadList() {
    const list = await req('/anime');
    return list.length ? list : null;
  },

  async saveList(list) {
    // Full-list save is used after imports and reorders — push order + fields.
    await req('/anime/reorder', {
      method: 'POST',
      body: JSON.stringify(list.map(a => ({ id: a.id, order: a.order }))),
    });
  },

  async createEntry(entry) {
    return req('/anime', { method: 'POST', body: JSON.stringify(entry) });
  },

  async updateEntry(id, fields) {
    return req(`/anime/${id}`, { method: 'PUT', body: JSON.stringify(fields) });
  },

  async patchEntry(id, fields) {
    return req(`/anime/${id}`, { method: 'PATCH', body: JSON.stringify(fields) });
  },

  async deleteEntry(id) {
    return req(`/anime/${id}`, { method: 'DELETE' });
  },

  async restoreEntry(entry) {
    return req(`/anime/${entry.id}/restore`, { method: 'POST', body: JSON.stringify(entry) });
  },

  // No local legacy key anymore — kept as a no-op so init() doesn't break.
  async migrateFromLegacy() {
    return null;
  },

  // ── Meta (view / sort / filter) ──────
  async loadMeta() {
    const meta = await req('/meta');
    return {
      view: meta.view || 'grid',
      sort: meta.sort || 'default',
      filter: meta.filter || 'all',
    };
  },

  async saveMeta(partial) {
    await req('/meta', { method: 'POST', body: JSON.stringify(partial) });
  },

  // ── Cover cache ───────────────────────
  async getCachedCover(name) {
    const res = await req(`/cover-cache/${encodeURIComponent(name)}`);
    return res.cached ? (res.url || null) : null;
  },

  async setCachedCover(name, url) {
    await req('/cover-cache', { method: 'POST', body: JSON.stringify({ name, url }) });
  },

  // ── Import / Export ───────────────────
  toJSON(list) {
    return JSON.stringify(list, null, 2);
  },

  toCSV(list) {
    const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const header = 'name,status,episode,notes';
    const rows = list.map(a => [a.name, a.status, a.episode, a.notes].map(esc).join(','));
    return [header, ...rows].join('\n');
  },

  async importJSON(text) {
    return req('/import', { method: 'POST', body: JSON.stringify({ format: 'json', content: text }) });
  },

  async importCSV(text) {
    return req('/import', { method: 'POST', body: JSON.stringify({ format: 'csv', content: text }) });
  },

  // Server-side export downloads (simpler + guarantees DB is source of truth)
  exportJSONUrl() { return `${API_BASE}/export/json`; },
  exportCSVUrl() { return `${API_BASE}/export/csv`; },
};
