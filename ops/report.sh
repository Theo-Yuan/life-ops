#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$PROJECT_DIR/.agents/discord.config" 2>/dev/null || true
cd "$PROJECT_DIR"

TODAY=$(date +%Y-%m-%d)
DAYS="${1:-7}"

# 聚合各项目数据 + 任务执行状态
REPORT_JSON=$(python3 ops/aggregate.py --days "$DAYS" 2>/dev/null)
if [ -z "$REPORT_JSON" ]; then
    echo "FATAL: Cannot get aggregate report data" >&2
    exit 1
fi

# 提取各模块内容，供 agent 组装消息
WORKOUT_LINES=$(printf '%s' "$REPORT_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)['workout']
t = d.get('today')
if t:
    print(f\"  今日训练: {t['title']} {t['duration_min']}min\")
else:
    print(f\"  今日训练: 无\")
print('  最近: ' + ', '.join(f\"{r['date']} {r['title']} {r['duration_min']}min\" for r in d.get('recent', [])[:3]))
")

ENGLISH_LINES=$(printf '%s' "$REPORT_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)['english_learning']
t = d.get('today')
if t:
    print(f\"  今日听写/学习: {t['minutes']}min (听写{t['dictation_min']}min + 手动{t['manual_min']}min)\")
else:
    print(f\"  今日听写/学习: 无\")
w = d.get('week', [])
if w:
    total = sum((r['minutes'] or 0) for r in w)
    print(f\"  近7天: {total}min\")
")

FINANCE_LINES=$(printf '%s' "$REPORT_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)['finance_plan']
t = d.get('today')
if t:
    print(f\"  今日理财学习: {t['minutes']}min ({t['entries']}条)\")
else:
    print(f\"  今日理财学习: 无\")
w = d.get('week', [])
if w:
    total = sum((r['minutes'] or 0) for r in w)
    print(f\"  近7天: {total}min\")
")

GMAIL_LINES=$(printf '%s' "$REPORT_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)['gmail']
if d.get('error'):
    print(f\"  {d['error']}\")
else:
    print(f\"  今日: {d['total']}封 ({d['unread']}未读)\")
    cats = d.get('categories', [])
    top = sorted(cats, key=lambda c: c['total'], reverse=True)[:5]
    for c in top:
        print(f\"    {c['name']}: {c['total']} ({c['unread']}未读)\")
    imp = d.get('important', [])
    if imp:
        print(f\"  重要未读: {len(imp)}封\")
        for i in imp[:3]:
            print(f\"    {i['from']} | {i['subject'][:40]}\")
")

TASK_LINES=$(printf '%s' "$REPORT_JSON" | python3 -c "
import sys, json
for t in json.load(sys.stdin).get('tasks', []):
    runs = t.get('runs', [])
    if not runs:
        print(f\"  {t['task']}: 无执行记录\")
        continue
    statuses = {r['status'] for r in runs}
    ok = sum(1 for r in runs if r['status'] == 'success')
    print(f\"  {t['task']}: {ok}/{len(runs)} 成功 ({len(runs)}次)  最近: {runs[-1]['date']} {runs[-1]['status']}\")
")

PROMPT_FILE=$(mktemp /tmp/life-ops-prompt-$$-XXXXXX.txt)
trap "rm -f $PROMPT_FILE" EXIT

cat > "$PROMPT_FILE" <<'PROMPT_EOF'
你是人生运营助手。请根据以下聚合数据，生成一份今日学习状态汇总 + 定时任务执行报告，并发送到 Discord 私信。

## 今日聚合数据
WORKOUT_PLACEHOLDER
ENGLISH_PLACEHOLDER
FINANCE_PLACEHOLDER
GMAIL_PLACEHOLDER
TASK_PLACEHOLDER

## 你的任务
1. 读取各项目的 profile（如需要个性化点评）：
   - projects/workout/.agents/profile.md
   - projects/english/.agents/profile.md
   - projects/finance/.agents/profile.md
2. 生成一份聚合日报，包含：
   - 训练 / 听写 / 理财学习 今日状态 + 简短点评（进步/持平/退步）
   - 定时任务执行报告（哪些任务跑了、成功/失败、异常提醒）
3. 发送到 target="__DC_TARGET__"（Discord 私信）
4. 发送完成后输出 Done

## 消息格式
- 中文，简洁，不超过 800 字符
- 用 emoji 分隔模块
- 若某模块今日无数据，明确写出「无」，不要编造

## 约束
- 数据以脚本提供为准，不要编造
- 任务异常时务必醒目提醒
- 发送完成后必须输出 Done（只输出一次）
PROMPT_EOF

TMP_PROMPT2=$(mktemp /tmp/life-ops-prompt2-$$-XXXXXX.txt)
while IFS= read -r line; do
    if [[ "$line" == "WORKOUT_PLACEHOLDER" ]]; then
        echo "$WORKOUT_LINES" >> "$TMP_PROMPT2"
    elif [[ "$line" == "ENGLISH_PLACEHOLDER" ]]; then
        echo "$ENGLISH_LINES" >> "$TMP_PROMPT2"
    elif [[ "$line" == "FINANCE_PLACEHOLDER" ]]; then
        echo "$FINANCE_LINES" >> "$TMP_PROMPT2"
    elif [[ "$line" == "GMAIL_PLACEHOLDER" ]]; then
        echo "$GMAIL_LINES" >> "$TMP_PROMPT2"
    elif [[ "$line" == "TASK_PLACEHOLDER" ]]; then
        echo "$TASK_LINES" >> "$TMP_PROMPT2"
    else
        echo "$line" >> "$TMP_PROMPT2"
    fi
done < "$PROMPT_FILE"
mv "$TMP_PROMPT2" "$PROMPT_FILE"
sed -i '' "s|__DC_TARGET__|$DISCORD_DM_USER|g" "$PROMPT_FILE"

MAX_ATTEMPTS=3
TIMEOUT_SEC=120
RETRY_DELAY=10

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "[$(date '+%H:%M:%S')] Attempt $attempt/$MAX_ATTEMPTS: launching opencode..." >&2

    opencode run \
        --pure \
        --auto \
        --dir "$PROJECT_DIR" \
        --title "人生日报 $TODAY" \
        "$(cat "$PROMPT_FILE")" &
    OP_PID=$!

    elapsed=0
    while [ $elapsed -lt $TIMEOUT_SEC ]; do
        if ! kill -0 $OP_PID 2>/dev/null; then
            EXIT_CODE=0
            wait $OP_PID || EXIT_CODE=$?
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
        wait $OP_PID 2>/dev/null || true
    fi

    if [ $attempt -lt $MAX_ATTEMPTS ]; then
        echo "[$(date '+%H:%M:%S')] Retrying in ${RETRY_DELAY}s..." >&2
        sleep $RETRY_DELAY
    fi
done

echo "[$(date '+%H:%M:%S')] FATAL: All $MAX_ATTEMPTS attempts failed" >&2
exit 1
