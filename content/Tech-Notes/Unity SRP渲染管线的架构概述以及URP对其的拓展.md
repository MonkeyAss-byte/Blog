---
title: Unity SRP渲染管线的架构概述
date: 2026-07-29
tags:
  - UnitySRP
description: 对之前的URP管线的代码表述，进一步对SRP的底层框架做一次理解与概述
---

# Unity SRP渲染管线的设计解析

> 目的为对SRP的框架进行理解，理解其***必要的部分与原理***，并非对非必要细节进行逐词翻译

---

## 一、SRP渲染管线与Unity 底层调用渲染指令的联系

![[Pasted image 20260729210632.png|697]]

---

## 二、RenderPipelineAsset

### 1.1 成员
#### 1.1.1 虚拟成员
#### 属性(get)
 - defaultMaterial(在编辑器中物体的默认material)
 - defaultShader(在编辑器中物体的默认shader)
 - renderPipelineShaderTag(对应于shaderlab的renderpipline tag)
 - ...
#### 方法
- OnValidate()(在编辑器中修改参数时调用)
- ...
#### 1.1.2  抽象成员
#### 方法
- **CreatePipeline(this) (实例化RenderPipeline)**


## 三、RenderPipeline

#### 关键方法
- **RenderInternal(context,cameras)** (调用Render)
- **Render(context,cameras)(abstract)**



> 以上为SRP的最基础的架构，即使没有URP对于Renderer,Pass,RendererFeature的抽象，依然可以通过直接对context进行指令填充，实现简单的渲染管线

- RenderPipeline.Render(context, cameras[])
    ↓
  - [逐相机循环]
    ↓
  - context.SetupCameraProperties(camera)    ← 同步 MVP 矩阵到 GPU
    ↓
  - camera.TryGetCullingParameters()         ← 准备剔除参数
    ↓
  - context.Cull()                           ← CPU 侧视锥体/遮挡剔除
    ↓
  - cmd.ClearRenderTarget()                  ← 清理 FrameBuffer
    ↓
  - context.DrawRenderers() [Opaque]         ← 不透明物体渲染
    ↓
  - context.DrawSkybox()                     ← 天空盒渲染
    ↓
  - context.DrawRenderers() [Transparent]    ← 半透明物体渲染
    ↓
  - context.Submit()                         ← 将 CommandBuffer 批量提交 GPU 执行


---
# URP对SRP的拓展

> 目的为URP基于SRP的框架的拓展进行理解，理解其***必要的部分与原理***，并非对非必要细节进行逐词翻译

---

## 一、UniversalRenderPipelineAsset
## 二、UniversalRenderPipeline
## 三、ScriptableRenderer
## 四、ScriptableRenderPass
## 五、ScriptableRendererFeature
