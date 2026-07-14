"""
Project Graph (.prg) → Markdown 转换器 v6
基于 prg-markdown-helper 扩展的核心思路重写

核心改进（相比 v5）：
  1. 图片以 Base64 Data URI 内嵌 → 完全自包含的 Markdown
  2. 深度嵌套节点收集 (collectNestedNodes)
  3. RFC 6901 JSON Pointer 引用解析
  4. reference-style 图片语法 `![图片][img-N]` + `[img-N]: data:image/...`
  5. 保留 Section + Edge 双层级模型

用法：
  python prg_to_markdown_v6.py <input.prg> [output.md]

依赖：
  pip install msgpack
"""
import zipfile
import msgpack
import base64
import os
import sys
from datetime import datetime
from collections import defaultdict

# ====================================================================
# 1. RFC 6901 JSON Pointer 引用解析
# ====================================================================

def resolve_ref(root, ref_path: str):
    """
    解析 $ 引用路径，兼容 RFC 6901 JSON Pointer:
    - "~0" 代表 "~", "~1" 代表 "/"
    - "#" 前缀可选
    """
    if not isinstance(ref_path, str) or not ref_path:
        return None
    if ref_path.startswith("#"):
        ref_path = ref_path[1:]
    parts = [p.replace("~1", "/").replace("~0", "~") for p in ref_path.strip("/").split("/")]
    obj = root
    for part in parts:
        if isinstance(obj, list):
            try:
                obj = obj[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict):
            obj = obj.get(part)
            if obj is None:
                try:
                    obj = obj.get(int(part))
                except:
                    return None
        else:
            return None
    return obj


def resolve_uuid(root, value) -> str | None:
    """从 $ 引用或直接对象中提取 UUID"""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    if "uuid" in value and isinstance(value["uuid"], str):
        return value["uuid"]
    if "$" in value and isinstance(value["$"], str):
        ref = resolve_ref(root, value["$"])
        if isinstance(ref, dict) and "uuid" in ref:
            return ref["uuid"]
    return None


# ====================================================================
# 2. 类型定义
# ====================================================================

PROJECT_NODE_TYPES = {
    "TextNode", "Section", "ImageNode", "UrlNode",
    "SvgNode", "LatexNode", "ConnectPoint",
    "ReferenceBlockNode", "ExtensionEntity",
}

MIME_MAP = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp",
    "svg": "image/svg+xml",
}


# ====================================================================
# 3. 节点与边提取
# ====================================================================

def get_position(item: dict) -> tuple | None:
    """获取节点位置 (x, y)"""
    cb = item.get("collisionBox", {})
    if not isinstance(cb, dict):
        return None
    shapes = cb.get("shapes", [])
    if not isinstance(shapes, list) or len(shapes) == 0:
        return None
    shape0 = shapes[0]
    if not isinstance(shape0, dict):
        return None
    loc = shape0.get("location", {})
    if not isinstance(loc, dict):
        return None
    return (loc.get("x", 0), loc.get("y", 0))


def get_node_text(item: dict, class_name: str) -> str:
    """获取节点显示文本"""
    if class_name in ("TextNode", "Section"):
        return item.get("text", "")
    elif class_name == "UrlNode":
        return f"🔗 {item.get('title', '')} | {item.get('url', '')}"
    elif class_name == "ImageNode":
        aid = item.get("attachmentId", "")
        return f"🖼️ Image [{aid[:8]}...]" if aid else "🖼️ Image"
    elif class_name == "LatexNode":
        return f"$${item.get('latexSource', '')}$$"
    elif class_name == "ConnectPoint":
        return "●"
    elif class_name == "ReferenceBlockNode":
        return f"📄 {item.get('fileName', '')}"
    elif class_name == "ExtensionEntity":
        ext_id = item.get("extensionId", "")
        type_name = item.get("typeName", "")
        h = " · ".join(filter(bool, [ext_id, type_name]))
        return f"🧩 {h}" if h else "🧩 扩展实体"
    return ""


def collect_nested_nodes(root: list) -> dict:
    """
    深度遍历整个对象树收集所有节点（不仅限于顶层数组）。
    这是扩展方案的关键创新——节点可能嵌套在 Section.children 或其他容器中。
    """
    nodes = {}
    seen = set()

    def walk(obj):
        if obj is None or not isinstance(obj, (dict, list)):
            return
        if isinstance(obj, list):
            for item in obj:
                walk(item)
            return
        obj_id = id(obj)
        if obj_id in seen:
            return
        seen.add(obj_id)

        class_name = obj.get("_", "")
        if class_name in PROJECT_NODE_TYPES:
            uuid = obj.get("uuid", "")
            if uuid and uuid not in nodes:
                text = get_node_text(obj, class_name)
                nodes[uuid] = {
                    "uuid": uuid,
                    "type": class_name,
                    "text": text,
                    "pos": get_position(obj),
                    "raw": obj,
                }

        for key, val in obj.items():
            if isinstance(val, (dict, list)):
                walk(val)

    for item in root:
        walk(item)
    return nodes


def collect_edges(root: list, nodes: dict) -> list:
    """收集所有边（LineEdge, ArcEdge, MultiTargetUndirectedEdge 等）"""
    edges = []
    seen = set()

    def walk(obj):
        if obj is None or not isinstance(obj, (dict, list)):
            return
        if isinstance(obj, list):
            for item in obj:
                walk(item)
            return
        obj_id = id(obj)
        if obj_id in seen:
            return
        seen.add(obj_id)

        class_name = obj.get("_", "")

        if class_name in ("LineEdge", "ArcEdge", "CubicCatmullRomSplineEdge"):
            assoc = obj.get("associationList", [])
            if isinstance(assoc, list) and len(assoc) >= 2:
                source = resolve_uuid(root, assoc[0])
                target = resolve_uuid(root, assoc[1])
                edge_text = obj.get("text", "")
                edges.append({
                    "source": source,
                    "target": target,
                    "text": edge_text,
                    "type": class_name,
                })

        elif class_name == "MultiTargetUndirectedEdge":
            assoc = obj.get("associationList", [])
            targets = []
            if isinstance(assoc, list):
                for a in assoc:
                    uid = resolve_uuid(root, a)
                    if uid:
                        targets.append(uid)
            if targets:
                edges.append({
                    "source": targets[0],
                    "target": targets[0],
                    "text": obj.get("text", ""),
                    "targets": targets,
                    "type": class_name,
                })

        for key, val in obj.items():
            if isinstance(val, (dict, list)):
                walk(val)

    for item in root:
        walk(item)
    return edges


def collect_section_hierarchy(root: list) -> tuple:
    """
    深度遍历收集 Section 包含关系。
    返回: (section_children, child_to_parent)
    """
    section_children = {}
    child_to_parent = {}
    seen = set()

    def walk(obj):
        if obj is None or not isinstance(obj, (dict, list)):
            return
        if isinstance(obj, list):
            for item in obj:
                walk(item)
            return
        obj_id = id(obj)
        if obj_id in seen:
            return
        seen.add(obj_id)

        if obj.get("_") == "Section":
            sec_uuid = obj.get("uuid", "")
            children_raw = obj.get("children", [])
            if sec_uuid and isinstance(children_raw, list) and children_raw:
                children = []
                for child in children_raw:
                    uid = resolve_uuid(root, child)
                    if uid:
                        children.append(uid)
                        child_to_parent[uid] = sec_uuid
                section_children[sec_uuid] = children

        for key, val in obj.items():
            if isinstance(val, (dict, list)):
                walk(val)

    for item in root:
        walk(item)
    return section_children, child_to_parent


# ====================================================================
# 4. 图片提取（Base64 Data URI）
# ====================================================================

def extract_images_as_datauri(prg_path: str) -> dict:
    """
    从 .prg (ZIP) 中提取 `attachments/` 下的图片，
    转为 Base64 Data URI。
    返回: {attachment_uuid: "data:image/png;base64,..."}
    """
    image_map = {}
    with zipfile.ZipFile(prg_path, "r") as zf:
        for name in zf.namelist():
            if not name.startswith("attachments/"):
                continue
            basename = os.path.basename(name)
            uuid_part = os.path.splitext(basename)[0]
            ext = os.path.splitext(basename)[1].lower().lstrip(".")
            mime = MIME_MAP.get(ext, f"image/{ext}")
            try:
                data = zf.read(name)
                b64 = base64.b64encode(data).decode("ascii")
                image_map[uuid_part] = f"data:{mime};base64,{b64}"
            except Exception:
                continue
    return image_map


# ====================================================================
# 5. 层级构建
# ====================================================================

def build_hierarchy(nodes, edges, section_children, child_to_parent):
    """构建顶层节点列表和边图"""
    edge_graph = defaultdict(list)

    for edge in edges:
        src, tgt = edge.get("source"), edge.get("target")
        if src and tgt:
            edge_graph[src].append({"target": tgt, "text": edge.get("text", "")})
        if edge.get("type") == "MultiTargetUndirectedEdge":
            for t in edge.get("targets", []):
                if t and t != src:
                    edge_graph[src].append({"target": t, "text": ""})

    def sort_key(uuid):
        node = nodes.get(uuid)
        if node and node.get("pos"):
            return (node["pos"][1], node["pos"][0])
        return (float("inf"), float("inf"))

    top_level = []
    for uuid in nodes:
        if uuid in child_to_parent:
            continue
        top_level.append(uuid)
    top_level.sort(key=sort_key)

    sorted_sec = {}
    for sec_uuid, child_list in section_children.items():
        sorted_sec[sec_uuid] = sorted(child_list, key=sort_key)

    return top_level, sorted_sec, edge_graph


# ====================================================================
# 6. Markdown 生成（参考扩展的 reference-style 图片语法）
# ====================================================================

def generate_markdown(title, nodes, top_level, section_children, edge_graph,
                       image_datauri_map):
    """生成 Markdown，使用 Data URI 内嵌图片"""
    lines = []
    lines.append("---")
    lines.append(f"title: {title}")
    lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("tags:")
    lines.append("  - 思维导图")
    lines.append("  - 技术笔记")
    lines.append(f"description: {title} - 从思维导图自动导出")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")

    text_count = sum(1 for n in nodes.values() if n["type"] == "TextNode")
    sec_count = sum(1 for n in nodes.values() if n["type"] == "Section")
    edge_count = sum(len(v) for v in edge_graph.values())

    lines.append(f"> 📊 **{text_count}** 个文本节点 · **{sec_count}** 个分组 · **{edge_count}** 条连线")
    lines.append("")

    visited = set()
    image_refs = {}  # ref_key → data_uri
    ref_idx = [0]    # mutable counter

    def write_image_node(node, indent):
        attachment_id = node["raw"].get("attachmentId", "")
        data_uri = image_datauri_map.get(attachment_id)
        if data_uri:
            ref_idx[0] += 1
            ref_key = f"img-{ref_idx[0]}"
            image_refs[ref_key] = data_uri
            # 图片引用必须顶格写，否则 Markdown 解析器可能不识别
            lines.append(f"![图片][{ref_key}]")
            if indent:
                lines.append(f"{indent}> 🖼️ *(上图引用自思维导图附件)*")
        else:
            lines.append(f"> 🖼️ *(图片附件未找到)*")

    def render_node(uuid, depth=0, as_heading=True):
        if uuid in visited:
            return
        visited.add(uuid)
        node = nodes.get(uuid)
        if not node:
            return
        text = node["text"].strip()
        node_type = node["type"]

        if as_heading:
            if node_type == "TextNode" and text:
                heading = "#" * min(depth + 2, 6)
                lines.append(f"{heading} {text}")
            elif node_type == "Section":
                heading = "#" * min(depth + 2, 6)
                lines.append(f"{heading} 📁 {text or '未命名分组'}")
            elif node_type == "ImageNode":
                write_image_node(node, "")
            else:
                if text:
                    lines.append(f"- {text}")
        else:
            if node_type == "TextNode" and text:
                lines.append(f"{'  ' * depth}- {text}")
            elif node_type == "Section":
                lines.append(f"{'  ' * depth}- 📁 **{text or '未命名分组'}**")
            elif node_type == "ImageNode":
                write_image_node(node, "  " * depth)

        # 1. Section 子节点
        for child_uuid in section_children.get(uuid, []):
            render_node(child_uuid, depth + 1, as_heading)

        # 2. Edge 连接的子节点
        outgoing = edge_graph.get(uuid, [])
        for edge_info in outgoing[:5]:  # limit depth
            tgt_uuid = edge_info["target"]
            if tgt_uuid not in visited:
                edge_text = edge_info.get("text", "").strip()
                tgt_node = nodes.get(tgt_uuid, {})
                tgt_text = tgt_node.get("text", "").strip()
                if edge_text and edge_text != tgt_text:
                    lines.append(f"{'  ' * depth}> 💬 *{edge_text}*")
                render_node(tgt_uuid, depth + 1, False)

    # 渲染顺序：Section 优先，再 TextNode
    for uuid in top_level:
        if nodes[uuid]["type"] == "Section":
            render_node(uuid)
            lines.append("")
    for uuid in top_level:
        if nodes[uuid]["type"] != "Section":
            render_node(uuid)
            lines.append("")

    # 未归类节点
    leftovers = [u for u in nodes if u not in visited]
    if leftovers:
        lines.append("---")
        lines.append("## 📌 未归类节点")
        lines.append("")
        leftovers.sort(key=lambda u: nodes[u].get("pos", (0, 0))[1] if nodes[u].get("pos") else 0)
        for uuid in leftovers:
            node = nodes[uuid]
            text = node["text"].strip()
            if node["type"] == "ImageNode":
                write_image_node(node, "")
            elif text:
                prefix = "📁 " if node["type"] == "Section" else ""
                lines.append(f"- {prefix}{text}")

    # 图片引用表（放在文末）
    if image_refs:
        lines.append("")
        for ref_key, data_uri in image_refs.items():
            lines.append(f"[{ref_key}]: {data_uri}")

    return "\n".join(lines)


# ====================================================================
# 7. 主函数
# ====================================================================

def convert_prg_to_markdown(prg_path: str, output_path: str = None) -> str:
    """
    将 .prg (思维导图项目) 转为自包含 Markdown。
    返回生成的 Markdown 文件路径。
    """
    if not os.path.exists(prg_path):
        raise FileNotFoundError(f"文件不存在: {prg_path}")

    title = os.path.splitext(os.path.basename(prg_path))[0]
    print(f"📦 解析: {prg_path}")

    # 读取 msgpack
    with zipfile.ZipFile(prg_path, "r") as zf:
        data = msgpack.unpackb(zf.read("stage.msgpack"), raw=False)

    root = data if isinstance(data, list) else []
    print(f"  顶层对象: {len(root)} 个")

    # 深度收集
    nodes = collect_nested_nodes(root)
    edges = collect_edges(root, nodes)
    section_children, child_to_parent = collect_section_hierarchy(root)
    image_map = extract_images_as_datauri(prg_path)

    print(f"  节点: {len(nodes)} | 边: {len(edges)} | 图片: {len(image_map)}")

    # 构建层级
    top_level, sorted_sec, edge_graph = build_hierarchy(
        nodes, edges, section_children, child_to_parent
    )

    # 生成 Markdown
    md = generate_markdown(
        title, nodes, top_level, sorted_sec, edge_graph, image_map
    )

    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(prg_path),
            f"{title}.md"
        )
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    file_size = os.path.getsize(output_path)
    print(f"✅ 已生成: {output_path} ({file_size / 1024:.0f} KB, 含 {len(image_map)} 张内嵌图片)")
    return output_path


# ====================================================================
# 8. 批量转换
# ====================================================================

def batch_convert(directory: str, output_dir: str) -> list:
    """批量转换目录下所有 .prg 文件"""
    results = []
    for filename in os.listdir(directory):
        if not filename.endswith(".prg"):
            continue
        prg_path = os.path.join(directory, filename)
        out_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.md")
        try:
            result = convert_prg_to_markdown(prg_path, out_path)
            results.append(result)
        except Exception as e:
            print(f"  ❌ {filename}: {e}")
    return results


# ====================================================================
# CLI
# ====================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python prg_to_markdown_v6.py <file.prg> [output.md]")
        print("  python prg_to_markdown_v6.py --batch <目录> <输出目录>")
        print()
        print("示例:")
        print('  python prg_to_markdown_v6.py "D:/思维导图/毛发渲染.prg"')
        print('  python prg_to_markdown_v6.py --batch "D:/思维导图" "D:/blog/content/Tech-Notes"')
        sys.exit(1)

    if sys.argv[1] == "--batch":
        if len(sys.argv) < 4:
            print("❌ --batch 需要两个参数: <目录> <输出目录>")
            sys.exit(1)
        batch_convert(sys.argv[2], sys.argv[3])
    else:
        prg_file = sys.argv[1]
        out_file = sys.argv[2] if len(sys.argv) > 2 else None
        convert_prg_to_markdown(prg_file, out_file)
