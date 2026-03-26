/**
 * 轻量 Mermaid 语法校验脚本（无需 Chrome/Puppeteer）
 * 使用 jsdom 模拟 DOM 环境，调用 mermaid.parse() 做纯语法校验
 *
 * 用法:
 *   node validate_mermaid.mjs <file>       从文件读取
 *   echo "..." | node validate_mermaid.mjs -   从 stdin 读取
 *
 * 输出:
 *   成功: 退出码 0，stdout 输出 "OK"
 *   失败: 退出码 1，stderr 输出错误信息
 */

import { JSDOM } from 'jsdom';
import { readFileSync } from 'fs';

// 模拟浏览器 DOM 环境
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
    pretendToBeVisual: true,
});
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, 'navigator', {
    value: dom.window.navigator,
    writable: true,
    configurable: true,
});
global.DOMParser = dom.window.DOMParser;
global.XMLSerializer = dom.window.XMLSerializer;

// 动态导入 mermaid（需要在 DOM 环境设置之后）
const mermaid = (await import('mermaid')).default;

mermaid.initialize({
    startOnLoad: false,
    suppressErrors: true,
});

// 读取输入
let code;
const arg = process.argv[2];

if (!arg || arg === '-') {
    code = readFileSync(0, 'utf-8');
} else {
    code = readFileSync(arg, 'utf-8');
}

code = code.trim();
if (!code) {
    console.error('Empty input');
    process.exit(1);
}

try {
    await mermaid.parse(code);
    console.log('OK');
    process.exit(0);
} catch (e) {
    const msg = e.message || e.toString();
    console.error(msg);
    process.exit(1);
}
