// Email check for the sign-up form. Same rule as app/mailer.py and firebase/jm.rules.fragment.json.
// It catches typos and fake-looking addresses before an account is made. It cannot prove the mailbox exists.
export const EMAIL_RE = /^(?!.*\.\.)[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$/;

// Common typos of big mail providers -> the address they almost certainly meant.
const TYPOS = {
  'gmial.com': 'gmail.com', 'gmai.com': 'gmail.com', 'gmail.con': 'gmail.com', 'gmail.co': 'gmail.com', 'gamil.com': 'gmail.com',
  'gnail.com': 'gmail.com', 'gmaill.com': 'gmail.com', 'gmail.cm': 'gmail.com', 'gmail.om': 'gmail.com',
  'yaho.com': 'yahoo.com', 'yahooo.com': 'yahoo.com', 'yahoo.con': 'yahoo.com', 'yhoo.com': 'yahoo.com',
  'hotmial.com': 'hotmail.com', 'hotmai.com': 'hotmail.com', 'hotmail.con': 'hotmail.com',
  'outlok.com': 'outlook.com', 'outloook.com': 'outlook.com', 'outlook.con': 'outlook.com',
};

// Returns { ok: true, email } (trimmed, lower case) or { ok: false, error }.
export function checkEmail(raw) {
  const email = String(raw ?? '').trim().toLowerCase();
  if (!email) return { ok: false, error: 'Enter your email address.' };
  if (email.length > 120 || !EMAIL_RE.test(email)) {
    return { ok: false, error: 'That email address does not look valid. Use the form name@example.com, with no spaces.' };
  }
  const domain = email.split('@')[1];
  if (TYPOS[domain]) {
    return { ok: false, error: `Did you mean ${email.split('@')[0]}@${TYPOS[domain]}? Check the spelling, then try again.` };
  }
  return { ok: true, email };
}
