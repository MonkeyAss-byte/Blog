# Unity资产管线流程与框架
## AssetPostprocessor与ScriptedImporter（资产导入 与资产操作之后（OnPostProcessAllAssets）
### 流程图
![[Pasted image 20260817100301.png]]

### 整体代码框架

![[Pasted image 20260817100330.png]]

### 自定义Import规则

![[Pasted image 20260817100348.png]]

## AssetModificationProcessor（资产操作之前）
### 代码框架
![[Pasted image 20260817112950.png]]

## IPreprocess(Compute)Shaders与shader_feature与muti_compile(打包Shader资产)
### IPreprocess(Compute)Shaders.OnProcess(Compute)Shaders
#### 参数：
- (Compute)Shader shader,
- ShaderSnippetData snippet(String kernelName)
- Ilist< ShaderComplierData > data
###  Shader Variants Collection
![[Pasted image 20260817144751.png]]

### shader_feature与muti_compile
####  _ {local} _ {frag/vertex}
- local表示Shader局部宏 (局部<=64)
- **frag,vertex表示变体作用域**（控制编译打包范围）
  
#### shader_feature
- 编译时按需打包（跟.mat的yaml和.shadervariants有关）
范围）
#### muti_compile
- 编译时全量打包

### SVC(.shadervariants)
- 用于提前加载Shader及其变体（**Shader预热**）
- 用于在**shader_feature**按需打包的基础上增加逻辑上的shader_feature(Shader.EnableKeyword())
### IPreprocess(Compute)Shaders
- 对于 IPreprocess(Compute)Shaders ，擅长针对**muti_compile**进行**非合理**的Shader变体的打包剔除
- 配合ShaderSnippetData.passName与ShaderSnippetData.shaderType剔除变体**多余_frag与_vertex**版本