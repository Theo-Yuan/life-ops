const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
const OAUTH_PATH = process.env.GMAIL_OAUTH_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');

const CLEANUP_RULES = [
  // Verification codes - delete after 1 day
  { query: 'subject:"verification code" OR subject:"验证码" OR subject:"Verification Code" older_than:1d', description: '验证码' },
  // Security alerts - archive after 7 days
  { query: 'from:accounts.google.com subject:"Security alert" older_than:7d', description: 'Google 安全提醒', archive: true },
  { query: 'subject:"login" older_than:30d', description: '登录通知(30天前)', archive: true },
  // Password reset - delete after 3 days
  { query: 'subject:"password" OR subject:"密码" older_than:3d', description: '密码重置' },
  // One-time codes
  { query: 'subject:"your code" OR subject:"security code" older_than:1d', description: '一次性验证码' },
  // Device verification
  { query: 'subject:"new device" OR subject:"新设备" older_than:7d', description: '新设备登录(7天前)', archive: true },
];

async function getAuth() {
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
  const oauthKeys = JSON.parse(fs.readFileSync(OAUTH_PATH, 'utf8'));
  const { client_id, client_secret } = oauthKeys.installed || oauthKeys.web;
  const auth = new google.auth.OAuth2(client_id, client_secret);
  auth.setCredentials(credentials);
  return auth;
}

async function main() {
  const dryRun = process.argv.includes('--dry-run');
  const mode = dryRun ? '🔍 DRY RUN (preview only)' : '🗑️  DELETE MODE';
  console.log(`${mode}\n`);

  const auth = await getAuth();
  const gmail = google.gmail({ version: 'v1', auth });

  let grandTotal = 0;

  for (const rule of CLEANUP_RULES) {
    console.log(`\n📋 ${rule.description}: "${rule.query}"`);
    
    const ids = [];
    let pageToken = null;
    
    while (true) {
      try {
        const res = await gmail.users.messages.list({
          userId: 'me', q: rule.query, maxResults: 500,
          pageToken: pageToken || undefined,
        });
        const messages = res.data.messages || [];
        ids.push(...messages.map(m => m.id));
        pageToken = res.data.nextPageToken;
        if (!pageToken) break;
        await new Promise(r => setTimeout(r, 200));
      } catch (e) {
        if (e.code === 429) { await new Promise(r => setTimeout(r, 3000)); continue; }
        console.error(`  Search error: ${e.message}`);
        break;
      }
    }

    if (ids.length === 0) {
      console.log(`  ⚪ No matches`);
      continue;
    }

    console.log(`  Found ${ids.length} emails`);

    if (dryRun) {
      // Show samples
      const samples = ids.slice(0, 5);
      for (const id of samples) {
        try {
          const detail = await gmail.users.messages.get({
            userId: 'me', id, format: 'metadata',
            metadataHeaders: ['From', 'Subject', 'Date'],
          });
          const h = detail.data.payload.headers;
          const from = h.find(x => x.name === 'From')?.value || '?';
          const subject = h.find(x => x.name === 'Subject')?.value || '?';
          console.log(`    📧 ${from.substring(0, 40)} | ${subject.substring(0, 50)}`);
        } catch (e) { /* skip */ }
      }
      if (ids.length > 5) console.log(`    ... and ${ids.length - 5} more`);
    } else {
      // Trash in batches of 500
      for (let i = 0; i < ids.length; i += 500) {
        const batch = ids.slice(i, i + 500);
        try {
          if (rule.archive) {
            await gmail.users.messages.batchModify({
              userId: 'me',
              requestBody: { ids: batch, removeLabelIds: ['INBOX'] },
            });
          } else {
            await gmail.users.messages.batchModify({
              userId: 'me',
              requestBody: { ids: batch, addLabelIds: ['TRASH'], removeLabelIds: ['INBOX'] },
            });
          }
        } catch (e) {
          if (e.code === 429) { await new Promise(r => setTimeout(r, 2000)); i -= 500; continue; }
          console.error(`  Error: ${e.message}`);
        }
        await new Promise(r => setTimeout(r, 200));
      }
      console.log(`  ${rule.archive ? '📦 Archived' : '🗑️  Trashed'} ${ids.length} emails`);
    }
    
    grandTotal += ids.length;
  }

  console.log(`\n═══════════════════════`);
  console.log(`${dryRun ? 'Would process' : 'Processed'} ${grandTotal} total`);
  if (dryRun) console.log('Run without --dry-run to execute');
}

main().catch(console.error);
