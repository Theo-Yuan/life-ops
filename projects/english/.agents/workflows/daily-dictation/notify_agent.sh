#!/bin/bash
# notify_agent.sh — Agent 主导的每日听写打卡通知。
#
# notify.py --data 提供原始数据，opencode agent 结合 .agents/profile.md
# 生成个性化打卡消息并发送到 Discord（参考 workout_plan 的 workout_summary.sh）。
#
# Usage:
#   ./notify_agent.sh              # 使用今日日期
#   ./notify_agent.sh 2026-08-04   # 指定日期

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MONOREPO_ROOT="$(git -C "$PROJECT_DIR" rev-parse --show-toplevel 2>/dev/null || echo "$PROJECT_DIR")"
source "$MONOREPO_ROOT/.agents/discord.config" 2>/dev/null || true
cd "$PROJECT_DIR"

TODAY="${1:-$(date +%Y-%m-%d)}"

# 获取当日听写数据 + 趋势 + profile（供 agent 生成个性化打卡消息）
DATA_JSON=$(python3 .agents/workflows/daily-dictation/notify.py --data "$TODAY")
if [ -z "$DATA_JSON" ]; then
    echo "FATAL: Cannot get dictation data" >&2
    exit 1
fi

# 检查今日是否有听写活动
HAS_ACTIVITY=$(printf '%s' "$DATA_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('stats',{}).get('api_minutes',0) > 0 else 'no')")
if [ "$HAS_ACTIVITY" = "no" ]; then
    echo "今日 ($TODAY) 无听写活动，不发送打卡消息"
    exit 0
fi

# 提取当日听写摘要（时长 + 累计 + 趋势 + 最近练习）
DATA_LINES=$(printf '%s' "$DATA_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
s = d['stats']
t = d['trends']
print(f\"日期: {d['date']}\")
print(f\"今日听写: {s['api_minutes']}min\")
print(f\"总完成: {s['lesson_completions']} 课 | 累计 {s['active_time_hours']}h（{s['active_days']} 天）\")
print(f\"站点统计: 近 7 天 {s['last_7d_hours']}h · 近 30 天 {s['last_30d_hours']}h\")
print(f\"近 7 天听写: {t['last_7d_minutes']}min · 近 30 天: {t['last_30d_minutes']}min\")
print(f\"连续打卡: {t['streak_days']} 天\")
print('最近练习:')
for l in d.get('recent_lessons', []):
    print(f\"  [{l.get('category')}] {l.get('title')}\")
")

PROMPT_FILE=$(mktemp /tmp/daily-dictation-prompt-$$-XXXXXX.txt)
trap "rm -f $PROMPT_FILE" EXIT

cat > "$PROMPT_FILE" <<'PROMPT_EOF'
你是英语学习打卡助手。请根据今日听写数据，生成个性化的每日听写打卡消息并发送到 Discord。

## 今日听写数据
DATA_PLACEHOLDER

## 你的任务
1. 读取 projects/english/.agents/profile.md 了解用户目标（IELTS 6.5，单科不低于 6.0）和弱项（听力、词组/搭配）
2. 生成中文打卡消息，发送到 target="__DC_TARGET__"
3. 结合 profile 和趋势数据给出个性化点评（连续打卡天数、进步/退步 vs 近 7/30 天、是否达标、建议）

## 消息格式（严格遵循）
- 用中文，简洁有力
- 开头标注打卡日期和连续打卡天数（如有）
- 列出今日听写时长和最近练习的课程
- 对比近 7 天 / 30 天趋势，点出进步或退步
- 结合 profile 给一句个性化建议（结合雅思听力目标或词组搭配弱项）
- 消息不超过 800 字符

示例格式：
📖 **每日听写打卡 2026-08-04**

🔥 连续打卡 12 天

▸ 今日 35min · 完成 1 课
▸ 最近练习: 118. The future

📈 近 7 天 4.2h，比之前有所回升，保持住
💡 听力目标 6.5，可以试试剑桥真题精听，配合词组积累

## 约束
- 数据以脚本提供的为准，不要编造
- 如果今日无听写活动，发送一条温和的提醒消息
- 发送完成后必须输出 Done（只输出一次）
PROMPT_EOF

TMP_PROMPT2=$(mktemp /tmp/daily-dictation-prompt2-$$-XXXXXX.txt)
while IFS= read -r line; do
    if [[ "$line" == "DATA_PLACEHOLDER" ]]; then
        echo "$DATA_LINES" >> "$TMP_PROMPT2"
    else
        echo "$line" >> "$TMP_PROMPT2"
    fi
done < "$PROMPT_FILE"
mv "$TMP_PROMPT2" "$PROMPT_FILE"
sed -i '' "s|__DC_TARGET__|$DISCORD_STUDY_TARGET|g" "$PROMPT_FILE"

MAX_ATTEMPTS=3
TIMEOUT_SEC=300
RETRY_DELAY=10

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "[$(date '+%H:%M:%S')] Attempt $attempt/$MAX_ATTEMPTS: launching opencode..." >&2

    opencode run \
        --pure \
        --auto \
        --dir "$MONOREPO_ROOT" \
        --title "听写打卡 $TODAY" \
        "$(cat "$PROMPT_FILE")" &
    OP_PID=$!

    elapsed=0
    while [ $elapsed -lt $TIMEOUT_SEC ]; do
        if ! kill -0 $OP_PID 2>/dev/null; then
            wait $OP_PID
            EXIT_CODE=$?
            if [ $EXIT_CODE -eq 0 ]; then
                echo "[$(date '+%H:%M:%S')] ✓ opencode success (attempt $attempt)" >&2
                exit 0
            fi
            echo "[$(date '+%H:%M:%S')] ✗ opencode exit=$EXIT_CODE (attempt $attempt)" >&2
            break
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    if kill -0 $OP_PID 2>/dev/null; then
        echo "[$(date '+%H:%M:%S')] ✗ opencode timeout after ${TIMEOUT_SEC}s (attempt $attempt)" >&2
        kill $OP_PID 2>/dev/null
        sleep 2
        kill -KILL $OP_PID 2>/dev/null
        wait $OP_PID 2>/dev/null || true
    fi

    if [ $attempt -lt $MAX_ATTEMPTS ]; then
        echo "[$(date '+%H:%M:%S')] Retrying in ${RETRY_DELAY}s..." >&2
        sleep $RETRY_DELAY
    fi
done

echo "[$(date '+%H:%M:%S')] FATAL: All $MAX_ATTEMPTS attempts failed" >&2
exit 1
