#!/bin/bash
set -eumo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MONOREPO_ROOT="$(git -C "$PROJECT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$PROJECT_DIR")"
source "$MONOREPO_ROOT/.agents/discord.config" 2>/dev/null || true
TMP="$PROJECT_DIR/tmp"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$TMP" "$LOG_DIR"

TODAY=$(date +%Y-%m-%d)
LOG="$LOG_DIR/summary-$(date +%Y%m%d-%H%M%S).log"
DIGEST="$TMP/digest.txt"
PROMPT_FILE=$(mktemp /tmp/email-summary-prompt-$$-XXXXXX.txt)
trap 'rm -f "$PROMPT_FILE"' EXIT

log() { echo "[$(date '+%F %T')] $*" >>"$LOG"; }

# ── 1. fetch emails (via gog CLI) ─────────────────────────────────
log "fetching emails..."
FETCH_OUTPUT=$(/Users/theoyuan/.nvm/versions/node/v23.3.0/bin/node "$PROJECT_DIR/scripts/gog-fetch.cjs" 2>&1) || {
    log "FATAL: gog-fetch.cjs failed"
    echo "$FETCH_OUTPUT" >>"$LOG"
    case "$FETCH_OUTPUT" in
        *auth*|*invalid_grant*|*expired*|*credential*) log "HINT: Gmail 授权失效。重新授权: gog auth add <你的gmail邮箱> --services gmail --gmail-scope full --extra-scopes https://www.googleapis.com/auth/gmail.labels --force-consent" ;;
    esac
    exit 1
}
OK=$(echo "$FETCH_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',False))" 2>/dev/null || echo "false")
if [ "$OK" != "True" ]; then
    log "FATAL: fetch returned ok=false"
    echo "$FETCH_OUTPUT" >>"$LOG"
    exit 1
fi
TOTAL=$(echo "$FETCH_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
log "fetched $TOTAL emails"

# ── 2. compose prompt (write to file only, no MCP) ────────────────
EMAILS_PATH="$TMP/emails.json"
cat > "$PROMPT_FILE" <<PROMPT_EOF
你是邮件助手。请阅读 emails.json，生成今日邮件摘要并**写入文件**（不要发送）。

## 数据
请先读取文件：$EMAILS_PATH

## 任务
1. 先写一段总体摘要（2-3句话），概括今天的邮件情况：主要是什么类型、有没有异常或需要关注的事
2. 重要邮件：按 category 分组，逐封列出 sender + subject + 结合 body 的1-2句内容总结
3. 其他邮件：按 category 分组，每封仅 sender + subject
4. 按以下格式生成（Discord markdown）：

\`\`\`
📊 𝗗𝗮𝗶𝗹𝘆 𝗗𝗶𝗴𝗲𝘀𝘁  ·  {date}
{总体摘要段落}

━━━━━━━━━━━━━━━━━━━━
🏦 𝗙𝗶𝗻𝗮𝗻𝗰𝗲  ·  {n}封
━━━━━━━━━━━━━━━━━━━━
🔴 ZA Bank — ✅ 你已转出USD 1,000.00
   通过CHATS转出至108***7005，16:41执行
🔴 ZA Bank — 👌 外汇交易已完成
   卖出HKD 15,745 → USD 2,000，汇率7.87

━━━━━━━━━━━━━━━━━━━━
📰 𝗡𝗲𝘄𝘀𝗹𝗲𝘁𝘁𝗲𝗿𝘀 ×3  📱 𝗦𝗼𝗰𝗶𝗮𝗹 ×5  📚 𝗟𝗲𝗮𝗿𝗻𝗶𝗻𝗴 ×2
━━━━━━━━━━━━━━━━━━━━
· NYT — Opinion Today: These 25 items...
· LinkedIn — 12位会员浏览了您的档案
\`\`\`

◆ 重要类别用粗体标题 + 分隔线，每封带 🔴未读/✅已读 标记
◆ 不重要类别合并到同一分隔线下，紧凑排列
◆ 用 emoji 区分类别：🏦Finance ✈️Travel 💻Dev ❤️Health 📰Newsletters 📱Social 📚Learning 🛒Shopping 📢Ads
◆ 总体摘要用正常字体，不加大标题
◆ 金额、时间、汇率等关键数据必须保留
◆ 如有异常（定投失败、大额转账、安全提醒），在总体摘要中提及

5. 把最终消息的完整文本写入文件：$DIGEST（只写纯文本，不要加代码块标记）

## 约束
- 数据以文件为准，不要编造
- 中文输出（类别名用英文原样）
- 正文中的交易金额、时间等关键信息务必保留
- 不重要邮件仅需 sender + subject，无需总结
- 排版美观：对齐、emoji 前置、分隔线清晰
- **不要调用任何 MCP 工具（尤其是 discord），只做读取、生成摘要、写文件**
PROMPT_EOF

# ── 3. compose with opencode ───────────────────────────────────────
MAX_ATTEMPTS=2
TIMEOUT_SEC=600
RETRY_DELAY=10

OP_EXIT_CODE=1
for attempt in $(seq 1 $MAX_ATTEMPTS); do
    log "opencode attempt $attempt/$MAX_ATTEMPTS"
    opencode run \
        --pure \
        --auto \
        --dir "$MONOREPO_ROOT" \
        --title "邮件摘要 $TODAY" \
        "$(cat "$PROMPT_FILE")" >>"$LOG" 2>&1 &
    OP_PID=$!

    elapsed=0
    while [ $elapsed -lt $TIMEOUT_SEC ]; do
        if ! kill -0 $OP_PID 2>/dev/null; then
            OP_EXIT_CODE=0
            wait $OP_PID || OP_EXIT_CODE=$?
            break 2
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    if kill -0 $OP_PID 2>/dev/null; then
        log "opencode timeout after ${TIMEOUT_SEC}s (attempt $attempt)"
        # kill entire process group so no orphaned MCP/agent holds the log pipe
        kill -TERM -$OP_PID 2>/dev/null || kill -TERM $OP_PID 2>/dev/null || true
        sleep 2
        kill -KILL -$OP_PID 2>/dev/null || kill -KILL $OP_PID 2>/dev/null || true
        wait $OP_PID 2>/dev/null || true
    fi

    [ $attempt -lt $MAX_ATTEMPTS ] && sleep $RETRY_DELAY
done

if [ "$OP_EXIT_CODE" -ne 0 ]; then
    log "ERROR: opencode failed after $MAX_ATTEMPTS attempts (exit=$OP_EXIT_CODE)"
fi

# ── 4. send digest ─────────────────────────────────────────────────
if [ -s "$DIGEST" ]; then
    log "sending digest..."
    python3 "$SCRIPT_DIR/send_discord.py" "$DIGEST" "$DISCORD_USER_ID" >>"$LOG" 2>&1 \
        || { log "FATAL: send failed"; exit 1; }
else
    log "FATAL: digest file is empty"
    exit 1
fi

log "done"
