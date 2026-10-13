"""
Asset Contract & Semantic Schema for AI 3D Asset Pipeline (Universal 3-Type Architecture)

Provides standard typing and schema generation for the 3 fundamental orthogonal asset types:
1. PROP_PBR: Unique 3D geometric prop PBR textures & meshes (Custom UV0 space)
2. TILING_PBR: Seamless architectural tiling materials (Floor, Wall, Ceiling)
3. DECAL_PBR: Surface-projected decals (Warning stripes, labels, stains, damage)

Note on Emissive & Advanced Shading:
Emissive (自发光) is NOT a fixed asset category. It is a material shading property dynamically
controlled and tuned by the Visual Model (VLM) inside Unreal Engine based on visual comparison
with the reference concept art.
"""

import os
import json
from enum import Enum
from typing import Dict, List, Any, Optional

class AssetSemanticType(str, Enum):
    PROP_PBR = "PROP_PBR"       # 三维几何道具 PBR 资产 (StaticMesh + 专用 UV 贴图)
    TILING_PBR = "TILING_PBR"   # 连续无缝平铺材质 (Floor, Wall, Terrain)
    DECAL_PBR = "DECAL_PBR"     # 表面投影贴花 (DecalActor, DBuffer)

class PBRChannel(str, Enum):
    BASE_COLOR = "MP_BaseColor"
    ROUGHNESS = "MP_Roughness"
    METALLIC = "MP_Metallic"
    AMBIENT_OCCLUSION = "MP_AmbientOcclusion"
    NORMAL = "MP_Normal"
    EMISSIVE_COLOR = "MP_EmissiveColor"

def create_prop_pbr_contract(
    asset_id: str,
    mesh_path: str,
    material_slots: Dict[str, Dict[str, Any]],
    target_ue_folder: str = "/Game/RetroServerRoom/Meshes",
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Creates a contract for a 3D geometric prop with dedicated UV PBR material slots."""
    return {
        "asset_id": asset_id,
        "semantic_type": AssetSemanticType.PROP_PBR.value,
        "tags": tags or ["prop"],
        "mesh": {
            "source_file": mesh_path,
            "target_ue_folder": target_ue_folder,
            "import_options": {
                "combine_meshes": True,
                "import_materials": False,
                "import_textures": False
            }
        },
        "material_slots": material_slots
    }

def create_tiling_pbr_contract(
    material_id: str,
    base_color: str,
    orm_map: str,
    normal_map: Optional[str] = None,
    default_tiling_uv: List[float] = [4.0, 4.0],
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Creates a contract for seamless architectural tiling surfaces."""
    return {
        "asset_id": material_id,
        "semantic_type": AssetSemanticType.TILING_PBR.value,
        "tags": tags or ["architectural", "seamless"],
        "material_domain": "MD_Surface",
        "tiling": {
            "default_u_scale": default_tiling_uv[0],
            "default_v_scale": default_tiling_uv[1]
        },
        "textures": {
            "BaseColor": {"source_file": base_color, "ue_property": PBRChannel.BASE_COLOR.value},
            "ORM": {
                "source_file": orm_map,
                "packing": {"R": PBRChannel.AMBIENT_OCCLUSION.value, "G": PBRChannel.ROUGHNESS.value, "B": PBRChannel.METALLIC.value}
            },
            "Normal": {"source_file": normal_map, "ue_property": PBRChannel.NORMAL.value} if normal_map else None
        }
    }

def create_decal_pbr_contract(
    decal_id: str,
    base_color: str,
    orm_map: Optional[str] = None,
    normal_map: Optional[str] = None,
    is_transparent: bool = True,
    default_projection_size: List[float] = [100.0, 100.0, 50.0],
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Creates a contract for a projected surface decal.
    - is_transparent=True (Stickers/Stains): Uses Workflow 02 (RMBG Alpha), DBuffer_TranslucentColorNormalRoughness.
    - is_transparent=False (Posters/Signs): Uses Workflow 03 (Base T2I Opaque RGB), DBuffer_ColorNormalRoughness.
    """
    default_tags = ["decal", "overlay"]
    default_tags.append("transparent" if is_transparent else "opaque_poster")
    if tags:
        default_tags.extend(tags)

    blend_mode = (
        "DBuffer_TranslucentColorNormalRoughness"
        if is_transparent
        else "DBuffer_ColorNormalRoughness"
    )

    textures: Dict[str, Any] = {
        "BaseColor": {"source_file": base_color, "ue_property": PBRChannel.BASE_COLOR.value}
    }
    if orm_map:
        textures["ORM"] = {
            "source_file": orm_map,
            "packing": {
                "R": PBRChannel.AMBIENT_OCCLUSION.value,
                "G": PBRChannel.ROUGHNESS.value,
                "B": PBRChannel.METALLIC.value
            }
        }
    if normal_map:
        textures["Normal"] = {"source_file": normal_map, "ue_property": PBRChannel.NORMAL.value}

    return {
        "asset_id": decal_id,
        "semantic_type": AssetSemanticType.DECAL_PBR.value,
        "is_transparent": is_transparent,
        "recommended_workflow": "02_decal_texture" if is_transparent else "03_base_text_to_image",
        "tags": default_tags,
        "material_domain": "MD_DeferredDecal",
        "decal_options": {
            "default_box_extent": default_projection_size,
            "blend_mode": blend_mode
        },
        "textures": textures
    }

