"""Blender Route B: Geometric Knife Bisect & Material Slot Partitioning
Performs exact geometric intersection cut along 2D mask contours,
partitions mesh into Slot 0 (Chassis) and Slot 1 (Sub-part/Screen),
and selectively remaps UV coordinates to [0, 1] x [0, 1] planar layout.

Usage:
  blender --background -P blender_knife_bisect.py -- <input_glb> <mask_image_or_json> <output_glb> [remap_uv_01=true] [view=front]
"""

import bpy
import bmesh
import sys
import os
import json
import numpy as np
import math
from mathutils import Vector

def main():
    argv = sys.argv
    if "--" not in argv:
        print("Usage: blender --background -P blender_knife_bisect.py -- <input_glb> <mask_path> <output_glb> [remap_uv_01] [view]")
        sys.exit(1)
        
    args = argv[argv.index("--") + 1:]
    input_glb = os.path.abspath(args[0])
    mask_path = os.path.abspath(args[1])
    output_glb = os.path.abspath(args[2])
    remap_uv_01 = args[3].lower() in ('true', '1', 'yes') if len(args) > 3 else True
    view = args[4].lower() if len(args) > 4 else "front"

    # 1. Clear scene & import
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=input_glb)

    mesh_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not mesh_objs:
        print("Error: No mesh found!")
        sys.exit(1)
    target_obj = mesh_objs[0]
    bpy.context.view_layer.objects.active = target_obj
    target_obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 2. Load Mask and Contour Points
    contour_uv_pts = []
    
    # Check for direct or companion JSON contour file
    json_path = None
    if mask_path.endswith('.json'):
        json_path = mask_path
    else:
        base_no_ext = os.path.splitext(mask_path)[0]
        candidates = [
            base_no_ext + ".json",
            base_no_ext + "_Contour.json",
            base_no_ext.replace("_Mask", "_Contour") + ".json",
            base_no_ext.replace("Mask", "Contour") + ".json"
        ]
        for c in candidates:
            if os.path.exists(c):
                json_path = c
                break
                
    if json_path and os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            cdata = json.load(f)
            contour_uv_pts = cdata.get('points', [])
            print(f"Loaded {len(contour_uv_pts)} contour points from {json_path}")

    # Load mask image for pixel testing
    img_path = mask_path if not mask_path.endswith('.json') else mask_path.replace('.json', '.png')
    if os.path.exists(img_path):
        b_img = bpy.data.images.load(img_path)
        W, H = b_img.size[0], b_img.size[1]
        pix = np.array(b_img.pixels[:]).reshape(H, W, b_img.channels)
        mask_binary = (pix[:, :, 0] > 0.5)
    else:
        print(f"Warning: Mask image not found at {img_path}, using bounding box heuristic.")
        W, H = 1024, 1024
        mask_binary = np.zeros((H, W), dtype=bool)

    if not contour_uv_pts and mask_binary.any():
        # Extract smooth polygon contour from mask binary
        shifted_u = np.pad(mask_binary, ((1, 0), (0, 0)), mode='constant')[:-1, :]
        shifted_d = np.pad(mask_binary, ((0, 1), (0, 0)), mode='constant')[1:, :]
        shifted_l = np.pad(mask_binary, ((0, 0), (1, 0)), mode='constant')[:, :-1]
        shifted_r = np.pad(mask_binary, ((0, 0), (0, 1)), mode='constant')[:, 1:]
        interior = mask_binary & shifted_u & shifted_d & shifted_l & shifted_r
        boundary = mask_binary & (~interior)
        y_b, x_b = np.where(boundary)

        if len(y_b) > 0:
            cx, cy = np.mean(x_b), np.mean(y_b)
            angles = np.arctan2(y_b - cy, x_b - cx)
            sort_idx = np.argsort(angles)
            num_pts = min(64, len(sort_idx))
            indices = np.linspace(0, len(sort_idx) - 1, num_pts, endpoint=False, dtype=int)
            contour_uv_pts = [(float(x_b[sort_idx[i]]) / W, float(y_b[sort_idx[i]]) / H) for i in indices]
        else:
            y_idx, x_idx = np.where(mask_binary)
            min_u, max_u = float(x_idx.min()) / W, float(x_idx.max()) / W
            min_v, max_v = float(y_idx.min()) / H, float(y_idx.max()) / H
            contour_uv_pts = [[min_u, min_v], [max_u, min_v], [max_u, max_v], [min_u, max_v]]

    # 3. Compute Bounding Box & projection coordinates
    bbox_corners = [target_obj.matrix_world @ Vector(corner) for corner in target_obj.bound_box]
    min_b = Vector((min(c.x for c in bbox_corners), min(c.y for c in bbox_corners), min(c.z for c in bbox_corners)))
    max_b = Vector((max(c.x for c in bbox_corners), max(c.y for c in bbox_corners), max(c.z for c in bbox_corners)))
    center = (min_b + max_b) / 2.0
    size = max_b - min_b
    max_dim = max(size.x, size.y, size.z) * 1.15

    # 4. Create Cutter Prism & Perform Exact Knife Intersection Cut
    cutter_mesh = bpy.data.meshes.new("CutterPrismMesh")
    cutter_bm = bmesh.new()

    if view == "right":
        # Right view: looking from +X towards -X; U -> +Y, V -> +Z
        front_verts = [cutter_bm.verts.new(Vector((max_b.x + 1.0, (u - 0.5) * max_dim + center.y, (v - 0.5) * max_dim + center.z))) for u, v in contour_uv_pts]
        back_verts = [cutter_bm.verts.new(Vector((min_b.x - 1.0, (u - 0.5) * max_dim + center.y, (v - 0.5) * max_dim + center.z))) for u, v in contour_uv_pts]
    elif view == "left":
        # Left view: looking from -X towards +X; U -> -Y, V -> +Z
        front_verts = [cutter_bm.verts.new(Vector((min_b.x - 1.0, -(u - 0.5) * max_dim + center.y, (v - 0.5) * max_dim + center.z))) for u, v in contour_uv_pts]
        back_verts = [cutter_bm.verts.new(Vector((max_b.x + 1.0, -(u - 0.5) * max_dim + center.y, (v - 0.5) * max_dim + center.z))) for u, v in contour_uv_pts]
    elif view == "back":
        # Back view: looking from +Y towards -Y; U -> -X, V -> +Z
        front_verts = [cutter_bm.verts.new(Vector((-(u - 0.5) * max_dim + center.x, max_b.y + 1.0, (v - 0.5) * max_dim + center.z))) for u, v in contour_uv_pts]
        back_verts = [cutter_bm.verts.new(Vector((-(u - 0.5) * max_dim + center.x, min_b.y - 1.0, (v - 0.5) * max_dim + center.z))) for u, v in contour_uv_pts]
    else:
        # Default front view: looking from -Y towards +Y; U -> +X, V -> +Z
        front_verts = [cutter_bm.verts.new(Vector(((u - 0.5) * max_dim + center.x, min_b.y - 1.0, (v - 0.5) * max_dim + center.z))) for u, v in contour_uv_pts]
        back_verts = [cutter_bm.verts.new(Vector(((u - 0.5) * max_dim + center.x, max_b.y + 1.0, (v - 0.5) * max_dim + center.z))) for u, v in contour_uv_pts]

    cutter_bm.verts.ensure_lookup_table()
    N = len(front_verts)
    for i in range(N):
        i_next = (i + 1) % N
        cutter_bm.faces.new([front_verts[i], front_verts[i_next], back_verts[i_next], back_verts[i]])
    cutter_bm.faces.new(front_verts)
    cutter_bm.faces.new(list(reversed(back_verts)))
    cutter_bm.to_mesh(cutter_mesh)
    cutter_bm.free()

    cutter_obj = bpy.data.objects.new("CutterPrism", cutter_mesh)
    bpy.context.scene.collection.objects.link(cutter_obj)

    # Execute mesh intersect
    bpy.ops.object.select_all(action='DESELECT')
    target_obj.select_set(True)
    cutter_obj.select_set(True)
    bpy.context.view_layer.objects.active = target_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode='CUT', solver='EXACT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(cutter_obj, do_unlink=True)

    # 5. Partition Faces into Slots
    bm = bmesh.new()
    bm.from_mesh(target_obj.data)
    bm.faces.ensure_lookup_table()

    # Materials
    orig_mat = target_obj.data.materials[0] if target_obj.data.materials else bpy.data.materials.new("M_CRT_Chassis")
    if not orig_mat.name.startswith("M_CRT_Chassis") and not orig_mat.name.startswith("M_Chassis"):
        orig_mat.name = "M_CRT_Chassis"
    target_obj.data.materials.clear()
    target_obj.data.materials.append(orig_mat) # Slot 0

    sub_mat = bpy.data.materials.new(name="M_CRT_Screen")
    sub_mat.use_nodes = True
    nodes = sub_mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = (0.02, 0.08, 0.04, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.15
    target_obj.data.materials.append(sub_mat)   # Slot 1

    uv_layer = bm.loops.layers.uv.verify()
    screen_faces = []

    for f in bm.faces:
        fc = f.calc_center_median()
        if view == "right":
            u = (fc.y - center.y) / max_dim + 0.5
            v = (fc.z - center.z) / max_dim + 0.5
            is_front_side = (fc.x > center.x)
        elif view == "left":
            u = -(fc.y - center.y) / max_dim + 0.5
            v = (fc.z - center.z) / max_dim + 0.5
            is_front_side = (fc.x < center.x)
        elif view == "back":
            u = -(fc.x - center.x) / max_dim + 0.5
            v = (fc.z - center.z) / max_dim + 0.5
            is_front_side = (fc.y > center.y)
        else:
            u = (fc.x - center.x) / max_dim + 0.5
            v = (fc.z - center.z) / max_dim + 0.5
            is_front_side = (fc.y < center.y)

        px = int(np.clip(u * W, 0, W - 1))
        py = int(np.clip(v * H, 0, H - 1))
        
        # Test if face center is inside mask and on the front half of the object
        if mask_binary[py, px] and is_front_side:
            f.material_index = 1
            screen_faces.append(f)
        else:
            f.material_index = 0

    print(f"Partitioned: {len(screen_faces)} screen faces (Slot 1), {len(bm.faces) - len(screen_faces)} chassis faces (Slot 0)")

    # 6. Optional UV Remap to [0, 1] x [0, 1]
    if remap_uv_01 and screen_faces:
        s_verts = list({v for f in screen_faces for v in f.verts})
        if view in ("right", "left"):
            min_h = min(v.co.y for v in s_verts)
            max_h = max(v.co.y for v in s_verts)
        else:
            min_h = min(v.co.x for v in s_verts)
            max_h = max(v.co.x for v in s_verts)
        min_z = min(v.co.z for v in s_verts)
        max_z = max(v.co.z for v in s_verts)
        w_span = max(max_h - min_h, 1e-5)
        h_span = max(max_z - min_z, 1e-5)

        for f in screen_faces:
            for l in f.loops:
                v = l.vert
                if view in ("right", "left"):
                    new_u = (v.co.y - min_h) / w_span
                else:
                    new_u = (v.co.x - min_h) / w_span
                new_v = (v.co.z - min_z) / h_span
                l[uv_layer].uv = Vector((new_u, new_v))
        print("Screen UVs remapped to [0, 1] x [0, 1] planar layout successfully!")

    bm.to_mesh(target_obj.data)
    bm.free()

    # 7. Export GLB
    os.makedirs(os.path.dirname(output_glb), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=output_glb, export_format='GLB')
    print(f"Exported partitioned GLB to: {output_glb}")

    # Also export FBX
    fbx_out = os.path.splitext(output_glb)[0] + ".fbx"
    try:
        bpy.ops.export_scene.fbx(filepath=fbx_out, use_selection=True)
        print(f"Exported partitioned FBX to: {fbx_out}")
    except Exception as e:
        print(f"FBX export notice: {e}")

if __name__ == "__main__":
    main()
