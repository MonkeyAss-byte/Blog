>帧分析工具基于renderdoc与XXMI开发，在此基础上梳理引擎与图形API的链接
>https://github.com/SpectrumQT/XXMI-Launcher.git
>https://github.com/baldurk/renderdoc.git

---
# 渲染管线对应的调用图形API的流程图（一般情况）
![[Pasted image 20260821153121.png]]

---

# 帧分析工具
## 注入D3D11
### NktHookLibHelpers::CreateProcessWithDllW
- 来自`NktHookLib` 就是 Nektra 官方开源的 C++ 轻量级挂钩库
- 
	1. 调用 Windows 底层原生 `CreateProcessW(..., CREATE_SUSPENDED, ...)` 创建目标游戏进程并**完全冻结主线程**；
	2. 解析目标 `.exe` 刚载入内存的 **PE 导入表（Import Table / IAT）**；
	3. 在目标进程的内存空隙里，**把我们的 `d3d11.dll` 临时塞进游戏的依赖导入表**（或者修改入口点 `RIP` 插入一段微小的 `LoadLibraryW` 汇编跳转指令）；
	4. 一切就绪后，恢复线程（`ResumeThread`）；
## D3D11初始化后动态注入



![[Pasted image 20260821163126.png]]