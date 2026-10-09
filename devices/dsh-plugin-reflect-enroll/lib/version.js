/**
 * version.js — ⑥ 版本管理：**唯一来源 = package.json**
 * =============================================================================
 * CLI 的 --tool-version、日志、反馈卡都从这里取；源码里**不允许**再写一份版本字面量
 * （R006 坑#6：两处版本必然漂移）。
 */
import fs from 'node:fs';

const PKG = JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

export const NAME = PKG.name;
export const VERSION = PKG.version;
export const R006 = PKG.r006 || {};
export const TOOL = 'reflect-enroll';
export const TOOL_FULL = 'dsh-plugin-reflect-enroll';
