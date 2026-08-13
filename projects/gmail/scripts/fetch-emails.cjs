const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS_PATH || path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
const OAUTH_PATH = process.env.GMAIL_OAUTH_PATH || path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');
const PROJECT_DIR = path.join(__dirname, '..');
const TMP_DIR = path.join(PROJECT_DIR, 'tmp');

const IMPORTANT_LABELS = [
  'Finance/Banking', 'Finance/Receipt', 'Finance/Tax',
  'Dev/GitHub', 'Dev/AI',
  'Travel/Airline', 'Travel/Hotel', 'Travel/Japan',
  'Health',
];
const SUMMARY_LABELS = [
  'Finance', 'Finance/Banking', 'Finance/Receipt', 'Finance/Tax',
  'Travel', 'Travel/Airline', 'Travel/Hotel', 'Travel/Japan',
  'Dev', 'Dev/GitHub', 'Dev/AI', 'Dev/Database', 'Dev/Python', 'Health',
  'Newsletters', 'Newsletters/News', 'Newsletters/Tech',
  'Social', 'Social/Reddit', 'Social/Twitch', 'Social/LinkedIn',
  'Social/Instagram', 'Social/Facebook', 'Social/Netflix',
  'Learning', 'Learning/Codecademy', 'Learning/Guitar', 'Learning/General',
  'Shopping', 'Ads',
];

async function getAuth() {
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
  const oauthKeys = JSON.parse(fs.readFileSync(OAUTH_PATH, 'utf8'));
  const { client_id, client_secret } = oauthKeys.installed || oauthKeys.web;
  const auth = new google.auth.OAuth2(client_id, client_secret);
  auth.setCredentials(credentials);
  return auth;
}

function extractBody(payload) {
  if (!payload) return '';
  if (payload.mimeType === 'text/plain' && payload.body?.data) {
    return Buffer.from(payload.body.data, 'base64').toString('utf-8');
  }
  if (payload.parts) {
    const plain = payload.parts.find(p => p.mimeType === 'text/plain');
    if (plain?.body?.data) return Buffer.from(plain.body.data, 'base64').toString('utf-8');
    const html = payload.parts.find(p => p.mimeType === 'text/html');
    if (html?.body?.data) {
      return Buffer.from(html.body.data, 'base64').toString('utf-8').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    }
  }
  return '';
}

function formatSender(from) {
  const match = from.match(/"?([^"<]*?)"?\s*<([^>]+)>/);
  if (match) return match[1].trim() || match[2];
  return from.substring(0, 40);
}

function getCategory(labelIds, idToName) {
  for (const id of labelIds) {
    const name = idToName[id];
    if (!name) continue;
    for (const cat of SUMMARY_LABELS) {
      if (name === cat || name.startsWith(cat + '/')) return cat;
    }
  }
  return labelIds.includes('INBOX') ? '收件箱' : '其他';
}

async function main() {
  const auth = await getAuth();
  const gmail = google.gmail({ version: 'v1', auth });
  const labelsRes = await gmail.users.labels.list({ userId: 'me' });
  const idToName = {};
  for (const l of labelsRes.data.labels) idToName[l.id] = l.name;

  const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const dateStr = yesterday.toISOString().split('T')[0].replace(/-/g, '/');

  // Step 1: list all message IDs
  const allIds = [];
  let pageToken = null;
  while (true) {
    try {
      const res = await gmail.users.messages.list({
        userId: 'me', q: `after:${dateStr}`, maxResults: 500,
        pageToken: pageToken || undefined,
      });
      allIds.push(...(res.data.messages || []));
      pageToken = res.data.nextPageToken;
      if (!pageToken) break;
      await new Promise(r => setTimeout(r, 200));
    } catch (e) {
      if (e.code === 429) { await new Promise(r => setTimeout(r, 3000)); continue; }
      break;
    }
  }

  // Step 2: fetch metadata for ALL emails, body for important unread
  const emails = [];
  for (let i = 0; i < allIds.length; i += 50) {
    const batch = allIds.slice(i, i + 50);
    const results = await Promise.all(batch.map(async (msg) => {
      try {
        const meta = await gmail.users.messages.get({
          userId: 'me', id: msg.id, format: 'metadata',
          metadataHeaders: ['From', 'Subject', 'Date'],
        });
        const h = meta.data.payload.headers;
        const labelIds = meta.data.labelIds || [];
        const isImportant = labelIds.some(id => {
          const name = idToName[id];
          return name && IMPORTANT_LABELS.some(l => name === l || name.startsWith(l + '/'));
        });
        const isUnread = labelIds.includes('UNREAD');

        const d = {
          id: msg.id,
          from: h.find(x => x.name === 'From')?.value || '?',
          subject: h.find(x => x.name === 'Subject')?.value || '?',
          date: h.find(x => x.name === 'Date')?.value || '?',
          sender: formatSender(h.find(x => x.name === 'From')?.value || '?'),
          isImportant, isUnread,
          category: getCategory(labelIds, idToName),
          snippet: meta.data.snippet || '',
          body: '',
        };

        if (isImportant && isUnread) {
          try {
            const full = await gmail.users.messages.get({
              userId: 'me', id: msg.id, format: 'full',
            });
            d.body = extractBody(full.data.payload);
          } catch (e) { /* body fetch failed, snippet is enough */ }
        }
        return d;
      } catch (e) { return null; }
    }));
    emails.push(...results.filter(Boolean));
    await new Promise(r => setTimeout(r, 200));
  }

  // Sort: important first, then by category
  emails.sort((a, b) => {
    if (a.isImportant !== b.isImportant) return a.isImportant ? -1 : 1;
    if (a.category !== b.category) return a.category.localeCompare(b.category);
    return 0;
  });

  // Stats
  const total = emails.length;
  const unread = emails.filter(e => e.isUnread).length;
  const categories = {};
  for (const e of emails) {
    if (!categories[e.category]) categories[e.category] = { total: 0, unread: 0 };
    categories[e.category].total++;
    if (e.isUnread) categories[e.category].unread++;
  }

  const topSenders = {};
  for (const e of emails) {
    const domain = e.from.match(/@([^\s>]+)/)?.[1] || e.from;
    topSenders[domain] = (topSenders[domain] || 0) + 1;
  }

  const important = emails.filter(e => e.isImportant && e.isUnread);
  const others = emails.filter(e => !e.isImportant);

  fs.mkdirSync(TMP_DIR, { recursive: true });

  const output = {
    fetchedAt: new Date().toISOString(),
    date: new Date().toISOString().split('T')[0],
    stats: { total, unread, read: total - unread },
    categories: Object.entries(categories).map(([n, c]) => ({ name: n, ...c })),
    topSenders: Object.entries(topSenders).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([d, c]) => ({ domain: d, count: c })),
    important: important.map(e => ({
      sender: e.sender,
      from: e.from,
      subject: e.subject,
      date: e.date,
      category: e.category,
      snippet: e.snippet,
      body: e.body ? e.body.substring(0, 800) : '',
    })),
    others: others.map(e => ({
      sender: e.sender,
      subject: e.subject,
      date: e.date,
      unread: e.isUnread,
      category: e.category,
      snippet: e.snippet,
    })),
  };

  const jsonPath = path.join(TMP_DIR, 'emails.json');
  fs.writeFileSync(jsonPath, JSON.stringify(output, null, 2));

  console.log(JSON.stringify({ ok: true, total, unread, jsonPath, emailsCount: emails.length }));
}

main().catch(e => { console.error(JSON.stringify({ ok: false, error: e.message })); process.exit(1); });
