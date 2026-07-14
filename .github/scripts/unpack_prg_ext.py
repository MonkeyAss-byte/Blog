"""
Project Graph (.prg) 通用解包 & Markdown 文档生成器

支持两种 .prg 格式：
  1. 扩展包 — 包含 extension.js + metadata.msgpack
  2. 项目/思维导图 — 包含 stage.msgpack + attachments/

用法：
  python unpack_prg_ext.py <.prg文件路径> [输出目录] [--content-images 图片根目录]

示例：
  python unpack_prg_ext.py "D:/plugins/my-ext.prg" "D:/blog/content/Tech-Notes/"
  python unpack_prg_ext.py "D:/思维导图/毛发渲染.prg" "D:/blog/content/Tech-Notes/" --content-images "D:/blog/content/images"

依赖：
  pip install msgpack
"""
import zipfile
import msgpack
import json
import os
import sys
from datetime import datetime

# ====================================================================
# 工具函数
# ====================================================================

def format_size(size_bytes: int) -> str:
    """将字节数转为可读大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def count_lines(text: str) -> int:
    return len(text.splitlines())


def extract_first_lines(text: str, n: int = 15) -> str:
    """提取文本的前 N 行"""
    lines = text.splitlines()
    if len(lines) <= n:
        return text
    return "\n".join(lines[:n]) + f"\n... (共 {len(lines)} 行)"


# ====================================================================
# 元数据解析
# ====================================================================

def parse_metadata(raw: bytes) -> dict:
    """从 msgpack 解析扩展元数据"""
    try:
        data = msgpack.unpackb(raw, raw=False)
    except Exception:
        data = msgpack.unpackb(raw, raw=True)
    
    if isinstance(data, dict):
        ext_info = data.get("extension", data)
        return {
            "id": ext_info.get("id", "unknown"),
            "name": ext_info.get("name", "Unknown"),
            "version": ext_info.get("version", "0.0.0"),
            "description": ext_info.get("description", ""),
            "author": ext_info.get("author", ""),
            "schema_version": data.get("version", ""),
        }
    return {"id": "unknown", "name": "Unknown", "version": "0.0.0", 
            "description": "", "author": "", "schema_version": ""}


# ====================================================================
# Markdown 生成
# ====================================================================

def generate_markdown(metadata: dict, entries: dict, prg_path: str) -> str:
    """生成扩展技术文档 Markdown"""
    ext_id = metadata["id"]
    ext_name = metadata["name"]
    ext_ver = metadata["version"]
    ext_desc = metadata["description"]
    ext_author = metadata["author"]
    
    # 生成 slug
    slug = ext_name.replace(" ", "-").replace("/", "-")
    
    lines = []
    lines.append("---")
    lines.append(f"title: Project Graph 扩展 - {ext_name}")
    lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("tags:")
    lines.append("  - Project Graph")
    lines.append("  - 扩展开发")
    lines.append("  - 工具")
    lines.append(f"description: Project Graph 扩展 {ext_name} v{ext_ver} 的技术拆解文档")
    lines.append("---")
    lines.append("")
    lines.append(f"# Project Graph 扩展 - {ext_name}")
    lines.append("")
    
    # 基本信息
    lines.append("## 📦 基本信息")
    lines.append("")
    lines.append("| 属性 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| **扩展 ID** | `{ext_id}` |")
    lines.append(f"| **名称** | {ext_name} |")
    lines.append(f"| **版本** | v{ext_ver} |")
    lines.append(f"| **作者** | {ext_author} |")
    if ext_desc:
        lines.append(f"| **描述** | {ext_desc} |")
    lines.append(f"| **源文件** | `{os.path.basename(prg_path)}` |")
    lines.append(f"| **包大小** | {format_size(entries.get('_total_size', 0))} |")
    lines.append("")
    
    # 包内容
    lines.append("## 📂 包内容")
    lines.append("")
    lines.append("| 文件 | 大小 | 说明 |")
    lines.append("|------|------|------|")
    
    for name, info in entries.items():
        if name.startswith("_"):
            continue
        label = {
            "extension.js": "扩展主逻辑（编译后）",
            "metadata.msgpack": "扩展元数据（ID/名称/版本）",
            "README.md": "扩展说明文档",
        }.get(name, "")
        icon_labels = {"icon.svg": "扩展图标", "icon.png": "扩展图标", 
                       "icon.webp": "扩展图标", "icon.jpg": "扩展图标"}
        if name in icon_labels:
            label = icon_labels[name]
        elif name.endswith((".svg", ".png", ".webp", ".jpg")):
            label = "图标文件"
        lines.append(f"| `{name}` | {format_size(info['size'])} | {label} |")
    
    lines.append("")
    
    # 源码分析
    js_entry = entries.get("extension.js")
    if js_entry:
        lines.append("## 🔍 源码概览")
        lines.append("")
        lines.append(f"- **大小**：{format_size(js_entry['size'])}")
        lines.append(f"- **行数**：{count_lines(js_entry.get('text', ''))} 行")
        lines.append("")
        lines.append("```javascript")
        lines.append(extract_first_lines(js_entry.get("text", ""), 25))
        lines.append("```")
        lines.append("")
    
    # README
    readme_entry = entries.get("README.md")
    if readme_entry:
        lines.append("## 📖 扩展说明（README）")
        lines.append("")
        lines.append(readme_entry.get("text", ""))
        lines.append("")
    
    # 元数据原始 JSON
    lines.append("## 🧾 完整元数据")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(metadata, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    
    # 安装说明
    lines.append("## 🚀 安装方法")
    lines.append("")
    lines.append("1. 将 `{os.path.basename(prg_path)}` 放入 Project Graph 扩展目录：")
    lines.append(f"   `%APPDATA%/liren.project-graph/extensions/{ext_id}/`")
    lines.append("2. 在 Project Graph 中点击 **设置 → 扩展 → 重载扩展**")
    lines.append("3. 按 `m n f` 触发导出功能")
    lines.append("")
    
    return "\n".join(lines)


# ====================================================================
# PRG 类型检测
# ====================================================================

def detect_prg_type(prg_path: str) -> str:
    """检测 .prg 文件类型：'extension' | 'project' | 'unknown'"""
    with zipfile.ZipFile(prg_path, "r") as zf:
        names = set(zf.namelist())
    if "extension.js" in names and "metadata.msgpack" in names:
        return "extension"
    if "stage.msgpack" in names:
        return "project"
    return "unknown"


# ====================================================================
# 主逻辑（智能路由）
# ====================================================================

def unpack_and_generate_markdown(prg_path: str, output_dir: str = None,
                                  content_images_dir: str = None) -> str:
    """
    通用 .prg 解包入口，自动检测类型并路由到对应处理器。
    - extension: 解析扩展元数据 + 源码
    - project: 解析思维导图节点 + 边 → Markdown
    """
    if not os.path.exists(prg_path):
        raise FileNotFoundError(f"文件不存在: {prg_path}")

    prg_type = detect_prg_type(prg_path)
    prg_name = os.path.splitext(os.path.basename(prg_path))[0]

    if output_dir is None:
        output_dir = os.path.dirname(prg_path)

    print(f"📦 解包: {prg_path}")
    print(f"🧭 检测到类型: {prg_type}")

    if prg_type == "extension":
        return _handle_extension(prg_path, output_dir)
    elif prg_type == "project":
        return _handle_project(prg_path, output_dir, content_images_dir)
    else:
        print(f"⚠️ 未知 .prg 类型，尝试按扩展包处理...")
        return _handle_extension(prg_path, output_dir)


def _handle_extension(prg_path: str, output_dir: str) -> str:
    """处理扩展 .prg（原有逻辑）"""
    entries = {}
    total_size = os.path.getsize(prg_path)

    with zipfile.ZipFile(prg_path, "r") as zf:
        for name in zf.namelist():
            info = zf.getinfo(name)
            data = zf.read(name)
            entries[name] = {
                "size": info.file_size,
                "data": data,
                "text": data.decode("utf-8", errors="replace")
                if not name.endswith((".msgpack", ".png", ".svg", ".webp", ".jpg")) else "",
            }
            print(f"  ├─ {name} ({format_size(info.file_size)})")

    entries["_total_size"] = total_size

    meta_entry = entries.get("metadata.msgpack")
    meta = parse_metadata(meta_entry["data"]) if meta_entry else {
        "id": os.path.splitext(os.path.basename(prg_path))[0],
        "name": os.path.splitext(os.path.basename(prg_path))[0],
        "version": "0.0.0", "description": "", "author": "", "schema_version": ""
    }

    js_entry = entries.get("extension.js")
    if js_entry:
        js_entry["text"] = js_entry["data"].decode("utf-8", errors="replace")

    readme_entry = entries.get("README.md")
    if readme_entry:
        readme_entry["text"] = readme_entry["data"].decode("utf-8", errors="replace")

    md_content = generate_markdown(meta, entries, prg_path)

    safe_name = meta["name"].replace(" ", "-").replace("/", "-").replace("\\", "-")
    md_path = os.path.join(output_dir, f"{safe_name}-技术拆解.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n✅ Markdown 已生成: {md_path}")
    return md_path


def _handle_project(prg_path: str, output_dir: str, content_images_dir: str = None) -> str:
    """处理思维导图 .prg（委派给 prg_to_markdown_v5）"""
    # 尝试导入 v5 模块
    try:
        # 将脚本所在目录的上级加入 path（以便找到 ProjectGraph 目录）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        projectgraph_dir = os.path.join(os.path.dirname(script_dir), "ProjectGraph")
        if os.path.isdir(projectgraph_dir):
            sys.path.insert(0, projectgraph_dir)
        from prg_to_markdown_v5 import process_file
    except ImportError:
        print("❌ 无法导入 prg_to_markdown_v5，请确保该脚本位于 ProjectGraph 目录同级")
        print("   或设置 PYTHONPATH 指向 D:\\zhuomian\\BlogProject\\ProjectGraph")
        sys.exit(1)

    if content_images_dir is None:
        content_images_dir = os.path.join(os.path.dirname(output_dir), "images")

    os.makedirs(content_images_dir, exist_ok=True)

    return process_file(prg_path, output_dir, content_images_dir)


# ====================================================================
# CLI
# ====================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python unpack_prg_ext.py <扩展.prg> [输出目录]")
        print()
        print("示例:")
        print('  python unpack_prg_ext.py "D:/plugins/my-ext.prg"')
        print('  python unpack_prg_ext.py "D:/plugins/my-ext.prg" "D:/blog/content/Tech-Notes/"')
        sys.exit(1)
    
    prg_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        unpack_and_generate_markdown(prg_file, out_dir)
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
