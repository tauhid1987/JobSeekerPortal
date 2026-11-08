import {
  auth, onAuthStateChanged, signOut, dbRef, get, set, update, push, onValue, serverTimestamp,
  idToken, esc, when, STATUSES, statusLabel, csvDownload, showLogin,
} from './fb.js';
import { API_BASE } from '../firebase-config.js';

const app = document.getElementById('app');
const nav = document.getElementById('nav');
let user = null;
let role = 'none';
let view = 'find';
let apps = {};       // my applications, live
let history = {};    // my search history, live
let last = null;     // latest search result
let unsubs = [];

onAuthStateChanged(auth, (u) => {
  unsubs.forEach((f) => f());
  unsubs = [];
  user = u && !u.isAnonymous ? u : null;
  if (!user) { nav.innerHTML = ''; showLogin(app); return; }
  watchAccess();
});

// Live account status: pending -> member the moment an admin approves, blocked the moment they turn it off.
function watchAccess() {
  const state = { admin: false, member: undefined, request: undefined };
  const apply = () => {
    if (state.admin) role = 'admin';
    else if (state.member === undefined || state.request === undefined) return;
    else if (state.member) role = state.member.active === true ? 'member' : 'blocked';
    else role = state.request ? 'pending' : 'none';
    render();
  };
  const uid = user.uid;
  unsubs.push(onValue(dbRef(`hosts/${uid}`), (s) => { state.admin = s.val() === true; apply(); }));
  unsubs.push(onValue(dbRef(`jm/members/${uid}`), (s) => { state.member = s.val() || null; apply(); }, () => { state.member = null; apply(); }));
  unsubs.push(onValue(dbRef(`jm/requests/${uid}`), (s) => { state.request = s.val() || null; apply(); }, () => { state.request = null; apply(); }));
  unsubs.push(onValue(dbRef(`jm/applications/${uid}`), (s) => { apps = s.val() || {}; header(); if (view === 'apps') render(); }, () => {}));
  unsubs.push(onValue(dbRef(`jm/activity/${uid}`), (s) => { history = s.val() || {}; if (view === 'history') render(); }, () => {}));
}

function header() {
  const tabs = [['find', 'Find jobs'], ['apps', `My applications (${Object.keys(apps).length})`], ['history', 'My history']];
  nav.innerHTML = (role === 'member' || role === 'admin'
    ? tabs.map(([k, l]) => `<a href="#" class="tab ${view === k ? 'on' : ''}" data-v="${k}">${esc(l)}</a>`).join('')
    : '')
    + (role === 'admin' ? '<a href="admin.html">Admin</a>' : '')
    + `<span class="mute small">${esc(user.displayName || user.email)}</span><button class="ghost small" id="out">Sign out</button>`;
  nav.querySelectorAll('[data-v]').forEach((a) => { a.onclick = (e) => { e.preventDefault(); view = a.dataset.v; render(); }; });
  nav.querySelector('#out').onclick = () => signOut(auth);
}

function render() {
  header();
  if (role === 'none') {
    app.innerHTML = `<div class="card"><h2>Request access</h2><p>Your account is not on the member list yet.</p><button id="req">Ask the admin for access</button></div>`;
    app.querySelector('#req').onclick = () => set(dbRef(`jm/requests/${user.uid}`), { name: user.displayName || user.email, email: user.email, at: serverTimestamp() });
  } else if (role === 'pending') {
    app.innerHTML = `<div class="card center"><h2>Waiting for approval</h2><p class="mute">An admin needs to approve your account. This page updates by itself.</p></div>`;
  } else if (role === 'blocked') {
    app.innerHTML = `<div class="card center"><h2>Access turned off</h2><p class="mute">An admin turned off your access. Contact them if this is a mistake.</p></div>`;
  } else if (view === 'apps') showApps();
  else if (view === 'history') showHistory();
  else showFind();
}

/* ---------- Find jobs ---------- */
function steps(n) {
  const names = ['Your CV', 'Your targets', 'Your jobs'];
  return `<div class="steps">${names.map((t, i) => `<div class="step ${i + 1 === n ? 'on' : ''} ${i + 1 < n ? 'done' : ''}"><b>${i + 1 < n ? '✓' : i + 1}</b>${t}</div>`).join('')}</div>`;
}

function showFind() {
  if (last) { showResults(); return; }
  app.innerHTML = `${steps(1)}<form class="card" id="f"><h2>Find jobs for you</h2>
    <p class="mute">Your CV is read on the server and deleted straight away. Every search is saved to your history.</p>
    <label>1. Your CV (PDF, DOCX or TXT)<input type="file" name="cv" accept=".pdf,.docx,.txt" required></label>
    <div class="grid2">
      <label>2. Job titles, separated by commas<input name="query" placeholder="QA Lead, QA Engineer, Security Expert"></label>
      <label>Your country (can you apply?)<select name="country" id="ctry"><option>Bangladesh</option></select></label>
      <label>Where to look<select name="scope"><option value="both">Local + remote (everything)</option><option value="local">Local jobs in my country</option><option value="remote">Remote jobs (other countries)</option></select></label>
      <label>Minimum match %<input name="min_score" type="number" min="0" max="100" value="20"></label>
      <label>Most jobs to list<input name="limit" type="number" min="10" max="500" value="100"></label>
      <label>Rank by<select name="sort"><option value="match">Best match</option><option value="deadline">Closest deadline first</option></select></label>
      <label>Eligibility<select name="eligibility"><option value="strict">Only jobs I can apply for</option><option value="all">Show all, with status</option></select></label>
    </div>
    <label class="row"><input type="checkbox" name="remote"> Remote jobs only</label>
    <button class="full" id="go">Search jobs</button><p id="msg" class="hint"></p></form>`;
  countriesReady.then((list) => {
    const sel = app.querySelector('#ctry'); if (!sel || !list.length) return;
    let saved = ''; try { saved = localStorage.getItem('jm_country') || ''; } catch (e) { /* storage blocked */ }
    sel.innerHTML = list.map((c) => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join('');
    sel.value = list.some((c) => c.name === saved) ? saved : 'Bangladesh';
  });
  const f = app.querySelector('#f');
  f.onsubmit = async (e) => {
    e.preventDefault();
    const msg = f.querySelector('#msg');
    f.querySelector('#go').disabled = true;
    msg.innerHTML = '<span class="spinner"></span>Searching the job sites. This takes up to a minute…';
    try {
      if (API_BASE.includes('REPLACE')) throw new Error('The search server address is not set yet. The admin must put it in docs/firebase-config.js (see README).');
      const r = await fetch(`${API_BASE}/api/search`, { method: 'POST', headers: { Authorization: `Bearer ${await idToken()}` }, body: new FormData(f) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'Search failed');
      last = d;
      try { localStorage.setItem('jm_country', d.country); } catch (e) { /* storage blocked */ }
      view = 'find';
      render();
    } catch (err) {
      const down = err instanceof TypeError ? 'Could not reach the search server. If it was idle it may need a minute to wake up. Try again shortly.' : err.message;
      msg.innerHTML = `<span class="error">${esc(down)}</span>`;
      f.querySelector('#go').disabled = false;
    }
  };
}

let countryList = [];
const countriesReady = fetch('countries.json').then((r) => r.json()).then((l) => (countryList = l)).catch(() => []);

function moreSearches(d) {
  const c = countryList.find((x) => x.name === d.country);
  const enc = encodeURIComponent;
  const titles = (d.queries && d.queries.length ? d.queries : ['']).slice(0, 4);
  const links = titles.map((t) => `<li><b>${esc(t || 'Jobs')}</b>:
    <a href="https://www.linkedin.com/jobs/search/?keywords=${enc(t)}&location=${enc(d.country)}" target="_blank" rel="noopener noreferrer">LinkedIn in ${esc(d.country)}</a> ·
    <a href="https://www.linkedin.com/jobs/search/?keywords=${enc(t)}&f_WT=2" target="_blank" rel="noopener noreferrer">LinkedIn remote</a> ·
    <a href="https://www.google.com/search?q=${enc(`${t} jobs in ${d.country}`)}&ibp=htl;jobs" target="_blank" rel="noopener noreferrer">Google Jobs</a></li>`).join('');
  const portals = c && c.portals.length ? `<p class="mute small">Local job sites in ${esc(d.country)}: ${c.portals.map((p) => `<a href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">${esc(p.name)}</a>`).join(' · ')}</p>` : '';
  return `<div class="card"><h3>Also look here</h3>
    <p class="mute small">LinkedIn does not allow automatic collection of its jobs, so open its own results from here (log in there to apply).</p>
    <ul class="mute">${links}</ul>${portals}</div>`;
}

const eligClass = { Yes: 'yes', Check: 'check', 'Visa/relocation': 'visa', No: 'no' };
const scoreClass = (s) => (s >= 60 ? 'hi' : s >= 40 ? 'mid' : 'lo');

function showResults() {
  const d = last;
  const applied = d.jobs.filter((j) => apps[j.key]?.status === 'applied').length;
  app.innerHTML = `${steps(3)}
    <div class="card"><h2>${d.jobs.length} jobs for you</h2>
      <div class="stats">
        <div class="stat"><b>${d.total}</b><span>jobs searched</span></div>
        <div class="stat"><b>${d.jobs.length}</b><span>listed</span></div>
        <div class="stat"><b>${d.not_eligible}</b><span>not open to ${esc(d.country)}</span></div>
        <div class="stat"><b>${d.expired}</b><span>past deadline</span></div>
        <div class="stat"><b>${applied}</b><span>applied from this list</span></div>
      </div>
      ${d.tracked ? '' : '<p class="warn-box">This search could not be saved to your history. Tell the admin.</p>'}
      <p class="mute small">Skills read from your CV: ${esc(d.skills.join(', ') || 'none')}</p>
      <p class="mute small">${d.log.map(esc).join(' · ')}</p>
      <div class="row"><button id="xl">Download Excel</button><button class="ghost" id="again">New search</button></div></div>
    ${moreSearches(d)}
    <div class="card"><div class="table"><table class="jobs"><thead><tr><th>#</th><th>Job</th><th>Match</th><th>Can apply?</th><th>Salary</th><th>Deadline</th><th>Track</th></tr></thead><tbody>
    ${d.jobs.map((j, i) => {
    const a = apps[j.key];
    const dl = j.deadline ? `<span class="dl ${j.days_left <= 3 ? 'hot' : j.days_left <= 7 ? 'warm' : ''}">${esc(j.deadline)}<br>${j.days_left === 0 ? 'today' : `${j.days_left} days left`}</span>` : '<span class="mute">Not listed</span>';
    return `<tr><td>${i + 1}</td>
      <td><a href="${esc(j.apply_url)}" target="_blank" rel="noopener noreferrer"><b>${esc(j.title)}</b></a><br>${esc(j.company)}<br><span class="mute small">${esc(j.source)} · ${esc(j.location || '')} · ${esc(j.type || '')}</span></td>
      <td class="score ${scoreClass(j.score)}">${j.score}%</td>
      <td><span class="pill ${eligClass[j.eligible] || ''}">${esc(j.eligible)}</span><div class="why">${esc(j.eligible_why)}</div></td>
      <td>${esc(j.salary || 'Not listed')}</td><td>${dl}</td>
      <td class="acts">${a ? `<span class="pill st-${esc(a.status)}">${esc(statusLabel(a.status))}</span>` : ''}
        <button class="small" data-apply="${i}">${a?.status === 'applied' ? 'Open again' : 'Open & mark applied'}</button>
        ${a ? '' : `<button class="ghost small" data-save="${i}">Save for later</button>`}</td></tr>`;
  }).join('')}</tbody></table></div></div>`;
  app.querySelector('#again').onclick = () => { last = null; render(); };
  app.querySelector('#xl').onclick = () => downloadExcel(d);
  app.querySelectorAll('[data-apply]').forEach((b) => { b.onclick = () => applyTo(d.jobs[b.dataset.apply]); });
  app.querySelectorAll('[data-save]').forEach((b) => { b.onclick = () => track(d.jobs[b.dataset.save], 'saved').then(showResults); });
}

// The Excel file comes back inside the search result (nothing is stored on the server).
function downloadExcel(d) {
  const bytes = Uint8Array.from(atob(d.xlsx), (c) => c.charCodeAt(0));
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
  a.download = d.file;
  a.click();
  URL.revokeObjectURL(a.href);
}

// Open the job page and record "Applied". Opening comes first so the browser does not block the pop-up.
async function applyTo(j) {
  window.open(j.apply_url, '_blank', 'noopener,noreferrer');
  if (apps[j.key]?.status !== 'applied') await track(j, 'applied');
  showResults();
}

async function track(j, status, note = '') {
  const cur = apps[j.key];
  const path = `jm/applications/${user.uid}/${j.key}`;
  if (cur) {
    const patch = { status, updatedAt: serverTimestamp() };
    if (status === 'applied' && !cur.appliedAt) patch.appliedAt = serverTimestamp();
    if (note) patch.note = note.slice(0, 500);
    await update(dbRef(path), patch);
  } else {
    const rec = { title: j.title.slice(0, 200), company: (j.company || '').slice(0, 120), url: j.apply_url.slice(0, 600), source: j.source.slice(0, 40), status, createdAt: serverTimestamp(), updatedAt: serverTimestamp() };
    if (status === 'applied') rec.appliedAt = serverTimestamp();
    await set(dbRef(path), rec);
  }
  await push(dbRef(`jm/applogs/${user.uid}`), { at: serverTimestamp(), key: j.key, title: j.title.slice(0, 200), status, note: note.slice(0, 500) });
}

/* ---------- My applications ---------- */
function showApps() {
  const list = Object.entries(apps).map(([key, a]) => ({ key, ...a }));
  const by = (s) => list.filter((a) => a.status === s).sort((x, y) => (y.updatedAt || 0) - (x.updatedAt || 0));
  app.innerHTML = `<div class="card"><h2>My applications</h2>
    <div class="stats">${STATUSES.map(([k, l]) => `<div class="stat"><b>${by(k).length}</b><span>${l}</span></div>`).join('')}</div>
    <div class="row"><button class="ghost" id="csv" ${list.length ? '' : 'disabled'}>Download CSV</button></div></div>
    ${list.length ? `<div class="board-cols">${STATUSES.map(([k, l]) => `<div class="col"><h3>${l}<span class="pill">${by(k).length}</span></h3>
      ${by(k).map((a) => `<div class="appcard"><a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer"><b>${esc(a.title)}</b></a><br>${esc(a.company)}
        <div class="mute small">${a.appliedAt ? `Applied ${esc(when(a.appliedAt))}<br>` : ''}Updated ${esc(when(a.updatedAt))}</div>
        ${a.note ? `<div class="small">${esc(a.note)}</div>` : ''}
        <div class="row" style="margin-top:6px"><select data-k="${esc(a.key)}">${STATUSES.map(([v, t]) => `<option value="${v}" ${v === a.status ? 'selected' : ''}>${t}</option>`).join('')}</select>
        <button class="ghost small" data-note="${esc(a.key)}">Note</button></div></div>`).join('') || '<p class="mute small">None</p>'}</div>`).join('')}</div>`
    : '<div class="card"><p class="mute">Nothing tracked yet. Use "Open &amp; mark applied" or "Save for later" in your job list.</p></div>'}`;
  app.querySelectorAll('select[data-k]').forEach((s) => {
    s.onchange = () => track({ key: s.dataset.k, title: apps[s.dataset.k].title }, s.value);
  });
  app.querySelectorAll('[data-note]').forEach((b) => {
    b.onclick = () => {
      const k = b.dataset.note;
      const text = prompt('Note for this application (e.g. interview date):', apps[k].note || '');
      if (text !== null) track({ key: k, title: apps[k].title }, apps[k].status, text.trim());
    };
  });
  const csv = app.querySelector('#csv');
  if (csv) csv.onclick = () => csvDownload('my-applications.csv', [['Job', 'Company', 'Status', 'Applied at', 'Updated', 'Link', 'Note'],
    ...list.map((a) => [a.title, a.company, statusLabel(a.status), when(a.appliedAt), when(a.updatedAt), a.url, a.note || ''])]);
}

/* ---------- My history ---------- */
function showHistory() {
  const rows = Object.entries(history).map(([id, h]) => ({ id, ...h })).sort((a, b) => b.at - a.at);
  app.innerHTML = `<div class="card"><h2>My search history</h2>
    ${rows.length ? `<div class="table"><table><thead><tr><th>When</th><th>Titles</th><th>Country</th><th>Searched</th><th>Listed</th></tr></thead><tbody>
    ${rows.map((h) => `<tr><td class="nowrap">${esc(when(h.at))}</td><td>${esc(h.titles)}</td><td>${esc(h.country)}</td><td>${h.found}</td><td>${h.shown}</td></tr>`).join('')}</tbody></table></div>`
    : '<p class="mute">No searches yet. Each search is saved here and cannot be edited or removed.</p>'}</div>`;
}
