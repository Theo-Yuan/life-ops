const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
const OAUTH_PATH = process.env.GMAIL_OAUTH_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');

async function main() {
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
  const oauthKeys = JSON.parse(fs.readFileSync(OAUTH_PATH, 'utf8'));
  const { client_id, client_secret } = oauthKeys.installed || oauthKeys.web;
  const auth = new google.auth.OAuth2(client_id, client_secret);
  auth.setCredentials(credentials);
  const gmail = google.gmail({ version: 'v1', auth });

  const inboxRes = await gmail.users.labels.get({ userId: 'me', id: 'INBOX' });
  console.log(`📬 Inbox: ${inboxRes.data.messagesTotal} total, ${inboxRes.data.messagesUnread} unread`);

  // Sample 50 emails, group by sender domain
  const senderCounts = {};
  let pageToken = null;
  let sampled = 0;

  while (sampled < 200 && sampled < inboxRes.data.messagesTotal) {
    const res = await gmail.users.messages.list({
      userId: 'me', q: 'in:inbox', maxResults: 100,
      pageToken: pageToken || undefined,
    });
    const messages = res.data.messages || [];
    for (const msg of messages) {
      try {
        const detail = await gmail.users.messages.get({
          userId: 'me', id: msg.id, format: 'metadata',
          metadataHeaders: ['From', 'Subject'],
        });
        const headers = detail.data.payload.headers;
        const from = headers.find(h => h.name === 'From')?.value || '?';
        const subject = headers.find(h => h.name === 'Subject')?.value || '?';
        const domain = from.match(/@([^\s>]+)/)?.[1] || from;
        if (!senderCounts[domain]) senderCounts[domain] = { count: 0, samples: [] };
        senderCounts[domain].count++;
        if (senderCounts[domain].samples.length < 2) {
          senderCounts[domain].samples.push({ from, subject });
        }
        sampled++;
      } catch (e) { /* skip */ }
    }
    pageToken = res.data.nextPageToken;
    if (!pageToken || sampled >= 200) break;
    await new Promise(r => setTimeout(r, 200));
  }

  const sorted = Object.entries(senderCounts).sort((a, b) => b[1].count - a[1].count);
  console.log(`\n🔍 Top senders in inbox (sampled ${sampled}):`);
  for (const [domain, info] of sorted.slice(0, 15)) {
    const pct = ((info.count / sampled) * 100).toFixed(0);
    console.log(`  ${pct}% ${domain} (${info.count})`);
    for (const s of info.samples) {
      console.log(`    └ ${s.subject.substring(0, 70)}`);
    }
  }
}
main().catch(console.error);
