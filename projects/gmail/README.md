# Gmail Organizer

AI-assisted Gmail inbox organization with automatic labeling, filtering, and daily summaries.
All scripts use the [`gog`](https://github.com/openclaw/gogcli) CLI — no `googleapis` dependency.

## Structure

```
scripts/
├── gog-fetch.cjs       — 每日摘要抓取（生成 tmp/emails.json）
├── apply-filters.cjs   — 将现有 Gmail 过滤器重新应用到收件箱（线程级）
├── migrate-labels.cjs  — 旧标签 → 新标签迁移，删除旧标签
├── check-inbox.cjs     — 分析收件箱发件人构成
└── cleanup-old.cjs     — 清理旧邮件（验证码/登录通知等）

sched/
└── email-summary.sh    — 每日摘要流水线：gog-fetch.cjs → opencode agent → Discord

config/
└── labels.json         — Label hierarchy & filter rules documentation
```

## Prerequisites

- [`gog`](https://github.com/openclaw/gogcli) CLI：`brew install openclaw/tap/gogcli`
- OAuth 授权一次（覆盖读 + 改标签 + 过滤器 + 删除标签）：

```bash
gog auth add <你的gmail邮箱> --services gmail --gmail-scope full \
  --extra-scopes https://www.googleapis.com/auth/gmail.labels --force-consent
```

- token 存 macOS Keychain，gog 自动续期；验证：`gog auth doctor --check`

## Usage

```bash
# 每日摘要（agent 主导，发送到 Discord）
bash sched/email-summary.sh

# 手动抓取最近 24h 邮件 → tmp/emails.json
node scripts/gog-fetch.cjs

# 将现有过滤器重新应用到收件箱
node scripts/apply-filters.cjs

# 旧标签 → 新标签迁移
node scripts/migrate-labels.cjs

# 分析收件箱发件人构成
node scripts/check-inbox.cjs

# 清理旧邮件（--dry-run 仅预览，不加则执行）
node scripts/cleanup-old.cjs --dry-run
node scripts/cleanup-old.cjs
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
