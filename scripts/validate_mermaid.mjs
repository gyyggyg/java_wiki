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

/**
 * 剥掉 sequenceDiagram 的 `box ... end` 包装用于校验。
 *
 * 原因：mermaid + jsdom 在 server-side 解析 sequenceDiagram 的 `box` 语法时
 * 会误报 "Option is not defined"（需要浏览器 CSS/theme 上下文）。`box` 只是视觉
 * 分组，不影响语法逻辑，校验时剥掉即可。
 *
 * 用栈精确匹配 box 对应的 end，绕开内部的 alt / opt / loop / par / rect /
 * critical / break 等其它块。
 */
function stripSeqBoxForValidation(src) {
    const lines = src.split('\n');
    // 只在 sequenceDiagram 里剥
    const isSeq = lines.slice(0, 5).some(l => l.trim().startsWith('sequenceDiagram'));
    if (!isSeq) return src;

    const openKws = ['alt ', 'opt ', 'loop ', 'par ', 'rect ', 'critical ', 'break '];
    const out = [];
    const stack = []; // "box" | "other"
    for (const ln of lines) {
        const s = ln.trim();
        if (s.startsWith('box ') || s === 'box') {
            stack.push('box');
            continue; // 丢弃 box 开启行
        }
        if (openKws.some(kw => s.startsWith(kw))) {
            stack.push('other');
            out.push(ln);
            continue;
        }
        if (s === 'end') {
            if (stack.length > 0) {
                const kind = stack.pop();
                if (kind === 'box') {
                    continue; // 丢弃配对的 end
                }
            }
            out.push(ln);
            continue;
        }
        out.push(ln);
    }
    return out.join('\n');
}

const codeForParse = stripSeqBoxForValidation(code);

try {
    await mermaid.parse(codeForParse);
    console.log('OK');
    process.exit(0);
} catch (e) {
    const msg = e.message || e.toString();
    console.error(msg);
    process.exit(1);
}
