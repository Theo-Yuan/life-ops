/**
 * Apply all Gmail filters to existing inbox emails.
 * For each filter: search inbox with the same criteria, then apply the same actions.
 */
const { google } = require('googleapis');
const fs = require('fs');
const path = require('path');

const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
const OAUTH_PATH = process.env.GMAIL_OAUTH_PATH || 
  path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');

async function getAuth() {
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
  const oauthKeys = JSON.parse(fs.readFileSync(OAUTH_PATH, 'utf8'));
  const { client_id, client_secret } = oauthKeys.installed || oauthKeys.web;
  
  const auth = new google.auth.OAuth2(client_id, client_secret);
  auth.setCredentials(credentials);
  return auth;
}

async function applyFilterToInbox(auth, filter) {
  const gmail = google.gmail({ version: 'v1', auth });
  const criteria = filter.criteria;
  const action = filter.action || {};
  
  // Build search query from filter criteria
  const parts = [];
  if (criteria.from) parts.push(`from:(${criteria.from})`);
  if (criteria.to) parts.push(`to:(${criteria.to})`);
  if (criteria.subject) parts.push(`subject:"${criteria.subject}"`);
  if (criteria.query) parts.push(`(${criteria.query})`);
  if (criteria.hasAttachment) parts.push('has:attachment');
  if (criteria.excludeChats) parts.push('-in:chats');
  
  const query = `in:inbox ${parts.join(' ')}`.trim();
  
  let totalProcessed = 0;
  let pageToken = null;
  
  while (true) {
    try {
      const res = await gmail.users.messages.list({
        userId: 'me',
        q: query,
        maxResults: 500,
        pageToken: pageToken || undefined,
      });
      
      const messages = res.data.messages || [];
      if (messages.length === 0) break;
      
      const ids = messages.map(m => m.id);
      
      // Batch modify in chunks of 500
      for (let i = 0; i < ids.length; i += 500) {
        const batch = ids.slice(i, i + 500);
        try {
          await gmail.users.messages.batchModify({
            userId: 'me',
            requestBody: {
              ids: batch,
              addLabelIds: action.addLabelIds || [],
              removeLabelIds: action.removeLabelIds || [],
            },
          });
          totalProcessed += batch.length;
        } catch (e) {
          // Rate limit - wait and retry
          if (e.code === 429 || (e.errors && e.errors[0]?.reason === 'rateLimitExceeded')) {
            console.log(`  Rate limited, waiting 2s...`);
            await new Promise(r => setTimeout(r, 2000));
            i -= 500; // retry this batch
            continue;
          }
          console.error(`  Error batch modifying: ${e.message}`);
        }
        // Small delay between batches
        await new Promise(r => setTimeout(r, 200));
      }
      
      pageToken = res.data.nextPageToken;
      if (!pageToken) break;
      
      // Delay between pages
      await new Promise(r => setTimeout(r, 300));
    } catch (e) {
      if (e.code === 429 || (e.errors && e.errors[0]?.reason === 'rateLimitExceeded')) {
        console.log(`  Rate limited on search, waiting 3s...`);
        await new Promise(r => setTimeout(r, 3000));
        continue;
      }
      console.error(`  Search error for query "${query}": ${e.message}`);
      break;
    }
  }
  
  return totalProcessed;
}

function filterDescription(filter) {
  const c = filter.criteria || {};
  const a = filter.action || {};
  const parts = [];
  if (c.from) parts.push(`from:${c.from}`);
  if (c.subject) parts.push(`subject:${c.subject}`);
  if (c.query) parts.push(`q:${c.query}`);
  const labels = [...(a.addLabelIds || []).map(l => `+${l}`), ...(a.removeLabelIds || []).map(l => `-${l}`)];
  return `${parts.join(', ') || '?'} → [${labels.join(', ')}]`;
}

async function main() {
  console.log('🔐 Authenticating...');
  const auth = await getAuth();
  const gmail = google.gmail({ version: 'v1', auth });
  
  console.log('📋 Fetching filters...');
  const filtersRes = await gmail.users.settings.filters.list({ userId: 'me' });
  const filters = filtersRes.data.filter || [];
  console.log(`Found ${filters.length} filters.\n`);
  
  let grandTotal = 0;
  const results = [];
  
  for (let i = 0; i < filters.length; i++) {
    const f = filters[i];
    const desc = filterDescription(f);
    console.log(`[${i + 1}/${filters.length}] ${desc}`);
    
    const count = await applyFilterToInbox(auth, f);
    results.push({ id: f.id, description: desc, processed: count });
    grandTotal += count;
    
    if (count > 0) console.log(`  ✅ Processed ${count} emails`);
    else console.log(`  ⚪ No unprocessed matches found`);
  }
  
  console.log(`\n📊 Summary:`);
  console.log(`   Total filters applied: ${filters.length}`);
  console.log(`   Total emails processed: ${grandTotal}`);
  
  // Check remaining inbox
  console.log(`\n📬 Checking inbox status...`);
  const inboxRes = await gmail.users.labels.get({ userId: 'me', id: 'INBOX' });
  console.log(`   Remaining in inbox: ${inboxRes.data.messagesTotal} (${inboxRes.data.messagesUnread} unread)`);
  
  // Get unclassified inbox samples
  console.log(`\n🔍 Sampling unclassified inbox emails...`);
  const sampleRes = await gmail.users.messages.list({
    userId: 'me',
    q: 'in:inbox',
    maxResults: 20,
  });
  
  if (sampleRes.data.messages) {
    console.log(`   Sample of ${sampleRes.data.messages.length} remaining inbox emails:`);
    for (const msg of sampleRes.data.messages) {
      try {
        const detail = await gmail.users.messages.get({ userId: 'me', id: msg.id, format: 'metadata', metadataHeaders: ['From', 'Subject', 'Date'] });
        const headers = detail.data.payload.headers;
        const from = headers.find(h => h.name === 'From')?.value || '?';
        const subject = headers.find(h => h.name === 'Subject')?.value || '?';
        console.log(`   📧 ${from.substring(0, 60)} | ${subject.substring(0, 60)}`);
      } catch (e) {
        // skip
      }
    }
  }
}

main().catch(console.error);
