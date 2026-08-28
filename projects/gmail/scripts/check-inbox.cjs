#!/usr/bin/env node
// check-inbox.cjs — 用 gog CLI 分析收件箱发件人构成（只读）。
const gog = require('./lib/gog.cjs');

function main() {
  const inbox = gog(['gmail', 'labels', 'get', 'INBOX', '--json', '--readonly', '--no-input']);
  const lbl = (inbox && inbox.label) || {};
  console.log(`📬 Inbox: ${lbl.messagesTotal || 0} total, ${lbl.messagesUnread || 0} unread`);

  const res = gog(['gmail', 'messages', 'search', 'in:inbox', '--max', '200', '--json', '--readonly', '--no-input']);
  const messages = (res && res.messages) || [];

  const senderCounts = {};
  for (const m of messages) {
    const from = m.from || '?';
    const domain = from.match(/@([^\s>]+)/)?.[1] || from;
    if (!senderCounts[domain]) senderCounts[domain] = { count: 0, samples: [] };
    senderCounts[domain].count++;
    if (senderCounts[domain].samples.length < 2) {
      senderCounts[domain].samples.push({ from, subject: m.subject || '?' });
    }
  }

  const sorted = Object.entries(senderCounts).sort((a, b) => b[1].count - a[1].count);
  console.log(`\n🔍 Top senders in inbox (sampled ${messages.length}):`);
  const total = messages.length || 1;
  for (const [domain, info] of sorted.slice(0, 15)) {
    const pct = Math.round((info.count / total) * 100);
    console.log(`  ${pct}% ${domain} (${info.count})`);
    for (const s of info.samples) console.log(`    └ ${s.subject.substring(0, 70)}`);
  }
}

try {
  main();
} catch (e) {
  console.error(`错误：${(e.stderr || e.message || '').toString().trim()}`);
  console.error('提示：需先授权 gog auth add <你的gmail> --services gmail --gmail-scope full --extra-scopes https://www.googleapis.com/auth/gmail.labels --force-consent');
  process.exit(1);
}
