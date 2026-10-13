"""
Scene Greybox Builder & Manifest Generator (Stage 1)
Builds or validates scene_manifest.json with spatial ground truth transforms,
semantic asset types, and material slot partitioning requirements.
"""

import os
import json
import argparse
from typing import Dict, Any, List

def generate_default_server_room_manifest(output_path: str) -> Dict[str, Any]:
    manifest = {
        "scene_id": "RetroServerRoom_V2",
        "description": "1990s retro server room workstation corner with CRT monitor, beige PC tower, folding table and chair",
        "camera": {
            "location": [-250.0, -180.0, 140.0],
            "rotation": [-14.0, 36.0, 0.0],
            "focal_length": 35.0,
            "fov": 65.0
        },
        "ground_plane_z": 0.0,
        "assets": [
            {
                "id": "Folding_Table",
                "name": "V2_SM_Folding_Table",
                "semantic_type": "PROP_PBR",
                "description": "Beige/grey industrial folding table",
                "target_transform": {
                    "location": [0.0, 0.0, 75.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                },
                "contact_plane_z": 0.0,
                "top_surface_z": 75.0,
                "needs_partition": False
            },
            {
                "id": "CRT_Monitor",
                "name": "V2_SM_CRT_Monitor",
                "semantic_type": "PROP_PBR",
                "description": "Retro CRT computer monitor with curved screen glass",
                "target_transform": {
                    "location": [0.0, 0.0, 75.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                },
                "contact_plane_z": 75.0,
                "needs_partition": True,
                "partition_spec": {
                    "part_prompt": "screen",
                    "view": "front",
                    "slot_0_name": "M_Chassis",
                    "slot_1_name": "M_Screen",
                    "remap_uv_01": True
                }
            },
            {
                "id": "PC_Tower",
                "name": "V2_SM_PC_Tower",
                "semantic_type": "PROP_PBR",
                "description": "Retro 1990s beige desktop PC tower",
                "target_transform": {
                    "location": [0.0, -65.0, 75.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                },
                "contact_plane_z": 75.0,
                "needs_partition": False
            },
            {
                "id": "Folding_Chair",
                "name": "V2_SM_Folding_Chair",
                "semantic_type": "PROP_PBR",
                "description": "Metal and faux-leather folding office chair",
                "target_transform": {
                    "location": [-80.0, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                },
                "contact_plane_z": 0.0,
                "needs_partition": False
            },
            {
                "id": "Soda_Can",
                "name": "V2_SM_Soda_Can",
                "semantic_type": "PROP_PBR",
                "description": "Vintage red cola aluminum can",
                "target_transform": {
                    "location": [20.0, 45.0, 75.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                },
                "contact_plane_z": 75.0,
                "needs_partition": False
            },
            {
                "id": "Antistatic_Floor",
                "name": "V2_Floor_Antistatic",
                "semantic_type": "TILING_PBR",
                "description": "Raised anti-static server room floor tiles",
                "tiling_uv": [6.0, 6.0],
                "target_transform": {
                    "location": [0.0, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [10.0, 10.0, 1.0]
                }
            },
            {
                "id": "Wall_Panel",
                "name": "V2_Wall_Panel",
                "semantic_type": "TILING_PBR",
                "description": "Brushed industrial wall panel with acoustic vents",
                "tiling_uv": [4.0, 3.0],
                "target_transform": {
                    "location": [200.0, 0.0, 150.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 10.0, 3.0]
                }
            }
        ],
        "lighting_topology": [
            {
                "id": "L01_L02_Overhead_Fluorescent_Front",
                "name": "RectLight_Overhead_Front",
                "group": "Overhead_Fixtures",
                "engine_type": "RectLight",
                "description": "前排双管荧光吊灯 (主照明)",
                "color_temperature_k": 5500,
                "color_rgb": [1.0, 1.0, 1.0],
                "intensity": 4000.0,
                "mobility": "Movable",
                "target_transform": {
                    "location": [0.0, -80.0, 260.0],
                    "rotation": [-90.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                }
            },
            {
                "id": "L03_L04_Overhead_Fluorescent_Back",
                "name": "RectLight_Overhead_Back",
                "group": "Overhead_Fixtures",
                "engine_type": "RectLight",
                "description": "纵深背景荧光灯 (景深补光)",
                "color_temperature_k": 5000,
                "color_rgb": [0.95, 0.98, 1.0],
                "intensity": 2500.0,
                "mobility": "Movable",
                "target_transform": {
                    "location": [0.0, 120.0, 260.0],
                    "rotation": [-90.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                }
            },
            {
                "id": "L05_CRT_Screen_Emissive_Magenta",
                "name": "Emissive_CRT_Magenta",
                "group": "CRT_Emissive",
                "engine_type": "Emissive_Plus_RectLight",
                "description": "中央CRT粉色屏幕 (高饱和洋红自发光与补光)",
                "color_rgb": [1.0, 0.08, 0.58],
                "emissive_intensity": 3.5,
                "fill_light_intensity": 150.0,
                "target_asset": "V2_SM_CRT_Monitor"
            },
            {
                "id": "L06_L07_Right_Desk_CRT_Screens",
                "name": "Emissive_CRT_Blue_White",
                "group": "CRT_Emissive",
                "engine_type": "Emissive_Plus_RectLight",
                "description": "右侧桌面蓝光屏与高亮白屏 (自发光+面光源补光)",
                "color_rgb": [0.2, 0.6, 1.0],
                "emissive_intensity": 3.0,
                "fill_light_intensity": 120.0,
                "target_asset": "V2_SM_CRT_Monitor_Right"
            },
            {
                "id": "L08_Ground_CRT_Teal",
                "name": "PointLight_Ground_Teal",
                "group": "Ground_Displays",
                "engine_type": "PointLight_Plus_Emissive",
                "description": "左侧地面堆积青光屏 (局部微光)",
                "color_rgb": [0.0, 0.8, 0.8],
                "intensity": 300.0,
                "mobility": "Movable",
                "target_transform": {
                    "location": [-60.0, -70.0, 25.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                }
            },
            {
                "id": "L09_Ground_CRT_Purple",
                "name": "PointLight_Ground_Purple",
                "group": "Ground_Displays",
                "engine_type": "PointLight_Plus_Emissive",
                "description": "右侧地面靠椅紫光屏 (局部微光)",
                "color_rgb": [0.65, 0.12, 0.95],
                "intensity": 300.0,
                "mobility": "Movable",
                "target_transform": {
                    "location": [60.0, 40.0, 25.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                }
            },
            {
                "id": "L10_Left_Door_Spill_Cyan",
                "name": "SpotLight_Door_Spill_Cyan",
                "group": "Spill_And_Accent",
                "engine_type": "SpotLight",
                "description": "左侧门洞外冷青色大范围环境溢光 (环境光/轮廓光)",
                "color_rgb": [0.0, 0.75, 0.9],
                "intensity": 6000.0,
                "mobility": "Movable",
                "target_transform": {
                    "location": [-220.0, -120.0, 180.0],
                    "rotation": [-20.0, 45.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                }
            },
            {
                "id": "L11_PC_Tower_Power_LED",
                "name": "PointLight_Power_LED",
                "group": "Spill_And_Accent",
                "engine_type": "PointLight",
                "description": "电脑机箱微弱电源指示LED (微弱背光点)",
                "color_rgb": [1.0, 0.35, 0.05],
                "intensity": 60.0,
                "mobility": "Movable",
                "target_transform": {
                    "location": [0.0, -65.0, 85.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0]
                }
            }
        ]
    }
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[GreyboxBuilder] Generated scene manifest at: {output_path}")
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate scene manifest")
    parser.add_argument("--output", default="scene_manifest.json", help="Path to output JSON")
    args = parser.parse_args()
    generate_default_server_room_manifest(args.output)
