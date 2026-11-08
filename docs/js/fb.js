// Firebase setup shared by every page. Against the local emulator when the server says so (testing), else the real project.
import { initializeApp } from '../vendor/firebase/firebase-app.js';
import {
  getAuth, connectAuthEmulator, onAuthStateChanged, signInWithEmailAndPassword,
  createUserWithEmailAndPassword, updateProfile, signOut,
} from '../vendor/firebase/firebase-auth.js';
import {
  getDatabase, connectDatabaseEmulator, ref, get, set, update, remove, push, onValue, serverTimestamp,
} from '../vendor/firebase/firebase-database.js';
import { firebaseConfig, EMULATOR } from '../firebase-config.js';

const firebaseApp = initializeApp(firebaseConfig);
export const auth = getAuth(firebaseApp);
export const db = getDatabase(firebaseApp);
if (EMULATOR) {
  connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true });
  connectDatabaseEmulator(db, '127.0.0.1', 9000);
}
export {
  onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, updateProfile, signOut,
  ref, get, set, update, remove, push, onValue, serverTimestamp,
};
export const dbRef = (path) => ref(db, path);
export const idToken = () => auth.currentUser.getIdToken();

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const when = (ms) => (ms ? new Date(ms).toLocaleString() : '');
export const STATUSES = [['saved', 'Saved'], ['applied', 'Applied'], ['interview', 'Interview'], ['offer', 'Offer'], ['rejected', 'Rejected']];
export const statusLabel = (s) => (STATUSES.find((x) => x[0] === s) || [s, s])[1];

export function csvDownload(filename, rows) {
  const cell = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const text = `﻿${rows.map((r) => r.map(cell).join(',')).join('\r\n')}`;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// Sign in / request access card. Calls onDone() after the account exists (and a request was filed for new accounts).
export function showLogin(el, message = '', mode = 'in') {
  const up = mode === 'up';
  el.innerHTML = `<form class="card" id="login"><h2>${up ? 'Request access' : 'Sign in'}</h2>
    <p class="mute">${up ? 'Create your account. An admin must approve it before you can search.' : 'Sign in to search jobs and track your applications.'}</p>
    ${message ? `<p class="error">${esc(message)}</p>` : ''}
    ${up ? '<label>Your name<input id="name" maxlength="60" autocomplete="name" required></label>' : ''}
    <label>Email<input id="email" type="email" autocomplete="username" required></label>
    <label>Password<input id="password" type="password" minlength="8" autocomplete="${up ? 'new-password' : 'current-password'}" required></label>
    <button class="full">${up ? 'Create account' : 'Sign in'}</button>
    <p class="center small"><a href="#" id="swap">${up ? 'I already have an account' : 'I need an account'}</a></p></form>`;
  el.querySelector('#swap').onclick = (e) => { e.preventDefault(); showLogin(el, '', up ? 'in' : 'up'); };
  el.querySelector('#login').onsubmit = async (e) => {
    e.preventDefault();
    const email = el.querySelector('#email').value.trim();
    const password = el.querySelector('#password').value;
    try {
      if (up) {
        const name = el.querySelector('#name').value.trim();
        const cred = await createUserWithEmailAndPassword(auth, email, password);
        await updateProfile(cred.user, { displayName: name });
        await set(dbRef(`jm/requests/${cred.user.uid}`), { name, email, at: serverTimestamp() });
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
    } catch (err) {
      const used = String(err.code).includes('email-already-in-use');
      showLogin(el, used ? 'That email already has an account. Sign in instead.' : up ? 'Could not create the account. Use a valid email and a password of 8+ characters.' : 'Sign in failed. Check the email and password.', mode);
    }
  };
}
