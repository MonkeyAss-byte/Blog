>对于RDC截取Mumu模拟器中部分游戏时，截帧会失效，原因在于Mumu模拟器的多实例Vulkan渲染的方法

---
## 图形API与Mumu模拟器实例化图形API逻辑

### 图形API生命周期
[[帧分析工具与DirectX11 API流程分析]]
### Mumu模拟器的实例化Vulkan过程
#### MumuDevice启动时：
	Adding Vulkan device
#### 启动游戏时：
	Adding Vulkan device Again
---
## RDC的截帧逻辑与目前缺陷

### 逻辑：
	 1.注入内存
	 2.检测图形资源
	 3.检测Present函数（在SwapChain对象中）激发
	 4.StartFrameCapture
	 5.EndFrameCapture
### 缺陷：
	当有多vulkan实例时，截帧不完整

---
## 解决方案：
- 为RDC申明一个全局的vulkan对象List
- 当检测到Present函数时，对于每个Vulkan实例都插入StartFrameCapture
- ...