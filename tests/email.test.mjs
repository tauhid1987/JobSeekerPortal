// Run with:  node --test tests/email.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { checkEmail } from '../docs/js/email.js';

test('accepts normal addresses and lower-cases them', () => {
  assert.deepEqual(checkEmail('  Tauhid.Islam+jobs@Example.COM '), { ok: true, email: 'tauhid.islam+jobs@example.com' });
  assert.equal(checkEmail('x_y-z@mail.example.com.bd').ok, true);
});

test('rejects invalid addresses', () => {
  for (const bad of ['', '   ', 'plain', 'a@b', 'a@@b.com', 'a b@c.com', 'a@b..com', 'a@.com', 'a@b.c', '@b.com', '.a@b', 'a@b.com\r\nBcc: z@z.com', `${'a'.repeat(65)}@b.com`]) {
    assert.equal(checkEmail(bad).ok, false, JSON.stringify(bad));
  }
});

test('suggests the right domain for common typos', () => {
  for (const [typed, want] of [['me@gmial.com', 'me@gmail.com'], ['me@yaho.com', 'me@yahoo.com'], ['me@hotmial.com', 'me@hotmail.com'], ['me@gmail.con', 'me@gmail.com']]) {
    const r = checkEmail(typed);
    assert.equal(r.ok, false);
    assert.ok(r.error.includes(want), r.error);
  }
});

test('error text is shown for missing input', () => {
  assert.match(checkEmail(undefined).error, /Enter your email/);
});
