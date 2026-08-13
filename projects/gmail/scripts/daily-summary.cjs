const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
const OAUTH_PATH = process.env.GMAIL_OAUTH_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');
const PROJECT_DIR = path.join(__dirname, '..');

const IMPORTANT_LABELS = [
  'Finance/Banking', 'Finance/Receipt', 'Finance/Tax',
  'Dev/GitHub', 'Dev/AI',
  'Travel/Airline', 'Travel/Hotel', 'Travel/Japan',
  'Health',
];

const SUMMARY_LABELS = [
  'Finance', 'Finance/Banking', 'Finance/Receipt', 'Finance/Tax',
  'Travel', 'Travel/Airline', 'Travel/Hotel', 'Travel/Japan',
  'Dev', 'Dev/GitHub', 'Dev/AI', 'Dev/Database', 'Dev/Python',
  'Health',
  'Newsletters', 'Newsletters/News', 'Newsletters/Tech',
  'Social', 'Social/Reddit', 'Social/Twitch', 'Social/LinkedIn',
  'Social/Instagram', 'Social/Facebook', 'Social/Netflix',
  'Learning', 'Learning/Codecademy', 'Learning/Guitar', 'Learning/General',
  'Shopping', 'Ads',
];

const SUMMARY_BODY_LENGTH = 100;
const DISCORD_MAX_LENGTH = 1900;

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
    if (plain?.body?.data) {
      return Buffer.from(plain.body.data, 'base64').toString('utf-8');
    }
    const html = payload.parts.find(p => p.mimeType === 'text/html');
    if (html?.body?.data) {
      const text = Buffer.from(html.body.data, 'base64').toString('utf-8');
      return text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    }
  }
  return '';
}

function summarizeBody(body, maxLen = SUMMARY_BODY_LENGTH) {
  const cleaned = body.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
  if (cleaned.length <= maxLen) return cleaned;
  return cleaned.substring(0, maxLen) + '…';
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
  if (labelIds.includes('INBOX')) return '收件箱';
  return '其他';
}

async function main() {
  const auth = await getAuth();
  const gmail = google.gmail({ version: 'v1', auth });

  const labelsRes = await gmail.users.labels.list({ userId: 'me' });
  const idToName = {};
  for (const l of labelsRes.data.labels) idToName[l.id] = l.name;

  const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const dateStr = yesterday.toISOString().split('T')[0].replace(/-/g, '/');
  const query = `after:${dateStr}`;

  const allIds = [];
  let pageToken = null;
  while (true) {
    try {
      const res = await gmail.users.messages.list({
        userId: 'me', q: query, maxResults: 500,
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

  const details = [];
  for (let i = 0; i < allIds.length; i += 50) {
    const batch = allIds.slice(i, i + 50);
    const promises = batch.map(async (msg) => {
      try {
        const res = await gmail.users.messages.get({
          userId: 'me', id: msg.id, format: 'metadata',
          metadataHeaders: ['From', 'Subject', 'Date'],
        });
        const h = res.data.payload.headers;
        const d = {
          id: msg.id, threadId: msg.threadId,
          from: h.find(x => x.name === 'From')?.value || '?',
          subject: h.find(x => x.name === 'Subject')?.value || '?',
          date: h.find(x => x.name === 'Date')?.value || '?',
          labelIds: res.data.labelIds || [],
          snippet: res.data.snippet || '',
        };
        const labelIds = d.labelIds;
        const isImportant = labelIds.some(id => {
          const name = idToName[id];
          return name && IMPORTANT_LABELS.some(l => name === l || name.startsWith(l + '/'));
        });
        d.isImportant = isImportant;
        d.isUnread = labelIds.includes('UNREAD');
        d.category = getCategory(labelIds, idToName);

        if (isImportant && d.isUnread) {
          try {
            const full = await gmail.users.messages.get({
              userId: 'me', id: msg.id, format: 'full',
            });
            d.body = extractBody(full.data.payload);
          } catch (e) { d.body = ''; }
        }
        return d;
      } catch (e) { return null; }
    });
    const results = await Promise.all(promises);
    details.push(...results.filter(Boolean));
    await new Promise(r => setTimeout(r, 200));
  }

  details.sort((a, b) => {
    const aImp = a.isImportant ? 0 : 1;
    const bImp = b.isImportant ? 0 : 1;
    if (aImp !== bImp) return aImp - bImp;
    return a.category.localeCompare(b.category);
  });

  const total = details.length;
  const unreadTotal = details.filter(d => d.isUnread).length;

  const categorized = {};
  for (const d of details) {
    if (!categorized[d.category]) categorized[d.category] = { total: 0, unread: 0 };
    categorized[d.category].total++;
    if (d.isUnread) categorized[d.category].unread++;
  }

  const now = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });

  // ── Console Output ──
  console.log('📊 DAILY EMAIL SUMMARY');
  console.log('═══════════════════════');
  console.log(`🕐 ${now}\n`);
  console.log(`📬 ${total}封（${unreadTotal}未读 / ${total - unreadTotal}已读）\n`);

  for (const [cat, c] of Object.entries(categorized)) {
    const bar = '█'.repeat(Math.min(c.total, 30));
    console.log(`  ${cat.padEnd(20)} ${String(c.total).padStart(3)}封  ${String(c.unread).padStart(3)}未读  ${bar}`);
  }

  const important = details.filter(d => d.isImportant);
  const others = details.filter(d => !d.isImportant);

  if (important.length > 0) {
    console.log(`\n── ⚠️ 重要邮件 (${important.length}封) ──`);
    for (const d of important) {
      const sender = formatSender(d.from);
      const readTag = d.isUnread ? '🆕' : '✅';
      console.log(`\n  ${readTag} ${sender}`);
      console.log(`     ${d.subject}`);
      if (d.body) {
        console.log(`     ✏️ ${summarizeBody(d.body, 120)}`);
      } else if (d.snippet) {
        console.log(`     ✏️ ${summarizeBody(d.snippet, 120)}`);
      }
    }
  }

  if (others.length > 0) {
    console.log(`\n── 📋 其他邮件 (${others.length}封) ──`);
    const byCat = {};
    for (const d of others) byCat[d.category] = (byCat[d.category] || 0) + 1;
    console.log(`  ${Object.entries(byCat).map(([k,v]) => `${k}×${v}`).join('  ')}`);
    for (const d of others) {
      const sender = formatSender(d.from);
      const readTag = d.isUnread ? '🆕' : '✅';
      console.log(`  ${readTag} ${sender} | ${d.subject.substring(0, 70)}`);
    }
  }

  // ── Discord Output ──
  const parts = [];
  parts.push(`📊 **今日邮件** 🕐 ${now.split(' ')[0]}\n📬 ${total}封（${unreadTotal}未读 / ${total - unreadTotal}已读）`);

  let catSection = '';
  for (const [cat, c] of Object.entries(categorized)) {
    catSection += `\`${cat}\` ${c.total}/${c.unread}  `;
  }
  parts.push(catSection);

  if (important.length > 0) {
    let impSection = `\n⚠️ **重要 (${important.length})**`;
    for (const d of important.slice(0, 6)) {
      const sender = formatSender(d.from);
      const readTag = d.isUnread ? '🔴' : '✅';
      impSection += `\n${readTag} **${sender}** — ${d.subject.substring(0, 50)}`;
      const summary = d.body ? summarizeBody(d.body, 60) : d.snippet.substring(0, 60);
      if (summary) impSection += `\n   > ${summary}`;
    }
    if (important.length > 6) impSection += `\n   …等${important.length - 6}封`;
    parts.push(impSection);
  }

  if (others.length > 0) {
    let otherSection = `\n📋 **其他 (${others.length})**`;
    const byCat = {};
    for (const d of others) byCat[d.category] = (byCat[d.category] || 0) + 1;
    otherSection += `\n${Object.entries(byCat).map(([k,v]) => `\`${k}\`×${v}`).join(' ')}`;
    for (const d of others.slice(0, 10)) {
      const sender = formatSender(d.from);
      otherSection += `\n· ${sender} — ${d.subject.substring(0, 50)}`;
    }
    if (others.length > 10) otherSection += `\n…等${others.length - 10}封`;
    parts.push(otherSection);
  }

  // Split into chunks if needed
  let discordMsg = '';
  for (const p of parts) {
    if ((discordMsg + '\n' + p).length > DISCORD_MAX_LENGTH) {
      const outFile = path.join(PROJECT_DIR, 'tmp', `discord-msg-${Date.now()}.txt`);
      fs.writeFileSync(outFile, discordMsg);
      console.log(`\n✂️ Discord message saved to ${outFile} (${discordMsg.length} chars)`);
      discordMsg = p;
    } else {
      discordMsg = (discordMsg ? discordMsg + '\n' : '') + p;
    }
  }

  // Always save the full message for scheduling
  const discordFile = path.join(PROJECT_DIR, 'tmp', 'discord-msg.txt');
  fs.writeFileSync(discordFile, discordMsg);
  console.log(`\n📨 Discord message saved: tmp/discord-msg.txt (${discordMsg.length} chars)`);

  // ── JSON Output ──
  const tmpDir = path.join(PROJECT_DIR, 'tmp');
  fs.mkdirSync(tmpDir, { recursive: true });

  const cats = Object.entries(categorized).map(([n, c]) => ({ name: n, ...c }));
  const topSenders = {};
  for (const d of details) {
    const domain = d.from.match(/@([^\s>]+)/)?.[1] || d.from;
    topSenders[domain] = (topSenders[domain] || 0) + 1;
  }

  fs.writeFileSync(path.join(tmpDir, 'daily-summary.json'), JSON.stringify({
    date: new Date().toISOString().split('T')[0],
    total, unread: unreadTotal,
    categories: cats,
    important: important.map(d => ({
      from: formatSender(d.from), subject: d.subject,
      unread: d.isUnread,
      summary: d.body ? summarizeBody(d.body, 100) : d.snippet.substring(0, 100),
    })),
    others: others.map(d => ({
      from: formatSender(d.from), subject: d.subject.substring(0, 80),
      unread: d.isUnread, category: d.category,
    })),
    topSenders: Object.entries(topSenders).sort((a, b) => b[1] - a[1]).slice(0, 5)
      .map(([d, c]) => ({ domain: d, count: c })),
  }, null, 2));

  fs.writeFileSync(discordFile, discordMsg);
  console.log('\n═══════════════════════');
}

main().catch(console.error);
