"""
Asset Generator Runner (Stage 2 & 3)
Consumes scene_manifest.json, checks existing generated assets or triggers Tripo/ComfyUI/Blender,
standardizes textures and material slots, and writes asset_manifest.json.
"""

import os
import json
import argparse
from typing import Dict, Any, List

def build_asset_manifest_from_sources(
    scene_manifest_path: str,
    source_assets_dir: str,
    output_path: str
) -> Dict[str, Any]:
    if not os.path.exists(scene_manifest_path):
        raise FileNotFoundError(f"Precondition failed: scene_manifest not found at {scene_manifest_path}")

    with open(scene_manifest_path, "r", encoding="utf-8") as f:
        scene = json.load(f)

    meshes_dir = os.path.join(source_assets_dir, "Meshes")
    textures_dir = os.path.join(source_assets_dir, "Textures")

    asset_manifest = {
        "pipeline_id": scene.get("scene_id", "RetroServerRoom_V2"),
        "source_assets_root": source_assets_dir,
        "assets": []
    }

    for item in scene.get("assets", []):
        asset_id = item["id"]
        sem_type = item["semantic_type"]
        asset_entry = {
            "id": asset_id,
            "name": item["name"],
            "semantic_type": sem_type,
            "target_transform": item.get("target_transform"),
        }

        if sem_type == "PROP_PBR":
            # Check mesh path
            fbx_path = os.path.join(meshes_dir, f"{item['name']}.fbx")
            glb_path = os.path.join(meshes_dir, f"{item['name']}.glb")
            chosen_mesh = fbx_path if os.path.exists(fbx_path) else glb_path
            asset_entry["mesh_path"] = chosen_mesh if os.path.exists(chosen_mesh) else None

            # Material slots & textures
            prop_core_name = item['name'].replace("V2_", "")
            candidates = [item['name'], prop_core_name]
            base_color, orm_map, normal_map = None, None, None
            for c in candidates:
                bc = os.path.join(textures_dir, f"T_{c}_BaseColor.png")
                orm = os.path.join(textures_dir, f"T_{c}_ORM.png")
                norm = os.path.join(textures_dir, f"T_{c}_Normal.png")
                if os.path.exists(bc): base_color = bc
                if os.path.exists(orm): orm_map = orm
                if os.path.exists(norm): normal_map = norm

            slots = {
                "0": {
                    "slot_index": 0,
                    "slot_name": "M_Chassis" if item.get("needs_partition") else f"M_{asset_id}",
                    "textures": {
                        "BaseColor": base_color,
                        "ORM": orm_map,
                        "Normal": normal_map,
                        "Emissive": None
                    }
                }
            }

            if item.get("needs_partition"):
                emissive_screen = os.path.join(textures_dir, "T_CRT_Screen_Emissive.png")
                slots["1"] = {
                    "slot_index": 1,
                    "slot_name": item.get("partition_spec", {}).get("slot_1_name", "M_Screen"),
                    "textures": {
                        "BaseColor": emissive_screen if os.path.exists(emissive_screen) else base_color,
                        "ORM": orm_map if os.path.exists(orm_map) else None,
                        "Normal": normal_map if os.path.exists(normal_map) else None,
                        "Emissive": emissive_screen if os.path.exists(emissive_screen) else None,
                        "EmissiveIntensity": 3.0
                    }
                }

            asset_entry["material_slots"] = slots

        elif sem_type == "TILING_PBR":
            prefix = "floor_antistatic" if "Floor" in asset_id else "wall_panel"
            bc = os.path.join(textures_dir, f"{prefix}_basecolor_00001_.png")
            orm = os.path.join(textures_dir, f"{prefix}_orm_00001_.png")
            norm = os.path.join(textures_dir, f"{prefix}_normal_00001_.png")
            asset_entry["material_slots"] = {
                "0": {
                    "slot_index": 0,
                    "slot_name": f"M_{asset_id}",
                    "tiling_uv": item.get("tiling_uv", [4.0, 4.0]),
                    "textures": {
                        "BaseColor": bc if os.path.exists(bc) else None,
                        "ORM": orm if os.path.exists(orm) else None,
                        "Normal": norm if os.path.exists(norm) else None,
                        "Emissive": None
                    }
                }
            }

        asset_manifest["assets"].append(asset_entry)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(asset_manifest, f, indent=2, ensure_ascii=False)
    print(f"[AssetGeneratorRunner] Produced asset_manifest.json at: {output_path}")
    return asset_manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build asset manifest")
    parser.add_argument("--scene-manifest", default="scene_manifest.json")
    parser.add_argument("--source-assets", default="D:/UE5Projects/AutoAIPipelineTest/SourceAssets/RetroServerRoom_V2")
    parser.add_argument("--output", default="asset_manifest.json")
    args = parser.parse_args()
    build_asset_manifest_from_sources(args.scene_manifest, args.source_assets, args.output)
