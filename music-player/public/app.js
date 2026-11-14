import { matchesQuery } from './search.js';
import { setupMediaSession } from './media-session.js';
import { parseLyrics, currentLineIndex } from './lyrics.js';
import { groupTracks, UNKNOWN_ARTIST } from './groups.js';
import { planUploads, mergeResults } from './upload-plan.js';
import { clickSelection, pruneSelection } from './selection.js';
import { planPlaylistAdd } from './playlist-add.js';
import { createListenTracker, recentTracks, topTracks } from './listening.js';
import { createSync, stamp, undo, jumpTo, missingCount, toLrc, lrcTime } from './lyric-sync.js';

// ───────────── 유틸 ─────────────
const $ = (sel) => document.querySelector(sel);

// 텍스트는 항상 textContent로 넣어 태그 정보(제목 등)로 인한 XSS를 막는다. html은 아이콘 상수에만 쓴다.
function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'class') el.className = v;
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else if (k === 'html') el.innerHTML = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  el.append(...children.flat().filter((c) => c != null && c !== false));
  return el;
}

function fmt(sec) {
  if (!Number.isFinite(sec)) return '0:00';
  sec = Math.floor(sec);
  const m = Math.floor(sec / 60);
  const s = String(sec % 60).padStart(2, '0');
  return m >= 60 ? `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}:${s}` : `${m}:${s}`;
}

function fmtTotal(sec) {
  if (sec < 60) return `${Math.round(sec)}초`;
  const m = Math.round(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)}시간 ${m % 60}분` : `${m}분`;
}

const store = {
  get(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* 저장 불가 환경은 무시 */ }
  },
};

const ICON = {
  play: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>',
  pause: '<svg viewBox="0 0 24 24"><path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>',
  prev: '<svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6 8.5 6V6z"/></svg>',
  next: '<svg viewBox="0 0 24 24"><path d="M16 6h2v12h-2zM6 18l8.5-6L6 6z"/></svg>',
  shuffle: '<svg viewBox="0 0 24 24"><path d="M10.59 9.17 5.41 4 4 5.41l5.17 5.17zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4zm.33 9.41-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04z"/></svg>',
  repeat: '<svg viewBox="0 0 24 24"><path d="M7 7h10v3l4-4-4-4v3H5v6h2zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2z"/></svg>',
  repeatOne: '<svg viewBox="0 0 24 24"><path d="M7 7h10v3l4-4-4-4v3H5v6h2zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2zm-4-2V9h-1l-2 1v1h1.5v4z"/></svg>',
  volume: '<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9zm13.5 3A4.5 4.5 0 0 0 14 8v8a4.5 4.5 0 0 0 2.5-4M14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6"/></svg>',
  mute: '<svg viewBox="0 0 24 24"><path d="M3 9v6h4l5 5V4L7 9zm13.6 3 2.7-2.7-1.4-1.4-2.7 2.7-2.7-2.7-1.4 1.4 2.7 2.7-2.7 2.7 1.4 1.4 2.7-2.7 2.7 2.7 1.4-1.4z"/></svg>',
  lyrics: '<svg viewBox="0 0 24 24"><path fill-rule="evenodd" d="M4 3h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H8l-4 4zm3 5v2h10V8zm0 4v2h7v-2z"/></svg>',
  queue: '<svg viewBox="0 0 24 24"><path d="M3 6h12v2H3zm0 4h12v2H3zm0 4h8v2H3zm14 0V6h4v2h-2v8a3 3 0 1 1-2-2.83"/></svg>',
  more: '<svg viewBox="0 0 24 24"><path d="M6 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4m6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4m6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4"/></svg>',
  close: '<svg viewBox="0 0 24 24"><path d="M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z"/></svg>',
};

// ───────────── API ─────────────
async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && !url.startsWith('/api/auth')) {
    showAuth(false);
    throw new Error('로그인이 필요합니다');
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.error || `요청 실패 (${res.status})`);
  return data;
}

// 버튼 핸들러에서 생긴 오류는 토스트로 보여준다.
const safe = (fn) => async (...args) => {
  try { await fn(...args); } catch (err) { toast(err.message); }
};

// ───────────── 상태 ─────────────
const state = {
  user: null,
  tracks: [],
  byId: new Map(),
  playlists: [],
  view: { type: 'library' },
  rows: [], // 현재 보기의 곡 (플레이리스트면 entryId 포함)
  shown: [], // rows 중 검색어와 일치해 실제로 그려진 곡
  selected: new Set(), // 선택한 행의 키 (rowKey)
  anchor: null, // Shift 범위 선택의 기준 행
  query: '',
};
let dragTrackId = null;

async function loadLibrary() {
  state.tracks = await api('GET', '/api/tracks');
  state.byId = new Map(state.tracks.map((t) => [t.id, t]));
  pruneQueue();
}

async function loadPlaylists() {
  state.playlists = await api('GET', '/api/playlists');
  renderSidebar();
}

const GRID_VIEWS = { artists: 'artist', albums: 'album' }; // 묶음 목록 보기 → 그 안의 곡 목록 보기
// 라이브러리에서 자동으로 뽑는 목록
const SMART_LISTS = {
  recent: {
    title: '최근 추가한 곡', pick: recentTracks,
    empty: '라이브러리가 비어 있습니다.',
  },
  top: {
    title: '많이 들은 곡', pick: topTracks,
    empty: '아직 들은 곡이 없습니다. 곡을 절반 이상(최대 4분) 들으면 여기에 쌓입니다.',
  },
};

async function openView(view) {
  const sameView = view?.type === state.view.type
    && (view.type === 'playlist' ? view.id === state.view.id : view.name === state.view.name);
  if (!sameView) {
    setQuery('');
    clearSelection(false);
  }
  if (view?.type === 'playlist') {
    const data = await api('GET', `/api/playlists/${view.id}`);
    state.view = { type: 'playlist', id: data.id, name: data.name };
    state.rows = data.tracks;
  } else if (GRID_VIEWS[view?.type]) {
    state.view = { type: view.type };
    state.rows = state.tracks;
  } else if (SMART_LISTS[view?.type]) {
    state.view = { type: view.type };
    state.rows = SMART_LISTS[view.type].pick(state.tracks);
  } else if (view?.type === 'artist' || view?.type === 'album') {
    const group = groupTracks(state.tracks, view.type).find((g) => g.name === view.name);
    state.view = { type: view.type, name: view.name };
    state.rows = group?.tracks ?? [];
  } else {
    state.view = { type: 'library' };
    state.rows = state.tracks;
  }
  store.set('mp_view', state.view);
  renderSidebar();
  renderMain();
}

const refreshView = () => openView(state.view);

// ───────────── 화면: 사이드바 ─────────────
function renderSidebar() {
  document.querySelectorAll('.nav-item').forEach((el) => {
    el.classList.toggle('active', [state.view.type, `${state.view.type}s`].includes(el.dataset.view));
  });
  $('#playlist-nav').replaceChildren(...state.playlists.map((p) => {
    const btn = h('button', {
      class: state.view.type === 'playlist' && state.view.id === p.id ? 'active' : null,
      title: p.name,
      onclick: safe(() => openView({ type: 'playlist', id: p.id })),
    }, p.name);
    // 곡을 끌어다 놓으면 플레이리스트에 추가
    btn.addEventListener('dragover', (e) => {
      if (dragTrackId == null) return;
      e.preventDefault();
      btn.classList.add('drop-target');
    });
    btn.addEventListener('dragleave', () => btn.classList.remove('drop-target'));
    btn.addEventListener('drop', safe(async (e) => {
      btn.classList.remove('drop-target');
      if (dragTrackId == null) return;
      e.preventDefault();
      await addTracksToPlaylist(p.id, [dragTrackId]);
    }));
    return h('li', {}, btn);
  }));
}

// ───────────── 화면: 곡 목록 ─────────────
// 아티스트·앨범 이름을 누르면 그 화면으로 이동한다. 곡 행·대기열 항목의 클릭(재생)으로 번지지 않게 막는다.
function groupLink(kind, name, label = name) {
  return h('button', {
    type: 'button',
    class: 'text-link',
    title: `${kind === 'artist' ? '아티스트' : '앨범'} 보기`,
    onclick: (e) => {
      e.stopPropagation();
      safe(() => openView({ type: kind, name }))();
    },
  }, label);
}
const artistLink = (t) => groupLink('artist', t.artist || UNKNOWN_ARTIST);
const albumLink = (t) => (t.album ? groupLink('album', t.album) : '');

function coverEl(track, cls = 'cover') {
  const el = h('div', { class: cls });
  if (track?.hasCover) el.append(h('img', { src: `/api/tracks/${track.id}/cover`, loading: 'lazy', alt: '' }));
  else el.textContent = '♪';
  return el;
}

function setQuery(value) {
  state.query = value;
  $('#search').value = value;
}

const VIEW_KIND = { library: '라이브러리', playlist: '플레이리스트', artist: '아티스트', album: '앨범', recent: '라이브러리', top: '라이브러리' };

function renderMain() {
  // 선택 막대는 곡 목록을 다 그린 뒤 renderSelection이 다시 보여 준다.
  $('#selection-bar').hidden = true;
  $('#track-list').classList.remove('selecting');
  if (GRID_VIEWS[state.view.type]) return renderGroups();
  const { view, rows, query } = state;
  const isPlaylist = view.type === 'playlist';
  const shown = query ? rows.filter((t) => matchesQuery(t, query)) : rows;
  state.shown = shown;
  state.selected = pruneSelection(state.selected, shown.map(rowKey));
  const total = shown.reduce((sum, t) => sum + (t.duration || 0), 0);

  $('#view-kind').textContent = VIEW_KIND[view.type];
  $('#view-title').textContent = view.type === 'library' ? '모든 곡' : SMART_LISTS[view.type]?.title ?? view.name;
  $('#view-meta').textContent = query
    ? `검색 결과 ${shown.length}곡 / 전체 ${rows.length}곡`
    : `${rows.length}곡 · ${fmtTotal(total)}`;
  $('#search').hidden = !rows.length;

  const ids = shown.map((t) => t.id);
  const actions = [
    h('button', { class: 'btn primary', disabled: !shown.length, onclick: () => playList(ids, 0) }, '▶ 재생'),
    h('button', { class: 'btn', disabled: !shown.length, onclick: () => playList(ids, 0, true) }, '셔플 재생'),
  ];
  if (isPlaylist) {
    actions.push(
      h('button', { class: 'btn', onclick: safe(renamePlaylist) }, '이름 변경'),
      h('button', { class: 'btn danger', onclick: safe(deletePlaylist) }, '삭제'),
    );
  } else if (view.type === 'artist' || view.type === 'album') {
    actions.push(h('button', { class: 'btn', onclick: safe(() => openView({ type: `${view.type}s` })) },
      view.type === 'artist' ? '← 모든 아티스트' : '← 모든 앨범'));
  } else if (view.type !== 'top') {
    actions.push(h('button', { class: 'btn', onclick: () => $('#file-input').click() }, '＋ 업로드'));
  }
  $('#view-actions').replaceChildren(...actions);

  const list = $('#track-list');
  if (!rows.length) {
    if (view.type === 'artist' || view.type === 'album') {
      list.replaceChildren(h('div', { class: 'empty' }, `이 ${VIEW_KIND[view.type]}에 해당하는 곡이 없습니다.`));
      return;
    }
    if (SMART_LISTS[view.type]) {
      list.replaceChildren(h('div', { class: 'empty' }, SMART_LISTS[view.type].empty));
      return;
    }
    list.replaceChildren(isPlaylist
      ? h('div', { class: 'empty' }, '아직 곡이 없습니다. 라이브러리에서 곡의 ⋯ 메뉴로 추가하거나 곡을 이 플레이리스트 이름 위로 끌어다 놓으세요.')
      : h('div', { class: 'empty' },
        h('div', {}, '라이브러리가 비어 있습니다. 음원 파일을 이 창에 끌어다 놓거나 업로드하세요.'),
        h('button', { class: 'btn primary', onclick: () => $('#file-input').click() }, '파일 선택')));
    return;
  }
  if (!shown.length) {
    list.replaceChildren(h('div', { class: 'empty' }, `'${query}'와(과) 일치하는 곡이 없습니다.`));
    return;
  }

  const head = h('div', { class: 'track-row head' },
    h('div', { class: 't-num' },
      h('span', { class: 'num' }, '#'),
      h('input', { type: 'checkbox', class: 't-check', id: 'select-all', 'aria-label': '모두 선택', onclick: (e) => { e.stopPropagation(); toggleSelectAll(); } })),
    h('div', {}, '제목'), h('div', { class: 't-album' }, view.type === 'top' ? '들은 횟수' : '앨범'),
    h('div', { class: 't-dur' }, '길이'), h('div'));
  list.replaceChildren(head, ...shown.map((t, i) => h('div', {
    class: 'track-row',
    role: 'listitem',
    draggable: 'true',
    dataset: { idx: i },
    title: '클릭하면 재생 · Ctrl/⌘+클릭으로 선택',
    onclick: (e) => {
      if (e.ctrlKey || e.metaKey || (e.shiftKey && state.selected.size)) return selectRow(i, e.shiftKey);
      playList(ids, i);
    },
  },
  h('div', { class: 't-num' },
    h('span', { class: 'num' }, String(i + 1)),
    h('input', { type: 'checkbox', class: 't-check', 'aria-label': `${t.title} 선택`, onclick: (e) => { e.stopPropagation(); selectRow(i, e.shiftKey); } })),
  h('div', { class: 't-main' }, coverEl(t),
    h('div', { class: 't-text' },
      h('div', { class: 't-title' }, t.title),
      h('div', { class: 't-artist' }, artistLink(t)))),
  h('div', { class: 't-album' }, view.type === 'top' ? `${t.playCount}회` : albumLink(t)),
  h('div', { class: 't-dur' }, fmt(t.duration)),
  h('button', {
    class: 'icon-btn', title: '더 보기', html: ICON.more,
    onclick: (e) => { e.stopPropagation(); openTrackMenu(e.currentTarget, i); },
  }))));
  highlightPlaying();
  renderSelection();
}

// 아티스트·앨범 목록: 커버 카드 격자. 카드를 누르면 그 곡 목록, 재생 버튼을 누르면 바로 재생.
function renderGroups() {
  const { view, query } = state;
  const kind = GRID_VIEWS[view.type];
  const all = groupTracks(state.tracks, kind);
  const groups = query
    ? all.filter((g) => matchesQuery({ title: g.name, artist: g.tracks.map((t) => t.artist).join(' ') }, query))
    : all;
  state.shown = groups.flatMap((g) => g.tracks);
  const unit = kind === 'artist' ? '명' : '개';

  $('#view-kind').textContent = '라이브러리';
  $('#view-title').textContent = kind === 'artist' ? '아티스트' : '앨범';
  $('#view-meta').textContent = query ? `검색 결과 ${groups.length}${unit} / 전체 ${all.length}${unit}` : `${all.length}${unit}`;
  $('#search').hidden = !all.length;
  const ids = state.shown.map((t) => t.id);
  $('#view-actions').replaceChildren(
    h('button', { class: 'btn primary', disabled: !ids.length, onclick: () => playList(ids, 0) }, '▶ 재생'),
    h('button', { class: 'btn', disabled: !ids.length, onclick: () => playList(ids, 0, true) }, '셔플 재생'),
  );

  const list = $('#track-list');
  if (!groups.length) {
    list.replaceChildren(h('div', { class: 'empty' }, query
      ? `'${query}'와(과) 일치하는 ${kind === 'artist' ? '아티스트' : '앨범'}가 없습니다.`
      : kind === 'artist' ? '라이브러리가 비어 있습니다.' : '앨범 정보가 있는 곡이 없습니다. 곡 정보 수정에서 앨범을 넣을 수 있습니다.'));
    return;
  }
  const open = (g) => safe(() => openView({ type: kind, name: g.name }));
  list.replaceChildren(h('div', { class: `group-grid ${view.type}` }, groups.map((g) => h('div', {
    class: 'group-card',
    role: 'button',
    tabindex: '0',
    title: g.name,
    onclick: open(g),
    onkeydown: (e) => { if (e.key === 'Enter') open(g)(); },
  },
  h('div', { class: 'group-art' },
    coverEl(g.cover, 'cover xl'),
    h('button', {
      class: 'icon-btn group-play', title: '재생', html: ICON.play,
      onclick: (e) => { e.stopPropagation(); playList(g.tracks.map((t) => t.id), 0); },
    })),
  h('div', { class: 'group-name' }, g.name),
  h('div', { class: 'group-sub' }, g.subtitle)))));
}

function highlightPlaying() {
  const id = currentTrack()?.id;
  document.querySelectorAll('#track-list .track-row[data-idx]').forEach((row) => {
    row.classList.toggle('playing', state.shown[row.dataset.idx]?.id === id);
  });
}

function openTrackMenu(anchor, i) {
  const t = state.shown[i];
  showMenu(anchor, [
    ['다음에 재생', () => { playNext([t.id]); toast('다음에 재생합니다'); }],
    ['대기열에 추가', () => { addToQueue([t.id]); toast('대기열에 추가했습니다'); }],
    ['플레이리스트에 추가…', safe(() => addToPlaylistFlow([t.id]))],
    ['곡 정보 수정…', safe(() => editTrack(t))],
    [state.selected.has(rowKey(t)) ? '선택 해제' : '선택', () => selectRow(i, false)],
    [t.hasLyrics ? '가사 편집…' : '가사 추가…', safe(() => editLyrics(t))],
    null,
    state.view.type === 'playlist'
      ? ['플레이리스트에서 제거', safe(() => removeFromPlaylist(t.entryId)), 'danger']
      : ['라이브러리에서 삭제', safe(() => deleteTrack(t)), 'danger'],
  ]);
}

// ───────────── 라이브러리 / 플레이리스트 작업 ─────────────
async function deleteTrack(t) {
  if (!confirm(`'${t.title}'을(를) 라이브러리에서 삭제할까요?\n파일도 서버에서 지워지고 모든 플레이리스트에서 빠집니다.`)) return;
  await api('DELETE', `/api/tracks/${t.id}`);
  await Promise.all([loadLibrary(), loadPlaylists()]);
  await refreshView();
  toast('삭제했습니다');
}

async function editTrack(t) {
  const field = (label, name, value, required) => h('label', {}, label,
    h('input', { name, value: value ?? '', maxlength: 200, required: required || null }));
  const inputs = [
    field('제목', 'title', t.title, true),
    field('아티스트', 'artist', t.artist),
    field('앨범', 'album', t.album),
  ];
  const result = await openDialog('곡 정보 수정', [h('div', { class: 'field-list' }, inputs)]);
  if (result !== 'ok') return;
  const value = (name) => inputs.find((el) => el.querySelector('input').name === name).querySelector('input').value.trim();
  await api('PATCH', `/api/tracks/${t.id}`, { title: value('title'), artist: value('artist'), album: value('album') });
  await loadLibrary();
  await refreshView();
  renderPlayer();
  renderQueue();
  toast('곡 정보를 바꿨습니다');
}

async function createPlaylist() {
  const name = await promptDialog('새 플레이리스트', `플레이리스트 ${state.playlists.length + 1}`);
  if (!name) return null;
  const playlist = await api('POST', '/api/playlists', { name });
  await loadPlaylists();
  return playlist;
}

async function renamePlaylist() {
  const name = await promptDialog('플레이리스트 이름 변경', state.view.name);
  if (!name || name === state.view.name) return;
  await api('PATCH', `/api/playlists/${state.view.id}`, { name });
  await loadPlaylists();
  await refreshView();
}

async function deletePlaylist() {
  if (!confirm(`'${state.view.name}' 플레이리스트를 삭제할까요? (곡 파일은 그대로 남습니다)`)) return;
  await api('DELETE', `/api/playlists/${state.view.id}`);
  await loadPlaylists();
  await openView({ type: 'library' });
}

// 이미 들어 있는 곡이 있으면 새 곡만 넣을지, 모두 넣을지 묻는다.
async function addTracksToPlaylist(playlistId, trackIds) {
  const name = state.playlists.find((p) => p.id === playlistId)?.name ?? '';
  const current = await api('GET', `/api/playlists/${playlistId}`);
  const plan = planPlaylistAdd(current.tracks.map((t) => t.id), trackIds);
  let ids = plan.all;
  if (plan.duplicates) {
    const allDupes = !plan.fresh.length;
    const choice = await chooseDialog('이미 들어 있는 곡이 있습니다', allDupes
      ? [{ value: 'all', label: plan.all.length > 1 ? `그래도 ${plan.all.length}곡 모두 추가` : '그래도 추가' }]
      : [
        { value: 'fresh', label: `새 곡 ${plan.fresh.length}곡만 추가` },
        { value: 'all', label: `이미 있는 곡까지 ${plan.all.length}곡 모두 추가` },
      ], allDupes
      ? `${plan.all.length > 1 ? '고른 곡이 모두' : '이 곡은'} '${name}'에 이미 있습니다.`
      : `고른 ${plan.all.length}곡 중 ${plan.duplicates}곡은 '${name}'에 이미 있습니다.`);
    if (choice !== 'fresh' && choice !== 'all') return;
    if (choice === 'fresh') ids = plan.fresh;
  }
  await api('POST', `/api/playlists/${playlistId}/tracks`, { trackIds: ids });
  await loadPlaylists();
  if (state.view.type === 'playlist' && state.view.id === playlistId) await refreshView();
  const skipped = plan.all.length - ids.length;
  toast(`'${name}'에 ${ids.length}곡을 추가했습니다${skipped ? ` (이미 있는 곡 ${skipped}개 건너뜀)` : ''}`);
}

async function addToPlaylistFlow(trackIds) {
  const NEW = '__new__';
  const choice = await chooseDialog('플레이리스트에 추가', [
    ...state.playlists.map((p) => ({ value: String(p.id), label: `${p.name}  ·  ${p.trackCount}곡` })),
    { value: NEW, label: '＋ 새 플레이리스트 만들기' },
  ]);
  if (!choice || choice === 'cancel') return;
  let id = Number(choice);
  if (choice === NEW) {
    const playlist = await createPlaylist();
    if (!playlist) return;
    id = playlist.id;
  }
  await addTracksToPlaylist(id, trackIds);
}

// ───────────── 여러 곡 선택 ─────────────
const rowKey = (t) => t.entryId ?? t.id;
const selectedRows = () => state.shown.filter((t) => state.selected.has(rowKey(t)));

function selectRow(i, range) {
  ({ selected: state.selected, anchor: state.anchor } = clickSelection(
    state.selected, state.shown.map(rowKey), i, { range, anchor: state.anchor }));
  renderSelection();
}

function toggleSelectAll() {
  const all = state.shown.length && state.shown.every((t) => state.selected.has(rowKey(t)));
  state.selected = all ? new Set() : new Set(state.shown.map(rowKey));
  renderSelection();
}

function clearSelection(render = true) {
  state.selected = new Set();
  state.anchor = null;
  if (render) renderSelection();
}

// 목록을 다시 그리지 않고 체크 상태와 선택 막대만 맞춘다.
function renderSelection() {
  const rows = document.querySelectorAll('#track-list .track-row[data-idx]');
  rows.forEach((row) => {
    const on = state.selected.has(rowKey(state.shown[row.dataset.idx]));
    row.classList.toggle('selected', on);
    row.querySelector('.t-check').checked = on;
  });
  const count = selectedRows().length;
  const all = $('#select-all');
  if (all) {
    all.checked = count > 0 && count === state.shown.length;
    all.indeterminate = count > 0 && count < state.shown.length;
  }
  $('#track-list').classList.toggle('selecting', count > 0);

  const bar = $('#selection-bar');
  bar.hidden = !count;
  if (!count) return bar.replaceChildren();
  const ids = () => selectedRows().map((t) => t.id);
  const done = (fn) => safe(async () => { await fn(); clearSelection(); });
  bar.replaceChildren(
    h('strong', {}, `${count}곡 선택`),
    h('button', { class: 'btn primary', onclick: done(() => playList(ids(), 0)) }, '▶ 재생'),
    h('button', { class: 'btn', onclick: done(() => { playNext(ids()); toast(`${count}곡을 다음에 재생합니다`); }) }, '다음에 재생'),
    h('button', { class: 'btn', onclick: done(() => { addToQueue(ids()); toast(`${count}곡을 대기열에 추가했습니다`); }) }, '대기열에 추가'),
    h('button', { class: 'btn', onclick: done(() => addToPlaylistFlow(ids())) }, '플레이리스트에 추가…'),
    state.view.type === 'playlist'
      ? h('button', { class: 'btn danger', onclick: done(() => removeEntries(selectedRows())) }, '플레이리스트에서 제거')
      : h('button', { class: 'btn danger', onclick: done(() => deleteTracks(selectedRows())) }, '삭제'),
    h('button', { class: 'link', onclick: () => clearSelection() }, '선택 해제'),
  );
}

async function deleteTracks(tracks) {
  if (!tracks.length || !confirm(`선택한 ${tracks.length}곡을 라이브러리에서 삭제할까요?\n파일도 서버에서 지워지고 모든 플레이리스트에서 빠집니다.`)) return;
  const { deleted } = await api('POST', '/api/tracks/bulk-delete', { trackIds: [...new Set(tracks.map((t) => t.id))] });
  await Promise.all([loadLibrary(), loadPlaylists()]);
  await refreshView();
  toast(`${deleted.length}곡을 삭제했습니다`);
}

async function removeEntries(rows) {
  for (const t of rows) await api('DELETE', `/api/playlists/${state.view.id}/tracks/${t.entryId}`);
  await loadPlaylists();
  await refreshView();
  toast(`플레이리스트에서 ${rows.length}곡을 뺐습니다`);
}

async function removeFromPlaylist(entryId) {
  await api('DELETE', `/api/playlists/${state.view.id}/tracks/${entryId}`);
  await loadPlaylists();
  await refreshView();
}

async function reorderPlaylist(from, to) {
  const rows = [...state.rows];
  rows.splice(to, 0, rows.splice(from, 1)[0]);
  state.rows = rows;
  renderMain();
  try {
    await api('PUT', `/api/playlists/${state.view.id}/order`, { entryIds: rows.map((r) => r.entryId) });
  } catch (err) {
    toast(err.message);
    await refreshView();
  }
}

// ───────────── 업로드 ─────────────
function uploadSummary({ added, duplicates = [], rejected = [], tooLarge = [], lyrics = { attached: [], unmatched: [] } }) {
  const parts = [];
  if (added.length) parts.push(`${added.length}곡을 추가했습니다`);
  if (lyrics.attached.length) parts.push(`가사 ${lyrics.attached.length}개를 연결했습니다`);
  let msg = parts.join(', ') || '새로 추가된 곡이 없습니다';
  const skipped = [];
  if (duplicates.length) skipped.push(`이미 있는 곡 ${duplicates.length}개`);
  if (lyrics.unmatched.length) skipped.push(`짝을 못 찾은 가사 ${lyrics.unmatched.length}개`);
  if (rejected.length) skipped.push(`지원하지 않는 파일 ${rejected.length}개`);
  if (tooLarge.length) skipped.push(`${Math.round(maxUploadBytes / 1024 / 1024)}MB가 넘는 파일 ${tooLarge.length}개`);
  if (skipped.length) msg += ` (${skipped.join(', ')} 건너뜀)`;
  return msg;
}

let maxUploadBytes = Infinity; // 서버가 알려 준 파일 하나의 최대 크기
let uploading = false;

// 묶음 하나를 보낸다. 응답 코드와 본문을 돌려주고, 네트워크 오류면 reject.
function postBatch(files, onProgress, onSent) {
  const form = new FormData();
  files.forEach((f) => form.append('files', f, f.name));
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/tracks');
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
    xhr.upload.onload = onSent;
    xhr.onerror = () => reject(new Error('네트워크 오류'));
    xhr.onload = () => {
      let data = null;
      try { data = JSON.parse(xhr.responseText); } catch { /* 본문 없음 */ }
      resolve({ status: xhr.status, data });
    };
    xhr.send(form);
  });
}

// 파일이 많거나 크면 여러 번에 나눠 보낸다. 한 묶음이 실패해도 나머지는 계속 올린다.
async function uploadFiles(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  if (uploading) return toast('이미 업로드 중입니다. 끝난 뒤 다시 시도하세요');
  const { batches, tooLarge } = planUploads(files, { maxFileBytes: maxUploadBytes });
  const sizeOf = (batch) => batch.reduce((sum, f) => sum + f.size, 0);
  const totalBytes = batches.reduce((sum, b) => sum + sizeOf(b), 0) || 1;
  const results = [];
  let failedFiles = 0;
  let failReason = '';
  let doneBytes = 0;

  uploading = true;
  try {
    for (const [i, batch] of batches.entries()) {
      const step = batches.length > 1 ? ` (${i + 1}/${batches.length})` : '';
      const bytes = sizeOf(batch);
      let res;
      try {
        res = await postBatch(
          batch,
          (ratio) => toast(`업로드 중… ${Math.min(100, Math.round(((doneBytes + ratio * bytes) / totalBytes) * 100))}%${step}`, 0),
          () => toast(`곡 정보를 읽는 중…${step}`, 0),
        );
      } catch (err) {
        res = { status: 0, data: { error: err.message } };
      }
      if (res.status === 401) {
        $('#toast').hidden = true;
        return showAuth(false);
      }
      if (res.status >= 200 && res.status < 300) results.push(res.data);
      else {
        failedFiles += batch.length;
        failReason = res.data?.error || `업로드 실패 (${res.status})`;
      }
      doneBytes += bytes;
    }
  } finally {
    uploading = false;
  }

  if (results.length) {
    await loadLibrary();
    if (state.view.type !== 'playlist') await refreshView();
    loadLyrics(true); // 지금 재생 중인 곡에 가사가 붙었을 수 있음
  }
  let msg = uploadSummary({ ...mergeResults(results), tooLarge });
  if (failedFiles) msg += ` · 파일 ${failedFiles}개 업로드 실패: ${failReason}`;
  toast(msg, failedFiles ? 8000 : 5000);
}

// ───────────── 플레이어 ─────────────
const audio = new Audio();
audio.preload = 'metadata';
let mediaSession = { update() {} }; // 아래 이벤트 연결부에서 설정

// 대기열 항목은 같은 곡이 여러 번 들어가도 구분되도록 고유 key를 가진다.
let nextKey = 1;
const item = (id) => ({ key: nextKey++, id });

const player = {
  queue: [],
  index: -1,
  original: null, // 셔플 전 순서 (셔플을 끄면 되돌림)
  shuffle: false,
  repeat: 'off', // off | all | one
};

const currentItem = () => player.queue[player.index];
const currentTrack = () => state.byId.get(currentItem()?.id);

function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// 현재 곡은 맨 앞에 두고 나머지만 섞는다.
function applyShuffle() {
  player.original = [...player.queue];
  const cur = currentItem();
  const rest = shuffleArray(player.queue.filter((it) => it !== cur));
  player.queue = cur ? [cur, ...rest] : rest;
  player.index = cur ? 0 : -1;
}

// 곡을 절반 이상 들으면 서버에 한 번 들었다고 기록한다.
const listenTracker = createListenTracker(() => {
  const t = currentTrack();
  if (!t) return;
  api('POST', `/api/tracks/${t.id}/plays`)
    .then(({ playCount, lastPlayedAt }) => Object.assign(t, { playCount, lastPlayedAt }))
    .catch(() => { /* 기록 실패는 재생에 영향 없음 */ });
});

function load(autoplay, startAt = 0) {
  listenTracker.reset();
  const track = currentTrack();
  if (!track) {
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
  } else {
    audio.src = `/api/tracks/${track.id}/stream`;
    if (startAt > 0) audio.addEventListener('loadedmetadata', () => { audio.currentTime = startAt; }, { once: true });
    if (autoplay) audio.play().catch(() => {});
  }
  queueChanged();
}

function playList(ids, start, shuffle = false) {
  if (!ids.length) return;
  player.queue = ids.map(item);
  player.index = start;
  player.original = null;
  if (shuffle) {
    player.shuffle = true;
    player.index = Math.floor(Math.random() * ids.length);
  }
  if (player.shuffle) applyShuffle();
  load(true);
}

function next(auto = false) {
  if (!player.queue.length) return;
  if (auto && player.repeat === 'one') {
    audio.currentTime = 0;
    audio.play().catch(() => {});
    return;
  }
  if (player.index < player.queue.length - 1) player.index++;
  else if (player.repeat === 'all') player.index = 0;
  else if (auto) return renderPlayer(); // 마지막 곡이 끝나면 멈춤
  else return;
  load(true);
}

function prev() {
  if (audio.currentTime > 3 || !player.queue.length) {
    audio.currentTime = 0;
    return;
  }
  if (player.index > 0) player.index--;
  else if (player.repeat === 'all') player.index = player.queue.length - 1;
  else { audio.currentTime = 0; return; }
  load(true);
}

function togglePlay() {
  if (!currentTrack()) {
    if (state.shown.length) playList(state.shown.map((t) => t.id), 0);
    return;
  }
  if (!audio.getAttribute('src')) return load(true);
  if (audio.paused) audio.play().catch(() => {});
  else audio.pause();
}

function playNext(ids) {
  const items = ids.map(item);
  player.queue.splice(player.index + 1, 0, ...items);
  if (player.original) player.original.push(...items);
  if (player.index < 0) { player.index = 0; load(true); return; }
  queueChanged();
}

function addToQueue(ids) {
  const items = ids.map(item);
  player.queue.push(...items);
  if (player.original) player.original.push(...items);
  if (player.index < 0) { player.index = 0; load(true); return; }
  queueChanged();
}

function removeFromQueue(i) {
  const [removed] = player.queue.splice(i, 1);
  if (player.original) player.original = player.original.filter((it) => it !== removed);
  if (i < player.index) player.index--;
  else if (i === player.index) {
    const atEnd = player.index >= player.queue.length;
    if (atEnd) player.index = player.queue.length - 1;
    load(!atEnd && !audio.paused);
    return;
  }
  queueChanged();
}

function moveInQueue(from, to) {
  const cur = currentItem();
  player.queue.splice(to, 0, player.queue.splice(from, 1)[0]);
  player.index = player.queue.indexOf(cur);
  queueChanged();
}

function clearUpcoming() {
  const keep = player.queue.slice(0, player.index + 1);
  if (player.original) player.original = player.original.filter((it) => keep.includes(it));
  player.queue = keep;
  queueChanged();
}

// 라이브러리에서 지워진 곡을 대기열에서도 뺀다.
function pruneQueue() {
  const cur = currentItem();
  const alive = (it) => state.byId.has(it.id);
  if (player.original) player.original = player.original.filter(alive);
  const before = player.queue.slice(0, Math.max(player.index, 0)).filter(alive).length;
  player.queue = player.queue.filter(alive);
  if (cur && alive(cur)) {
    player.index = player.queue.indexOf(cur);
    return queueChanged();
  }
  if (cur) {
    player.index = Math.min(before, player.queue.length - 1);
    load(false);
  }
}

function toggleShuffle() {
  player.shuffle = !player.shuffle;
  if (player.shuffle) applyShuffle();
  else if (player.original) {
    const cur = currentItem();
    player.queue = player.original;
    player.index = player.queue.indexOf(cur);
    player.original = null;
  }
  queueChanged();
}

function cycleRepeat() {
  player.repeat = { off: 'all', all: 'one', one: 'off' }[player.repeat];
  renderPlayer();
  savePlayer();
}

function queueChanged() {
  renderPlayer();
  renderQueue();
  loadLyrics();
  highlightPlaying();
  savePlayer();
}

function savePlayer() {
  store.set('mp_player', {
    ids: player.queue.map((it) => it.id),
    index: player.index,
    shuffle: player.shuffle,
    repeat: player.repeat,
    volume: audio.volume,
    muted: audio.muted,
    time: audio.currentTime || 0,
  });
}

function restorePlayer() {
  const s = store.get('mp_player', null);
  if (!s) return;
  audio.volume = Number.isFinite(s.volume) ? s.volume : 1;
  audio.muted = Boolean(s.muted);
  player.shuffle = Boolean(s.shuffle);
  player.repeat = ['off', 'all', 'one'].includes(s.repeat) ? s.repeat : 'off';
  const ids = Array.isArray(s.ids) ? s.ids : [];
  const sameTrack = state.byId.has(ids[s.index]);
  const removedBefore = ids.slice(0, s.index).filter((id) => !state.byId.has(id)).length;
  player.queue = ids.filter((id) => state.byId.has(id)).map(item);
  player.index = player.queue.length ? Math.min(Math.max(s.index - removedBefore, 0), player.queue.length - 1) : -1;
  load(false, sameTrack ? s.time : 0);
}

// ───────────── 화면: 플레이어 / 대기열 ─────────────
function setFill(input) {
  const max = Number(input.max) || 1;
  input.style.setProperty('--fill', `${(Number(input.value) / max) * 100}%`);
}

function renderPlayer() {
  const t = currentTrack();
  $('#now-cover').replaceWith(Object.assign(coverEl(t), { id: 'now-cover' }));
  $('#now-title').textContent = t ? t.title : '재생 중인 곡 없음';
  $('#now-artist').replaceChildren(t ? artistLink(t) : '');
  document.title = t ? `${t.title}${t.artist ? ` - ${t.artist}` : ''}` : 'My Music';

  $('#btn-play').innerHTML = audio.paused ? ICON.play : ICON.pause;
  $('#btn-play').title = audio.paused ? '재생' : '일시정지';
  $('#btn-shuffle').classList.toggle('active', player.shuffle);
  $('#btn-repeat').innerHTML = player.repeat === 'one' ? ICON.repeatOne : ICON.repeat;
  $('#btn-repeat').classList.toggle('active', player.repeat !== 'off');
  $('#btn-repeat').title = { off: '반복 안 함', all: '전체 반복', one: '한 곡 반복' }[player.repeat];
  $('#btn-mute').innerHTML = audio.muted || audio.volume === 0 ? ICON.mute : ICON.volume;
  $('#volume').value = audio.muted ? 0 : audio.volume;
  setFill($('#volume'));
  mediaSession.update();
}

function renderQueue() {
  const box = $('#queue-list');
  if (!player.queue.length) {
    box.replaceChildren(h('div', { class: 'empty' }, '대기열이 비어 있습니다'));
    return;
  }
  const row = (it, i) => {
    const t = state.byId.get(it.id);
    const isCurrent = i === player.index;
    return h('div', {
      class: `q-item${isCurrent ? ' current' : ''}`,
      draggable: isCurrent ? null : 'true',
      dataset: { idx: i },
    },
    coverEl(t),
    h('div', { class: 't-text', onclick: () => { player.index = i; load(true); } },
      h('div', { class: 'q-title' }, t.title),
      h('div', { class: 'q-artist' }, artistLink(t))),
    h('button', { class: 'icon-btn', title: '대기열에서 빼기', html: ICON.close, onclick: () => removeFromQueue(i) }));
  };
  const upcoming = player.queue.slice(player.index + 1);
  box.replaceChildren(
    h('div', { class: 'queue-label' }, '지금 재생 중'),
    currentItem() ? row(currentItem(), player.index) : null,
    h('div', { class: 'queue-label' }, `다음 곡 · ${upcoming.length}`),
    ...upcoming.map((it, k) => row(it, player.index + 1 + k)),
  );
}

// ───────────── 가사 ─────────────
const lyricsState = { trackId: null, parsed: null, active: -1 };

const currentPanel = () => (!$('#queue').hidden ? 'queue' : !$('#lyrics').hidden ? 'lyrics' : null);

// 오른쪽 패널은 대기열과 가사 중 하나만 연다.
function setPanel(name) {
  $('#queue').hidden = name !== 'queue';
  $('#lyrics').hidden = name !== 'lyrics';
  $('#btn-queue').classList.toggle('active', name === 'queue');
  $('#btn-lyrics').classList.toggle('active', name === 'lyrics');
  store.set('mp_panel', name);
  if (name === 'lyrics') loadLyrics(true);
}
const togglePanel = (name) => setPanel(currentPanel() === name ? null : name);

async function loadLyrics(force = false) {
  if ($('#lyrics').hidden) return;
  const t = currentTrack();
  if (!force && lyricsState.trackId === (t?.id ?? null)) return;
  lyricsState.trackId = t?.id ?? null;
  lyricsState.parsed = null;
  if (!t) return renderLyrics();
  if (!t.hasLyrics) {
    lyricsState.parsed = parseLyrics('');
    return renderLyrics();
  }
  renderLyrics();
  let parsed;
  try {
    parsed = parseLyrics((await api('GET', `/api/tracks/${t.id}/lyrics`)).lyrics);
  } catch (err) {
    toast(err.message);
    parsed = parseLyrics('');
  }
  if (lyricsState.trackId !== t.id) return; // 불러오는 사이 곡이 바뀜
  lyricsState.parsed = parsed;
  renderLyrics();
}

function renderLyrics() {
  const box = $('#lyrics-body');
  const t = currentTrack();
  const parsed = lyricsState.parsed;
  $('#lyrics-edit').hidden = !t;
  $('#lyrics-sync').hidden = !t || !parsed?.lines.length;
  box.classList.toggle('synced', Boolean(parsed?.synced));
  lyricsState.active = -1;
  if (!t) return box.replaceChildren(h('div', { class: 'empty' }, '재생 중인 곡이 없습니다'));
  if (!parsed) return box.replaceChildren(h('div', { class: 'empty' }, '가사를 불러오는 중…'));
  if (!parsed.lines.length) {
    return box.replaceChildren(h('div', { class: 'empty' },
      h('div', {}, '이 곡에는 가사가 없습니다.'),
      h('button', { class: 'btn', onclick: safe(() => editLyrics(t)) }, '가사 추가')));
  }
  box.replaceChildren(...parsed.lines.map((line, i) => h('p', {
    class: 'lyric-line',
    dataset: { idx: i },
    title: parsed.synced ? '이 부분부터 재생' : null,
    onclick: parsed.synced ? () => {
      audio.currentTime = line.time;
      if (audio.paused) audio.play().catch(() => {});
    } : null,
  }, line.text || (parsed.synced ? '♪' : '\u00a0'))));
  syncLyrics(true);
}

// 재생 위치에 맞는 줄을 강조하고 가운데로 스크롤한다.
function syncLyrics(jump = false) {
  const parsed = lyricsState.parsed;
  if ($('#lyrics').hidden || !parsed?.synced || lyricsState.trackId !== currentTrack()?.id) return;
  const i = currentLineIndex(parsed.lines, audio.currentTime);
  if (i === lyricsState.active) return;
  lyricsState.active = i;
  const box = $('#lyrics-body');
  box.querySelector('.lyric-line.active')?.classList.remove('active');
  const el = box.querySelector(`.lyric-line[data-idx="${i}"]`);
  if (!el) return;
  el.classList.add('active');
  box.scrollTo({ top: el.offsetTop - box.clientHeight / 2 + el.offsetHeight / 2, behavior: jump ? 'auto' : 'smooth' });
}

async function editLyrics(t) {
  const current = t.hasLyrics ? (await api('GET', `/api/tracks/${t.id}/lyrics`)).lyrics : '';
  const textarea = h('textarea', { name: 'lyrics', placeholder: '[00:12.34] 가사 첫 줄\n[00:17.80] 가사 둘째 줄', spellcheck: 'false' });
  textarea.value = current ?? '';
  const fileInput = h('input', { type: 'file', accept: '.lrc,.txt,text/plain', hidden: true, onchange: async (e) => {
    const file = e.target.files[0];
    if (file) textarea.value = await file.text();
  } });
  const result = await openDialog(`가사 · ${t.title}`, [
    h('p', { class: 'dialog-hint' }, '싱크 가사(.lrc, [분:초] 형식)나 일반 가사를 붙여 넣으세요. 비우고 확인하면 가사가 지워집니다.'),
    textarea,
    h('div', { class: 'dialog-tools' },
      h('button', { type: 'button', class: 'link', onclick: () => fileInput.click() }, '.lrc 파일 불러오기'),
      fileInput),
  ]);
  if (result !== 'ok') return;
  const updated = await api('PUT', `/api/tracks/${t.id}/lyrics`, { lyrics: textarea.value });
  await loadLibrary();
  await refreshView();
  if (currentTrack()?.id === t.id) loadLyrics(true);
  toast(updated.hasLyrics ? '가사를 저장했습니다' : '가사를 지웠습니다');
}

// 싱크 맞추기: 노래를 들으며 줄이 시작될 때 Enter(또는 "찍기")를 누른다.
let syncingLyrics = false;

async function openLyricSync() {
  const t = currentTrack();
  if (!t) return;
  const parsed = parseLyrics((await api('GET', `/api/tracks/${t.id}/lyrics`)).lyrics);
  if (!parsed.lines.length) return toast('먼저 가사를 넣어 주세요');
  let sync = createSync(parsed.lines);

  const list = h('ol', { class: 'sync-list' });
  const progress = h('span', { class: 'muted' });
  const clock = h('span', { class: 'sync-clock' });
  const playBtn = h('button', { type: 'button', class: 'icon-btn play', title: '재생/일시정지 (Space)', onclick: togglePlay });
  const render = () => {
    list.replaceChildren(...sync.lines.map((line, i) => h('li', {
      class: `sync-line${i === sync.target ? ' target' : ''}${line.time != null ? ' done' : ''}`,
      title: '이 줄부터 다시 찍기',
      onclick: () => { sync = jumpTo(sync, i); render(); },
    },
    h('span', { class: 'sync-stamp' }, line.time != null ? lrcTime(line.time).slice(1, -1) : '--:--.--'),
    h('span', {}, line.text || '♪'))));
    list.querySelector('.target')?.scrollIntoView({ block: 'center' });
    progress.textContent = `${sync.lines.length - missingCount(sync)} / ${sync.lines.length}줄`;
  };
  const doStamp = () => { sync = stamp(sync, audio.currentTime); render(); };
  const doUndo = () => { sync = undo(sync); render(); };
  const tick = () => {
    clock.textContent = fmt(audio.currentTime);
    playBtn.innerHTML = audio.paused ? ICON.play : ICON.pause;
  };
  const onKey = (e) => {
    if (e.key === 'Enter') { e.preventDefault(); doStamp(); }
    else if (e.key === 'Backspace') { e.preventDefault(); doUndo(); }
    else if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
  };
  const events = ['timeupdate', 'play', 'pause', 'seeked'];
  events.forEach((ev) => audio.addEventListener(ev, tick));
  $('#dialog').addEventListener('keydown', onKey);
  syncingLyrics = true;
  tick();
  render();

  let result;
  try {
    result = await openDialog(`싱크 맞추기 · ${t.title}`, [
      h('p', { class: 'dialog-hint' }, '재생하면서 각 줄이 시작될 때 Enter(또는 "찍기")를 누르세요. ⌫ 되돌리기, Space 재생/일시정지. 줄을 누르면 그 줄부터 다시 찍습니다.'),
      h('div', { class: 'sync-controls' },
        playBtn,
        h('button', { type: 'button', class: 'btn', onclick: () => { audio.currentTime = 0; } }, '처음부터'),
        h('button', { type: 'button', class: 'btn', onclick: () => { audio.currentTime = Math.max(0, audio.currentTime - 3); } }, '−3초'),
        clock,
        h('span', { class: 'spacer' }),
        h('button', { type: 'button', class: 'btn', onclick: doUndo }, '되돌리기'),
        h('button', { type: 'button', class: 'btn primary', onclick: doStamp }, '찍기')),
      progress,
      list,
    ]);
  } finally {
    syncingLyrics = false;
    events.forEach((ev) => audio.removeEventListener(ev, tick));
    $('#dialog').removeEventListener('keydown', onKey);
  }
  if (result !== 'ok') return;
  const missing = missingCount(sync);
  if (missing === sync.lines.length) return toast('시간을 찍은 줄이 없어 저장하지 않았습니다');
  if (missing && !confirm(`아직 시간을 찍지 않은 ${missing}줄은 가사에서 빠집니다. 저장할까요?`)) return;
  await api('PUT', `/api/tracks/${t.id}/lyrics`, { lyrics: toLrc(sync) });
  await loadLibrary();
  if (currentTrack()?.id === t.id) loadLyrics(true);
  toast('싱크 가사를 저장했습니다');
}

// ───────────── 드래그 정렬 ─────────────
function sortable(listEl, { canReorder, onMove, onStart, onEnd }) {
  let from = null;
  const clearMarks = () => listEl.querySelectorAll('.drop-before, .drop-after')
    .forEach((el) => el.classList.remove('drop-before', 'drop-after'));
  const end = () => {
    clearMarks();
    listEl.querySelectorAll('.dragging').forEach((el) => el.classList.remove('dragging'));
    from = null;
    onEnd?.();
  };
  listEl.addEventListener('dragstart', (e) => {
    const row = e.target.closest('[data-idx]');
    if (!row) return;
    from = Number(row.dataset.idx);
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'copyMove';
    e.dataTransfer.setData('text/plain', '');
    onStart?.(from);
  });
  listEl.addEventListener('dragover', (e) => {
    if (from === null || !canReorder()) return;
    e.preventDefault();
    clearMarks();
    const row = e.target.closest('[data-idx]');
    if (!row) return;
    const r = row.getBoundingClientRect();
    row.classList.add(e.clientY < r.top + r.height / 2 ? 'drop-before' : 'drop-after');
  });
  listEl.addEventListener('drop', (e) => {
    if (from === null || !canReorder()) return;
    e.preventDefault();
    const row = e.target.closest('[data-idx]');
    const start = from;
    end();
    if (!row) return;
    let to = Number(row.dataset.idx) + (e.clientY >= row.getBoundingClientRect().top + row.offsetHeight / 2 ? 1 : 0);
    if (to > start) to--;
    if (to !== start) onMove(start, to);
  });
  // 드롭 후 다시 그리면 원래 요소가 사라져 dragend가 목록까지 올라오지 않으므로 document에서도 받는다.
  document.addEventListener('dragend', () => { if (from !== null) end(); });
}

sortable($('#track-list'), {
  canReorder: () => state.view.type === 'playlist' && !state.query, // 검색 중엔 보이는 순서와 실제 순서가 달라 막음
  onMove: (from, to) => reorderPlaylist(from, to),
  onStart: (i) => { dragTrackId = state.shown[i]?.id ?? null; },
  onEnd: () => { dragTrackId = null; },
});

sortable($('#queue-list'), {
  canReorder: () => true,
  onMove: (from, to) => moveInQueue(from, Math.max(to, player.index + 1)),
});

// ───────────── 메뉴 / 대화상자 / 토스트 ─────────────
function showMenu(anchor, items) {
  const menu = $('#menu');
  menu.replaceChildren(...items.map((it) => (it
    ? h('button', { class: it[2] || null, onclick: () => { hideMenu(); it[1](); } }, it[0])
    : h('hr'))));
  menu.hidden = false;
  const r = anchor.getBoundingClientRect();
  const { offsetWidth: w, offsetHeight: hgt } = menu;
  menu.style.left = `${Math.max(8, Math.min(r.right - w, innerWidth - w - 8))}px`;
  menu.style.top = `${r.bottom + hgt + 8 > innerHeight ? Math.max(8, r.top - hgt - 4) : r.bottom + 4}px`;
}
const hideMenu = () => { $('#menu').hidden = true; };

function openDialog(title, children, { ok = true } = {}) {
  const dlg = $('#dialog');
  $('#dialog-title').textContent = title;
  $('#dialog-body').replaceChildren(...children);
  $('#dialog-ok').hidden = !ok;
  dlg.returnValue = '';
  return new Promise((resolve) => {
    dlg.addEventListener('close', () => resolve(dlg.returnValue), { once: true });
    dlg.showModal();
  });
}

async function promptDialog(title, value = '') {
  const input = h('input', { value, maxlength: 100, required: true, autofocus: true });
  const result = await openDialog(title, [input]);
  return result === 'ok' ? input.value.trim() : null;
}

function chooseDialog(title, options, message) {
  const dlg = $('#dialog');
  const list = h('div', { class: 'choice-list' }, ...options.map((o) => h('button', {
    type: 'button', onclick: () => dlg.close(o.value),
  }, o.label)));
  return openDialog(title, [message ? h('p', { class: 'dialog-hint' }, message) : null, list].filter(Boolean), { ok: false });
}

let toastTimer;
function toast(message, ms = 2600) {
  const el = $('#toast');
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  if (ms) toastTimer = setTimeout(() => { el.hidden = true; }, ms);
}

// ───────────── 로그인 ─────────────
let authMode = 'login';
let started = false;

function showAuth(setup) {
  audio.pause();
  authMode = setup ? 'setup' : 'login';
  $('#app').hidden = true;
  $('#auth').hidden = false;
  $('#auth-desc').textContent = setup
    ? '처음 오셨네요. 사용할 계정을 만드세요. 이 계정 하나만 접속할 수 있습니다.'
    : '로그인하세요.';
  $('#auth-submit').textContent = setup ? '계정 만들기' : '로그인';
  $('#auth-form').password.autocomplete = setup ? 'new-password' : 'current-password';
  $('#auth-error').textContent = '';
}

$('#auth-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.currentTarget;
  try {
    const { user } = await api('POST', `/api/auth/${authMode}`, {
      username: form.username.value,
      password: form.password.value,
    });
    form.password.value = '';
    await startApp(user);
  } catch (err) {
    $('#auth-error').textContent = err.message;
  }
});

async function startApp(user) {
  state.user = user;
  $('#username').textContent = user.username;
  $('#auth').hidden = true;
  $('#app').hidden = false;
  await Promise.all([loadLibrary(), loadPlaylists()]);
  if (!started) {
    started = true;
    restorePlayer();
  }
  await openView(store.get('mp_view', { type: 'library' })).catch(() => openView({ type: 'library' }));
}

// ───────────── 이벤트 연결 ─────────────
$('#btn-play').addEventListener('click', togglePlay);
mediaSession = setupMediaSession({
  audio,
  getTrack: currentTrack,
  onPlay: () => { if (audio.paused) togglePlay(); },
  onPause: () => audio.pause(),
  onNext: () => next(),
  onPrev: prev,
});
$('#btn-next').addEventListener('click', () => next());
$('#btn-prev').addEventListener('click', prev);
$('#btn-shuffle').innerHTML = ICON.shuffle;
$('#btn-shuffle').addEventListener('click', toggleShuffle);
$('#btn-repeat').addEventListener('click', cycleRepeat);
$('#btn-prev').innerHTML = ICON.prev;
$('#btn-next').innerHTML = ICON.next;
$('#btn-queue').innerHTML = ICON.queue;
$('#btn-queue').addEventListener('click', () => togglePanel('queue'));
$('#btn-lyrics').innerHTML = ICON.lyrics;
$('#btn-lyrics').addEventListener('click', () => togglePanel('lyrics'));
$('#lyrics-edit').addEventListener('click', safe(() => currentTrack() && editLyrics(currentTrack())));
$('#lyrics-sync').addEventListener('click', safe(openLyricSync));
setPanel(store.get('mp_panel', store.get('mp_queue_open', false) ? 'queue' : null));
$('#queue-clear').addEventListener('click', clearUpcoming);

$('#btn-mute').addEventListener('click', () => {
  if (audio.volume === 0) { audio.volume = 0.5; audio.muted = false; } else audio.muted = !audio.muted;
});
$('#volume').addEventListener('input', (e) => {
  audio.volume = Number(e.target.value);
  audio.muted = false;
});

let seeking = false;
const seek = $('#seek');
seek.addEventListener('input', () => {
  seeking = true;
  $('#time-cur').textContent = fmt(Number(seek.value));
  setFill(seek);
});
seek.addEventListener('change', () => {
  audio.currentTime = Number(seek.value);
  seeking = false;
});

let lastSave = 0;
audio.addEventListener('timeupdate', () => {
  if (!seeking) {
    seek.value = audio.currentTime;
    $('#time-cur').textContent = fmt(audio.currentTime);
    setFill(seek);
  }
  syncLyrics();
  if (!audio.paused) listenTracker.tick(audio.currentTime, audio.duration);
  if (Date.now() - lastSave > 5000) { lastSave = Date.now(); savePlayer(); }
});
audio.addEventListener('seeked', () => {
  listenTracker.seeked(audio.currentTime);
  syncLyrics(true);
});
audio.addEventListener('loadedmetadata', () => {
  seek.max = audio.duration || 0;
  $('#time-dur').textContent = fmt(audio.duration);
});
audio.addEventListener('emptied', () => {
  seek.max = 0;
  seek.value = 0;
  setFill(seek);
  $('#time-cur').textContent = '0:00';
  $('#time-dur').textContent = '0:00';
});
audio.addEventListener('play', renderPlayer);
audio.addEventListener('pause', renderPlayer);
audio.addEventListener('volumechange', () => { renderPlayer(); savePlayer(); });
audio.addEventListener('ended', () => {
  listenTracker.reset(); // 한 곡 반복이면 다시 들을 때 또 센다
  if (syncingLyrics) return renderPlayer(); // 싱크 맞추는 중에는 다음 곡으로 넘어가지 않음
  next(true);
});
audio.addEventListener('error', () => {
  if (audio.getAttribute('src')) toast('이 곡을 재생할 수 없습니다. 브라우저가 지원하지 않는 형식일 수 있습니다.');
});
addEventListener('pagehide', savePlayer);

document.querySelectorAll('.nav-item').forEach((el) => {
  el.addEventListener('click', safe(() => openView({ type: el.dataset.view })));
});
$('#new-playlist').addEventListener('click', safe(async () => {
  const playlist = await createPlaylist();
  if (playlist) await openView({ type: 'playlist', id: playlist.id });
}));
$('#logout').addEventListener('click', safe(async () => {
  await api('POST', '/api/auth/logout');
  showAuth(false);
}));

$('#search').addEventListener('input', (e) => {
  state.query = e.target.value;
  renderMain();
});

$('#file-input').addEventListener('change', (e) => {
  uploadFiles(e.target.files).catch((err) => toast(err.message));
  e.target.value = '';
});

// 창 전체에 파일을 끌어다 놓으면 업로드
let dragDepth = 0;
const hasFiles = (e) => e.dataTransfer?.types.includes('Files');
addEventListener('dragenter', (e) => {
  if (!hasFiles(e) || $('#app').hidden) return;
  dragDepth++;
  $('#dropzone').hidden = false;
});
addEventListener('dragleave', (e) => {
  if (!hasFiles(e)) return;
  if (--dragDepth <= 0) { dragDepth = 0; $('#dropzone').hidden = true; }
});
addEventListener('dragover', (e) => { if (hasFiles(e)) e.preventDefault(); });
addEventListener('drop', (e) => {
  if (!hasFiles(e)) return;
  e.preventDefault();
  dragDepth = 0;
  $('#dropzone').hidden = true;
  if (!$('#app').hidden) uploadFiles(e.dataTransfer.files).catch((err) => toast(err.message));
});

document.addEventListener('click', (e) => { if (!e.target.closest('#menu')) hideMenu(); }, true);
$('#main').addEventListener('scroll', hideMenu);
addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    hideMenu();
    if (e.target.id === 'search') { setQuery(''); renderMain(); e.target.blur(); } else if (state.selected.size && !e.target.closest('dialog')) clearSelection();
  }
  // Ctrl/⌘+A: 보이는 곡 모두 선택 (입력 중이 아닐 때, 곡 목록 화면에서)
  if (e.key.toLowerCase() === 'a' && (e.ctrlKey || e.metaKey) && !e.target.closest('input, textarea, dialog')
      && !$('#app').hidden && document.querySelector('#track-list .track-row[data-idx]')) {
    e.preventDefault();
    state.selected = new Set(state.shown.map(rowKey));
    renderSelection();
  }
  if (e.key === '/' && !e.target.closest('input, textarea, dialog') && !$('#app').hidden) {
    e.preventDefault();
    $('#search').focus();
  }
  const typing = e.target.closest('input, textarea, button, dialog');
  if (e.code === 'Space' && !typing && !$('#app').hidden) {
    e.preventDefault();
    togglePlay();
  }
});

// ───────────── 시작 ─────────────
renderPlayer();
renderQueue();
api('GET', '/api/auth/status')
  .then((s) => {
    if (s.maxUploadMb) maxUploadBytes = s.maxUploadMb * 1024 * 1024;
    return s.user ? startApp(s.user) : showAuth(s.setupRequired);
  })
  .catch((err) => toast(err.message, 0));
