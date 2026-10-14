# GPU外层：
![[Pasted image 20261014000204.png]]
## 核心概念
### PCIE总线
- 负责我们的CPU<->GPU的信息的相互传递
### GigaThread Engine(全局总调度器)
- 负责我们的Block切分与任务**派发**给我们SM
### GPC(图形处理集群)
- 负责图形（光栅化与OM阶段（后测试与后写入））
- 由RasterEngine和ROP和TPC构成
# GPC结构
![[Pasted image 20261014113939.png]]

## 核心概念
### RasterEngine
- 负责光栅化以及片元着色器**派发**
### ROP
- 负责OM阶段的后测试与后写入
# TPC结构
![[Pasted image 20261014114634.png]]
## 核心概念
### PolyMorph Engine
- 负责曲面细分与几何着色器
###  SM(流多处理器)
- RT core
- L1 Cache/Shared Memory
- Tex core
- Sub core
# SM结构
![[Pasted image 20261014122605.png]]
## 核心概念
### Sub core
- Warp Scheduler（线程调度）
- L0 i-cache（指令缓存）
- Register File(寄存器)
-ALU:
- Tensor core
- LD/ST(负责从Subcore外部拿数据)
- SFU
- Cuda core
### L1 Cache/Shared Memory
### TEX Core
- 读取贴图
### RT Core
# Sub core
![[Pasted image 20261014124357.png]]
## 核心概念
###  Warp Scheduler（线程调度）
###  L0 i-cache（指令缓存）
###  Register File(寄存器)
### ALU:
###  Tensor core
###  LD/ST
- 负责从Subcore外部拿数据与输出数据
###  SFU
###  Cuda core