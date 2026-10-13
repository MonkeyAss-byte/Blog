"""AI 3D Asset Pipeline Engine
Central orchestrator connecting ComfyUI workflows, Blender automation scripts, and asset file management.
Provides dedicated high-level Python functions for all 6 industrial workflows.
"""

import os
import sys
import json
import shutil
import subprocess
from typing import Dict, Any, Optional, List

# Locate script directory & templates
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)
TEMPLATES_DIR = os.path.join(SKILL_ROOT, "resources", "templates")
BLENDER_PATH = "D:/Blenders/blender.exe" if os.path.exists("D:/Blenders/blender.exe") else "blender"

try:
    from comfy_runner import ComfyWorkflowRunner
except ImportError:
    from .comfy_runner import ComfyWorkflowRunner

runner = ComfyWorkflowRunner()

def _get_api_template(filename: str) -> str:
    path = os.path.join(TEMPLATES_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Workflow template not found at: {path}")
    return path

# -------------------------------------------------------------------------
# 01. 搭配平铺工作流 (Texture Semantics)
# -------------------------------------------------------------------------
def run_tiling_workflow(prompt: str, prefix: str = "tiling_floor", seed: Optional[int] = None) -> Dict[str, Any]:
    """
    Executes Workflow 01: Seamless PBR texture generation for large structures / whiteboxes.
    """
    wf_path = _get_api_template("01_texture_semantics_seamless_api.json")
    overrides = {}
    if prompt:
        overrides["PrimitiveStringMultiline"] = {"value": prompt}
    if seed is not None:
        overrides["KSampler"] = {"seed": seed}
    if prefix:
        overrides["17"] = {"filename_prefix": f"{prefix}_basecolor"}
        overrides["13"] = {"filename_prefix": f"{prefix}_normal"}
        overrides["16"] = {"filename_prefix": f"{prefix}_height"}
        overrides["36"] = {"filename_prefix": f"{prefix}_orm"}
        overrides["29"] = {"filename_prefix": f"{prefix}_check_tiling"}
        overrides["30"] = {"filename_prefix": f"{prefix}_check_effect"}
    return runner.run_workflow(wf_path, overrides)

# -------------------------------------------------------------------------
# 02. 贴花工作流 (Decal Texture: 透明贴花与实体海报)
# -------------------------------------------------------------------------
def run_decal_workflow(prompt: str, prefix: str = "decal", steps: int = 25) -> Dict[str, Any]:
    """
    Executes Workflow 02: Local decal generation with soft alpha falloff (transparent sticker/damage).
    """
    wf_path = _get_api_template("02_decal_texture_api.json")
    suffix = ", centered isolated asset on pure flat black background, soft transparent edges, neutral diffuse, 8k"
    full_prompt = f"{prompt.strip()}{suffix}"
    overrides = {
        "PrimitiveStringMultiline": {"value": full_prompt},
        "KSampler": {"steps": steps}
    }
    if prefix:
        overrides["43"] = {"filename_prefix": f"{prefix}_basecolor"}
        overrides["44"] = {"filename_prefix": f"{prefix}_normal"}
        overrides["48"] = {"filename_prefix": f"{prefix}_height"}
        overrides["53"] = {"filename_prefix": f"{prefix}_orm"}
        overrides["56"] = {"filename_prefix": f"{prefix}_check_effect"}
    return runner.run_workflow(wf_path, overrides)

def run_decal_pipeline(
    prompt: str,
    is_transparent: bool = True,
    prefix: str = "decal",
    steps: int = 25,
    width: int = 1024,
    height: int = 1024
) -> Dict[str, Any]:
    """
    Intelligent Decal Dispatcher:
    - is_transparent=True (Stickers, warning marks, stains): Routes to Workflow 02 (Decal Texture with Alpha).
    - is_transparent=False (Posters, placards, signboards): Routes to Workflow 03 (Base T2I Opaque RGB).
    """
    if is_transparent:
        return run_decal_workflow(prompt, prefix=prefix, steps=steps)
    else:
        return run_text_to_image(prompt, filename_prefix=prefix, width=width, height=height)

# -------------------------------------------------------------------------
# 03. 基础文生图元工作流 (Base Text to Image)
# -------------------------------------------------------------------------
def run_text_to_image(prompt: str, filename_prefix: str = "Based_image", width: int = 1024, height: int = 1024) -> Dict[str, Any]:
    """
    Executes Workflow 03: Generates 2D hero concept design or screen contents.
    """
    wf_path = _get_api_template("03_base_text_to_image_api.json")
    overrides = {
        "PrimitiveStringMultiline": {"value": prompt},
        "EmptySD3LatentImage": {"width": width, "height": height},
        "SaveImage": {"filename_prefix": filename_prefix}
    }
    return runner.run_workflow(wf_path, overrides)

# -------------------------------------------------------------------------
# 04. 3D 几何与纹理生成工作流 (Tripo 3D API 极速通道 - 推荐)
# -------------------------------------------------------------------------
def run_tripo_3d_withtex(
    image_filename: str,
    output_prefix: str = "3d/Tripo_asset",
    model_version: str = "v2.5-20250123",
    pbr: bool = True,
    texture: bool = True,
    model_seed: int = 42,
    texture_seed: int = 42,
    texture_quality: str = "standard",
    texture_alignment: str = "original_image",
    geometry_quality: str = "standard"
) -> Dict[str, Any]:
    """
    Executes Tripo_3d_WithTex workflow: High-speed cloud 3D mesh + PBR texture generation in 15-20s.
    Zero local VRAM footprint.
    """
    wf_path = _get_api_template("04_tripo_3d_withtex_api.json")
    overrides = {
        "LoadImage": {"image": image_filename},
        "TripoImageToModelNodeV2": {
            "model_version": model_version,
            "texture": texture,
            "pbr": pbr,
            "model_seed": model_seed,
            "texture_seed": texture_seed,
            "texture_quality": texture_quality,
            "texture_alignment": texture_alignment,
            "geometry_quality": geometry_quality
        },
        "Save3DAdvanced": {"filename_prefix": output_prefix}
    }
    return runner.run_workflow(wf_path, overrides)

# -------------------------------------------------------------------------
# 04-B. 本地 3D 网格生成工作流 (Hunyuan 3D 2.1 DiT - 离线备用)
# -------------------------------------------------------------------------
def run_mesh_generation(image_filename: str, output_name: str = "Chair_Mesh", steps: int = 15) -> Dict[str, Any]:
    """
    Executes Workflow 04: Generates dense 3D geometry mesh from 2D concept image.
    """
    wf_path = _get_api_template("04_mesh_generation_api.json")
    overrides = {
        "LoadImage": {"image": image_filename},
        "Hy3D21MeshGenerator": {"steps": steps},
        "Hy3D21ExportMesh": {"filename_prefix": output_name},
        "SaveGLB": {"filename_prefix": f"3d/{output_name}"}
    }
    return runner.run_workflow(wf_path, overrides)

# -------------------------------------------------------------------------
# 05. 多视图 PBR 纹理工作流 (Mesh Texturing with Metadata RMBG)
# -------------------------------------------------------------------------
def run_mesh_texturing(mesh_filename: str, image_filename: str, asset_name: str = "textured_asset") -> Dict[str, Any]:
    """
    Executes Workflow 05: Multiview projection, PBR baking (Albedo, MR, Self-AO -> ORM), and GLB export.
    """
    wf_path = _get_api_template("05_mesh_texturing_rmbg_api.json")
    overrides = {
        "Hy3D21LoadMesh": {"glb_path": mesh_filename},
        "Hy3D21LoadImageWithTransparency": {"image": image_filename},
        "Hy3D21MultiViewsGeneratorWithMetaData": {"output_name": asset_name}
    }
    return runner.run_workflow(wf_path, overrides)

# -------------------------------------------------------------------------
# 06. 材质语义切分工作流 (Material Clip - SAM 2)
# -------------------------------------------------------------------------
def run_material_clip(image_filename: str, semantic_prompt: str = "inner screen", output_prefix: str = "Mask") -> Dict[str, Any]:
    """
    Executes Workflow 06: SAM 2 semantic view segmentation driven by text prompt.
    """
    wf_path = _get_api_template("06_material_clip_api.json")
    overrides = {
        "LoadImage": {"image": image_filename},
        "SAM2Segment": {"prompt": semantic_prompt},
        "SaveImage": {"filename_prefix": output_prefix}
    }
    return runner.run_workflow(wf_path, overrides)

# -------------------------------------------------------------------------
# Blender DCC 辅助自动化
# -------------------------------------------------------------------------
def render_ortho_views(model_path: str, output_dir: str, resolution: int = 1024) -> bool:
    """Renders 6 orthographic views (front, back, left, right, top, bottom) using Blender."""
    script_path = os.path.join(SCRIPT_DIR, "blender_render_ortho.py")
    cmd = [BLENDER_PATH, "--background", "-P", script_path, "--", model_path, output_dir, str(resolution)]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    return ret.returncode == 0

def execute_knife_bisect(input_glb: str, mask_path: str, output_glb: str, remap_uv_01: bool = True, view: str = "front") -> bool:
    """Executes Route B exact geometric Knife Bisect cut, slot partitioning, and [0,1] planar UV remapping."""
    script_path = os.path.join(SCRIPT_DIR, "blender_knife_bisect.py")
    cmd = [BLENDER_PATH, "--background", "-P", script_path, "--", input_glb, mask_path, output_glb, str(remap_uv_01).lower(), view]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    return ret.returncode == 0

if __name__ == "__main__":
    print("AI 3D Asset Pipeline Engine initialized successfully.")
    print("Available workflow functions: run_tiling_workflow, run_decal_workflow, run_decal_pipeline, run_text_to_image, run_tripo_3d_withtex, run_mesh_generation, run_mesh_texturing, run_material_clip, render_ortho_views, execute_knife_bisect")
