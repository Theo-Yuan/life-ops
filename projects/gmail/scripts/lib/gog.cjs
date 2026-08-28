'use strict';
// lib/gog.cjs — 调用 gog CLI 并解析 JSON，带瞬时错误重试（Google API 偶发 EOF/限频）。
const { execFileSync } = require('child_process');

const TRANSIENT = /EOF|round trip|connection reset|connection refused|timeout|429|rate.?limit|temporarily unavailable/i;

function sleepSync(ms) {
  const sab = new SharedArrayBuffer(4);
  Atomics.wait(new Int32Array(sab), 0, 0, ms);
}

function gog(args, attempts = 3) {
  let lastErr;
  for (let a = 0; a < attempts; a++) {
    try {
      const r = execFileSync('gog', args, {
        encoding: 'utf8',
        maxBuffer: 256 * 1024 * 1024,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      return JSON.parse(r);
    } catch (err) {
      lastErr = err;
      const msg = `${(err.stderr || '')} ${err.message || ''}`;
      const transient = TRANSIENT.test(msg);
      if (!transient || a === attempts - 1) throw err;
      sleepSync(1000 * (a + 1));
    }
  }
  throw lastErr;
}

module.exports = gog;
