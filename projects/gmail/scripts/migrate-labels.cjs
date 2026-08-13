const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
const OAUTH_PATH = process.env.GMAIL_OAUTH_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');

/** Old label → New label mapping. null = delete only (no migration). */
const MIGRATIONS = {
  // Social
  'linkedin': 'Social/LinkedIn',
  'twitch': 'Social/Twitch',
  'facebook': 'Social/Facebook',
  'feed/netflix': 'Social/Netflix',
  'feed': 'Social',
  // News
  'News': 'Newsletters/News',
  // Dev
  'mongodb': 'Dev/Database',
  'deeplearning.ai': 'Dev/AI',
  'AI': 'Dev/AI',
  'Real Python': 'Dev/Python',
  // Travel
  'tour/japan': 'Travel/Japan',
  'tour': 'Travel',
  // Finance
  'receipt': 'Finance/Receipt',
  // Other
  'advertisement': 'Ads',
  'google': 'Newsletters',
  'zoom': null,
  'Conversation History': null,
  '对话历史记录': null,
  'Notes': null,
};

async function getAuth() {
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
  const oauthKeys = JSON.parse(fs.readFileSync(OAUTH_PATH, 'utf8'));
  const { client_id, client_secret } = oauthKeys.installed || oauthKeys.web;
  const auth = new google.auth.OAuth2(client_id, client_secret);
  auth.setCredentials(credentials);
  return auth;
}

async function getAllMessageIds(gmail, labelId) {
  const ids = [];
  let pageToken = null;
  while (true) {
    try {
      const res = await gmail.users.messages.list({
        userId: 'me', labelIds: [labelId], maxResults: 500,
        pageToken: pageToken || undefined,
      });
      const messages = res.data.messages || [];
      ids.push(...messages.map(m => m.id));
      pageToken = res.data.nextPageToken;
      if (!pageToken) break;
      await new Promise(r => setTimeout(r, 200));
    } catch (e) {
      if (e.code === 429) { await new Promise(r => setTimeout(r, 3000)); continue; }
      console.error(`  List error: ${e.message}`);
      break;
    }
  }
  return ids;
}

async function main() {
  const auth = await getAuth();
  const gmail = google.gmail({ version: 'v1', auth });

  const labelsRes = await gmail.users.labels.list({ userId: 'me' });
  const labels = labelsRes.data.labels || [];
  const labelMap = {};
  for (const l of labels) labelMap[l.name] = l.id;
  
  // Also build reverse: id → name
  const idToName = {};
  for (const l of labels) idToName[l.id] = l.name;

  console.log('📋 Old label migration plan:\n');

  const entries = Object.entries(MIGRATIONS);
  for (let i = 0; i < entries.length; i++) {
    const [oldName, newName] = entries[i];
    const oldId = labelMap[oldName];
    const newId = newName ? labelMap[newName] : null;

    if (!oldId) {
      console.log(`[${i + 1}/${entries.length}] ⚪ ${oldName} — label not found, skipping`);
      continue;
    }

    // Get email count
    const labelInfo = await gmail.users.labels.get({ userId: 'me', id: oldId });
    const count = labelInfo.data.messagesTotal || 0;

    if (newId && count > 0) {
      console.log(`[${i + 1}/${entries.length}] 🔄 ${oldName} → ${newName} (${count} emails)`);
      
      const ids = await getAllMessageIds(gmail, oldId);
      if (ids.length === 0) { console.log(`  ⚪ No emails to migrate`); }
      
      // Batch add new label in chunks of 500
      for (let j = 0; j < ids.length; j += 500) {
        const batch = ids.slice(j, j + 500);
        try {
          await gmail.users.messages.batchModify({
            userId: 'me',
            requestBody: { ids: batch, addLabelIds: [newId] },
          });
        } catch (e) {
          if (e.code === 429 || (e.errors && e.errors[0]?.reason === 'rateLimitExceeded')) {
            console.log(`  Rate limited, retrying...`);
            await new Promise(r => setTimeout(r, 2000));
            j -= 500;
            continue;
          }
          console.error(`  Batch error: ${e.message}`);
        }
        await new Promise(r => setTimeout(r, 200));
      }
      console.log(`  ✅ Migrated ${ids.length} to ${newName}`);
    } else if (!newId) {
      console.log(`[${i + 1}/${entries.length}] ℹ️  ${oldName} (${count} emails) — keep/delete manually`);
      continue;
    } else {
      console.log(`[${i + 1}/${entries.length}] ⚪ ${oldName} → ${newName} (0 emails, delete)`);
    }

    // Delete old label (even if count > 0 — the emails now have the new label)
    try {
      await gmail.users.labels.delete({ userId: 'me', id: oldId });
      console.log(`  🗑️  Deleted old label: ${oldName}`);
    } catch (e) {
      console.log(`  ⚠️  Could not delete ${oldName}: ${e.message}`);
    }
    await new Promise(r => setTimeout(r, 300));
  }

  console.log('\n✅ Label migration complete.');
}

main().catch(console.error);
