#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MONOREPO_ROOT="$(git -C "$PROJECT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$PROJECT_DIR")"
source "$SCRIPT_DIR/digest_config"

TODAY=$(date +%Y-%m-%d)
CANDIDATES=$(mktemp /tmp/digest-cand-$$-XXXXXX.txt)
DIGEST=$(mktemp /tmp/digest-out-$$-XXXXXX.txt)
PROMPT_FILE=$(mktemp /tmp/digest-prompt-$$-XXXXXX.txt)
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/digest-$(date +%Y%m%d-%H%M%S).log"
trap 'rm -f "$CANDIDATES" "$DIGEST" "$PROMPT_FILE"' EXIT

echo "[$(date '+%F %T')] fetch candidates" >>"$LOG"
python3 "$SCRIPT_DIR/digest_fetch.py" "$CANDIDATES" >>"$LOG" 2>&1

if [ ! -s "$CANDIDATES" ]; then
  echo "[$(date '+%F %T')] no candidates fetched (upstream unavailable), exiting gracefully" >>"$LOG"
  exit 0
fi

echo "[$(date '+%F %T')] curate with opencode" >>"$LOG"
cat > "$PROMPT_FILE" <<PROMPT_EOF
今天是 ${TODAY}。请从候选文章文件中挑选最值得阅读的文章，生成一份中英对照的每日推送。

候选文件路径: ${CANDIDATES}
每行格式：主题 | 标题 | 来源 | 时间 | 链接 | 摘要

## 任务
1. 通读所有候选文章，按"信息价值 + 与主题贴合度 + 来源多样性"挑选 6-10 篇（每个主题至少 2 篇）
2. 对每篇生成：英文标题 + 中文标题翻译 + 一句中文摘要（不超过 40 字，忠于原文）
3. 按主题分组输出，格式如下（纯文本）：

🌍 **世界新闻**
**英文标题** / 中文标题
中文一句话摘要
🔗 链接

4. 把最终推送文本完整写入文件: ${DIGEST}

## 约束
- 只使用候选文件里真实出现的文章，禁止编造标题或链接
- 摘要必须准确，不夸大、不夹带个人观点
- 输出只用纯文本，不要附加任务说明或代码块标记
- 不要调用任何 MCP 工具（尤其是 discord），只做筛选、翻译、写文件
PROMPT_EOF

MAX_ATTEMPTS=2
TIMEOUT_SEC=1800
RETRY_DELAY=10

OP_EXIT_CODE=1
for attempt in $(seq 1 $MAX_ATTEMPTS); do
  echo "[$(date '+%F %T')] opencode attempt $attempt/$MAX_ATTEMPTS" >>"$LOG"

  opencode run \
    --pure \
    --auto \
    --dir "$MONOREPO_ROOT" \
    --title "每日文章推送 $TODAY" \
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
    echo "[$(date '+%F %T')] opencode timeout after ${TIMEOUT_SEC}s (attempt $attempt)" >>"$LOG"
    kill $OP_PID 2>/dev/null
    sleep 2
    kill -KILL $OP_PID 2>/dev/null
    wait $OP_PID 2>/dev/null || true
  fi

  if [ $attempt -lt $MAX_ATTEMPTS ]; then
    sleep $RETRY_DELAY
  fi
done

if [ "$OP_EXIT_CODE" -ne 0 ]; then
  echo "ERROR: opencode failed after $MAX_ATTEMPTS attempts (exit=$OP_EXIT_CODE)" >>"$LOG"
fi

echo "[$(date '+%F %T')] send digest" >>"$LOG"
if [ -s "$DIGEST" ]; then
  python3 "$SCRIPT_DIR/send_discord.py" "$DIGEST" "$DISCORD_USER_ID" >>"$LOG" 2>&1
else
  echo "ERROR: digest file is empty" >>"$LOG"
  exit 1
fi

echo "[$(date '+%F %T')] done" >>"$LOG"
