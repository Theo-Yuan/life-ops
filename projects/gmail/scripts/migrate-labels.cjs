#!/usr/bin/env node
// migrate-labels.cjs — 用 gog CLI 迁移旧标签 → 新标签（线程级），并删除旧标签。
const gog = require('./lib/gog.cjs');

const MIGRATIONS = {
  'linkedin': 'Social/LinkedIn',
  'twitch': 'Social/Twitch',
  'facebook': 'Social/Facebook',
  'feed/netflix': 'Social/Netflix',
  'feed': 'Social',
  'News': 'Newsletters/News',
  'mongodb': 'Dev/Database',
  'deeplearning.ai': 'Dev/AI',
  'AI': 'Dev/AI',
  'Real Python': 'Dev/Python',
  'tour/japan': 'Travel/Japan',
  'tour': 'Travel',
  'receipt': 'Finance/Receipt',
  'advertisement': 'Ads',
  'google': 'Newsletters',
  'zoom': null,
  'Conversation History': null,
  '对话历史记录': null,
  'Notes': null,
};

function labelQuery(name) {
  return `label:"${name.replace(/"/g, '\\"')}"`;
}

function main() {
  const dryRun = process.argv.includes('--dry-run');
  console.log(`${dryRun ? '🔍 DRY RUN (preview only)' : '🚀 MIGRATE MODE'}\n`);

  const labelsRes = gog(['gmail', 'labels', 'list', '--json', '--readonly', '--no-input']);
  const labels = (labelsRes && labelsRes.labels) || [];
  const existing = new Set(labels.map((l) => l.name));

  const entries = Object.entries(MIGRATIONS);
  for (let i = 0; i < entries.length; i++) {
    const [oldName, newName] = entries[i];
    if (!existing.has(oldName)) {
      console.log(`[${i + 1}/${entries.length}] ⚪ ${oldName} — label not found, skipping`);
      continue;
    }

    let messages = 0;
    let threads = 0;
    try {
      const info = gog(['gmail', 'labels', 'get', oldName, '--json', '--readonly', '--no-input']);
      messages = (info && info.label && info.label.messagesTotal) || 0;
      threads = (info && info.label && info.label.threadsTotal) || 0;
    } catch (e) {
      messages = 0;
      threads = 0;
    }

    if (!newName) {
      console.log(`[${i + 1}/${entries.length}] ℹ️  ${oldName} (${messages} emails) — no mapping, keep manually`);
      continue;
    }

    console.log(`[${i + 1}/${entries.length}] 🔄 ${oldName} → ${newName} (${messages} emails / ${threads} threads)`);

    if (dryRun) {
      try {
        const sample = gog(['gmail', 'search', labelQuery(oldName), '--max', '5', '--json', '--readonly', '--no-input']);
        for (const t of (sample && sample.threads) || []) {
          console.log(`      📧 ${(t.from || '?').substring(0, 40)} | ${(t.subject || '?').substring(0, 50)}`);
        }
      } catch (e) {
        console.log('      (sample unavailable)');
      }
      console.log(`  🗑️  [DRY RUN] would delete old label: ${oldName}`);
      continue;
    }

    if (messages > 0) {
      let threadIds = [];
      if (threads > 0) {
        const searchRes = gog(['gmail', 'search', labelQuery(oldName), '--all', '--json', '--readonly', '--no-input']);
        threadIds = ((searchRes && searchRes.threads) || []).map((t) => t.id);
      }
      for (let j = 0; j < threadIds.length; j += 100) {
        const chunk = threadIds.slice(j, j + 100);
        gog(['gmail', 'labels', 'modify', ...chunk, `--add=${newName}`, '--force', '--json']);
      }
      console.log(`  ✅ Migrated ${threadIds.length} threads to ${newName}`);
    } else {
      console.log(`  ⚪ ${oldName} → ${newName} (0 emails)`);
    }

    try {
      gog(['gmail', 'labels', 'delete', oldName, '--force', '--json']);
      console.log(`  🗑️  Deleted old label: ${oldName}`);
    } catch (e) {
      console.log(`  ⚠️  Could not delete ${oldName}: ${(e.stderr || e.message || '').toString().trim()}`);
    }
  }

  console.log('\n═══════════════════════');
  console.log(dryRun ? '✅ Label migration dry-run complete.' : '✅ Label migration complete.');
  if (dryRun) console.log('Run without --dry-run to execute');
}

try {
  main();
} catch (e) {
  console.error(`错误：${(e.stderr || e.message || '').toString().trim()}`);
  console.error('提示：需先授权 gog auth add <你的gmail> --services gmail --gmail-scope full --extra-scopes https://www.googleapis.com/auth/gmail.labels --force-consent');
  process.exit(1);
}
