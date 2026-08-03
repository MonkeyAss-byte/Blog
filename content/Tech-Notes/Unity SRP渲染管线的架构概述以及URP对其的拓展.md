---
title: Unity SRP渲染管线的架构概述
date: 2026-07-29
tags:
  - UnitySRP
description: 对之前的URP管线的代码表述，进一步对SRP的底层框架做一次理解与概述
---

# Unity SRP渲染管线的设计解析

> 目的为对 SRP 的框架进行理解，理解其 ***必要的部分与原理***，并非对非必要细节进行逐词翻译。

---

## 一、SRP 渲染管线与 Unity 底层调用渲染指令的联系

![[Pasted image 20260729210632.png|697]]

---

## 二、RenderPipelineAsset

### 1.1 成员

#### 1.1.1 虚拟成员
##### 属性 (get; set;)
- `defaultMaterial` (在编辑器中物体的默认 material)
- `defaultShader` (在编辑器中物体的默认 shader)
- `renderPipelineShaderTag` (对应于 shaderlab 的 renderpipline tag)
- ...

##### 方法
- `OnValidate()` (在编辑器中修改参数时调用)
- ...

#### 1.1.2 抽象成员
##### 方法
- **`CreatePipeline(this)` (实例化 RenderPipeline)**

---

## 三、RenderPipeline

#### 关键方法
- **`RenderInternal(context, cameras)`** (调用 Render)
- **`Render(context, cameras)`** (abstract)

> 以上为 SRP 的最基础的架构，即使没有 URP 对于 Renderer、Pass、RendererFeature 的抽象，依然可以通过直接对 context 进行指令填充，实现简单的渲染管线。
>
> **渲染基础流程：**
> - `RenderPipeline.Render(context, cameras[])`
>   ↓
>   - [逐相机循环]
>     ↓
>     - `context.SetupCameraProperties(camera)` ← 同步 MVP 矩阵到 GPU
>       ↓
>     - `camera.TryGetCullingParameters()` ← 准备剔除参数
>       ↓
>     - `context.Cull()` ← CPU 侧视锥体/遮挡剔除
>       ↓
>     - `cmd.ClearRenderTarget()` ← 清理 FrameBuffer
>       ↓
>     - `context.DrawRenderers()` [Opaque] ← 不透明物体渲染
>       ↓
>     - `context.DrawSkybox()` ← 天空盒渲染
>       ↓
>     - `context.DrawRenderers()` [Transparent] ← 半透明物体渲染
>       ↓
>     - `context.Submit()` ← 将 CommandBuffer 批量提交 GPU 执行

---

# URP 对 SRP 的拓展

> 目的为 URP 基于 SRP 的框架的拓展进行理解，理解其 ***必要的部分与原理***，并非对非必要细节进行逐词翻译。

---

## 一、UniversalRenderPipelineAsset

### 1.1 关键改动或新增

#### 1.1.1 成员
##### 字段
- `m_RendererDataList`
- `m_Renderers`

##### 方法
- `CreatePipeline(this)` 
  - 核心逻辑：`{ rendererdata.create() added }`
  
---

## 二、UniversalRenderPipeline

### 1.1 关键改动或新增

#### 1.1.1 成员
##### 属性
- `asset` (`pipelineAsset`)
- ...

##### 方法
- `Render(...)` 
  - 核心逻辑：`{ **sortCameras** (深度+是否渲染到 RenderTexture) -> **RenderCameraStack**(Base), for x in **Base.cameraStack，RenderSingleCamera**(x) }`
- `RenderSingleCamera(...)`
  - 核心逻辑：`{ TryGetCullingParameters -> context.Cull() -> 读取 camera.UniversalAdditionalCameraData -> 获取绑定 Renderer (从 asset 获得) -> 装配 renderingData -> renderer.AddRenderPasses (foreach features.AddRenderPasses) -> renderer.Setup(context, ref renderingData) -> renderer.Execute(context, ref renderingData) }`
- ...
  
---

## 三、ScriptableRendererData

### 1.1 成员
#### 1.1.1 正常成员
##### 属性
- `rendererFeatures` (SO)

#### 1.1.2 抽象成员
##### 方法
- **`Create(this)` (实例化 Renderer)**

---

## 四、ScriptableRenderer

### 1.1 成员
#### 1.1.1 正常成员
##### 字段
- `asset`

##### 构造方法
- `Renderer(...)`
  - 核心逻辑：`{ new xxxpass(...)..., this.asset = asset }`

##### 方法
- `Execute(...)`
  - 核心逻辑：`{ for pass in passes, pass.OnCameraSetup(...) -> context.ExecuteCommandBuffer(cmd) -> SortStable(passes) by renderpassEvent -> SetBlockRanges(设置每个 Block 包括的 passIndexRange, 一般共四个) -> for pass in passes, pass.Configure(...) -> ExecuteBlock(...) { for pass in passesInBlock, setRendererPassAttachments(...(判断并懒设置 RenderTarget)), pass.Execute(...) } four times (**BeforeRendering**，**MainRenderingOpaque**，**MainRenderingTransparent**，**AfterRendering**) -> for pass in passes, pass.OnCameraCleanup(...) }`

#### 1.1.2 抽象成员
##### 方法
- `Setup(...)`
  - 核心逻辑：`{ alloc cameraTarget from cameraData -> alloc RT and passes from passes in features configureinput + Enqueue(xxxpass) + features.SetupRenderPasses(...) }`

---

## 五、ScriptableRenderPass

### 1.1 成员

#### 1.1.1 正常成员
##### 属性
- `colorAttachments`
- `depthAttachment`
- `clearFlag`
- `clearColor`
- `renderPassEvent`
- `m_Input`
- ...

##### 方法
- `ConfigureTarget()`
- `ConfigureClear()`
- `ConfigureInput()`
  
#### 1.1.2 抽象成员
##### 方法
- `Execute(...)`

#### 1.1.3 虚拟成员
##### 方法
- `OnCameraSetup(...)`
- `Configure(...)`
- `OnCameraCleanup(...)`
- `ResetRenderTarget(...)`

---

## 六、ScriptableRendererFeature

### 1.1 成员

#### 1.1.1 抽象成员
##### 方法
- `Create(...)`
- `AddRenderPasses(...)`

#### 1.1.2 虚拟成员
##### 方法
- `SetupRenderPasses(...)`
- `Dispose(...)`
  
---

> 以上对于 URP 的 ***必要的部分与原理*** 进行了理解与分析，以下分别为实例化渲染管线与每帧渲染的精简示意图：

```mermaid
graph TD
    A[Project Settings] -->|在 Graphics 槽位中分配| B(UniversalRenderPipelineAsset)
    
    B -.->|Unity 底层事件触发| C[RenderPipelineManager]
    C -->|1. 请求创建管线实例| D(Asset.CreatePipeline)
    
    D -->|2. 提取并调用| E[Asset.CreateRenderers]
    E -->|3. 根据传入的 RendererData| F(实例化 UniversalRenderer)
    
    F -.->|4. Renderer 构造时, 提取 Data 里的 Features| G[遍历 ScriptableRendererFeature]
    G -.->|5. 触发 Feature 生命周期的第一步| H(feature.Create)
    
    H -.->|6. 开发者手写逻辑| I[new MyCustomPass: 实例化 Pass]
```

> ***以上为管线实例化过程***

```mermaid
graph TD
    A[UniversalRenderPipeline.Render 传入多个摄像机] --> B(1. SortCameras: 按 TargetTexture 有无 以及 Depth 大小排序)
    B --> C[2. 主循环：遍历所有 Camera]
    
    C --> D{检查 Camera 的 RenderType}
    
    D -- Overlay --> E[直接忽略跳过<br>不能作为独立主入口]
    
    D -- Base --> F[3. 进入 RenderCameraStack]
    
    F -.-> G[3.1 执行 RenderSingleCamera<br>渲染 Base 摄像机本身]
    G -.-> H[3.2 遍历 Base 相机的 cameraStack]
    H -.-> I[3.3 依次执行 RenderSingleCamera<br>渲染叠加的 Overlay 摄像机]
```

> ***以上为在 RenderSingleCamera 之前的相机排序过程***
  
```mermaid
graph TD
    A[RenderSingleCamera] --> B(① renderer.AddRenderPasses)
    A --> C(② renderer.Setup)
    A --> D(③ renderer.Execute)
    
    B -.-> B1[Feature.AddRenderPasses]
    B1 -.-> B2[① 声明需求 ConfigureInput<br>② 占位入队 EnqueuePass<br>状态: 拿着假Target]
    
    C -.-> C1[遍历队列查需求 pass.input]
    C1 -.-> C2[根据需求分配真实 RenderTarget]
    C2 -.-> C3[官方基础 Pass 入队]
    C3 -.-> C4[Feature.SetupRenderPasses]
    C4 -.-> C5[拿到真实Target, 替换Pass中的假Target]
    
    D -.-> D1[SortStable: 按 Event 全局排序]
    D1 -.-> D2[Block 归纳: 划定 startIndex 与 endIndex]
    D2 -.-> D3[调用所有 Pass 的 Configure]
    D3 -.-> D4[按 Block 顺序执行]
    D4 -.-> D5[Block 内循环: 懒设置 SetRenderTarget]
    D5 -.-> D6[调用 pass.Execute]
```

> ***以上为在 RenderSingleCamera 之后的 URP 的渲染过程***