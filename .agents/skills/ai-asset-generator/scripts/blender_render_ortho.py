"""Blender Orthographic 6-View Capture Tool
Renders accurate Front, Back, Left, Right, Top, Bottom orthographic projections of a 3D asset.
Used by Material Clip (SAM 2) for exact multi-view segmentation.

Usage:
  blender --background -P blender_render_ortho.py -- <input_glb> <output_dir> [resolution=1024]
"""

import bpy
import sys
import os
import math
from mathutils import Vector

def main():
    argv = sys.argv
    if "--" not in argv:
        print("Usage: blender --background -P blender_render_ortho.py -- <input_glb> <output_dir> [resolution]")
        sys.exit(1)
    
    args = argv[argv.index("--") + 1:]
    input_glb = os.path.abspath(args[0])
    output_dir = os.path.abspath(args[1])
    res = int(args[2]) if len(args) > 2 else 1024
    os.makedirs(output_dir, exist_ok=True)

    # 1. Clear default scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. Import GLB
    bpy.ops.import_scene.gltf(filepath=input_glb)
    
    # 3. Find mesh objects
    mesh_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not mesh_objs:
        print("Error: No mesh objects found in imported file!")
        sys.exit(1)

    # Calculate bounding box
    bbox_corners = [mesh_objs[0].matrix_world @ Vector(corner) for corner in mesh_objs[0].bound_box]
    min_b = Vector((min(c.x for c in bbox_corners), min(c.y for c in bbox_corners), min(c.z for c in bbox_corners)))
    max_b = Vector((max(c.x for c in bbox_corners), max(c.y for c in bbox_corners), max(c.z for c in bbox_corners)))
    center = (min_b + max_b) / 2.0
    size = max_b - min_b
    max_dim = max(size.x, size.y, size.z) * 1.15

    # Setup rendering engine
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') and 'BLENDER_EEVEE_NEXT' in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items else 'BLENDER_EEVEE'
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    # Create Camera
    cam_data = bpy.data.cameras.new(name="OrthoCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = max_dim
    cam_obj = bpy.data.objects.new("OrthoCam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Create Light
    light_data = bpy.data.lights.new(name="SunLight", type='SUN')
    light_data.energy = 4.0
    light_obj = bpy.data.objects.new("SunLight", light_data)
    scene.collection.objects.link(light_obj)

    # Views config (name: (distance_vec, euler_rot_deg))
    dist = max_dim * 2.0
    views = {
        "front": ((0, -dist, 0), (90, 0, 0)),
        "back": ((0, dist, 0), (90, 0, 180)),
        "left": ((-dist, 0, 0), (90, 0, -90)),
        "right": ((dist, 0, 0), (90, 0, 90)),
        "top": ((0, 0, dist), (0, 0, 0)),
        "bottom": ((0, 0, -dist), (180, 0, 0))
    }

    for name, (offset, rot) in views.items():
        cam_obj.location = center + Vector(offset)
        cam_obj.rotation_euler = (math.radians(rot[0]), math.radians(rot[1]), math.radians(rot[2]))
        light_obj.location = cam_obj.location
        light_obj.rotation_euler = cam_obj.rotation_euler
        out_file = os.path.join(output_dir, f"ortho_{name}.png")
        scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        print(f"Rendered: {out_file}")

    print("All 6 orthographic views rendered successfully!")

if __name__ == "__main__":
    main()
