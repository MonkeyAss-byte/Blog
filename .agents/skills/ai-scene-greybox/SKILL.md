---
name: ai-scene-greybox
description: >-
  Stage 1 of the 3D Asset Pipeline: Spatial greybox alignment, 2D concept lock, camera frustum matching,
  and semantic asset manifest generation via UE MCP Vision-Action Closed Loop. Use when initializing a new scene layout or creating scene_manifest.json.
---

# 阶段一：场景构思与空间白模定焦 (Concept & Spatial Greybox Alignment)

本 Skill 专门负责在不耗费 3D 扩散算力前，通过 **UE MCP (`http://127.0.0.1:8000/mcp`)** 实时驱动引擎搭建场景几何骨架、闭环比对摄像机透视视锥与全景资产技术规格，提供绝对的**空间真值（Ground Truth）**。

---

## 一、输入与输出契约 (Contract)

* **输入（Precondition）**：用户场景创意描述、关键词或 2D 概念参考图；
* **输出（Postcondition）**：`scene_manifest.json`（持久化记录每个资产的空间 Transform、包围盒 Bound、语义类型与材质槽意图）。

---

## 二、五大执行步骤与技术准则

### 1. 2D 概念设计定调与视角工程 (Concept Art & Perspective Engineering)
* **视角铁律：必须为 35°～45° 斜三四分之三视角 (Three-Quarter Front View)**：
  * *理论根基*：纯正交正视图缺乏 Z 轴进深信息，极易导致 3D 扩散模型产生“对称性幻觉”（误将正面屏幕特征镜像复制到侧面，形成侧面开窗、内部塞球的畸形网格）；35°~45° 斜视图同时暴露出【正面屏幕】、【侧面封闭塑料壳的厚度与进深】与【顶板】，强制 3D 视觉模型构建实心长方体空间认知。
* **背景清理准则**：必须经由 RMBG 剔除阴影，未抠图的地面灰色投影会被 3D 扩散模型实体化成底座下方的“一滩泥”。

### 2. 2D 视觉语义标注与灯光拓扑拆解 (Concept Asset & Lighting Breakdown)
在启动任何 3D 资产生成或引擎搭建前，必须基于概念图完成两份标准化视觉反思标注（作为阶段一到阶段五的技术对标真值）：
* **标注 A：场景 3D 资产拆解与制作清单 (Scene 3D Asset Breakdown)**：
  * 🖵 **电子与算力核心 (Core Electronics)**：复古 CRT 显示器（多形态/发光屏）、90 年代立式塔式主机、老式机械键盘/鼠标与桌面杂物；
  * 🪑 **家具与陈列设施 (Furniture)**：白色折叠长条办公桌（多张拼接）、蓝色金属折叠椅（前/中景多把）、桌底备用机箱/托架；
  * 🧱 **建筑与模块化结构 (Modular Arch)**：白色地铁瓷砖墙体（带微旧/污损）、顶面工业混凝土天花与排风管道、空间中央承重工字钢柱/梁、右侧铁质百叶卷帘门；
  * 🔌 **电气管线与环境细节 (Lighting & Props)**：悬吊式工业双管荧光吊灯、墙面走线软管/排插/地面电缆、墙面告示板/极客海报贴花、地面散落书籍/杂志/杂物。
* **标注 B：场景完整灯光拓扑与类型拆解 (Scene Lighting & Types Breakdown)**：
  * 💡 **天花板实用光源 (Overhead Fixtures)**：
    * `[L01/L02]` 前排双管荧光吊灯（主照明）$\rightarrow$ 引擎类型：`Rect Light`（冷白 5500K，高照度）
    * `[L03/L04]` 纵深背景荧光灯（景深补光）$\rightarrow$ 引擎类型：`Rect Light`（冷白 5000K，中照度）
  * 🟢 **屏幕自发光与色相补光 (CRT Emissive)**：
    * `[L05]` 中央 CRT 粉色屏幕（高饱和洋红）$\rightarrow$ 引擎类型：`Emissive` + 微弱 `Rect Light` 局部补光
    * `[L06/L07]` 右侧桌面蓝光屏与高亮白屏 $\rightarrow$ 引擎类型：`Emissive` + 局部面光源补光
  * 🟣 **地面堆积微光 (Ground Displays)**：
    * `[L08]` 左侧地面堆积青光屏 $\rightarrow$ 引擎类型：`Point Light` / `Emissive` (Teal)
    * `[L09]` 右侧地面靠椅紫光屏 $\rightarrow$ 引擎类型：`Point Light` / `Emissive` (Purple)
  * 🔵 **环境溢色与细节 (Spill & Accent)**：
    * `[L10]` 左侧门洞外冷青色大范围环境溢光 $\rightarrow$ 引擎类型：`Spot Light` / `Directional Bounce`
    * `[L11]` 电脑机箱微弱电源指示 LED $\rightarrow$ 引擎类型：`Tiny Point Light` (Amber / Red)

### 3. UE MCP 语义白模搭建 (Semantic Greybox)
* 调用 `editor_toolset.toolsets.scene.SceneTools` 放置基础几何图元，赋予鲜艳特征色编码：
  * 🟩 **工位桌 (Tables)**：绿色图元，标定工位排布；
  * 🟦 **显示器/主机 (Monitors & PC)**：蓝色图元，标定视觉焦点道具；
  * 🟨 **展板/告示/贴花 (Decals & Posters)**：黄色平面，标定投影表面；
  * ⬜ **立柱/墙体 (Walls & Columns)**：白色几何体，标定房间轮廓；
  * 💡 **荧光灯条 (Ceiling Lights)**：自发光图元，标定主光源位置。

### 4. 机位对齐与物理吸附闭环 (Camera Frustum & Physics Snapping Loop)
* **视口抓帧与比对**：
  * 调用 `EditorToolset.EditorAppToolset.SetCameraTransform` 锁定摄像机机位（如 Hero Camera: $X=-250, Y=-180, Z=140, Pitch=-14^\circ, Yaw=36^\circ$）；
  * 调用 `CaptureViewport(bShowUI=False)` 抓取视口渲染帧；
  * VLM 将视口渲染与概念图深度透视严格比对（透视灭点、视锥 FOV、物体空间进深）。
* **神经-符号物理吸附约束 (Physics-Informed Neuro-Symbolic Snapping)**：
  * 地面接触面基准锁死：$Z_{floor} = 0.0\text{ cm}$；
  * 桌面吸附基准面锁死：$Z_{table} = 75.0\text{ cm}$；
  * 显示器、机箱底面自动吸附于 $Z = 75.0\text{ cm}$，彻底杜绝悬空或穿模。

### 5. 导出全景资产与灯光拓扑语义清单 (Semantic Asset & Lighting Manifest)
将所有白模及灯光参数分别映射，输出 `scene_manifest.json`：
```json
{
  "scene_id": "RetroServerRoom_V2",
  "camera": {"location": [-250.0, -180.0, 140.0], "rotation": [-14.0, 36.0, 0.0], "fov": 65.0},
  "ground_plane_z": 0.0,
  "assets": [
    {
      "id": "CRT_Monitor",
      "name": "V2_SM_CRT_Monitor",
      "semantic_type": "PROP_PBR",
      "target_transform": {"location": [0.0, 0.0, 75.0], "rotation": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0]},
      "contact_plane_z": 75.0,
      "needs_partition": true,
      "partition_spec": {"part_prompt": "screen", "slot_0_name": "M_Chassis", "slot_1_name": "M_Screen", "remap_uv_01": true}
    }
  ],
  "lighting_topology": [
    {
      "id": "L01_L02_Overhead_Fluorescent_Front",
      "type": "RectLight",
      "role": "Primary_Overhead",
      "color_temp_k": 5500,
      "intensity": 3500.0,
      "location": [0.0, -100.0, 260.0],
      "mobility": "Movable"
    },
    {
      "id": "L05_CRT_Screen_Emissive_Pink",
      "type": "Emissive_Plus_RectLight",
      "role": "Screen_Magenta",
      "color_rgb": [1.0, 0.08, 0.58],
      "intensity": 3.0,
      "target_asset": "V2_SM_CRT_Monitor_02"
    },
    {
      "id": "L10_Doorway_Spill_Cyan",
      "type": "SpotLight",
      "role": "Ambient_Spill",
      "color_rgb": [0.0, 0.8, 0.9],
      "intensity": 5000.0,
      "mobility": "Movable"
    }
  ]
}
```

---

## 三、开箱脚本调用指引

```bash
# 生成并验证场景清单
python .agents/skills/ai-scene-greybox/scripts/greybox_builder.py --output scene_manifest.json
```
产出 `scene_manifest.json` 后，状态机更新 `STAGE_1_GREYBOX = COMPLETED`，推进至阶段二。
