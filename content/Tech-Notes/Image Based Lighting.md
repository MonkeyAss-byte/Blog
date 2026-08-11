---
title: Image Based Lighting
date: 2026-08-10
tags:
  - 渲染基础
  - 物理原理
description: 对于双向分布函数的IBL的工程实现
---
# IBL

> Image Based Lighting多在工程中应用于环境光,分别针对于漫反射与镜面反射
---
## 漫反射
### 球谐函数
- 球谐函数是一组全球空间的基函数
- 对于基函数的投影系数：$$c_l = \int_{\Omega} f(\omega) \cdot Y_l(\omega) \, d\omega$$
- 可进行旋转变换（基于球谐函数的线性组合拟合以及球谐函数的旋转不变性）：
  $$
  	R=\begin{pmatrix}
		R_{x x}&R_{xy}&R_{xz}\\R_{y x}&R_{yy}&R_{yz}\\R_{z x}&R_{zy}&R_{zz}
	\end{pmatrix}(作用于坐标轴)
  $$
	旋转变换时，我们应通过改变系数的方式去实现相应旋转，方便通过N采样时，我们能即时的将其（x,y,z）带入基函数，其中二阶基函数为$B_{0}=C_{0}\cdot y$,$B_{1}=C_{1}\cdot z$,$B_{0}=C_{2}\cdot x$,即：
  $$
  	\begin{pmatrix}
		C_{0}'\\C_{1}'\\C_{2}'
	\end{pmatrix}=\begin{pmatrix}
		R_{xy}&R_{yy}&R_{zy}\\R_{xz}&R_{yz}&R_{zz}\\R_{xx}&R_{yx}&R_{zx}
	\end{pmatrix}\cdot \begin{pmatrix}
		C_{0}\\C_{1}\\C_{2}
	\end{pmatrix}
  $$
	同理，对于三阶的基函数，同样是通过提取多项式中的原基函数的系数建立矩阵（5x5)
### 球面卷积
- 卷积个人理解：对原函数进行相对位置的积分处理得到一个新函数
- $Irradiance_{IBL_{diffuse}}$**公式**：
  $$
  	E(n)=\int L_{i}(w)\cdot max(0,n\cdot \omega )d\omega 
  $$
- 对于球谐基函数或傅里叶基函数此类频域的基函数来说，卷积操作等于基函数系数相乘(**基于其基底正交性推导**），即：
  $$
  	E(n)=\begin{pmatrix}
		f_{0,0}\\f_{-1,0\\}\\f_{-1,0}\\\dots
	\end{pmatrix}\cdot \begin{pmatrix}
		f(n)_{0,0}&f(n)_{-1,0\\}&f(n)_{-1,0}&\dots
	\end{pmatrix}
  $$
  推导过程：
  $$
		L_{i}(w)=\sum_{i=0}^{K-1}c_{i}Y_{i}(w)
	$$
	$$
		max(0,n\cdot \omega)=\sum_{i=0}^{K-1}c_{ni}Y_{i}(w)
	$$
	$$
  	E(n)=\int L_{i}(w)\cdot max(0,n\cdot \omega )d\omega=\int \sum_{i=0}^{K-1}c_{i}Y_{i}(w)\sum_{i=0}^{K-1}c_{ni}Y_{i}(w)d\omega=\sum_{i=0}^{K-1}c_{i}\cdot\sum_{i=0}^{K-1}c_{ni}
  $$
  其中Cni(**基于勒让德多项式**）：
  $$
	c^0_{i}=\pi \cdot Y^0_{i}(n)  , c^1_{i}=\frac{2}{3}\pi \cdot Y^1_{i}(n)  , c^2_{i}=\frac{1}{4}\pi \cdot Y^2_{i}(n)  
  $$
### 真实立体角（Cubemap->球面空间）
- 公式：
  $$
  	dw=\frac{du\cdot dv\cdot \cos \alpha}{u^2+v^2+1},\cos \alpha=\frac{1}{\sqrt{ u^2+v^2+1 }}
  $$
## 镜面反射
### 蒙特卡洛重要性采样
- $Irradiance_{IBL_{specular}}$**公式**：
   $$
  	L_{o}=\int L_{i}(w)\cdot \frac{DFG}{4(N\cdot V)}d\omega =\frac{1}{N}\sum^N_{k=1}\frac{L_{i}(w)*\frac {DFG}{4(N\cdot V)}}{\rho(w)}
  $$
	其中
	$$
		\rho(w_{l})=\frac{D(H)\cdot(N\cdot H)}{4(H\cdot V)}
	$$
	推导：
	$$
		\rho(w_{l})*dw_{l}=\rho(h)*dw_{h}\implies p(w_{l})=\frac{\rho(h)*dw_{h}}{dw_{l}}=\frac{\rho(h)}{4(H\cdot V)}(反射立体角的变换)
	$$
	- 法线分布函数D（H）并非法线的概率密度函数，理由：D(H)为微观面积与宏观面积的立体角之比
	- 对于除以概率密度的理解：
		- 概率密度控制采样密度，积分本质为面积的计算，采样密度控制采样范围，累加（采样范围*采样值）=面积
- 分离为：
- **预滤波环境贴图**:
  $$
  	Sum_{1}=\frac{1}{N}\sum^N_{k=1}L_{i}(w)=\int L_{i}(w)*\rho(w)dw
  $$
- **BRDF项**：
  $$
  	Sum_{2}=\frac{1}{N}\sum^N_{k=1}(F_{0}\cdot(1-( 1-V\cdot H)^5)\cdot \frac{G\cdot(H\cdot V)}{(N\cdot V)(N\cdot H)} +(1-V\cdot H)^5\cdot \frac{G\cdot(H\cdot V)}{(N\cdot V)(N\cdot H)})
  $$
	其中第一项为R（Scale),第二项为G（Offset).