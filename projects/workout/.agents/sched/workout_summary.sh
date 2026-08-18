#!/bin/bash
set -eumo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
MONOREPO_ROOT="$(git -C "$PROJECT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$PROJECT_DIR")"
source "$MONOREPO_ROOT/.agents/discord.config" 2>/dev/null || true
cd "$PROJECT_DIR"

TODAY=$(date +%Y-%m-%d)
DIGEST="$SCRIPT_DIR/.summary-$TODAY.txt"
PROMPT_FILE=$(mktemp /tmp/workout-summary-prompt-$$-XXXXXX.txt)
trap 'rm -f "$PROMPT_FILE" "$DIGEST"' EXIT

# 获取今日训练数据 + 最近同类对比 + profile（供 agent 生成个性化摘要）
SUMMARY_JSON=$(python3 .agents/sched/workout_summary.py --data 2>/dev/null)
if [ -z "$SUMMARY_JSON" ]; then
    echo "FATAL: Cannot get summary data" >&2
    exit 1
fi

# 检查是否有训练数据
HAS_DATA=$(printf '%s' "$SUMMARY_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print('no' if d.get('error') else 'yes')")
if [ "$HAS_DATA" = "no" ]; then
    echo "今日 ($TODAY) 无训练数据，不发送摘要"
    exit 0
fi

# 提取今日训练摘要（动作 + 组次）
TRAIN_LINES=$(printf '%s' "$SUMMARY_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"标题: {d['title']} | 时长: {d['duration_min']}min\")
print('动作:')
for m in d['movements']:
    sets = [f\"{s['weight']}kg×{s['reps']}\" if s['weight'] else f\"自重×{s['reps']}\" for s in m['sets'] if s.get('done')]
    if sets:
        print(f\"  {m['name']}: {' + '.join(sets)}\")
")

# 提取最近同类训练（供对比）
RECENT_LINES=$(printf '%s' "$SUMMARY_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for r in d.get('recent_same_type', []):
    moves = ', '.join(f\"{m['name']}({m['sets']}组)\" for m in r.get('movements', []))
    print(f\"  {r['datestr']}  {r['title']}  {r['duration_min']}min  {moves}\")
")

cat > "$PROMPT_FILE" <<'PROMPT_EOF'
你是训记训练助手。请根据今日训练数据，生成个性化的训练完成摘要并**写入文件**（不要发送）。

## 今日训练
TRAIN_PLACEHOLDER

## 最近同类训练（对比参考）
RECENT_PLACEHOLDER

## 你的任务
1. 读取 projects/workout/.agents/profile.md 了解用户偏好、当前阶段（减载周等）
2. 生成训练完成摘要
3. 结合 profile 和同类历史给出个性化点评（如进步/持平/退步、是否达标、建议）
4. 把最终消息完整写入文件：__DIGEST_PATH__（只写纯文本，不要加代码块标记）

## 消息格式（严格遵循）
- 用中文，简洁有力
- 列出今日主要动作和组次
- 给出 vs 上次同类训练的简短对比（如有数据）
- 结合 profile 给一句个性化建议
- 消息不超过 800 字符

示例格式：
✅ **今日训练完成 — 推日**

📅 2026-07-28 | ⏱ 45分钟

1. 杠铃卧推  80kg×5 + 85kg×5 + 85kg×4
2. 器械坐姿推举  40kg×10 ×3
3. 绳索侧平举  12kg×12 ×3

📊 正式组：12 组 · 100 次

📈 卧推 80kg×5 → 85kg×5（+5kg，进步）
💡 减载周保持 RPE 5-6，不要力竭

## 约束
- 数据以脚本提供的为准，不要编造
- 减载周务必提醒「不要力竭」
- **不要调用任何 MCP 工具（尤其是 discord），只做读取、生成摘要、写文件**
PROMPT_EOF

TMP_PROMPT2=$(mktemp /tmp/workout-summary-prompt2-$$-XXXXXX.txt)
while IFS= read -r line; do
    if [[ "$line" == "TRAIN_PLACEHOLDER" ]]; then
        echo "$TRAIN_LINES" >> "$TMP_PROMPT2"
    elif [[ "$line" == "RECENT_PLACEHOLDER" ]]; then
        echo "$RECENT_LINES" >> "$TMP_PROMPT2"
    else
        echo "$line" >> "$TMP_PROMPT2"
    fi
done < "$PROMPT_FILE"
mv "$TMP_PROMPT2" "$PROMPT_FILE"
sed -i '' "s|__DIGEST_PATH__|$DIGEST|g" "$PROMPT_FILE"

MAX_ATTEMPTS=2
TIMEOUT_SEC=300
RETRY_DELAY=10

OP_EXIT_CODE=1
for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "[$(date '+%H:%M:%S')] Attempt $attempt/$MAX_ATTEMPTS: launching opencode..." >&2

    opencode run \
        --pure \
        --auto \
        --dir "$MONOREPO_ROOT" \
        --title "训练摘要 $TODAY" \
        "$(cat "$PROMPT_FILE")" &
    OP_PID=$!

    elapsed=0
    while [ $elapsed -lt $TIMEOUT_SEC ]; do
        if ! kill -0 $OP_PID 2>/dev/null; then
            wait $OP_PID
            OP_EXIT_CODE=$?
            break 2
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    if kill -0 $OP_PID 2>/dev/null; then
        echo "[$(date '+%H:%M:%S')] ✗ opencode timeout after ${TIMEOUT_SEC}s (attempt $attempt)" >&2
        kill -TERM -$OP_PID 2>/dev/null || kill -TERM $OP_PID 2>/dev/null || true
        sleep 2
        kill -KILL -$OP_PID 2>/dev/null || kill -KILL $OP_PID 2>/dev/null || true
        wait $OP_PID 2>/dev/null || true
    fi

    [ $attempt -lt $MAX_ATTEMPTS ] && sleep $RETRY_DELAY
done

if [ "$OP_EXIT_CODE" -ne 0 ]; then
    echo "FATAL: opencode failed after $MAX_ATTEMPTS attempts (exit=$OP_EXIT_CODE)" >&2
    exit 1
fi

if [ -s "$DIGEST" ]; then
    python3 "$SCRIPT_DIR/send_discord.py" "$DIGEST" "$DISCORD_WORKOUT_CHANNEL_ID" \
        || { echo "FATAL: send failed" >&2; exit 1; }
else
    echo "FATAL: digest file is empty" >&2
    exit 1
fi

echo "Success"
