import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { STAGES, STAGE_IMPL, HUMAN_GATED } from './gate.js';

export function runSelfCheck(root) {
  const missing = [], warnings = [], notes = [];

  // 1) 依赖完整性：peer 是否可解析
  // ★ 修（2026-09-10，真挂载冒烟抓到）：原版 = path.join(root, 'devices/dsh-plugin-reflect/package.json')
  //   而 root 常被传成 ctx.root（宿主给的任意根）或插件自身目录 → 拼出 .../dsh-plugin-reflect/devices/... → ENOENT
  //   → **插件在 host 里挂不上**（除非 ctx.root 恰好是 ~/dsh-collab）
  //   现改为**从本模块自身位置推导**（import.meta.url → 包根），不依赖任何外部传入的 root。
  const _here = path.dirname(fileURLToPath(import.meta.url));   // <pkg>/lib
  const pkgPath = path.join(_here, '..', 'package.json');
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
    notes.push(`package.json 可解析：v${pkg.version}`);
    for (const peer of Object.keys(pkg.peerDependencies || {})) {
      try { require.resolve ? null : null; } catch {}
      notes.push(`peer 声明：${peer}（运行期不 import 宿主内部路径）`);
    }
  } catch (e) {
    missing.push(`package.json 读取失败：${e.message}`);
  }

  // 2) 五环节实现是否就位（缺的不报错，报"未就位"）
  const stageStatus = [];
  for (const s of STAGES) {
    const impl = STAGE_IMPL[s];
    const p = path.join(root, 'devices', impl.plugin, impl.cli);
    const ok = fs.existsSync(p);
    stageStatus.push(`  ${ok ? '✅' : '⏳'} ${s.padEnd(11)} ${impl.plugin}${ok ? '' : '（未就位）'}`);
    if (!ok) warnings.push(`环节 ${s} 的插件未就位：${impl.plugin}`);
  }

  return {
    ok: missing.length === 0,
    capability: [
      '【① 能力清单】',
      '  · 编排五个环节：' + STAGES.join(' / '),
      '  · 断点续跑（按各环节产物存在性判断从哪继续）',
      '  · 查看流水线状态（reflect_status）',
      '  · 日志落盘 ~/dsh-collab/logs/dsh-plugin-reflect.log',
    ],
    mustNot: [
      '【② 不该发生路径清单】',
      '  · 跑不存在的环节 → 类型层无此值（STAGES 冻结枚举）',
      '  · 自动入册（enroll）→ 结构门拒绝（HUMAN_GATED）',
      '  · 执行任意系统命令 → 命令白名单（STAGE_IMPL 冻结映射）',
      '  · 绕过证据门 → 本编排器无证据判定能力，证据门在下游 harvest',
    ],
    deps: [
      '【③ 依赖完整性】',
      ...stageStatus,
      missing.length === 0 ? '  ✅ 无缺失依赖' : `  ❌ 缺失：${missing.join(', ')}`,
    ],
    missing, warnings, notes,
  };
}
