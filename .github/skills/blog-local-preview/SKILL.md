---
name: blog-local-preview
description: Quartz 博客本地预览工作流。当你修改了 Blog 仓库的 content/ 目录（文章、图片、配置等）并希望在浏览器中预览效果时使用此 skill。关键词：预览博客、本地预览、预览网站、启动预览、quartz preview、本地运行。
---

# Blog 本地预览工作流

本 skill 记录了 Quartz 博客从修改到本地预览的完整操作流程。

## 前置条件

- Node.js >= 22 已安装
- npm 已安装
- 博客仓库已克隆到本地：`D:\zhuomian\BlogProject\Blog`
- 依赖已安装（`npm install` 已执行）
- Quartz 插件已安装（`npx quartz plugin install --from-config` 已执行）

## 操作流程

### 1. 同步内容文件

VS Code 中通过 GitHub Remote Hub 编辑的文件存储在 **changestore** 中，不会自动同步到本地克隆。需要手动同步：

```powershell
# changestore 路径
$cs = "C:\Users\QuKing\AppData\Roaming\Code\User\globalStorage\github.remotehub\80431c9f7feab0cf943b3cdae6c960b7\changestore\vscode-vfs-github\MonkeyAss-byte\Blog"

# 本地克隆路径
$local = "D:\zhuomian\BlogProject\Blog"

# 同步 content 目录（将 changestore 中的修改复制到本地）
Copy-Item -Path "$cs\content\*" -Destination "$local\content\" -Recurse -Force
```

> 💡 **更简单的做法**：直接在 `D:\zhuomian\BlogProject\Blog\content\` 下编辑 Markdown 文件，然后在 VS Code 的源码管理面板中提交到 GitHub，避免来回同步。

### 2. 启动本地预览服务器

```powershell
cd "D:\zhuomian\BlogProject\Blog"
npx quartz build --serve
```

构建成功后会显示：
```
Started a Quartz server listening at http://localhost:8080
```

### 3. 浏览器预览

打开浏览器访问 **http://localhost:8080**

### 4. 停止服务器

在终端中按 `Ctrl+C` 停止。

## 常见问题

### `npm error could not determine executable to run`

当前工作目录不正确。必须先 `cd` 到 `D:\zhuomian\BlogProject\Blog`。

### `Could not resolve "../../.quartz/plugins"`

Quartz 插件未安装。执行：
```powershell
cd "D:\zhuomian\BlogProject\Blog"
npx quartz plugin install --from-config
```

### GitHub 克隆插件失败（`Recv failure: Connection was reset`）

网络问题导致并发克隆被限流。等待几分钟后重试。

### 图片不显示

确保图片放在 `content/images/` 下，且 Markdown 中的引用路径相对于 `content/` 目录。例如：
```markdown
![描述](images/毛发渲染/xxx.png)
```

## 目录结构参考

```
D:\zhuomian\BlogProject\Blog\
├── content/                  ← 所有内容放这里
│   ├── index.md              ← 主页
│   ├── images/               ← 图片资源
│   ├── Portfolio/            ← 项目复盘
│   └── Tech-Notes/           ← 技术笔记
├── quartz.config.default.yaml ← 站点配置
├── package.json
└── node_modules/
```
