# 6 大核心资产工作流技术规格与学术理论说明 (Workflows Specification)

本文件详细阐述了 AI 3D 资产生产管线中 6 大核心工作流的学术理论基础、节点拓扑架构、物理通道映射规范与显存预算配置。

---

## 零、学术理论与国际顶会技术突破支撑

本管线深度融合了近年国际图形学与生成式 AI 顶会（SIGGRAPH / CVPR）的里程碑突破：

1. **OmniPart: Part-Aware 3D Generation with Semantic Decoupling (SIGGRAPH Asia 2025)**：
   * 针对传统 3D 扩散模型只能生成单一不可拆分网格（Monolithic Mesh）的缺陷，提出了**“语义解耦与面组结构划分”**。
   * 本管线在工业级量产中采用其核心思想：网格拓扑保持轻量单层，但面组进行多材质槽划分（Multi-Material Slots）与 UV01 空间解耦。
2. **PartGen: Part-level 3D Generation with Multi-View Diffusion (CVPR 2025 Highlight)**：
   * 从单张概念图重构出具有独立层级部件的 3D 资产，赋予关键功能区域（如屏幕）独立的局部坐标系和规整平展 UV，彻底解决全局 UV 碎裂无法挂载 Shader / 动态界面的难题。
3. **MAGE: Material-Aware 3D via Multi-View G-Buffer Estimation (CVPR 2025)**：
   * 解决传统 3D 模型“光照烘死、无 PBR 物理反射”的致命痛点，通过多视角扩散模型反求 G-Buffer（Albedo, Roughness, Metallic, NormalGL），实现与现代实时引擎（UE5 Lumen）的动态交互。
4. **Paint3D: Paint Anything 3D with Lighting-Less Texture Diffusion (CVPR 2024)**：
   * 确立了无光照（Lighting-Less）固有色生成与 UV 空间多视角融合的数学基础。
5. **Ubisoft Chord (SIGGRAPH Asia 2025)**：
   * 工业级 PBR 通道物理估计网络，将 2D 固有色精准解构为切线空间法线、微表面粗糙度与金属度。

---

## 一、6 大核心工作流详细规格

### 01. 搭配平铺工作流 (Texture Semantics)
* **适用场景**：超大物体、地形、建筑结构、房间地砖、大面积墙体白模。
* **特性**：不依赖 3D 扩散模型，直接对几何体表面施加连续无缝（Seamless Tileable）PBR 材质（BaseColor、ORM、Normal、Displacement）。
* **核心架构**：FLUX.1-dev / Rayflux (DiT + T5-XXL 4.7B) + Universal-Seamless-Tiles (潜空间滚动+环形VAE) + Ubisoft Chord + ORM 工业通道打包。
* **技术优势**：T5-XXL 深度解析空间从属；12B MM-DiT 双流自注意力锁死 90° 水平垂直网格，杜绝传统 SDXL 卷积局部感受野导致的砖缝 10°~15° 倾斜走样。

### 02. 贴花工作流 (Decal Texture: 透明贴花分支)
* **适用场景**：机甲局部编号、警示标志、战损划痕、孤立贴纸、污渍、涂鸦。
* **特性**：生成带透明通道（RGBA）的高分辨率贴花图层。
* **技术链路**：ComfyUI 扩散出图 $\rightarrow$ RMBG-2.0 自动扣除背景 $\rightarrow$ 导出带 Alpha 通道及专用 Normal/ORM 的透明贴花。
* **引擎配置**：DecalActor 绑定 `DBuffer_TranslucentColorNormalRoughness`。

### 03. 基础文生图元工作流 (Base Text to Image: 概念图、屏幕与实体海报)
* **适用场景**：
  1. **3D 概念生成**：生成 3D 扩散模型的正面设计图（Hero Front Image）；
  2. **道具屏幕内容**：生成终端代码界面、UI、示波器波形等屏幕贴图；
  3. **实体海报与告示看板（不透明贴花分支 `transparent=False`）**：
     * **核心洞察**：海报、操作展板、警示告示牌本身是完整的规则矩形画面，**绝对不应使用 RMBG 扣除背景**（避免破坏海报画面完整性）；
     * **引擎配置**：作为 DecalActor 贴附于墙体/物体表面，材质绑定 `DBuffer_ColorNormalRoughness`（实体投影）。

### 04. 3D 几何与 PBR 纹理生成工作流 (端云双通道)

#### 04-A. Tripo_3d_WithTex (云端 3D 极速通道 - 推荐首选)
* **适用场景**：独立道具、复杂工业设备、主视觉资产（Hero Props）的极速工业级建模与纹理生成。
* **特性**：
  * **耗时极短**：单模型端到端仅需 **15 ~ 20 秒**；
  * **0 本地显存**：将复杂的 3D 几何拓扑解算与多视角扩散反投影上云，避免本地消费级显卡（8GB/16GB）的 PCIe 共享显存颠簸与 OOM；
  * **高质量原生 PBR 纹理**：原生预测并输出高分辨率 `BaseColor`、标准 `ORM`（Occlusion/Roughness/Metallic）与切线空间法线 `NormalGL`。
* **节点拓扑**：`LoadImage` $\rightarrow$ `RMBG (RMBG-2.0 自动抠除背景)` $\rightarrow$ `TripoImageToModelNodeV2 (v2.5-20250123 / PBR enabled)` $\rightarrow$ `Save3DAdvanced (GLB 导出)`。

#### 04-B. 本地 3D 网格生成工作流 (Hunyuan 3D 2.1 Mesh Generation - 离线备用)
* **适用场景**：断网私有化、局域网安全环境下的离线几何建模备用通道。
* **核心模型**：混元 3D 2.1（DiT 结构预测 + VAE 稠密八叉树体素网格解码）。
* **RTX 4060 8GB 显存控制规范**：
  * `steps`: 10 ~ 15
  * `guidance_scale`: 5.0 ~ 6.0
  * `octree_resolution`: 384
  * `mc_algo`: `mc` (标准 Marching Cubes)
  * `force_offload`: `true` (生成 Latent 后立即卸载 DiT，释放全部 8GB 显存给 VAE 解码)。

### 05. 元数据多视角纹理工作流 (Mesh Texturing with Metadata RMBG)
* **技术链路**：
  1. `Load Image with Transparency`（RMBG 抠图透明底输入）；
  2. 多视角投影与相机参数标定（Camera Config）；
  3. 多视角扩散上色与 InPaint 补全遮挡盲区；
  4. 烘焙固有色 `albedo`、双通道物理贴图 `mr`（R=Metallic, G=Roughness）；
  5. 通过 `BakeAmbientOcclusion` 进行**单网格几何自烘焙 AO**；
  6. 通过 `Pack PBR Channels` 打包合成标准的 **ORM（Occlusion / Roughness / Metallic）** 贴图；
  7. 导出带标准 PBR 材质球的 `.glb` 资产。

### 06. 材质语义拆分与 UV 重构工作流 (Material Clip & Route B Bisect)
* **执行步骤**：
  1. **正交 6 视图渲染**：`blender_render_ortho.py` 以物体系包围盒导出 6 视角无透视畸变 RGBA 图；
  2. **SAM 2 语义分割**：输入单次语义词（如 `screen`），输出 2D 像素级二值 Mask；
  3. **Route B 物理 Knife 刀切**：`blender_knife_bisect.py` 沿轮廓构建挤压棱柱几何体，调用 Blender EXACT 求解器执行布尔物理相交切分，在原网格上生成全新交界顶点与三角面；
  4. **材质槽拆分**：Slot 0 赋给 `M_Chassis`，Slot 1 赋给 `M_SubPart`；
  5. **UV01 重构**：屏幕部件执行平面正交拉伸至 $[0, 1] \times [0, 1]$，机身保留原生烘焙 UV。

---

## 二、PBR 物理通道与通道打包工业规范

| 通道名称 | 格式 | 色彩空间 | 引擎连接映射 | 物理含义 |
| :--- | :--- | :--- | :--- | :--- |
| **Albedo / BaseColor** | RGB (.png) | sRGB | `BaseColor` | 纯净固有色（严禁烘焙明暗阴影与高光点） |
| **Normal** | Tangent Space (.png) | Linear / TC_Normalmap | `Normal` | 切线空间法线（微表面凹凸朝向） |
| **ORM (R 通道)** | 灰度 | Linear | `AmbientOcclusion` | 环境光遮蔽（几何缝隙自阴影） |
| **ORM (G 通道)** | 灰度 | Linear | `Roughness` | 微表面粗糙度（0.0镜面 ~ 1.0完全粗糙） |
| **ORM (B 通道)** | 灰度 | Linear | `Metallic` | 金属度（0.0绝缘体 ~ 1.0纯金属） |
| **Emissive** | RGB (.png) | sRGB | `Emissive` | 自发光表面（如 CRT 屏幕亮绿荧光） |
