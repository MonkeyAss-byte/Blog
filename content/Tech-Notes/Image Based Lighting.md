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
#### 数学基础
- 对于基函数的投影系数：$$c_l = \int_{\Omega} f(\omega) \cdot Y_l(\omega) \, d\omega$$
- 旋转不变性：
  $$
  	R=\begin{pmatrix}
		R_{x x}&R_{xy}&R_{xz}\\R_{y x}&R_{yy}&R_{yz}\\R_{z x}&R_{zy}&R_{zz}
	\end{pmatrix}
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

