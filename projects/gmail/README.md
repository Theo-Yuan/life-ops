# Gmail Organizer

AI-assisted Gmail inbox organization with automatic labeling, filtering, and daily summaries.

## Structure

```
scripts/
├── apply-filters.cjs   — Apply all Gmail filters to existing inbox emails
├── migrate-labels.cjs  — Migrate old labels to new hierarchy, delete old labels
├── check-inbox.cjs     — Analyze inbox sender composition
└── daily-summary.cjs   — Daily email report (last 24h, by category, important highlights)

config/
└── labels.json         — Label hierarchy & filter rules documentation
```

## Prerequisites

- Node.js 18+
- Google Cloud project with Gmail API enabled
- OAuth credentials at `~/.gmail-mcp/gcp-oauth.keys.json`
- Authenticated token at `~/.gmail-mcp/credentials.json`

## Usage

```bash
# Apply filters to existing inbox
node scripts/apply-filters.cjs

# Migrate old labels to new system
node scripts/migrate-labels.cjs

# Check inbox composition
node scripts/check-inbox.cjs

# Daily email summary
node scripts/daily-summary.cjs
```

## Label System

| Category | Important | Action |
|---|---|---|
| Finance/* | ✅ | Label + Keep in inbox |
| Travel/* | ✅ | Label + Keep in inbox |
| Dev/* | ✅ | Label + Keep in inbox |
| Health | ✅ | Label + Keep in inbox |
| Newsletters/* | ❌ | Label + Archive |
| Social/* | ❌ | Label + Archive |
| Learning/* | ❌ | Label + Archive |
| Shopping | ❌ | Label + Archive |
| Ads | ❌ | Label + Archive |

## MCP Server

This project was set up alongside `pouyanafisi/gmail-mcp` for interactive AI-driven email management.

Config location: `~/.config/opencode/opencode.json`
Server path: `~/.gmail-mcp-server/`
