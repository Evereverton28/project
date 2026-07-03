// ══════════════════════════════════════════
//  AniVault — app.js
//  UI logic only. All persistence delegated
//  to AniStorage (storage.js → Flask/SQLite backend).
// ══════════════════════════════════════════

// ── App State ─────────────────────────────
let animeList      = [];
let currentFilter  = 'all';
let currentSearch  = '';
let currentSort    = 'default';
let currentView    = 'grid';
let editingId      = null;
let drawerAnimeId  = null;
let selectedStatus = 'planned';
let toastTimer     = null;
let undoBuffer     = null;
let dragSrcId      = null;

// ── Cover Fetching ────────────────────────
async function fetchCover(name) {
  const cached = await AniStorage.getCachedCover(name);
  if (cached !== null) return cached;

  try {
    const q   = encodeURIComponent(name);
    const res = await fetch(`https://api.jikan.moe/v4/anime?q=${q}&limit=1&sfw=true`);
    if (!res.ok) return null;
    const json = await res.json();
    const img  = json?.data?.[0]?.images?.jpg?.large_image_url ?? null;
    await AniStorage.setCachedCover(name, img ?? '');
    return img;
  } catch {
    return null;
  }
}

async function loadMissingCovers(list) {
  const todo = list.filter(a => !a.coverFetched);
  for (let i = 0; i < todo.length; i++) {
    const anime = todo[i];
    const cover = await fetchCover(anime.name);

    await AniStorage.patchEntry(anime.id, { coverUrl: cover, coverFetched: true });

    const idx = animeList.findIndex(a => a.id === anime.id);
    if (idx !== -1) {
      animeList[idx].coverUrl     = cover;
      animeList[idx].coverFetched = true;
    }

    if (cover) updateCoverInDOM(anime.id, cover, anime);

    // Jikan rate limit: 3 req/sec max → 350ms gap is safe
    if (i < todo.length - 1) await delay(350);
  }
}

function updateCoverInDOM(id, cover, anime) {
  const cardCover = grid.querySelector(`[data-id="${id}"] .card-cover`);
  if (cardCover) {
    cardCover.innerHTML = `
      <img src="${cover}" alt="${escAttr(anime.name)}" loading="lazy"
           onerror="this.outerHTML='<div class=cover-placeholder><span class=cover-placeholder-icon>⛩</span></div>'" />
      <span class="card-status-badge">${statusLabel(anime.status)}</span>
      ${anime.episode ? `<span class="card-episode-tag">${escHtml(anime.episode)}</span>` : ''}
      <span class="card-drag-handle" title="Drag to reorder">⠿</span>
    `;
  }
  const listPlaceholder = listBody.querySelector(`[data-id="${id}"] .list-thumb-placeholder`);
  if (listPlaceholder) {
    listPlaceholder.outerHTML = `<img class="list-thumb" src="${cover}" alt="" loading="lazy"
      onerror="this.outerHTML='<div class=list-thumb-placeholder>⛩</div>'" />`;
  }
  if (drawerAnimeId === id) renderDrawerCover(cover);
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── DOM refs ──────────────────────────────
const grid                = document.getElementById('animeGrid');
const listView            = document.getElementById('animeListView');
const listBody            = document.getElementById('animeListBody');
const emptyState          = document.getElementById('emptyState');
const searchInput         = document.getElementById('searchInput');
const searchClear         = document.getElementById('searchClear');
const filterTabs          = document.getElementById('filterTabs');
const sortSelect          = document.getElementById('sortSelect');
const btnAdd              = document.getElementById('btnAdd');
const modalOverlay        = document.getElementById('modalOverlay');
const modalTitle          = document.getElementById('modalTitle');
const formName            = document.getElementById('formName');
const formEpisode         = document.getElementById('formEpisode');
const formNotes           = document.getElementById('formNotes');
const statusPicker        = document.getElementById('statusPicker');
const btnSave             = document.getElementById('btnSave');
const btnCancel           = document.getElementById('btnCancel');
const modalClose          = document.getElementById('modalClose');
const viewGrid            = document.getElementById('viewGrid');
const viewList            = document.getElementById('viewList');
const btnExportJSON       = document.getElementById('btnExportJSON');
const btnExportCSV        = document.getElementById('btnExportCSV');
const btnImport           = document.getElementById('btnImport');
const importFile          = document.getElementById('importFile');
const drawerOverlay       = document.getElementById('drawerOverlay');
const detailDrawer        = document.getElementById('detailDrawer');
const drawerTitle         = document.getElementById('drawerTitle');
const drawerClose         = document.getElementById('drawerClose');
const drawerEditBtn       = document.getElementById('drawerEditBtn');
const drawerCoverArea     = document.getElementById('drawerCoverArea');
const drawerBadge         = document.getElementById('drawerBadge');
const drawerEpRow         = document.getElementById('drawerEpRow');
const drawerEp            = document.getElementById('drawerEp');
const drawerNotesRow      = document.getElementById('drawerNotesRow');
const drawerNotes         = document.getElementById('drawerNotes');
const drawerStatusPicker  = document.getElementById('drawerStatusPicker');

// ── Helpers ───────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(str) {
  return String(str).replace(/'/g,"&apos;").replace(/"/g,"&quot;");
}
function statusLabel(s) {
  if (s === 'completed') return '✓✓ Completed';
  if (s === 'watching')  return '✓ Watching';
  return 'Not Started';
}

// ── Render ────────────────────────────────
function getFiltered() {
  let list = [...animeList];
  if (currentFilter !== 'all') list = list.filter(a => a.status === currentFilter);
  if (currentSearch.trim()) {
    const q = currentSearch.toLowerCase();
    list = list.filter(a => a.name.toLowerCase().includes(q));
  }
  if (currentSort === 'alpha') {
    list.sort((a, b) => a.name.localeCompare(b.name));
  } else if (currentSort === 'status') {
    const ord = { completed: 0, watching: 1, planned: 2 };
    list.sort((a, b) => ord[a.status] - ord[b.status]);
  } else {
    list.sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  }
  return list;
}

function renderAll() {
  const list = getFiltered();
  grid.innerHTML     = '';
  listBody.innerHTML = '';

  const empty = list.length === 0;
  emptyState.style.display = empty ? 'flex' : 'none';

  if (!empty) {
    if (currentView === 'grid') {
      grid.style.display     = '';
      listView.style.display = 'none';
      list.forEach((a, i) => grid.appendChild(renderCard(a, i)));
    } else {
      grid.style.display     = 'none';
      listView.style.display = '';
      list.forEach((a, i) => listBody.appendChild(renderRow(a, i + 1)));
    }
    loadMissingCovers(list);
  } else {
    grid.style.display     = 'none';
    listView.style.display = 'none';
  }

  updateStats();
}

// ── Grid Card ─────────────────────────────
function renderCard(anime, index) {
  const card = document.createElement('div');
  card.className = `anime-card status-${anime.status}`;
  card.style.animationDelay = `${Math.min(index * 0.03, 0.6)}s`;
  card.dataset.id = anime.id;
  card.draggable  = true;

  const coverHtml = anime.coverUrl
    ? `<img src="${anime.coverUrl}" alt="${escAttr(anime.name)}" loading="lazy"
           onerror="this.outerHTML='<div class=cover-placeholder><span class=cover-placeholder-icon>⛩</span><span class=cover-placeholder-text>${escAttr(anime.name)}</span></div>'" />`
    : `<div class="cover-placeholder">
         <span class="cover-placeholder-icon">⛩</span>
         <span class="cover-placeholder-text">${escHtml(anime.name)}</span>
       </div>`;

  card.innerHTML = `
    <div class="card-cover">
      ${coverHtml}
      <span class="card-status-badge">${statusLabel(anime.status)}</span>
      ${anime.episode ? `<span class="card-episode-tag">${escHtml(anime.episode)}</span>` : ''}
      <span class="card-drag-handle" title="Drag to reorder">⠿</span>
    </div>
    <div class="card-body">
      <p class="card-title">${escHtml(anime.name)}</p>
      ${anime.notes ? `<p class="card-notes">${escHtml(anime.notes)}</p>` : ''}
    </div>
    <div class="card-actions">
      <button class="card-btn card-btn-edit"   data-id="${anime.id}">✎ Edit</button>
      <button class="card-btn card-btn-delete" data-id="${anime.id}">✕ Remove</button>
    </div>
  `;

  card.addEventListener('click', e => {
    if (e.target.closest('.card-btn,.card-drag-handle')) return;
    openDrawer(anime.id);
  });

  card.addEventListener('dragstart', onDragStart);
  card.addEventListener('dragover',  onDragOver);
  card.addEventListener('dragleave', onDragLeave);
  card.addEventListener('drop',      onDrop);
  card.addEventListener('dragend',   onDragEnd);
  return card;
}

// ── List Row ──────────────────────────────
function renderRow(anime, num) {
  const tr = document.createElement('tr');
  tr.className = 'list-row';
  tr.dataset.id = anime.id;
  tr.draggable  = true;

  const thumb = anime.coverUrl
    ? `<img class="list-thumb" src="${anime.coverUrl}" alt="" loading="lazy"
           onerror="this.outerHTML='<div class=list-thumb-placeholder>⛩</div>'" />`
    : `<div class="list-thumb-placeholder">⛩</div>`;

  tr.innerHTML = `
    <td><div class="list-drag-handle" title="Drag to reorder">⠿</div></td>
    <td><span class="list-num">${num}</span></td>
    <td>${thumb}</td>
    <td class="list-name">${escHtml(anime.name)}</td>
    <td><span class="list-badge ${anime.status}">${statusLabel(anime.status)}</span></td>
    <td><span class="list-ep">${escHtml(anime.episode || '—')}</span></td>
    <td><span class="list-notes" title="${escAttr(anime.notes || '')}">${escHtml(anime.notes || '—')}</span></td>
    <td>
      <div class="list-actions">
        <button class="list-act-btn edit" data-id="${anime.id}">✎</button>
        <button class="list-act-btn del"  data-id="${anime.id}">✕</button>
      </div>
    </td>
  `;

  tr.addEventListener('click', e => {
    if (e.target.closest('.list-act-btn,.list-drag-handle')) return;
    openDrawer(anime.id);
  });
  tr.addEventListener('dragstart', onDragStart);
  tr.addEventListener('dragover',  onDragOver);
  tr.addEventListener('dragleave', onDragLeave);
  tr.addEventListener('drop',      onDrop);
  tr.addEventListener('dragend',   onDragEnd);
  return tr;
}

function updateStats() {
  document.getElementById('statTotal').textContent     = animeList.length;
  document.getElementById('statCompleted').textContent = animeList.filter(a => a.status === 'completed').length;
  document.getElementById('statWatching').textContent  = animeList.filter(a => a.status === 'watching').length;
  document.getElementById('statPlanned').textContent   = animeList.filter(a => a.status === 'planned').length;
}

// ── Drag and Drop ─────────────────────────
function onDragStart(e) {
  dragSrcId = Number(this.dataset.id);
  this.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', dragSrcId);
}
function onDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  if (Number(this.dataset.id) !== dragSrcId) this.classList.add('drag-over');
}
function onDragLeave() { this.classList.remove('drag-over'); }
async function onDrop(e) {
  e.preventDefault();
  this.classList.remove('drag-over');
  const tgtId = Number(this.dataset.id);
  if (tgtId === dragSrcId) return;
  const si = animeList.findIndex(a => a.id === dragSrcId);
  const ti = animeList.findIndex(a => a.id === tgtId);
  if (si === -1 || ti === -1) return;
  const [moved] = animeList.splice(si, 1);
  animeList.splice(ti, 0, moved);
  animeList.forEach((a, i) => { a.order = i; });
  await AniStorage.saveList(animeList); // pushes new order to backend
  renderAll();
}
function onDragEnd() {
  this.classList.remove('dragging');
  document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
  dragSrcId = null;
}

// ── Detail Drawer ─────────────────────────
function openDrawer(id) {
  const anime = animeList.find(a => a.id === id);
  if (!anime) return;
  drawerAnimeId = id;

  drawerTitle.textContent = anime.name;
  renderDrawerCover(anime.coverUrl);

  drawerBadge.className   = `drawer-badge ${anime.status}`;
  drawerBadge.textContent = statusLabel(anime.status);

  drawerEpRow.style.display = anime.episode ? '' : 'none';
  drawerEp.textContent      = anime.episode || '';

  drawerNotesRow.style.display = anime.notes ? '' : 'none';
  drawerNotes.textContent      = anime.notes || '';

  document.querySelectorAll('.dsp-btn').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.status === anime.status)
  );

  drawerOverlay.classList.add('open');
  detailDrawer.classList.add('open');
}

function renderDrawerCover(url) {
  drawerCoverArea.innerHTML = url
    ? `<img class="drawer-cover" src="${url}" alt=""
           onerror="this.outerHTML='<div class=drawer-cover-placeholder>⛩</div>'" />`
    : `<div class="drawer-cover-placeholder">⛩</div>`;
}

function closeDrawer() {
  drawerOverlay.classList.remove('open');
  detailDrawer.classList.remove('open');
  drawerAnimeId = null;
}

drawerClose.addEventListener('click', closeDrawer);
drawerOverlay.addEventListener('click', closeDrawer);

drawerEditBtn.addEventListener('click', () => {
  const id = drawerAnimeId;
  closeDrawer();
  openEditModal(id);
});

drawerStatusPicker.addEventListener('click', async e => {
  const btn = e.target.closest('.dsp-btn');
  if (!btn || drawerAnimeId === null) return;
  const s = btn.dataset.status;
  const idx = animeList.findIndex(a => a.id === drawerAnimeId);
  if (idx === -1) return;
  animeList[idx].status = s;
  await AniStorage.patchEntry(drawerAnimeId, { status: s });
  renderAll();
  openDrawer(drawerAnimeId);
  showToast(`Status → ${statusLabel(s)}`);
});

// ── Modal ─────────────────────────────────
function openAddModal() {
  editingId = null;
  modalTitle.textContent = 'Add Anime';
  formName.value = formEpisode.value = formNotes.value = '';
  setStatus('planned');
  modalOverlay.classList.add('open');
  setTimeout(() => formName.focus(), 100);
}

function openEditModal(id) {
  const anime = animeList.find(a => a.id === id);
  if (!anime) return;
  editingId = id;
  modalTitle.textContent = 'Edit Anime';
  formName.value    = anime.name;
  formEpisode.value = anime.episode || '';
  formNotes.value   = anime.notes   || '';
  setStatus(anime.status);
  modalOverlay.classList.add('open');
  setTimeout(() => formName.focus(), 100);
}

function closeModal() { modalOverlay.classList.remove('open'); }

function setStatus(status) {
  selectedStatus = status;
  document.querySelectorAll('.sp-btn').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.status === status)
  );
}

async function saveAnime() {
  const name = formName.value.trim();
  if (!name) {
    formName.focus();
    formName.style.borderColor = '#ff6b9d';
    setTimeout(() => formName.style.borderColor = '', 1500);
    return;
  }

  if (editingId !== null) {
    const idx = animeList.findIndex(a => a.id === editingId);
    if (idx !== -1) {
      const sameTitle = animeList[idx].name === name;
      const fields = {
        name,
        status:       selectedStatus,
        episode:      formEpisode.value.trim(),
        notes:        formNotes.value.trim(),
        coverFetched: sameTitle ? animeList[idx].coverFetched : false,
        coverUrl:     sameTitle ? animeList[idx].coverUrl     : null,
      };
      const updated = await AniStorage.updateEntry(editingId, fields);
      animeList[idx] = updated;
      showToast('✓ Updated');
    }
  } else {
    const created = await AniStorage.createEntry({
      name,
      status:  selectedStatus,
      episode: formEpisode.value.trim(),
      notes:   formNotes.value.trim(),
    });
    animeList.unshift(created);
    showToast('✓ Added to vault');
  }

  closeModal();
  renderAll();
}

// ── Delete with Undo ──────────────────────
async function deleteAnime(id) {
  const idx = animeList.findIndex(a => a.id === id);
  if (idx === -1) return;
  const deleted = await AniStorage.deleteEntry(id);
  undoBuffer = { anime: deleted, index: idx };
  animeList.splice(idx, 1);
  if (drawerAnimeId === id) closeDrawer();
  renderAll();
  showToast('✕ Removed from vault', true);
}

async function undoDelete() {
  if (!undoBuffer) return;
  const restored = await AniStorage.restoreEntry(undoBuffer.anime);
  animeList.splice(undoBuffer.index, 0, restored);
  animeList.sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  undoBuffer = null;
  renderAll();
  showToast('↩ Restored');
}

// ── Toast ─────────────────────────────────
function showToast(msg, withUndo = false) {
  document.querySelector('.toast')?.remove();
  clearTimeout(toastTimer);

  const t = document.createElement('div');
  t.className = 'toast';

  if (withUndo) {
    t.innerHTML = `<span>${escHtml(msg)}</span><button class="toast-undo">Undo</button>`;
    t.querySelector('.toast-undo').addEventListener('click', () => {
      undoDelete();
      t.remove();
      clearTimeout(toastTimer);
    });
  } else {
    t.textContent = msg;
  }

  document.body.appendChild(t);
  toastTimer = setTimeout(() => { t.remove(); undoBuffer = null; }, 4000);
}

// ── Import / Export ───────────────────────
btnExportJSON.addEventListener('click', () => {
  window.open(AniStorage.exportJSONUrl(), '_blank');
  showToast('↓ Exported as JSON');
});

btnExportCSV.addEventListener('click', () => {
  window.open(AniStorage.exportCSVUrl(), '_blank');
  showToast('↓ Exported as CSV');
});

btnImport.addEventListener('click', () => importFile.click());

importFile.addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async ev => {
    try {
      const text = ev.target.result;
      animeList = file.name.endsWith('.csv')
        ? await AniStorage.importCSV(text)
        : await AniStorage.importJSON(text);
      renderAll();
      showToast(`✓ Imported ${animeList.length} entries`);
    } catch (err) {
      showToast('✕ Import failed — check file format');
    }
  };
  reader.readAsText(file);
  importFile.value = '';
});

// ── View Toggle ───────────────────────────
viewGrid.addEventListener('click', async () => {
  currentView = 'grid';
  viewGrid.classList.add('active');
  viewList.classList.remove('active');
  await AniStorage.saveMeta({ view: 'grid' });
  renderAll();
});

viewList.addEventListener('click', async () => {
  currentView = 'list';
  viewList.classList.add('active');
  viewGrid.classList.remove('active');
  await AniStorage.saveMeta({ view: 'list' });
  renderAll();
});

// ── Event listeners ───────────────────────
btnAdd.addEventListener('click', openAddModal);

searchInput.addEventListener('input', () => {
  currentSearch = searchInput.value;
  searchClear.classList.toggle('visible', !!currentSearch);
  renderAll();
});
searchClear.addEventListener('click', () => {
  searchInput.value = '';
  currentSearch = '';
  searchClear.classList.remove('visible');
  searchInput.focus();
  renderAll();
});

filterTabs.addEventListener('click', async e => {
  const tab = e.target.closest('.ftab');
  if (!tab) return;
  document.querySelectorAll('.ftab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentFilter = tab.dataset.filter;
  await AniStorage.saveMeta({ filter: currentFilter });
  renderAll();
});

sortSelect.addEventListener('change', async () => {
  currentSort = sortSelect.value;
  await AniStorage.saveMeta({ sort: currentSort });
  renderAll();
});

statusPicker.addEventListener('click', e => {
  const btn = e.target.closest('.sp-btn');
  if (btn) setStatus(btn.dataset.status);
});

btnSave.addEventListener('click', saveAnime);
btnCancel.addEventListener('click', closeModal);
modalClose.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(); });

grid.addEventListener('click', e => {
  const ed = e.target.closest('.card-btn-edit');
  const dl = e.target.closest('.card-btn-delete');
  if (ed) openEditModal(Number(ed.dataset.id));
  if (dl) deleteAnime(Number(dl.dataset.id));
});
listBody.addEventListener('click', e => {
  const ed = e.target.closest('.list-act-btn.edit');
  const dl = e.target.closest('.list-act-btn.del');
  if (ed) openEditModal(Number(ed.dataset.id));
  if (dl) deleteAnime(Number(dl.dataset.id));
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (detailDrawer.classList.contains('open')) { closeDrawer(); return; }
    if (modalOverlay.classList.contains('open'))  { closeModal(); return; }
  }
  if (e.key === 'Enter' && modalOverlay.classList.contains('open') && document.activeElement !== formNotes) {
    saveAnime();
  }
});

// ── Init ──────────────────────────────────
(async function init() {
  try {
    animeList = await AniStorage.loadList() || [];
  } catch (err) {
    console.error('Could not reach AniVault backend:', err);
    emptyState.style.display = 'flex';
    emptyState.querySelector('p').textContent =
      'Cannot reach backend — is app.py running on http://localhost:5000?';
    return;
  }

  const meta = await AniStorage.loadMeta();
  currentView   = meta.view;
  currentSort   = meta.sort;
  currentFilter = meta.filter;
  sortSelect.value = currentSort;
  document.querySelectorAll('.ftab').forEach(t =>
    t.classList.toggle('active', t.dataset.filter === currentFilter)
  );
  if (currentView === 'list') {
    viewList.classList.add('active');
    viewGrid.classList.remove('active');
  }

  renderAll();
})();