---
name: prg-extension-unpack
description: 解包 Project Graph 扩展 (.prg) 并生成 Markdown 技术文档。当你需要分析、记录或发布一个 Project Graph 扩展的技术拆解文章时使用此 skill。也支持将思维导图 .prg 转为 Markdown。关键词：解包prg、解包扩展、prg to markdown、扩展文档、分析prg扩展、unpack prg extension、思维导图转markdown。
trigger: auto -> markdown-polish
---

# Project Graph .prg 解包 & Markdown 生成

本 skill 涵盖两种 .prg 文件的处理：

| 类型 | 识别特征 | 处理脚本 |
|------|----------|----------|
| **扩展包** | 含 `extension.js` + `metadata.msgpack` | `unpack_prg_ext.py` |
| **思维导图** | 含 `stage.msgpack` | `prg_to_markdown_v6.py` |

## 思维导图 .prg → Markdown（推荐 v6）

基于 `prg-markdown-helper` 扩展的核心思路重写：

### 核心改进

| 特性 | v5 (旧) | v6 (基于扩展思路) |
|------|---------|-------------------|
| 图片处理 | 提取到磁盘 `images/` 目录 | **Base64 Data URI 内嵌** → 自包含 Markdown |
| 节点收集 | 仅顶层数组 | **深度遍历**整个对象树 |
| 引用解析 | 简单路径拆分 | **RFC 6901 JSON Pointer** |
| 图片语法 | `![alt](path.png)` | `![图片][img-N]` + `[img-N]: data:...` |
| 依赖 | msgpack, zipfile | msgpack, zipfile（仅标准库） |

### 用法

```powershell
# 单文件
python .github/scripts/prg_to_markdown_v6.py "D:/思维导图/毛发渲染.prg"

# 批量转换
python .github/scripts/prg_to_markdown_v6.py --batch "D:/思维导图" "D:/blog/content/Tech-Notes"
```

### 输出示例

生成的 Markdown 完全自包含，无需额外图片文件：

```markdown
# 毛发渲染
![图片][img-1]

[img-1]: data:image/png;base64,iVBORw0KGgo...
```

## 扩展包 .prg → Markdown

```powershell
python .github/scripts/unpack_prg_ext.py "D:/plugins/my-ext.prg" "D:/blog/content/Tech-Notes/"
```

`unpack_prg_ext.py` 已升级为智能路由——自动检测 .prg 类型并委派处理。

## 文件位置

- `unpack_prg_ext.py` — 通用路由（扩展包 + 思维导图）
- `prg_to_markdown_v6.py` — 思维导图专用（推荐）
- `prg_to_markdown_v5.py` — 旧版（仍可用，需外部图片目录）
