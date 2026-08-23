#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$PROJECT_DIR/.agents/discord.config" 2>/dev/null || true
cd "$PROJECT_DIR"

TODAY=$(date +%Y-%m-%d)
NOW=$(date '+%Y-%m-%dT%H:%M:%S')
DAYS="${1:-3}"

AUDIT_DIR="$PROJECT_DIR/audit"
SNAPSHOT_DIR="$AUDIT_DIR/snapshots"
INCIDENT_DIR="$AUDIT_DIR/incidents"
mkdir -p "$SNAPSHOT_DIR" "$INCIDENT_DIR"

# ===== 1. 巡检并保存快照（含各仓 git SHA 版本）=====
HEALTH_JSON=$(python3 ops/task_health.py --days "$DAYS" --snapshot 2>/dev/null)
if [ -z "$HEALTH_JSON" ]; then
    echo "FATAL: Cannot get task health data" >&2
    exit 1
fi
SNAPSHOT_FILE="$SNAPSHOT_DIR/task-health-$TODAY.json"
echo "[$(date '+%H:%M:%S')] 快照已保存: $SNAPSHOT_FILE" >&2

# 提取健康摘要 + 失败详情
HEALTH_LINES=$(printf '%s' "$HEALTH_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for t in d['tasks']:
    status = '✅' if t['healthy'] else '🔴'
    run_info = f\"{t['success']}/{t['runs']} 成功\"
    if t.get('running'):
        run_info += f\" | {t['running']} 次运行中\"
    if t['failed']:
        run_info += f\" | {t['failed']} 次失败\"
    print(f\"  {status} {t['name']}: {run_info} (最近: {t['last_run']})\")
    for f in t.get('failures', []):
        err = (f.get('stderr_tail') or '')[:300]
        print(f\"      ✗ {f['date']} exit={f['exit_code']}: {err}\")
")

ANY_FAILURE=$(printf '%s' "$HEALTH_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('yes' if d['any_failure'] else 'no')
")

# ===== 2. 健康时提交快照并退出 =====
if [ "$ANY_FAILURE" = "no" ]; then
    echo "[$(date '+%H:%M:%S')] 所有定时任务健康，无需处理"
    if git -C "$PROJECT_DIR" diff --quiet 2>/dev/null; then
        :
    else
        git -C "$PROJECT_DIR" add audit/ 2>/dev/null || true
        git -C "$PROJECT_DIR" commit -m "audit: 巡检快照 $TODAY (全部健康)" 2>/dev/null || true
        git -C "$PROJECT_DIR" push 2>/dev/null || true
    fi
    exit 0
fi

# ===== 3. 有失败：先写 incident 草稿（防止故障信息丢失）=====
FAILED_TASKS=$(printf '%s' "$HEALTH_JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = [t['name'] for t in d['tasks'] if t['failed'] > 0]
print(','.join(names) if names else 'unknown')
")
INCIDENT_ID="$TODAY-$FAILED_TASKS"
INCIDENT_FILE="$INCIDENT_DIR/$INCIDENT_ID.md"
if [ ! -f "$INCIDENT_FILE" ]; then
    cat > "$INCIDENT_FILE" <<'INCIDENT_EOF'
---
status: open
detected: DETECTED_PLACEHOLDER
tasks: TASKS_PLACEHOLDER
---

# 定时任务故障 Incident

## 状态
- **检测时间**: DETECTED_PLACEHOLDER
- **涉及任务**: TASKS_PLACEHOLDER
- **状态**: open（待排查）
INCIDENT_EOF
    sed -i '' \
        -e "s|DETECTED_PLACEHOLDER|$NOW|g" \
        -e "s|TASKS_PLACEHOLDER|$FAILED_TASKS|g" \
        "$INCIDENT_FILE"
    echo "[$(date '+%H:%M:%S')] incident 草稿: $INCIDENT_FILE" >&2
fi

PROMPT_FILE=$(mktemp /tmp/task-health-prompt-$$-XXXXXX.txt)
trap "rm -f $PROMPT_FILE" EXIT

cat > "$PROMPT_FILE" <<'PROMPT_EOF'
你是定时任务巡检助手。检测到部分 reveille 定时任务执行失败，请排查原因、修复并留下审计记录。

## 任务健康报告
HEALTH_PLACEHOLDER

## 审计上下文
- 巡检快照（含 git SHA）: audit/snapshots/task-health-DATE_PLACEHOLDER.json
- Incident 记录文件: audit/incidents/INCIDENT_PLACEHOLDER.md （status: open，请回写）
- 巡检脚本在 monorepo 内（版本受控，修改需提交）

## 你的任务
1. **排查**：读取失败任务日志确认原因
   - 执行记录: ~/.config/reveille/executions/*.json（含 stdoutPath/stderrPath）
   - stderr 日志: ~/.local/share/reveille/logs/<taskId>/<timestamp>.stderr.log
   - 任务配置: ~/.config/reveille/tasks/*.md
2. **定位根因**（脚本 bug / 数据缺失 / 路径问题 / API 限频 / opencode 超时等）
3. **修复**：
   - 脚本 bug：直接修改对应项目脚本，用 py_compile / bash -n 验证
   - 数据缺失：确认是否正常场景（如休息日无训练数据），判断是否已修复
   - 瞬时错误：评估是否需要代码加固
4. **验证**：`reveille run <taskId>` 或直接跑脚本确认退出码为 0
5. **提交版本控制**（重要）：
   - 在 monorepo 内 `git add <files> && git commit && git push`
   - 提交信息用 fix: 前缀，说明根因
   - 同时更新 audit/ 下的 incident 记录（改为 resolved）并提交推送
6. **回写 Incident 记录**（audit/incidents/*.md），追加：
   - 根因分析
   - 修复动作（改了哪些文件、commit SHA）
   - 验证结果
   - 状态改为 resolved
7. **发送报告**到 target="__DC_TARGET__"（Discord 私信），包含：
   - 哪个任务、哪天失败、根因
   - 修复动作 + commit SHA + 验证结果
   - 若属正常现象，说明为何不算故障
8. 发送完成后输出 Done

## 约束
- 数据以日志为准，不要编造根因
- 修改代码前先读相关文件了解上下文，遵循项目现有风格
- 所有修复必须走 git 提交（含 audit/incident 回写），不提交不算完成
- 发送完成后必须输出 Done（只输出一次）
PROMPT_EOF

TMP_PROMPT2=$(mktemp /tmp/task-health-prompt2-$$-XXXXXX.txt)
while IFS= read -r line; do
    if [[ "$line" == "HEALTH_PLACEHOLDER" ]]; then
        echo "$HEALTH_LINES" >> "$TMP_PROMPT2"
    elif [[ "$line" == "DATE_PLACEHOLDER" ]]; then
        echo "$TODAY" >> "$TMP_PROMPT2"
    elif [[ "$line" == "INCIDENT_PLACEHOLDER" ]]; then
        echo "$INCIDENT_ID.md" >> "$TMP_PROMPT2"
    else
        echo "$line" >> "$TMP_PROMPT2"
    fi
done < "$PROMPT_FILE"
mv "$TMP_PROMPT2" "$PROMPT_FILE"
sed -i '' "s|__DC_TARGET__|$DISCORD_DM_USER|g" "$PROMPT_FILE"

MAX_ATTEMPTS=3
TIMEOUT_SEC=300
RETRY_DELAY=10

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "[$(date '+%H:%M:%S')] Attempt $attempt/$MAX_ATTEMPTS: launching opencode..." >&2

    opencode run \
        --pure \
        --auto \
        --dir "$PROJECT_DIR" \
        --title "任务巡检 $TODAY" \
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
