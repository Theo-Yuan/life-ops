#!/usr/bin/env node
// gog-fetch.cjs — 用 `gog` CLI 抓取最近 24h 的 Gmail，生成 emails.json（结构与原 fetch-emails.cjs 一致）。
//
// 依赖：
//   gog 已安装且完成授权（gog auth add <email> --services gmail --gmail-scope readonly）
//
// 输出：与 fetch-emails.cjs 相同的 emails.json 结构 + 一行 JSON 结果。
const gog = require('./lib/gog.cjs');
const fs = require('fs');
const path = require('path');

const PROJECT_DIR = path.join(__dirname, '..');
const TMP_DIR = path.join(PROJECT_DIR, 'tmp');

// 重要标签（未读时抓全文 body）
const IMPORTANT_LABELS = [
  'Finance/Banking', 'Finance/Receipt', 'Finance/Tax',
  'Dev/GitHub', 'Dev/AI',
  'Travel/Airline', 'Travel/Hotel', 'Travel/Japan',
  'Health',
];
// 分类标签（决定 category 字段）
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

function formatSender(from) {
  const m = from.match(/"?([^"<]*?)"?\s*<([^>]+)>/);
  if (m) return m[1].trim() || m[2];
  return from.substring(0, 40);
}

function getCategory(labels) {
  for (const name of labels) {
    for (const cat of SUMMARY_LABELS) {
      if (name === cat || name.startsWith(cat + '/')) return cat;
    }
  }
  return labels.includes('INBOX') ? '收件箱' : '其他';
}

function main() {
  const res = gog([
    'gmail', 'messages', 'search', 'newer_than:1d',
    '--max', '500', '--json', '--readonly', '--no-input',
  ]);
  const messages = (res && res.messages) || [];

  const emails = [];
  const importantIds = [];

  for (const m of messages) {
    const labels = m.labels || [];
    const isUnread = labels.includes('UNREAD');
    const isImportant = labels.some((l) =>
      IMPORTANT_LABELS.some((x) => l === x || l.startsWith(x + '/'))
    );
    const from = m.from || '?';
    const e = {
      id: m.id,
      from,
      subject: m.subject || '?',
      date: m.date || m.internalDateIso || '?',
      sender: formatSender(from),
      isImportant,
      isUnread,
      category: getCategory(labels),
      snippet: '',
      body: '',
    };
    if (isImportant && isUnread) importantIds.push(m.id);
    emails.push(e);
  }

  // 重要未读 → 抓全文 body + snippet
  const bodyById = {};
  for (const id of importantIds) {
    try {
      const g = gog(['gmail', 'get', id, '--sanitize-content', '--json', '--readonly', '--no-input']);
      const msg = (g && g.message) || {};
      bodyById[id] = { snippet: msg.snippet || '', body: msg.body || '' };
    } catch (err) {
      bodyById[id] = { snippet: '', body: '' };
    }
  }
  for (const e of emails) {
    const b = bodyById[e.id];
    if (b) {
      e.snippet = b.snippet;
      e.body = b.body.substring(0, 800);
    }
  }

  // 排序：重要优先，再按分类
  emails.sort((a, b) => {
    if (a.isImportant !== b.isImportant) return a.isImportant ? -1 : 1;
    if (a.category !== b.category) return a.category.localeCompare(b.category);
    return 0;
  });

  const total = emails.length;
  const unread = emails.filter((e) => e.isUnread).length;

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

  const important = emails.filter((e) => e.isImportant && e.isUnread);
  const others = emails.filter((e) => !e.isImportant);

  fs.mkdirSync(TMP_DIR, { recursive: true });

  const output = {
    fetchedAt: new Date().toISOString(),
    date: new Date().toISOString().split('T')[0],
    stats: { total, unread, read: total - unread },
    categories: Object.entries(categories).map(([n, c]) => ({ name: n, ...c })),
    topSenders: Object.entries(topSenders)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([d, c]) => ({ domain: d, count: c })),
    important: important.map((e) => ({
      sender: e.sender,
      from: e.from,
      subject: e.subject,
      date: e.date,
      category: e.category,
      snippet: e.snippet,
      body: e.body,
    })),
    others: others.map((e) => ({
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

try {
  main();
} catch (e) {
  const stderr = (e.stderr || '').toString();
  const detail = stderr.trim() || e.message;
  console.error(JSON.stringify({ ok: false, error: detail }));
  process.exit(1);
}
