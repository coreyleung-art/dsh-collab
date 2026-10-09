/**
 * version.js — R006 ⑥ 版本单一来源
 * =============================================================================
 * 版本号**只写在 package.json**。CLI 与插件入口都从这里读，两边都不硬编码。
 *
 * ★ 为什么单独一个文件（③ CLD 自适应的血泪条）：
 *   初版让 `cli.js` 从 `lib/index.js` 取 packageVersion —— 而 index.js 顶部
 *   `import { defineTool } from '@deepseek-ai/dsh-tools'`。结果在**无宿主环境**下
 *   （本机 bash 的 PATH 里没有 profile node_modules）连 `--tool-version` 都跑不了，
 *   直接 `ERR_MODULE_NOT_FOUND` 崩掉 —— 违反 ③「无 CLD 时可独立跑 CLI，降级而非崩溃」。
 *   修法：版本读取下沉到本文件（零依赖，只读 package.json）。
 */
import fs from 'node:fs';

/** 从 package.json 读版本（唯一来源）。读不到时返回醒目的 unknown，绝不假装成某个版本。 */
export function packageVersion() {
  try {
    return JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version;
  } catch {
    return '0.0.0-unknown';
  }
}
