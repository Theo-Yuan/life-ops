#!/usr/bin/env python3
"""Send a digest file to a Discord user via DM using the bot token from Keychain.

Usage:
    python3 send_discord.py <message_file> <user_id>

Reads the bot token from macOS Keychain (discord-bot-token / opencode),
creates a DM channel with the given user, and sends the message content
in chunks (Discord 2000-char limit). Uses the REST API directly for
reliability (no discord.py gateway, no MCP).
"""
import http.client
import json
import subprocess
import sys
import time

HOST = "discord.com"
TOKEN = subprocess.check_output(
    ["security", "find-generic-password", "-s", "discord-bot-token", "-a", "opencode", "-w"]
).decode().strip()

CHUNK_LIMIT = 1900


def api(path: str, method: str = "GET", body: dict | None = None):
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    payload = json.dumps(body).encode() if body is not None else None
    last_err = None
    for attempt in range(3):
        conn = None
        try:
            conn = http.client.HTTPSConnection(HOST, timeout=20)
            conn.request(method, path, body=payload, headers=headers)
            resp = conn.getresponse()
            raw = resp.read().decode(errors="replace")
            if resp.status >= 400:
                sys.stderr.write(f"HTTP {resp.status} {path}: {raw}\n")
                if resp.status == 429:
                    retry_after = resp.getheader("Retry-After", "1")
                    time.sleep(float(retry_after))
                    continue
                raise RuntimeError(f"discord api error {resp.status}")
            return json.loads(raw) if raw else {}
        except (http.client.RemoteDisconnected,
                TimeoutError,
                ConnectionError,
                OSError) as e:
            last_err = e
            sys.stderr.write(f"discord connection error (attempt {attempt + 1}/3): {e}\n")
            time.sleep(2 ** attempt)
        finally:
            if conn:
                conn.close()
    raise last_err


def split_chunks(msg: str) -> list[str]:
    lines = msg.splitlines()
    chunks, cur = [], ""
    for ln in lines:
        if cur and len(cur) + len(ln) + 1 > CHUNK_LIMIT:
            chunks.append(cur)
            cur = ln
        else:
            cur = f"{cur}\n{ln}" if cur else ln
    if cur:
        chunks.append(cur)
    return chunks


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: send_discord.py <message_file> <user_id>\n")
        return 1
    msg_path, user_id = sys.argv[1], sys.argv[2]
    with open(msg_path, encoding="utf-8") as f:
        msg = f.read().strip()
    if not msg:
        sys.stderr.write("empty message\n")
        return 1

    dm = api("/api/v10/users/@me/channels", "POST", {"recipient_id": user_id})
    channel_id = dm["id"]

    chunks = split_chunks(msg)
    for i, chunk in enumerate(chunks):
        api(f"/api/v10/channels/{channel_id}/messages", "POST", {"content": chunk})
        if i < len(chunks) - 1:
            time.sleep(0.4)
    print(f"sent {len(chunks)} message(s) to {user_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
