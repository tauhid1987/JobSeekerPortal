// Run with:  npm run test:rules   (needs Java; uses the local Firebase emulator, never the real project)
import { test, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { initializeTestEnvironment, assertFails, assertSucceeds } from '@firebase/rules-unit-testing';

const TS = { '.sv': 'timestamp' };
let env;

before(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-jobmatch',
    database: { rules: readFileSync(new URL('../firebase/database.rules.json', import.meta.url), 'utf8'), host: '127.0.0.1', port: 9000 },
  });
});
after(() => env.cleanup());
beforeEach(async () => {
  await env.clearDatabase();
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.database();
    await db.ref('hosts/admin1').set(true);
    await db.ref('jm/members/alice').set({ active: true, name: 'Alice' });
    await db.ref('jm/members/bob').set({ active: true, name: 'Bob' });
    await db.ref('jm/members/blocked1').set({ active: false, name: 'Blocked' });
  });
});

const as = (uid) => env.authenticatedContext(uid).database();
const activity = (extra = {}) => ({ at: TS, titles: 'QA Engineer', country: 'Bangladesh', found: 100, shown: 20, ...extra });
const app = (extra = {}) => ({ title: 'QA Engineer', company: 'Acme', status: 'applied', createdAt: TS, updatedAt: TS, appliedAt: TS, url: 'https://x.y/1', ...extra });
const KEY = 'a1b2c3d4e5f60718';

test('anonymous users see and write nothing under jm', async () => {
  const db = env.unauthenticatedContext().database();
  await assertFails(db.ref('jm/members/alice').get());
  await assertFails(db.ref(`jm/activity/alice`).push(activity()));
});

test('a new user can ask for access but cannot approve themselves', async () => {
  await assertSucceeds(as('carol').ref('jm/requests/carol').set({ name: 'Carol', email: 'c@x.com', at: TS }));
  await assertFails(as('carol').ref('jm/members/carol').set({ active: true, name: 'Carol' }));
  await assertFails(as('carol').ref('jm/requests/dave').set({ name: 'D', email: 'd@x.com', at: TS }));
  await assertFails(as('carol').ref('jm/requests/carol').set({ name: 'Carol2', email: 'c@x.com', at: TS })); // no re-write
});

test('only an admin approves, blocks and reads the member list', async () => {
  await assertSucceeds(as('admin1').ref('jm/members/carol').set({ active: true, name: 'Carol' }));
  await assertSucceeds(as('admin1').ref('jm/members/bob').update({ active: false }));
  await assertSucceeds(as('admin1').ref('jm/members').get());
  await assertFails(as('alice').ref('jm/members').get());
  await assertSucceeds(as('alice').ref('jm/members/alice').get());
  await assertFails(as('alice').ref('jm/members/bob').get());
  await assertFails(as('alice').ref('jm/members/alice/active').set(false));
});

test('search history: members add it, nobody edits or deletes it', async () => {
  const ref = await assertSucceeds(as('alice').ref('jm/activity/alice').push(activity()));
  await assertFails(as('alice').ref(`jm/activity/alice/${ref.key}`).update({ found: 1 }));
  await assertFails(as('alice').ref(`jm/activity/alice/${ref.key}`).remove());
  await assertFails(as('admin1').ref(`jm/activity/alice/${ref.key}`).remove());
  await assertFails(as('alice').ref('jm/activity/alice').push(activity({ at: 123 })));            // fake time
  await assertFails(as('alice').ref('jm/activity/bob').push(activity()));                           // someone else's
  await assertFails(as('blocked1').ref('jm/activity/blocked1').push(activity()));                  // blocked
  await assertFails(as('stranger').ref('jm/activity/stranger').push(activity()));                  // not a member
});

test('history is private to the user, visible to admins', async () => {
  await as('alice').ref('jm/activity/alice').push(activity());
  await assertSucceeds(as('alice').ref('jm/activity/alice').get());
  await assertFails(as('bob').ref('jm/activity/alice').get());
  await assertFails(as('bob').ref('jm/activity').get());
  await assertSucceeds(as('admin1').ref('jm/activity').get());
});

test('admins can use the tool too', async () => {
  await assertSucceeds(as('admin1').ref('jm/activity/admin1').push(activity()));
  await assertSucceeds(as('admin1').ref(`jm/applications/admin1/${KEY}`).set(app()));
});

test('applications: create, change status, never delete, createdAt is fixed', async () => {
  const r = as('alice').ref(`jm/applications/alice/${KEY}`);
  await assertSucceeds(r.set(app({ status: 'saved', appliedAt: null })));
  await assertSucceeds(r.update({ status: 'applied', appliedAt: TS, updatedAt: TS }));
  await assertSucceeds(r.update({ status: 'interview', note: 'Phone screen Mon', updatedAt: TS }));
  await assertFails(r.remove());
  await assertFails(r.update({ createdAt: 1, updatedAt: TS }));
  await assertFails(r.update({ appliedAt: 5, updatedAt: TS }));                                   // cannot rewrite applied time
  await assertFails(r.update({ status: 'hired', updatedAt: TS }));                                 // not a valid status
  await assertFails(r.update({ status: 'offer' }));                                                 // updatedAt must be refreshed
  await assertFails(as('bob').ref(`jm/applications/alice/${KEY}`).update({ status: 'rejected', updatedAt: TS }));
  await assertFails(as('alice').ref('jm/applications/alice/not-a-valid-key!').set(app()));
  await assertFails(as('blocked1').ref(`jm/applications/blocked1/${KEY}`).set(app()));
});

test('applications are private to the user, visible to admins', async () => {
  await as('alice').ref(`jm/applications/alice/${KEY}`).set(app());
  await assertFails(as('bob').ref('jm/applications/alice').get());
  await assertSucceeds(as('alice').ref('jm/applications/alice').get());
  await assertSucceeds(as('admin1').ref('jm/applications').get());
});

test('status change log is append-only', async () => {
  const log = { at: TS, key: KEY, title: 'QA Engineer', status: 'applied' };
  const r = await assertSucceeds(as('alice').ref('jm/applogs/alice').push(log));
  await assertFails(as('alice').ref(`jm/applogs/alice/${r.key}`).update({ status: 'offer' }));
  await assertFails(as('alice').ref(`jm/applogs/alice/${r.key}`).remove());
  await assertFails(as('alice').ref('jm/applogs/alice').push({ ...log, status: 'hired' }));
});

test('Quiz Arena rules are untouched', async () => {
  await assertFails(as('alice').ref('hosts/alice').set(true));
  await assertSucceeds(as('admin1').ref('hosts/admin1').get());
  await assertFails(as('alice').ref('history').get());
  await assertSucceeds(as('admin1').ref('history').get());
});
