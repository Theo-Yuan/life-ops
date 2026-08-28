#!/usr/bin/env node
// cleanup-old.cjs — 用 gog CLI 清理旧邮件（验证码/登录通知/密码重置等）。--dry-run 仅预览。
const gog = require('./lib/gog.cjs');

const CLEANUP_RULES = [
  { query: 'subject:"verification code" OR subject:"验证码" OR subject:"Verification Code" older_than:1d', description: '验证码' },
  { query: 'from:accounts.google.com subject:"Security alert" older_than:7d', description: 'Google 安全提醒', archive: true },
  { query: 'subject:"login" older_than:30d', description: '登录通知(30天前)', archive: true },
  { query: 'subject:"password" OR subject:"密码" older_than:3d', description: '密码重置' },
  { query: 'subject:"your code" OR subject:"security code" older_than:1d', description: '一次性验证码' },
  { query: 'subject:"new device" OR subject:"新设备" older_than:7d', description: '新设备登录(7天前)', archive: true },
];

function searchMatches(query) {
  const res = gog(['gmail', 'messages', 'search', query, '--max', '500', '--json', '--readonly', '--no-input']);
  return (res && res.messages) || [];
}

function main() {
  const dryRun = process.argv.includes('--dry-run');
  console.log(`${dryRun ? '🔍 DRY RUN (preview only)' : '🗑️ DELETE MODE'}\n`);
  let grandTotal = 0;

  for (const rule of CLEANUP_RULES) {
    const matches = searchMatches(rule.query);
    const n = matches.length;
    if (n === 0) {
      console.log(`\n📋 ${rule.description}: ⚪ No matches`);
      continue;
    }

    if (dryRun) {
      console.log(`\n📋 ${rule.description}: ${n} 封 (${rule.archive ? '📦 archive' : '🗑️ trash'})`);
      for (const m of matches.slice(0, 5)) {
        console.log(`    📧 ${(m.from || '?').substring(0, 40)} | ${(m.subject || '?').substring(0, 50)}`);
      }
      if (n > 5) console.log(`    ... and ${n - 5} more`);
    } else {
      const verb = rule.archive ? 'archive' : 'trash';
      gog(['gmail', verb, `--query=${rule.query}`, `--max=${n}`, '--force', '--json']);
      console.log(`\n📋 ${rule.description}: ${rule.archive ? '📦 Archived' : '🗑️ Trashed'} ${n} emails`);
    }
    grandTotal += n;
  }

  console.log('\n═══════════════════════');
  console.log(`${dryRun ? 'Would process' : 'Processed'} ${grandTotal} total`);
  if (dryRun) console.log('Run without --dry-run to execute');
}

try {
  main();
} catch (e) {
  console.error(`错误：${(e.stderr || e.message || '').toString().trim()}`);
  console.error('提示：需先授权 gog auth add <你的gmail> --services gmail --gmail-scope full --extra-scopes https://www.googleapis.com/auth/gmail.labels --force-consent');
  process.exit(1);
}
