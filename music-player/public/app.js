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
  rows: [], // 현재 화면에 보이는 곡 (플레이리스트면 entryId 포함)
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

async function openView(view) {
  if (view?.type === 'playlist') {
    const data = await api('GET', `/api/playlists/${view.id}`);
    state.view = { type: 'playlist', id: data.id, name: data.name };
    state.rows = data.tracks;
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
    el.classList.toggle('active', state.view.type === el.dataset.view);
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
function coverEl(track, cls = 'cover') {
  const el = h('div', { class: cls });
  if (track?.hasCover) el.append(h('img', { src: `/api/tracks/${track.id}/cover`, loading: 'lazy', alt: '' }));
  else el.textContent = '♪';
  return el;
}

function renderMain() {
  const { view, rows } = state;
  const isPlaylist = view.type === 'playlist';
  const total = rows.reduce((sum, t) => sum + (t.duration || 0), 0);

  $('#view-kind').textContent = isPlaylist ? '플레이리스트' : '라이브러리';
  $('#view-title').textContent = isPlaylist ? view.name : '모든 곡';
  $('#view-meta').textContent = `${rows.length}곡 · ${fmtTotal(total)}`;

  const ids = rows.map((t) => t.id);
  const actions = [
    h('button', { class: 'btn primary', disabled: !rows.length, onclick: () => playList(ids, 0) }, '▶ 재생'),
    h('button', { class: 'btn', disabled: !rows.length, onclick: () => playList(ids, 0, true) }, '셔플 재생'),
  ];
  if (isPlaylist) {
    actions.push(
      h('button', { class: 'btn', onclick: safe(renamePlaylist) }, '이름 변경'),
      h('button', { class: 'btn danger', onclick: safe(deletePlaylist) }, '삭제'),
    );
  } else {
    actions.push(h('button', { class: 'btn', onclick: () => $('#file-input').click() }, '＋ 업로드'));
  }
  $('#view-actions').replaceChildren(...actions);

  const list = $('#track-list');
  if (!rows.length) {
    list.replaceChildren(isPlaylist
      ? h('div', { class: 'empty' }, '아직 곡이 없습니다. 라이브러리에서 곡의 ⋯ 메뉴로 추가하거나 곡을 이 플레이리스트 이름 위로 끌어다 놓으세요.')
      : h('div', { class: 'empty' },
        h('div', {}, '라이브러리가 비어 있습니다. 음원 파일을 이 창에 끌어다 놓거나 업로드하세요.'),
        h('button', { class: 'btn primary', onclick: () => $('#file-input').click() }, '파일 선택')));
    return;
  }

  const head = h('div', { class: 'track-row head' },
    h('div', { class: 't-num' }, '#'), h('div', {}, '제목'), h('div', { class: 't-album' }, '앨범'),
    h('div', { class: 't-dur' }, '길이'), h('div'));
  list.replaceChildren(head, ...rows.map((t, i) => h('div', {
    class: 'track-row',
    role: 'listitem',
    draggable: 'true',
    dataset: { idx: i },
    title: '클릭하면 재생',
    onclick: () => playList(ids, i),
  },
  h('div', { class: 't-num' }, String(i + 1)),
  h('div', { class: 't-main' }, coverEl(t),
    h('div', { class: 't-text' },
      h('div', { class: 't-title' }, t.title),
      h('div', { class: 't-artist' }, t.artist || '알 수 없는 아티스트'))),
  h('div', { class: 't-album' }, t.album || ''),
  h('div', { class: 't-dur' }, fmt(t.duration)),
  h('button', {
    class: 'icon-btn', title: '더 보기', html: ICON.more,
    onclick: (e) => { e.stopPropagation(); openTrackMenu(e.currentTarget, i); },
  }))));
  highlightPlaying();
}

function highlightPlaying() {
  const id = currentTrack()?.id;
  document.querySelectorAll('#track-list .track-row[data-idx]').forEach((row) => {
    row.classList.toggle('playing', state.rows[row.dataset.idx]?.id === id);
  });
}

function openTrackMenu(anchor, i) {
  const t = state.rows[i];
  showMenu(anchor, [
    ['다음에 재생', () => { playNext([t.id]); toast('다음에 재생합니다'); }],
    ['대기열에 추가', () => { addToQueue([t.id]); toast('대기열에 추가했습니다'); }],
    ['플레이리스트에 추가…', safe(() => addToPlaylistFlow([t.id]))],
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

async function addTracksToPlaylist(playlistId, trackIds) {
  await api('POST', `/api/playlists/${playlistId}/tracks`, { trackIds });
  await loadPlaylists();
  if (state.view.type === 'playlist' && state.view.id === playlistId) await refreshView();
  const name = state.playlists.find((p) => p.id === playlistId)?.name ?? '';
  toast(`'${name}'에 추가했습니다`);
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
function uploadFiles(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  const form = new FormData();
  files.forEach((f) => form.append('files', f, f.name));

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/tracks');
  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) toast(`업로드 중… ${Math.round((e.loaded / e.total) * 100)}%`, 0);
  };
  xhr.upload.onload = () => toast('곡 정보를 읽는 중…', 0);
  xhr.onerror = () => toast('업로드 중 네트워크 오류가 발생했습니다');
  xhr.onload = safe(async () => {
    let data = null;
    try { data = JSON.parse(xhr.responseText); } catch { /* 본문 없음 */ }
    if (xhr.status === 401) {
      $('#toast').hidden = true;
      return showAuth(false);
    }
    if (xhr.status >= 300) return toast(data?.error || `업로드 실패 (${xhr.status})`);
    await loadLibrary();
    if (state.view.type === 'library') await refreshView();
    let msg = `${data.added.length}곡을 추가했습니다`;
    if (data.rejected.length) msg += ` (지원하지 않는 파일 ${data.rejected.length}개 제외)`;
    toast(msg, 4000);
  });
  xhr.send(form);
}

// ───────────── 플레이어 ─────────────
const audio = new Audio();
audio.preload = 'metadata';

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

function load(autoplay, startAt = 0) {
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
    if (state.rows.length) playList(state.rows.map((t) => t.id), 0);
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
  $('#now-artist').textContent = t ? (t.artist || '알 수 없는 아티스트') : '';
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
      h('div', { class: 'q-artist' }, t.artist || '알 수 없는 아티스트')),
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
  canReorder: () => state.view.type === 'playlist',
  onMove: (from, to) => reorderPlaylist(from, to),
  onStart: (i) => { dragTrackId = state.rows[i]?.id ?? null; },
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

function chooseDialog(title, options) {
  const dlg = $('#dialog');
  const list = h('div', { class: 'choice-list' }, ...options.map((o) => h('button', {
    type: 'button', onclick: () => dlg.close(o.value),
  }, o.label)));
  return openDialog(title, [list], { ok: false });
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
$('#btn-next').addEventListener('click', () => next());
$('#btn-prev').addEventListener('click', prev);
$('#btn-shuffle').innerHTML = ICON.shuffle;
$('#btn-shuffle').addEventListener('click', toggleShuffle);
$('#btn-repeat').addEventListener('click', cycleRepeat);
$('#btn-prev').innerHTML = ICON.prev;
$('#btn-next').innerHTML = ICON.next;
$('#btn-queue').innerHTML = ICON.queue;
$('#btn-queue').addEventListener('click', () => {
  $('#queue').hidden = !$('#queue').hidden;
  $('#btn-queue').classList.toggle('active', !$('#queue').hidden);
  store.set('mp_queue_open', !$('#queue').hidden);
});
if (store.get('mp_queue_open', false)) $('#btn-queue').click();
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
  if (Date.now() - lastSave > 5000) { lastSave = Date.now(); savePlayer(); }
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
audio.addEventListener('ended', () => next(true));
audio.addEventListener('error', () => {
  if (audio.getAttribute('src')) toast('이 곡을 재생할 수 없습니다. 브라우저가 지원하지 않는 형식일 수 있습니다.');
});
addEventListener('pagehide', savePlayer);

document.querySelector('.nav-item[data-view="library"]').addEventListener('click', safe(() => openView({ type: 'library' })));
$('#new-playlist').addEventListener('click', safe(async () => {
  const playlist = await createPlaylist();
  if (playlist) await openView({ type: 'playlist', id: playlist.id });
}));
$('#logout').addEventListener('click', safe(async () => {
  await api('POST', '/api/auth/logout');
  showAuth(false);
}));

$('#file-input').addEventListener('change', (e) => {
  uploadFiles(e.target.files);
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
  if (!$('#app').hidden) uploadFiles(e.dataTransfer.files);
});

document.addEventListener('click', (e) => { if (!e.target.closest('#menu')) hideMenu(); }, true);
$('#main').addEventListener('scroll', hideMenu);
addEventListener('keydown', (e) => {
  if (e.key === 'Escape') hideMenu();
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
  .then((s) => (s.user ? startApp(s.user) : showAuth(s.setupRequired)))
  .catch((err) => toast(err.message, 0));
