---
name: markdown-polish
description: 润色 v5/v6 脚本自动生成的 Markdown 思维导图文章，保留原有层级结构并提升可读性。当 prg-extension-unpack 或 prg-to-markdown 工具生成原始 Markdown 后，自动触发此 skill 进行精修。关键词：润色markdown、精修文章、美化文档、polish markdown、格式化思维导图、markdown beautify。
trigger: after prg-extension-unpack
---

# Markdown 思维导图润色 Skill

当 `prg_to_markdown_v6.py`（或旧版 v5）生成原始 Markdown 后，自动执行以下润色流程。

## v6 生成物的特殊处理

v6 使用 **Base64 Data URI** 内嵌图片，生成格式为：

```markdown
![图片][img-1]

...（文章内容）...

[img-1]: data:image/png;base64,iVBORw0KGgo...
```

润色时：
- ✅ **保留** `[img-N]: data:...` 引用块（放在文末）
- ✅ 为图片添加描述性 alt text：`![参考图：xxx][img-1]`
- ✅ 如果图片在文章末尾过于冗长，可将其折叠为 `<details>` 块

## 核心原则

- **保留原有层级结构**：不动 `##` / `###` / `####` 标题层次
- **保留所有节点文本**：不删改任何思维导图节点内容
- **增强可读性**：添加 Mermaid 图、表格、分隔线、引用块
- **添加 Frontmatter**：确保 YAML 头部完整（title / date / tags / description）

## 润色步骤

### 1. 修复 Frontmatter

确保文章开头包含完整 YAML：

```yaml
---
title: [文章标题]
date: YYYY-MM-DD
tags:
  - 图形渲染
  - [相关标签]
description: [一句话摘要]
---
```

### 2. 添加文章头部信息

在 `# 标题` 后添加统计信息：

```markdown
> 📊 思维导图导出 | **N** 个节点 · **M** 个分组 · **K** 条连线 · **P** 张参考图
```

### 3. 优化 Section 分组标题

将 v5 生成的 `📁 分组名` 改为带描述的段落：

```markdown
## 一、分组名
> 该分组包含 N 个子节点
```

### 4. 合并游离的 Section

v5 脚本因 Edge 遍历可能产生多个同名 `📁 原理` Section，将它们合并为一个。

### 5. 添加分隔线

在主要章节之间添加 `---` 分隔。

### 6. 为叶子节点添加表格

对于深度嵌套的叶子节点（4 级及以上），改为表格形式：

```markdown
| 概念 | 说明 |
|------|------|
| 节点A | 描述 |
| 节点B | 描述 |
```

### 7. 修复图片引用

确保图片路径为 `images/主题/xxx.png` 格式（Quartz 兼容）。

### 8. 添加 Mermaid 架构图（可选）

对于有明确父子关系的节点，生成 Mermaid `graph TD` 图。

## 执行示例

输入（v5 原始输出片段）：
```markdown
## 水体渲染
### 📁 原理
#### 漫反射
##### 经验型的补光策略
```

输出（润色后）：
```markdown
## 一、水体渲染

> 本章涵盖水体渲染的核心原理与实现

### 1.1 原理

水体渲染的底层物理模型，主要包括：

| 光照模型 | 说明 |
|----------|------|
| 漫反射 | 经验型的补光策略 |
```

## 注意事项

- ⚠️ 不要修改节点文本内容（保留原意）
- ⚠️ 不要改变层级关系（A是B的父节点 → 润色后仍是）
- ⚠️ 如果原始结构中存在明显的语义错误，添加 `> ⚠️ 注意：...` 提示
- ✅ 可以为相似的节点添加统一的前缀编号（一、/ 1.1 / 1.1.1）
- ✅ 对于过长节点文本（>50字），可适当简化为表格行
