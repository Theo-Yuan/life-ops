#!/bin/bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MONOREPO_ROOT="$(git -C "$PROJECT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$PROJECT_DIR")"
TMP="$PROJECT_DIR/tmp"
mkdir -p "$TMP"

TODAY=$(date +%Y-%m-%d)

echo "[$(date '+%H:%M:%S')] Fetching emails..." >&2
FETCH_OUTPUT=$(/Users/theoyuan/.nvm/versions/node/v23.3.0/bin/node "$PROJECT_DIR/scripts/fetch-emails.cjs" 2>/dev/null)
OK=$(echo "$FETCH_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',False))" 2>/dev/null || echo "false")

if [ "$OK" != "True" ]; then
    echo "[$(date '+%H:%M:%S')] FATAL: fetch failed" >&2
    exit 1
fi

TOTAL=$(echo "$FETCH_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null)
echo "[$(date '+%H:%M:%S')] Fetched $TOTAL emails → $TMP/emails.json" >&2

cat > "$TMP/prompt.txt" <<'EOF'
你是邮件助手。请阅读 emails.json，生成今日邮件摘要并发送到 Discord 私信（target="f1andre8472"）。

## 数据
/tmp/emails.json 的完整路径是：EMAILS_JSON_PATH
请先读取该文件。

## 任务
1. 先写一段总体摘要（2-3句话），概括今天的邮件情况：主要是什么类型、有没有异常或需要关注的事
2. 重要邮件：按 category 分组，逐封列出 sender + subject + 结合 body 的1-2句内容总结
3. 其他邮件：按 category 分组，每封仅 sender + subject
4. 按以下格式生成（Discord markdown）：

```
📊 𝗗𝗮𝗶𝗹𝘆 𝗗𝗶𝗴𝗲𝘀𝘁  ·  {date}
{总体摘要段落}

━━━━━━━━━━━━━━━━━━━━
🏦 𝗙𝗶𝗻𝗮𝗻𝗰𝗲  ·  {n}封
━━━━━━━━━━━━━━━━━━━━
🔴 ZA Bank — ✅ 你已转出USD 1,000.00
   通过CHATS转出至108***7005，16:41执行
🔴 ZA Bank — 👌 外汇交易已完成
   卖出HKD 15,745 → USD 2,000，汇率7.87
✅ ZA Bank — 更改转出限额
   已上调登记收款人转出限额

━━━━━━━━━━━━━━━━━━━━
✈️ 𝗧𝗿𝗮𝘃𝗲𝗹  ·  2封
━━━━━━━━━━━━━━━━━━━━
🔴 Korean Air — 6月电子账单

━━━━━━━━━━━━━━━━━━━━
📰 𝗡𝗲𝘄𝘀𝗹𝗲𝘁𝘁𝗲𝗿𝘀 ×3  📱 𝗦𝗼𝗰𝗶𝗮𝗹 ×5  📚 𝗟𝗲𝗮𝗿𝗻𝗶𝗻𝗴 ×2
━━━━━━━━━━━━━━━━━━━━
· NYT — Opinion Today: These 25 items...
· LinkedIn — 12位会员浏览了您的档案
· Codecademy — 50% off Pro ends tomorrow
```

◆ 重要类别用粗体标题 + 分隔线，每封带 🔴未读/✅已读 标记
◆ 不重要类别合并到同一分隔线下，紧凑排列
◆ 用 emoji 区分类别：🏦Finance ✈️Travel 💻Dev ❤️Health 📰Newsletters 📱Social 📚Learning 🛒Shopping 📢Ads
◆ 总体摘要用正常字体，不加大标题
◆ 金额、时间、汇率等关键数据必须保留
◆ 如有异常（定投失败、大额转账、安全提醒），在总体摘要中提及

5. 发送到 target="f1andre8472"（Discord 私信），一条消息不超过 1900 字符
6. 输出 Done

## 约束
- 数据以文件为准，不要编造
- 中文输出（类别名用英文原样）
- 正文中的交易金额、时间等关键信息务必保留
- 不重要邮件仅需 sender + subject，无需总结
- 排版美观：对齐、emoji 前置、分隔线清晰
EOF

EMAILS_PATH="$TMP/emails.json"
PROMPT=$(sed "s|EMAILS_JSON_PATH|$EMAILS_PATH|g" "$TMP/prompt.txt")

MAX_ATTEMPTS=2
TIMEOUT_SEC=300

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "[$(date '+%H:%M:%S')] Attempt $attempt/$MAX_ATTEMPTS: opencode..." >&2
    opencode run --pure --auto --dir "$MONOREPO_ROOT" --title "邮件摘要 $TODAY" "$PROMPT" &
    PID=$!
    elapsed=0
    while [ $elapsed -lt $TIMEOUT_SEC ]; do
        if ! kill -0 $PID 2>/dev/null; then
            wait $PID; EXIT=$?
            if [ $EXIT -eq 0 ]; then
                echo "[$(date '+%H:%M:%S')] Done" >&2
                exit 0
            fi
            echo "[$(date '+%H:%M:%S')] Failed (exit=$EXIT)" >&2
            break
        fi
        sleep 2; elapsed=$((elapsed + 2))
    done
    if kill -0 $PID 2>/dev/null; then kill $PID 2>/dev/null; wait $PID 2>/dev/null || true; fi
    [ $attempt -lt $MAX_ATTEMPTS ] && sleep 10
done

echo "[$(date '+%H:%M:%S')] FATAL: all attempts failed" >&2
exit 1
