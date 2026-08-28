#!/usr/bin/env node
// apply-filters.cjs — 用 gog CLI 将现有 Gmail 过滤器重新应用到收件箱（线程级）。
const gog = require('./lib/gog.cjs');

function buildQuery(criteria) {
  const parts = [];
  if (criteria.from) parts.push(`from:(${criteria.from})`);
  if (criteria.to) parts.push(`to:(${criteria.to})`);
  if (criteria.subject) parts.push(`subject:"${criteria.subject}"`);
  if (criteria.query) parts.push(`(${criteria.query})`);
  if (criteria.hasAttachment) parts.push('has:attachment');
  if (criteria.excludeChats) parts.push('-in:chats');
  return `in:inbox ${parts.join(' ')}`.trim();
}

function labelNames(ids, idToName) {
  return (ids || []).map((id) => idToName[id] || id).join(', ');
}

function filterDescription(filter, idToName) {
  const c = filter.criteria || {};
  const a = filter.action || {};
  const parts = [];
  if (c.from) parts.push(`from:${c.from}`);
  if (c.subject) parts.push(`subject:${c.subject}`);
  if (c.query) parts.push(`q:${c.query}`);
  const adds = (a.addLabelIds || []).map((l) => `+${idToName[l] || l}`);
  const removes = (a.removeLabelIds || []).map((l) => `-${idToName[l] || l}`);
  return `${parts.join(', ') || '?'} → [${[...adds, ...removes].join(', ')}]`;
}

function main() {
  const dryRun = process.argv.includes('--dry-run');
  console.log(`${dryRun ? '🔍 DRY RUN (preview only)' : '🚀 APPLY MODE'}\n`);

  console.log('📋 Fetching filters...');
  const filtersRes = gog(['gmail', 'settings', 'filters', 'list', '--json', '--readonly', '--no-input']);
  const filters = (filtersRes && filtersRes.filters) || [];
  console.log(`Found ${filters.length} filters.\n`);

  const labelsRes = gog(['gmail', 'labels', 'list', '--json', '--readonly', '--no-input']);
  const idToName = {};
  for (const l of (labelsRes && labelsRes.labels) || []) idToName[l.id] = l.name;

  let grandTotal = 0;
  for (let i = 0; i < filters.length; i++) {
    const f = filters[i];
    const add = (f.action && f.action.addLabelIds) || [];
    const remove = (f.action && f.action.removeLabelIds) || [];
    console.log(`[${i + 1}/${filters.length}] ${filterDescription(f, idToName)}`);

    const query = buildQuery(f.criteria || {});

    if (dryRun) {
      const res = gog(['gmail', 'search', query, '--max', '10', '--json', '--readonly', '--no-input']);
      const threads = (res && res.threads) || [];
      if (threads.length === 0) {
        console.log('  ⚪ No matches');
        continue;
      }
      grandTotal += threads.length;
      console.log(`  [DRY RUN] 匹配 ${threads.length}+ 线程; 加标签: ${labelNames(add, idToName) || '(无)'}; 减标签: ${labelNames(remove, idToName) || '(无)'}`);
      for (const t of threads.slice(0, 5)) {
        console.log(`      📧 ${(t.from || '?').substring(0, 40)} | ${(t.subject || '?').substring(0, 50)}`);
      }
      if (threads.length > 5) console.log('      ... and more');
    } else {
      const searchRes = gog(['gmail', 'search', query, '--all', '--json', '--readonly', '--no-input']);
      const threads = (searchRes && searchRes.threads) || [];
      const threadIds = threads.map((t) => t.id);
      if (threadIds.length === 0) {
        console.log('  ⚪ No unprocessed matches found');
        continue;
      }
      for (let j = 0; j < threadIds.length; j += 100) {
        const chunk = threadIds.slice(j, j + 100);
        const args = ['gmail', 'labels', 'modify', ...chunk];
        if (add.length) args.push(`--add=${add.join(',')}`);
        if (remove.length) args.push(`--remove=${remove.join(',')}`);
        args.push('--force', '--json');
        gog(args);
      }
      grandTotal += threadIds.length;
      console.log(`  ✅ Processed ${threadIds.length} threads`);
    }
  }

  console.log(`\n📊 Summary:`);
  console.log(`   Total filters: ${filters.length}`);
  console.log(`   ${dryRun ? 'Would process ≥' : 'Processed'} ${grandTotal} threads`);
  if (dryRun) console.log('Run without --dry-run to execute');
}

try {
  main();
} catch (e) {
  console.error(`错误：${(e.stderr || e.message || '').toString().trim()}`);
  console.error('提示：需先授权 gog auth add <你的gmail> --services gmail --gmail-scope full --extra-scopes https://www.googleapis.com/auth/gmail.labels --force-consent');
  process.exit(1);
}
