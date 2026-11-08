import {
  auth, onAuthStateChanged, signOut, dbRef, set, update, remove, onValue, serverTimestamp,
  esc, when, STATUSES, statusLabel, csvDownload, showLogin,
} from './fb.js';

const app = document.getElementById('app');
const nav = document.getElementById('nav');
let tab = 'people';
let userFilter = '';
let statusFilter = '';
const data = { members: {}, requests: {}, activity: {}, applications: {} };
let started = false;

onAuthStateChanged(auth, (u) => {
  if (!u || u.isAnonymous) { nav.innerHTML = ''; showLogin(app); return; }
  onValue(dbRef(`hosts/${u.uid}`), (s) => {
    if (s.val() !== true) {
      app.innerHTML = `<div class="card"><h2>Not an admin</h2><p>This page is for approved admins only (the same list as Quiz Arena hosts).</p>
        <p><a href="./">Back to JobMatch</a> · <button class="ghost small" id="out">Sign out</button></p></div>`;
      app.querySelector('#out').onclick = () => signOut(auth);
      return;
    }
    if (!started) { started = true; listen(); }
    render();
  });
});

function listen() {
  ['members', 'requests', 'activity', 'applications'].forEach((k) => {
    onValue(dbRef(`jm/${k}`), (s) => { data[k] = s.val() || {}; render(); });
  });
}

// uid -> display name
const nameOf = (uid) => data.members[uid]?.name || data.requests[uid]?.name || uid.slice(0, 8);
const emailOf = (uid) => data.requests[uid]?.email || '';
const flat = (tree) => Object.entries(tree).flatMap(([uid, items]) => Object.entries(items).map(([id, v]) => ({ uid, id, ...v })));

function render() {
  if (!started) return;
  nav.innerHTML = `${[['people', 'People'], ['activity', 'Who used it'], ['apps', 'Applications']]
    .map(([k, l]) => `<a href="#" class="tab ${tab === k ? 'on' : ''}" data-t="${k}">${l}</a>`).join('')}<a href="./">Job search</a><button class="ghost small" id="out">Sign out</button>`;
  nav.querySelectorAll('[data-t]').forEach((a) => { a.onclick = (e) => { e.preventDefault(); tab = a.dataset.t; render(); }; });
  nav.querySelector('#out').onclick = () => signOut(auth);

  const acts = flat(data.activity);
  const appsAll = flat(data.applications);
  const week = Date.now() - 7 * 864e5;
  const pending = Object.keys(data.requests).filter((u) => !data.members[u]);
  const head = `<div class="stats">
    <div class="stat"><b>${Object.keys(data.members).filter((u) => data.members[u].active).length}</b><span>active members</span></div>
    <div class="stat"><b>${pending.length}</b><span>waiting for approval</span></div>
    <div class="stat"><b>${acts.length}</b><span>searches (${acts.filter((a) => a.at > week).length} this week)</span></div>
    <div class="stat"><b>${appsAll.filter((a) => a.status !== 'saved').length}</b><span>applications</span></div></div>`;
  if (tab === 'activity') app.innerHTML = head + activityView(acts);
  else if (tab === 'apps') app.innerHTML = head + appsView(appsAll);
  else app.innerHTML = head + peopleView(pending, acts, appsAll);
  wire(acts, appsAll);
}

function peopleView(pending, acts, appsAll) {
  const members = Object.entries(data.members).sort((a, b) => a[1].name.localeCompare(b[1].name));
  const count = (list, uid) => list.filter((x) => x.uid === uid).length;
  return `${pending.length ? `<div class="card"><h2>Waiting for approval</h2><div class="table"><table><thead><tr><th>Name</th><th>Email</th><th>Asked</th><th></th></tr></thead><tbody>
    ${pending.map((u) => `<tr><td>${esc(data.requests[u].name)}</td><td>${esc(data.requests[u].email)}</td><td>${esc(when(data.requests[u].at))}</td>
      <td class="row"><button class="small" data-approve="${esc(u)}">Approve</button><button class="ghost small" data-decline="${esc(u)}">Decline</button></td></tr>`).join('')}
    </tbody></table></div></div>` : ''}
    <div class="card"><h2>Members</h2>${members.length ? `<div class="table"><table><thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Searches</th><th>Applied</th><th></th></tr></thead><tbody>
    ${members.map(([u, m]) => `<tr><td><a href="#" data-who="${esc(u)}">${esc(m.name)}</a></td><td>${esc(emailOf(u))}</td>
      <td><span class="pill ${m.active ? 'yes' : 'no'}">${m.active ? 'Active' : 'Blocked'}</span></td><td>${count(acts, u)}</td>
      <td>${appsAll.filter((x) => x.uid === u && x.status !== 'saved').length}</td>
      <td><button class="${m.active ? 'ghost' : ''} small" data-toggle="${esc(u)}">${m.active ? 'Block' : 'Unblock'}</button></td></tr>`).join('')}</tbody></table></div>`
    : '<p class="mute">No members yet. New people appear above after they request access.</p>'}</div>`;
}

function userSelect() {
  const uids = [...new Set([...Object.keys(data.members), ...Object.keys(data.requests)])];
  return `<label class="grow">Person<select id="uf"><option value="">Everyone</option>${uids.map((u) => `<option value="${esc(u)}" ${u === userFilter ? 'selected' : ''}>${esc(nameOf(u))}</option>`).join('')}</select></label>`;
}

function activityView(acts) {
  const rows = acts.filter((a) => !userFilter || a.uid === userFilter).sort((a, b) => b.at - a.at);
  return `<div class="card"><h2>Who used it</h2><div class="row">${userSelect()}<button class="ghost" id="csv" ${rows.length ? '' : 'disabled'}>Download CSV</button></div>
    ${rows.length ? `<div class="table"><table><thead><tr><th>When</th><th>Person</th><th>Titles</th><th>Country</th><th>Searched</th><th>Listed</th></tr></thead><tbody>
    ${rows.map((a) => `<tr><td class="nowrap">${esc(when(a.at))}</td><td>${esc(nameOf(a.uid))}</td><td>${esc(a.titles)}</td><td>${esc(a.country)}</td><td>${a.found}</td><td>${a.shown}</td></tr>`).join('')}</tbody></table></div>`
    : '<p class="mute">No searches yet.</p>'}</div>`;
}

function appsView(list) {
  const rows = list.filter((a) => (!userFilter || a.uid === userFilter) && (!statusFilter || a.status === statusFilter)).sort((a, b) => b.updatedAt - a.updatedAt);
  return `<div class="card"><h2>Applications</h2><div class="row">${userSelect()}
    <label class="grow">Status<select id="sf"><option value="">All</option>${STATUSES.map(([k, l]) => `<option value="${k}" ${k === statusFilter ? 'selected' : ''}>${l}</option>`).join('')}</select></label>
    <button class="ghost" id="csv" ${rows.length ? '' : 'disabled'}>Download CSV</button></div>
    ${rows.length ? `<div class="table"><table><thead><tr><th>Person</th><th>Job</th><th>Company</th><th>Status</th><th>Applied</th><th>Updated</th></tr></thead><tbody>
    ${rows.map((a) => `<tr><td>${esc(nameOf(a.uid))}</td><td><a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer">${esc(a.title)}</a>${a.note ? `<div class="mute small">${esc(a.note)}</div>` : ''}</td><td>${esc(a.company)}</td>
      <td><span class="pill st-${esc(a.status)}">${esc(statusLabel(a.status))}</span></td><td class="nowrap">${esc(when(a.appliedAt))}</td><td class="nowrap">${esc(when(a.updatedAt))}</td></tr>`).join('')}</tbody></table></div>`
    : '<p class="mute">Nothing matches.</p>'}</div>`;
}

function wire(acts, appsAll) {
  app.querySelectorAll('[data-approve]').forEach((b) => {
    b.onclick = () => set(dbRef(`jm/members/${b.dataset.approve}`), { active: true, name: data.requests[b.dataset.approve].name, approvedAt: serverTimestamp() });
  });
  app.querySelectorAll('[data-decline]').forEach((b) => {
    b.onclick = () => confirm(`Decline ${data.requests[b.dataset.decline].name}?`) && remove(dbRef(`jm/requests/${b.dataset.decline}`));
  });
  app.querySelectorAll('[data-toggle]').forEach((b) => {
    const u = b.dataset.toggle;
    b.onclick = () => update(dbRef(`jm/members/${u}`), { active: !data.members[u].active });
  });
  app.querySelectorAll('[data-who]').forEach((a) => { a.onclick = (e) => { e.preventDefault(); userFilter = a.dataset.who; tab = 'activity'; render(); }; });
  const uf = app.querySelector('#uf');
  if (uf) uf.onchange = () => { userFilter = uf.value; render(); };
  const sf = app.querySelector('#sf');
  if (sf) sf.onchange = () => { statusFilter = sf.value; render(); };
  const csv = app.querySelector('#csv');
  if (csv && tab === 'activity') csv.onclick = () => csvDownload('jobmatch-usage.csv', [['When', 'Person', 'Email', 'Titles', 'Country', 'Searched', 'Listed', 'Skills'],
    ...acts.filter((a) => !userFilter || a.uid === userFilter).sort((a, b) => b.at - a.at).map((a) => [when(a.at), nameOf(a.uid), emailOf(a.uid), a.titles, a.country, a.found, a.shown, a.skills || ''])]);
  if (csv && tab === 'apps') csv.onclick = () => csvDownload('jobmatch-applications.csv', [['Person', 'Email', 'Job', 'Company', 'Status', 'Applied at', 'Updated', 'Link', 'Note'],
    ...appsAll.filter((a) => (!userFilter || a.uid === userFilter) && (!statusFilter || a.status === statusFilter)).map((a) => [nameOf(a.uid), emailOf(a.uid), a.title, a.company, statusLabel(a.status), when(a.appliedAt), when(a.updatedAt), a.url, a.note || ''])]);
}
