---
title: BSDF 材质工作流 - 技术拆解
date: 2026-07-16
tags:
  - 图形渲染
  - BSDF
  - 次表面散射
  - Shader
  - Unity
description: 基于球谐函数的 BSDF 材质工作流技术拆解，涵盖 SH 深度烘焙、SSS/BRDF LUT 预计算、Kawase 模糊背景及实时 BSDF Shader 渲染管线
---

# BSDF 材质工作流技术文档

## 概述

本项目实现了一套基于 **Spherical Harmonics（球谐函数）** 的次表面散射（SSS）与透射（Transmittance）渲染管线。核心思路是：通过预烘焙将模型的厚度信息编码为 3 阶球谐系数（9 个系数）存入顶点 UV 通道，运行时在 Shader 中实时重建任意方向上的厚度，并结合预计算的 SSS LUT、BRDF LUT 以及 Kawase 模糊后的背景图，实现物理可信的半透明材质渲染。

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            BSDF 工作流全景图                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ① 球谐深度烘焙           ② SSS LUT 烘焙          ③ BRDF LUT 烘焙        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐       │
│  │ Cubemap → SH 系数 │    │ Burley 扩散曲线   │    │ NdotV × Roughness│      │
│  │ → Vertex UV2/3/4 │    │ + 球面圆截面积分   │    │ GGX 重要性采样    │       │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘       │
│           │                      │                      │                │
│           └──────────────────────┼──────────────────────┘                │
│                                  ▼                                       │
│                    ④ 渲染资源准备与队列设置                                 │
│                    ┌─────────────────────────┐                           │
│                    │ Opaque 后抓取背景图        │                           │
│                    │ Dual Kawase 降采样+上采样  │                           │
│                    │ 队列: AfterSkybox → BeforeTransparent │              │
│                    └─────────────────────────┘                           │
│                                  │                                       │
│                                  ▼                                       │
│                    ⑤ BSDF Shader 实时渲染                                 │
│                    ┌─────────────────────────┐                           │
│                    │ 直接光: Diffuse → SSS → Trans │                     │
│                    │ 环境光: IBL + 透射背景图       │                     │
│                    └─────────────────────────┘                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 一、球谐深度烘焙（Cubemap → SH → 顶点信息）

### 1.1 原理

对于每个顶点，从该顶点位置向所有方向发射射线，记录射线在模型内部穿行的距离（即厚度）。这本质上是一个 **6 面 Cubemap 深度图** 的采集过程。为了将 Cubemap 压缩为可存储在顶点中的数据，使用 **3 阶球谐函数（9 个系数）** 进行投影。

球谐基函数定义：

| 系数 | 表达式 | 含义 |
|------|--------|------|
| $Y_0$ | $0.2820947917$ | 常数项（平均厚度） |
| $Y_1$ | $0.4886025119 \cdot y$ | Y 方向线性 |
| $Y_2$ | $0.4886025119 \cdot z$ | Z 方向线性 |
| $Y_3$ | $0.4886025119 \cdot x$ | X 方向线性 |
| $Y_4$ | $1.0925484306 \cdot xy$ | XY 双线性 |
| $Y_5$ | $1.0925484306 \cdot yz$ | YZ 双线性 |
| $Y_6$ | $0.3153915652 \cdot (3z^2 - 1)$ | Z 二次项 |
| $Y_7$ | $1.0925484306 \cdot xz$ | XZ 双线性 |
| $Y_8$ | $0.5462742153 \cdot (x^2 - y^2)$ | XY 二次差 |

SH 投影公式：
$$c_l = \int_{\Omega} f(\omega) \cdot Y_l(\omega) \, d\omega$$

### 1.2 烘焙流程（ThicknessCompute.cs）

```
For each vertex:
  1. 将顶点置于统一 10m 烘焙沙盒中（scaleFactor = 10 / maxDim）
  2. 相机放到顶点位置 + 沿法线向内偏移 0.05m
  3. 使用 Cull Front 的 Thickness Shader 渲染到 128×128 Cubemap
     - 剔除正面 → 相机在模型内部看到对面的内壁
     - 输出: distance / 20.0（压缩到 0~1）
  4. 调用 GPU_Project_Uniform_9Coeff() 将 Cubemap 投影为 9 个 SH 系数
  5. 解码: 系数 × (20.0 / scaleFactor) → 恢复模型空间真实厚度
  6. 存储到 UV2, UV3, UV4 通道
```

### 1.3 顶点数据布局

| UV 通道 | 分量 | 内容 |
|---------|------|------|
| **UV2** | `.xyzw` | SH 系数 0~3（$Y_0$, $Y_1$, $Y_2$, $Y_3$） |
| **UV3** | `.xyzw` | SH 系数 4~7（$Y_4$, $Y_5$, $Y_6$, $Y_7$） |
| **UV4** | `.x` | SH 系数 8（$Y_8$） |
| **UV4** | `.y` | 顶点曲率（curvature，用于 SSS LUT） |

>**关键设计**：使用 `float4` 类型（TEXCOORD1/2/3）接收数据，而非 Unity 传统的 `COLOR` 通道（8-bit），保证了 32-bit 全精度，避免 SH 系数量化误差。

### 1.4 GPU 投影核心

#### Reduce_Uniform.compute

用于 Uniform 采样的 Cubemap → SH 投影：

```
For each coefficient (0~8):
  1. 6 个 cubemap face × 分辨率 → 3D Texture2DArray
  2. 每个像素: color × SH_Basis(dir) × DifferentialSolidAngle
  3. 多级 Reduce（8×8→4×4→2×2→1×1 树形归约）
  4. 输出单精度 float4 到 coefficients buffer
```

#### Reduce_MC_1024.compute

用于 Monte Carlo 采样的快速投影（1024 样本）：

```
1. 9 个 Pass 分别渲染 32×32 tile（3×3 布局 = 96×96 RT）
2. 每个 Pass 采样随机方向，乘对应 SH 基函数
3. 1024 线程并行归约（512→256→128→...→1）
4. 最终 × 4π × (1/1024) 归一化
```

### 1.5 相关文件

| 文件 | 作用 |
|------|------|
| `Editor/ThicknessCompute.cs` | Editor 窗口，驱动整个烘焙流程 |
| `Resources/Shaders/Thickness.shader` | Cull Front 的深度渲染 Shader |
| `Resources/Shaders/Reduce_Uniform.compute` | Uniform 采样的 GPU SH 投影 |
| `Resources/Shaders/Reduce_MC_1024.compute` | Monte Carlo 采样的 GPU SH 投影 |
| `Resources/Shaders/SH_Utils.hlsl` | SH 基函数 + 微分立体角 + Cubemap 方向映射 |
| `Scripts/SphericalHarmonics.cs` | C# 侧的 SH 工具类（CPU 投影、格式转换） |

---

## 二、SSS LUT 烘焙（平面圆扩散积分）

### 2.1 原理

SSS LUT 用于快速查询在给定 **光照角度（NdotL）** 和 **表面曲率** 下，次表面散射的出射强度。

核心模型：**Burley Normalized Diffusion**（迪士尼标准散射曲线）：
$$R(r, d) = \frac{e^{-r/d} + e^{-r/(3d)}}{8\pi \cdot d \cdot r}$$

其中 $r$ 是表面两点间的距离，$d$ 是散射距离。

### 2.2 积分方法：1D 圆环截面积分

```
LUT 布局: 128×128
  X 轴 (0→127): NdotL ∈ [-1, 1]  → 光照方向与表面法线的夹角
  Y 轴 (0→127): curvature ∈ [0.005, 2.0] → 表面曲率（半径 = 1/curvature）

积分步骤:
  1. 将曲率转为球面半径 R = 1 / curvature
  2. 对于每个角度 θ ∈ [-π, π]（720 步）:
     a. 计算弦长 chord = 2R · sin(|θ| / 2)
     b. 计算扩散权重 weight = Burley(chord, d=1.0)
     c. 只有 cos(θ - α) > 0 的被照面才有贡献
     d. 累加: result += cos(θ - α) × weight
  3. 归一化: result / totalWeight
```

>**设计思想**：只烘焙物理基准距离 `d=1.0` 的单通道灰度 LUT。运行时在 Shader 中对 RGB 三通道分别采样：`curvature × ScatterRadius.rgb × ScatterScale`，实现免重复烘焙的万能体积散射。

### 2.3 相关文件

| 文件 | 作用 |
|------|------|
| `Editor/SSSLUTGenerator.cs` | Editor 窗口，生成 Universal SSS LUT |

---

## 三、BRDF LUT 烘焙（NdotV × Roughness）

### 3.1 原理

BRDF LUT 为 IBL（Image-Based Lighting）的环境高光提供预计算的 **Fresnel Scale** 和 **Fresnel Bias**。

LUT 布局：
- **横轴（X）**: $N \cdot V$（法线与视线夹角余弦）∈ [0, 1]
- **纵轴（Y）**: Roughness ∈ [0, 1]

### 3.2 计算方法：蒙特卡洛积分 + GGX 重要性采样

```hlsl
// Split-Sum Approximation 的第二项:
// ∫_Ω f_r(p, ω_i, ω_o) · (ω_i · n) dω_i

for each sample (Hammersley 低差异序列, 1024 次):
  1. 用 GGX 重要性采样生成半向量 H
  2. 反射得到光照方向 L = 2(V·H)H - V
  3. 计算几何遮蔽 G = G_SchlickGGX(N·V) × G_SchlickGGX(N·L)
  4. 计算权重 G_Vis = G × (V·H) / ((N·H) × (N·V))
  5. Fresnel: Fc = (1 - V·H)^5
  6. 累加:
     scale += (1 - Fc) × G_Vis    // F0 的系数
     bias  += Fc × G_Vis          // 常数偏移

最终存储: RG = (scale/1024, bias/1024)
```

运行时重建 IBL 高光：
```hlsl
float3 indirectSpecular = Envmap.Sample(rv, roughness_mip)
                        * (F0 * BRDF_LUT.r + BRDF_LUT.g);
```

### 3.3 相关文件

| 文件 | 作用 |
|------|------|
| `Editor/BRDFLUTGenerator.cs` | Editor 窗口，生成 BRDF LUT |

---

## 四、渲染资源准备与队列设置

### 4.1 整体管线时序

```
渲染顺序:
  Opaque Geometry          ← 场景不透明物体
       ↓
  [抓取背景图]             ← AfterRenderingOpaques + 1
       ↓
  Kawase Downsample        ← 多次降采样（模糊扩散）
       ↓
  Kawase Upsample          ← 逐步升采样回原分辨率
       ↓
  [设置全局 RT]            ← _TransmittanceSharpRT & _TransmittanceBlurRT
       ↓
  Skybox                   ← 天空盒
       ↓
  Transmittance Queue      ← BSDF 材质渲染（LightMode = "Transmittance"）
       ↓
  Transparent Geometry     ← 普通半透明物体
```

### 4.2 Dual Kawase 模糊

Kawase 模糊是一种高效的近似高斯模糊，通过对角线采样实现大半径模糊。

```
降采样链（Pass 0）:
  Original (1920×1080) → 960×540 → 480×270 → 240×135
  每级: 采样 4 个对角像素求平均，分辨率减半

升采样链（Pass 1）:
  240×135 → 480×270 → 960×540 → 1920×1080
  每级: 采样 4 个对角像素求平均，分辨率翻倍

最终输出:
  _TransmittanceSharpRT = 原图（清晰参考）
  _TransmittanceBlurRT  = Kawase 模糊结果（散射背景）
```

**参数控制**：
- `blurIterations`：模糊迭代次数（1~4），越大越模糊
- `blurOffset`：采样偏移量（0.5~3.0），控制模糊扩散半径

### 4.3 相关文件

| 文件 | 作用 |
|------|------|
| `Scripts/TransmittanceObjectDrawFeature.cs` | URP RendererFeature，管理整个渲染 Pass |
| `Resources/Shaders/KawaseBlur.shader` | Kawase 降采样/升采样 Shader |

### 4.4 TransmittanceObjectDrawFeature 关键代码解析

```csharp
// 1. 抓取背景原图
Blitter.BlitCameraTexture(cmd, cameraColorTarget, m_sharpCameraRT);
cmd.SetGlobalTexture("_TransmittanceSharpRT", m_sharpCameraRT);

// 2. Kawase 降采样
for (int i = 0; i < blurIterations; i++)
    Blitter.BlitCameraTexture(cmd, currentSource, m_tempRTs[i], m_blurMaterial, 0);

// 3. Kawase 升采样
for (int i = blurIterations - 2; i >= 0; i--)
    Blitter.BlitCameraTexture(cmd, currentSource, m_tempRTs[i + MAX_ITERATIONS], m_blurMaterial, 1);

// 4. 发布模糊结果
cmd.SetGlobalTexture("_TransmittanceBlurRT", m_finalBlurRT);

// 5. 绘制 Transmittance 队列（LightMode = "Transmittance"）
cmd.DrawRendererList(rendererList);
```

---

## 五、BSDF Shader 编写

### 5.1 Shader 整体结构

```
BSDF.shader
├── Properties (材质参数)
├── SubShader / Pass "Transmittance"
│   ├── Vertex Shader
│   │   ├── 标准空间变换
│   │   └── 解包 SH 系数 (UV2/3/4 → sh_0, sh_1, sh8, curvature)
│   └── Fragment Shader
│       ├── 采样贴图 (BaseMap, MetallicGloss, Occlusion, Normal)
│       ├── [厚度重建] V 方向厚度 + 折射偏移
│       ├── [体积衰减] TransmittanceColor + TransmittanceDistance
│       ├── [直接光] ── 分解为三层 ──
│       │   ├── Specular (GGX BRDF)
│       │   ├── SSS Diffuse (Burley LUT 查表)
│       │   └── Single Scattering (相位函数 + 体积衰减)
│       └── [环境光] ── 分解为三层 ──
│           ├── Indirect Diffuse (Light Probes / SH)
│           ├── Indirect Specular (Envmap + BRDF LUT)
│           └── Indirect Transmission (背景图混合)
```

### 5.2 厚度重建

```hlsl
// 1. 将世界空间视线方向转为模型空间
float3 V_OS = TransformWorldToObjectDir(V);

// 2. 用视线反方向采样 SH 基函数
float4 sh0 = float4(Y0(-V_OS), Y1(-V_OS), Y2(-V_OS), Y3(-V_OS));
float4 sh1 = float4(Y4(-V_OS), Y5(-V_OS), Y6(-V_OS), Y7(-V_OS));

// 3. 点积重建该方向上的模型空间厚度
float thickness_V_OS = max(0, dot(sh0, input.sh_0)
                           + dot(sh1, input.sh_1)
                           + Y8(-V_OS) * input.sh8);

// 4. 恢复到世界物理尺度
float thickness = thickness_V_OS * worldScale;
```

### 5.3 直接光分解

#### 5.3.1 高光（Specular）— Cook-Torrance GGX

```hlsl
float D = D_GGX(NdotH, roughness);        // 法线分布
float G = G_Smith(NdotV, NdotL, roughness); // 几何遮蔽
float3 F = F_Schlick(VdotH, F0);           // Fresnel

float3 specular = (D * G * F) / max(4 * NdotV * NdotL, 0.001) * NdotL;
```

#### 5.3.2 次表面散射（SSS）→ 替代漫反射

SSS 是传统 Lambert 漫反射的高级替代：

```hlsl
// 1. 构建 LUT 采样坐标
float sndl = rawNdotL * 0.5 + 0.5;          // 映射到 [0,1]
float baseCurvature = saturate(abs(curvature));

// 2. 三通道独立采样（不同散射距离 → 不同颜色）
float3 scatterDist = max(ScatterRadiusRGB * ScatterScale, 0.001);
float3 curvRGB = saturate(baseCurvature * scatterDist);

float sssR = SSS_LUT.Sample(float2(sndl, curvRGB.r)).r;
float sssG = SSS_LUT.Sample(float2(sndl, curvRGB.g)).r;
float sssB = SSS_LUT.Sample(float2(sndl, curvRGB.b)).r;

// 3. 计算逆光透射（Thickness SSS）
float3 thinness = exp(-thickness_L / scatterDist);
float3 thicknessSSS = thinness * albedo / π * ThicknessSSSIntensity;

// 4. 混合
float3 sssDiffuse = sssEfficiency * albedo / π
                  + thicknessSSS * saturate(1.0 - rawNdotL);
```

**参数说明**：

| 参数 | 作用 |
|------|------|
| `_ScatterRadiusRGB` | RGB 三通道散射半径（控制色彩分离程度） |
| `_ScatterScale` | 全局散射缩放（0.01~1000） |
| `_SSSIntensity` | Lambert → SSS 混合系数（0 = 纯漫反射） |
| `_ThicknessSSSIntensity` | 逆光厚度透射强度 |

#### 5.3.3 单次散射透射（Single Scattering Transmission）

```hlsl
// 相位函数（Henyey-Greenstein）
float phase = HG_Phase(dot(L, V), _Anisotropy);

// 体积衰减
float3 volumeAttenuation = pow(_TransmittanceColor, thickness / _TransmittanceDistance);

// 透射贡献
float3 singleScatter = phase * volumeAttenuation * lightColor * attenuation * shadow;

directTransmission = singleScatter * _Transmission * kD_direct;
```

**参数说明**：

| 参数 | 作用 |
|------|------|
| `_Transmission` | 全局透射强度（0~1），同时剥离漫反射能量 |
| `_IOR` | 折射率（1~2.5），影响折射偏移 |
| `_ThicknessDistort` | 折射偏移强度（0~1） |
| `_TransmittanceColor` | 体积透射颜色（Beer-Lambert 衰减基准色） |
| `_TransmittanceDistance` | 透射衰减距离 |
| `_Anisotropy` | 相位函数各向异性（-1 后向 ~ +1 前向） |

### 5.4 环境光分解

#### 5.4.1 间接漫反射

```hlsl
float3 indirectDiffuse = SampleSH(N) * albedo * (1 - metallic);
```

#### 5.4.2 间接高光（IBL）

```hlsl
float2 brdfUV = float2(NdotV, roughness);
float2 preBRDF = BRDF_LUT.Sample(brdfUV).xy;

float3 indirectSpecular = Envmap.SampleLevel(rv, roughness * 7).rgb
                        * (F0 * preBRDF.x + preBRDF.y);
```

#### 5.4.3 间接透射（背景图可视度）

通过 `_Transmission` 在间接漫反射和背景透射之间过渡：

```hlsl
// 背景图模糊度由厚度控制
float3 transmittanceColor = lerp(sharpRT, blurRT,
    saturate(pow(thickness, _ThicknessPower) / 2.0) * (1 - _TransmittanceSmoothness));

// 体积衰减
float3 volumeAttenuation = pow(_TransmittanceColor, thickness / _TransmittanceDistance);

float3 indirectSpecTrans = kD_Trans * transmittanceColor * volumeAttenuation;

// 过渡
float3 indirectColor = lerp(indirectDiffuse, indirectSpecTrans, _Transmission)
                     + indirectSpecular;
```

**参数说明**：

| 参数 | 作用 |
|------|------|
| `_ThicknessPower` | 厚度对模糊度的非线性控制（0.1~5） |
| `_TransmittanceSmoothness` | 透射背景清晰度（0 = 纯模糊 ~ 1 = 纯清晰） |

### 5.5 能量守恒架构

```
最终颜色 = (直接光高光 + 直接光漫反射) × Occlusion
         + 直接透射 × Occlusion
         + 间接光（漫反射↔透射 lerp + 高光）

其中:
  直接光漫反射 = lerp(Lambert × kD, SSS_Diffuse × (1-metallic), _SSSIntensity)
               × (1 - _Transmission)   ← 透射从漫反射中剥走能量

  间接光 = lerp(SH Diffuse, Transmission_Background, _Transmission) + IBL Specular
```

---

## 六、文件清单总览

| 类别 | 文件路径 | 功能 |
|------|----------|------|
| **Shader** | `SHTranslucency/Resources/Shaders/BSDF.shader` | 主材质 Shader |
| **Shader** | `SHTranslucency/Resources/Shaders/Thickness.shader` | 深度烘焙 Shader |
| **Shader** | `SHTranslucency/Resources/Shaders/KawaseBlur.shader` | Kawase 模糊 Shader |
| **Shader** | `SHTranslucency/Resources/Shaders/MonteCarloProject.shader` | MC SH 投影 Shader |
| **Shader** | `SHTranslucency/Resources/Shaders/SH_Utils.hlsl` | SH 基函数与工具函数 |
| **Compute** | `SHTranslucency/Resources/Shaders/Reduce_Uniform.compute` | Uniform 归约计算 |
| **Compute** | `SHTranslucency/Resources/Shaders/Reduce_MC_1024.compute` | MC 归约计算 |
| **Script** | `SHTranslucency/Scripts/SphericalHarmonics.cs` | C# SH 工具类 |
| **Script** | `SHTranslucency/Scripts/TransmittanceObjectDrawFeature.cs` | URP 渲染 Feature |
| **Editor** | `SHTranslucency/Editor/ThicknessCompute.cs` | 厚度烘焙工具 |
| **Editor** | `SHTranslucency/Editor/SSSLUTGenerator.cs` | SSS LUT 生成工具 |
| **Editor** | `SHTranslucency/Editor/BRDFLUTGenerator.cs` | BRDF LUT 生成工具 |

---

## 七、使用流程

```
1. 烘焙阶段（Editor 工具）:
   ├── Window → ThicknessCompute → 选择 Mesh → Compute Thickness
   │   └── 输出: Assets/TranslucentMeshes/{name}.asset
   ├── Window → Generate Universal SSS LUT
   │   └── 输出: Assets/SHTranslucency/Resources/Universal_SSS_LUT.exr
   └── Window → Generate BRDF LUT
       └── 输出: Assets/SHTranslucency/Resources/BRDF_LUT.exr

2. 材质设置:
   ├── 将烘焙后的 Mesh asset 赋给模型
   ├── 创建 Translucency/BSDF 材质
   ├── 设置 BaseMap, Normal, MetallicGloss 等标准 PBR 贴图
   ├── 设置 _UniversalSSSLUT = Universal_SSS_LUT
   ├── 设置 _BRDF = BRDF_LUT
   ├── 设置 _Envmap = 反射探针 Cubemap
   └── 调节 SSS 与 Transmission 参数

3. 渲染管线:
   ├── 确保 URP Renderer 上挂载 TransmittanceObjectDrawFeature
   ├── 设置 blurIterations & blurOffset
   └── 运行 → BSDF 材质在 Transmittance Pass 中渲染
```
