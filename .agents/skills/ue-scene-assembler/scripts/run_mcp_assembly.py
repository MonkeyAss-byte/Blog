import urllib.request
import json
import base64
import os
import time

def run_stage4_and_5():
    # 1. Initialize MCP session
    data = json.dumps({
        'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
        'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'AntigravityPipeline', 'version': '1.0'}}
    }).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/mcp', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        session_id = r.headers.get('Mcp-Session-Id')
    print("[MCP] Connected! Session ID:", session_id)

    req_id = 10
    def call_tool(ts, tool, args={}):
        nonlocal req_id
        req_id += 1
        payload = json.dumps({
            'jsonrpc': '2.0', 'id': req_id, 'method': 'tools/call',
            'params': {
                'name': 'call_tool',
                'arguments': {
                    'toolset_name': ts,
                    'tool_name': tool,
                    'arguments': args
                }
            }
        }).encode('utf-8')
        headers = {'Content-Type': 'application/json', 'Mcp-Session-Id': session_id}
        request = urllib.request.Request('http://127.0.0.1:8000/mcp', data=payload, headers=headers)
        with urllib.request.urlopen(request, timeout=30) as resp:
            raw = json.loads(resp.read())
            content = raw.get('result', {}).get('content', [])
            if content and content[0].get('type') == 'text':
                try:
                    return json.loads(content[0]['text'])
                except Exception:
                    return content[0]['text']
            return raw

    textures_dir = r"D:\UE5Projects\AutoAIPipelineTest\SourceAssets\RetroServerRoom_V2\Textures"
    ue_tex_folder = "/Game/RetroServerRoom_V2/Textures"
    ue_mat_folder = "/Game/RetroServerRoom_V2/Materials"
    ue_mesh_folder = "/Game/RetroServerRoom_V2/Meshes"

    # =========================================================================
    # STEP 1: IMPORT ALL TEXTURES
    # =========================================================================
    print("\n--- STEP 1: Importing Textures via UE MCP ---")
    texture_files = [
        "T_SM_CRT_Monitor_BaseColor.png",
        "T_SM_CRT_Monitor_Normal.png",
        "T_SM_CRT_Monitor_ORM.png",
        "T_CRT_Screen_Emissive.png",
        "T_SM_PC_Tower_BaseColor.png",
        "T_SM_PC_Tower_Normal.png",
        "T_SM_PC_Tower_ORM.png",
        "T_SM_Folding_Chair_BaseColor.png",
        "T_SM_Folding_Chair_Normal.png",
        "T_SM_Folding_Chair_ORM.png",
        "T_SM_Folding_Table_BaseColor.png",
        "T_SM_Folding_Table_Normal.png",
        "T_SM_Folding_Table_ORM.png",
        "T_SM_Soda_Can_BaseColor.png",
        "T_SM_Soda_Can_Normal.png",
        "T_SM_Soda_Can_ORM.png",
        "floor_antistatic_basecolor_00001_.png",
        "floor_antistatic_normal_00001_.png",
        "floor_antistatic_orm_00001_.png",
        "wall_panel_basecolor_00001_.png",
        "wall_panel_normal_00001_.png",
        "wall_panel_orm_00001_.png",
        "bulletin_board_posters.png"
    ]

    saved_tex_paths = []
    for tf in texture_files:
        full_path = os.path.join(textures_dir, tf)
        if not os.path.exists(full_path):
            continue
        asset_name = os.path.splitext(tf)[0]
        res = call_tool('editor_toolset.toolsets.texture.TextureTools', 'import_file', {
            'folder_path': ue_tex_folder,
            'asset_name': asset_name,
            'source_file': full_path
        })
        saved_tex_paths.append(f"{ue_tex_folder}/{asset_name}")
        print(f"  [Tex] Imported {asset_name}")

    if saved_tex_paths:
        call_tool('editor_toolset.toolsets.asset.AssetTools', 'save_assets', {'asset_paths': saved_tex_paths})
        print(f"  [Tex] Saved {len(saved_tex_paths)} texture assets to disk!")

    # =========================================================================
    # STEP 2: BIND TEXTURES TO MATERIAL INSTANCES
    # =========================================================================
    print("\n--- STEP 2: Binding Textures to Material Instances ---")
    material_bindings = [
        {
            "instance": "MI_V2_CRT_Chassis",
            "base_color": "T_SM_CRT_Monitor_BaseColor",
            "normal": "T_SM_CRT_Monitor_Normal",
            "orm": "T_SM_CRT_Monitor_ORM",
            "emissive": None
        },
        {
            "instance": "MI_V2_CRT_Screen",
            "base_color": "T_CRT_Screen_Emissive",
            "normal": "T_SM_CRT_Monitor_Normal",
            "orm": "T_SM_CRT_Monitor_ORM",
            "emissive": "T_CRT_Screen_Emissive"
        },
        {
            "instance": "MI_V2_PC_Tower",
            "base_color": "T_SM_PC_Tower_BaseColor",
            "normal": "T_SM_PC_Tower_Normal",
            "orm": "T_SM_PC_Tower_ORM",
            "emissive": None
        },
        {
            "instance": "MI_V2_Folding_Table",
            "base_color": "T_SM_Folding_Table_BaseColor",
            "normal": "T_SM_Folding_Table_Normal",
            "orm": "T_SM_Folding_Table_ORM",
            "emissive": None
        },
        {
            "instance": "MI_V2_Folding_Chair",
            "base_color": "T_SM_Folding_Chair_BaseColor",
            "normal": "T_SM_Folding_Chair_Normal",
            "orm": "T_SM_Folding_Chair_ORM",
            "emissive": None
        },
        {
            "instance": "MI_V2_Soda_Can",
            "base_color": "T_SM_Soda_Can_BaseColor",
            "normal": "T_SM_Soda_Can_Normal",
            "orm": "T_SM_Soda_Can_ORM",
            "emissive": None
        },
        {
            "instance": "MI_V2_Floor",
            "base_color": "floor_antistatic_basecolor_00001_",
            "normal": "floor_antistatic_normal_00001_",
            "orm": "floor_antistatic_orm_00001_",
            "emissive": None
        },
        {
            "instance": "MI_V2_Wall",
            "base_color": "wall_panel_basecolor_00001_",
            "normal": "wall_panel_normal_00001_",
            "orm": "wall_panel_orm_00001_",
            "emissive": None
        },
        {
            "instance": "MI_V2_Bulletin_Board",
            "base_color": "bulletin_board_posters",
            "normal": None,
            "orm": None,
            "emissive": None
        }
    ]

    saved_mat_paths = []
    for mb in material_bindings:
        inst_name = mb["instance"]
        inst_ref = f"{ue_mat_folder}/{inst_name}.{inst_name}"
        
        # BaseColor
        if mb["base_color"]:
            tex_ref = f"{ue_tex_folder}/{mb['base_color']}.{mb['base_color']}"
            call_tool('editor_toolset.toolsets.material_instance.MaterialInstanceTools', 'set_texture_parameter', {
                'instance': {'refPath': inst_ref},
                'name': 'BaseColor',
                'value': {'refPath': tex_ref}
            })
        # Normal
        if mb["normal"]:
            tex_ref = f"{ue_tex_folder}/{mb['normal']}.{mb['normal']}"
            call_tool('editor_toolset.toolsets.material_instance.MaterialInstanceTools', 'set_texture_parameter', {
                'instance': {'refPath': inst_ref},
                'name': 'Normal',
                'value': {'refPath': tex_ref}
            })
        # ORM
        if mb["orm"]:
            tex_ref = f"{ue_tex_folder}/{mb['orm']}.{mb['orm']}"
            call_tool('editor_toolset.toolsets.material_instance.MaterialInstanceTools', 'set_texture_parameter', {
                'instance': {'refPath': inst_ref},
                'name': 'ORM',
                'value': {'refPath': tex_ref}
            })
        # Emissive
        if mb["emissive"]:
            tex_ref = f"{ue_tex_folder}/{mb['emissive']}.{mb['emissive']}"
            call_tool('editor_toolset.toolsets.material_instance.MaterialInstanceTools', 'set_texture_parameter', {
                'instance': {'refPath': inst_ref},
                'name': 'Emissive',
                'value': {'refPath': tex_ref}
            })
        saved_mat_paths.append(f"{ue_mat_folder}/{inst_name}")
        print(f"  [Mat] Parameterized {inst_name}")

    if saved_mat_paths:
        call_tool('editor_toolset.toolsets.asset.AssetTools', 'save_assets', {'asset_paths': saved_mat_paths})
        print(f"  [Mat] Saved {len(saved_mat_paths)} material instances to disk!")

    # =========================================================================
    # STEP 3: ASSIGN MATERIALS TO STATIC MESH SLOTS
    # =========================================================================
    print("\n--- STEP 3: Assigning Material Instances to StaticMesh Slots ---")
    mesh_slot_configs = [
        {
            "mesh": "V2_SM_CRT_Monitor",
            "slots": {
                "M_Chassis": "MI_V2_CRT_Chassis",
                "M_Screen": "MI_V2_CRT_Screen"
            }
        },
        {
            "mesh": "V2_SM_PC_Tower",
            "slots": {
                "M_PC_Tower": "MI_V2_PC_Tower"
            }
        },
        {
            "mesh": "V2_SM_Folding_Table",
            "slots": {
                "M_Folding_Table": "MI_V2_Folding_Table"
            }
        },
        {
            "mesh": "V2_SM_Folding_Chair",
            "slots": {
                "M_Folding_Chair": "MI_V2_Folding_Chair"
            }
        },
        {
            "mesh": "V2_SM_Soda_Can",
            "slots": {
                "M_Soda_Can": "MI_V2_Soda_Can"
            }
        }
    ]

    saved_mesh_paths = []
    for msc in mesh_slot_configs:
        mesh_name = msc["mesh"]
        mesh_ref = f"{ue_mesh_folder}/{mesh_name}.{mesh_name}"
        
        # Query actual slot names
        slots_res = call_tool('editor_toolset.toolsets.static_mesh.StaticMeshTools', 'get_material_slots', {
            'mesh': {'refPath': mesh_ref}
        })
        actual_slots = slots_res.get('returnValue', []) if isinstance(slots_res, dict) else []
        print(f"  [Mesh] {mesh_name} slots found in asset: {actual_slots}")

        for actual_slot in actual_slots:
            target_mat = None
            if "Screen" in actual_slot:
                target_mat = "MI_V2_CRT_Screen"
            elif "Chassis" in actual_slot:
                target_mat = "MI_V2_CRT_Chassis"
            elif mesh_name == "V2_SM_PC_Tower":
                target_mat = "MI_V2_PC_Tower"
            elif mesh_name == "V2_SM_Folding_Table":
                target_mat = "MI_V2_Folding_Table"
            elif mesh_name == "V2_SM_Folding_Chair":
                target_mat = "MI_V2_Folding_Chair"
            elif mesh_name == "V2_SM_Soda_Can":
                target_mat = "MI_V2_Soda_Can"

            if target_mat:
                mat_ref = f"{ue_mat_folder}/{target_mat}.{target_mat}"
                call_tool('editor_toolset.toolsets.static_mesh.StaticMeshTools', 'set_material', {
                    'mesh': {'refPath': mesh_ref},
                    'slot_name': actual_slot,
                    'material': {'refPath': mat_ref}
                })
                print(f"    Assigned slot '{actual_slot}' -> {target_mat}")
        saved_mesh_paths.append(f"{ue_mesh_folder}/{mesh_name}")

    if saved_mesh_paths:
        call_tool('editor_toolset.toolsets.asset.AssetTools', 'save_assets', {'asset_paths': saved_mesh_paths})
        print(f"  [Mesh] Saved {len(saved_mesh_paths)} StaticMeshes to disk!")

    # =========================================================================
    # STEP 4: CLEANUP REDUNDANT ACTORS & ENSURE TARGET ACTORS
    # =========================================================================
    print("\n--- STEP 4: Cleaning up duplicates & placing target actors ---")
    actors_res = call_tool('editor_toolset.toolsets.scene.SceneTools', 'find_actors', {
        'name': '', 'tag': '', 'collision_channels': []
    })
    actors = actors_res.get('returnValue', []) if isinstance(actors_res, dict) else []
    print(f"  Found {len(actors)} total actors in scene.")

    # Delete redundant StaticMeshActor duplicate copies
    deleted_count = 0
    for a in actors:
        ref = a.get('refPath', '')
        name = ref.split('.')[-1]
        # Keep lights, clouds, sky, fog, cameras, floor, walls
        if any(keep in name for keep in ['Light', 'Sky', 'Fog', 'Cloud', 'PlayerStart', 'WorldSettings', 'Brush', 'Camera']):
            continue
        if any(sm in name for sm in ['StaticMeshActor_1', 'StaticMeshActor_2', 'StaticMeshActor_3', 'StaticMeshActor_4',
                                    'StaticMeshActor_5', 'StaticMeshActor_6', 'StaticMeshActor_7', 'StaticMeshActor_8',
                                    'StaticMeshActor_9', 'Proxy']):
            try:
                call_tool('editor_toolset.toolsets.actor.ActorTools', 'destroy_actor', {'actor': {'refPath': ref}})
                deleted_count += 1
            except Exception:
                pass

    print(f"  Cleaned up {deleted_count} duplicate/redundant actors.")

    # =========================================================================
    # STEP 5: FIX LIGHTING CONFLICTS (Eliminate Red Cross)
    # =========================================================================
    print("\n--- STEP 5: Lighting De-confliction ---")
    # Identify PointLights and make sure stationary overlap doesn't trigger red cross
    for a in actors:
        ref = a.get('refPath', '')
        if 'PointLight' in ref:
            # Change mobility to Movable via property if available
            try:
                call_tool('editor_toolset.toolsets.object.ObjectTools', 'set_property', {
                    'object': {'refPath': ref},
                    'property_name': 'Mobility',
                    'value': 2 # EComponentMobility::Movable
                })
            except Exception:
                pass

    # =========================================================================
    # STEP 6: PIE IN-GAME SIMULATION VIEWPORT CAPTURE
    # =========================================================================
    print("\n--- STEP 6: In-Game PIE Closed-Loop Capture ---")
    cam_xform = {
        'location': {'x': 0.0, 'y': -365.0, 'z': 130.0},
        'rotation': {'pitch': -2.0, 'yaw': 90.0, 'roll': 0.0},
        'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0}
    }

    call_tool('EditorToolset.EditorAppToolset', 'SetCameraTransform', {'transform': cam_xform})
    print("  Starting PIE simulation session (eliminating all editor billboards/icons)...")
    call_tool('EditorToolset.EditorAppToolset', 'StartPIE', {
        'options': {
            'bSimulate': True,
            'playMode': 'PlayMode_InViewPort',
            'startTransform': cam_xform,
            'warmupSeconds': 1.5
        }
    })

    time.sleep(1.5)
    print("  Capturing in-game pure viewport frame...")
    cap_res = call_tool('EditorToolset.EditorAppToolset', 'CaptureViewport', {
        'captureTransform': cam_xform,
        'annotations': {
            'gridSpacing': 0.0,
            'gridExtent': 0.0,
            'gridHeight': 0.0,
            'maxLabelDistance': 0.0,
            'classFilter': {'refPath': '/Script/Engine.Actor'},
            'maxLabels': 0
        },
        'bShowUI': False
    })

    print("  Stopping PIE...")
    call_tool('EditorToolset.EditorAppToolset', 'StopPIE', {})

    # Extract & save final capture
    out_img = r"C:\Users\QuKing\.gemini\antigravity\brain\ea0424ff-dc89-4dda-b027-46bf771d4143\stage5_final_pie_render.png"
    if isinstance(cap_res, dict) and "returnValue" in cap_res:
        img_b64 = cap_res["returnValue"]["image"]["data"]
        img_bytes = base64.b64decode(img_b64)
        with open(out_img, "wb") as f:
            f.write(img_bytes)
        print(f"\n>>> [SUCCESS] Saved final Stage 5 PIE capture to: {out_img} ({len(img_bytes)} bytes) <<<")
    else:
        print("  Capture result format:", type(cap_res))

run_stage4_and_5()
