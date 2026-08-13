#!/usr/bin/env python3
"""
从 .env 读取 API Key → 生成 auth.<domain>.md 鉴权文件。
生成的鉴权文件已被 .gitignore 排除，不会提交到仓库。
"""

import os
from pathlib import Path

SKILLS_DIR = Path(__file__).parent
ENV_FILE = Path(__file__).parents[3] / ".env"

AUTH_CONFIGS = {
    "market": {
        "env_keys": ["MARKET_API_KEY"],
        "description": "行情数据 API",
    },
    "crypto": {
        "env_keys": ["CRYPTO_API_KEY"],
        "description": "加密货币行情 API",
    },
    "fx": {
        "env_keys": ["FX_API_KEY"],
        "description": "汇率 API",
    },
}


def load_env():
    env_vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip()
    return env_vars


def generate_auth(domain: str, env_vars: dict) -> str:
    config = AUTH_CONFIGS[domain]
    lines = [
        f"---",
        f"description: \"{config['description']} 鉴权配置 - 自动生成，请勿手动修改\"",
        f"auto_generated: true",
        f"generated_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)",
        f"---",
        f"",
        f"# {config['description']} 鉴权",
        f"",
        f"```yaml",
    ]

    all_ok = True
    for key in config["env_keys"]:
        value = env_vars.get(key, "")
        if value:
            lines.append(f"{key}: \"{value}\"")
        else:
            lines.append(f"{key}: \"\"  # ⚠️ 未设置")
            all_ok = False

    lines.append("```")
    if not all_ok:
        lines.append("")
        lines.append("> ⚠️ 部分 Key 未设置，请在 .env 中配置后重新运行此脚本。")

    return "\n".join(lines)


def main():
    env_vars = load_env()

    if not ENV_FILE.exists():
        print(f"[!] .env 文件不存在: {ENV_FILE}")
        print(f"    请先 cp .env.example .env 并填入 API Key")
        return

    generated = 0
    for domain in AUTH_CONFIGS:
        content = generate_auth(domain, env_vars)
        output_path = SKILLS_DIR / f"auth.{domain}.md"
        with open(output_path, "w") as f:
            f.write(content)
        print(f"[✓] 已生成 {output_path}")
        generated += 1

    print(f"\n完成: 生成 {generated} 个鉴权文件")


if __name__ == "__main__":
    main()
