"""
Unreal Engine MCP Client Library
Connects to live Unreal Engine editor via the official UE MCP endpoint (http://127.0.0.1:8000/mcp).
Enables seamless programmatic control of Toolsets and closed-loop viewport capture.
"""

import os
import json
import base64
import urllib.request
from typing import Dict, Any, Optional, List

DEFAULT_ENDPOINT = "http://127.0.0.1:8000/mcp"

class UnrealMcpClient:
    def __init__(self, endpoint: str = DEFAULT_ENDPOINT):
        self.endpoint = endpoint
        self.session_id: Optional[str] = None
        self._req_id = 0
        self.initialize()

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def initialize(self):
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AntigravityMcpClient", "version": "1.0"}
            }
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            self.session_id = r.headers.get("Mcp-Session-Id")

    def call_raw(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        req = urllib.request.Request(self.endpoint, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read())
            if "error" in res:
                raise RuntimeError(f"UE MCP Error: {res['error']}")
            return res

    def call_tool(self, toolset_name: str, tool_name: str, arguments: Dict[str, Any], timeout: float = 30.0) -> Any:
        res = self.call_raw("tools/call", {
            "name": "call_tool",
            "arguments": {
                "toolset_name": toolset_name,
                "tool_name": tool_name,
                "arguments": arguments
            }
        }, timeout=timeout)
        content = res.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            try:
                parsed = json.loads(content[0]["text"])
                if "returnValue" in parsed:
                    return parsed["returnValue"]
                return parsed
            except Exception:
                return content[0]["text"]
        return content

    # --- Convenience Toolset Wrappers ---

    def set_camera_transform(self, location: Dict[str, float], rotation: Dict[str, float]) -> Any:
        """Sets the active editor viewport camera transform."""
        xform = {
            "location": location,
            "rotation": rotation,
            "scale": {"x": 1.0, "y": 1.0, "z": 1.0}
        }
        return self.call_tool("EditorToolset.EditorAppToolset", "SetCameraTransform", {"transform": xform})

    def start_pie(self, cam_transform: Optional[Dict[str, Any]] = None, warmup: float = 1.0) -> Any:
        """Starts Play-In-Editor (Simulate) session to clear billboards and render in pure game mode."""
        options = {
            "bSimulate": True,
            "playMode": "PlayMode_InViewPort",
            "warmupSeconds": warmup
        }
        if cam_transform:
            options["startTransform"] = cam_transform
        return self.call_tool("EditorToolset.EditorAppToolset", "StartPIE", {"options": options})

    def stop_pie(self) -> Any:
        """Stops the Play-In-Editor session."""
        return self.call_tool("EditorToolset.EditorAppToolset", "StopPIE", {})

    def capture_viewport(
        self,
        cam_transform: Optional[Dict[str, Any]] = None,
        save_path: Optional[str] = None,
        show_ui: bool = False
    ) -> bytes:
        """Captures the active viewport buffer as PNG bytes and optionally saves to disk."""
        if not cam_transform:
            cam_transform = {
                "location": {"x": 0.0, "y": -365.0, "z": 130.0},
                "rotation": {"pitch": -2.0, "yaw": 90.0, "roll": 0.0},
                "scale": {"x": 1.0, "y": 1.0, "z": 1.0}
            }

        args = {
            "captureTransform": cam_transform,
            "annotations": {
                "gridSpacing": 0.0,
                "gridExtent": 0.0,
                "gridHeight": 0.0,
                "maxLabelDistance": 0.0,
                "classFilter": {"refPath": "/Script/Engine.Actor"},
                "maxLabels": 0
            },
            "bShowUI": show_ui
        }
        res = self.call_tool("EditorToolset.EditorAppToolset", "CaptureViewport", args)
        if isinstance(res, dict) and "image" in res:
            img_b64 = res["image"]["data"]
        else:
            raise RuntimeError(f"Unexpected CaptureViewport response: {res}")

        img_bytes = base64.b64decode(img_b64)
        if save_path:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(img_bytes)
        return img_bytes

    def capture_pie_loop(
        self,
        cam_transform: Optional[Dict[str, Any]] = None,
        save_path: Optional[str] = None
    ) -> bytes:
        """Executes the standard Stage 5 closed-loop capture: StartPIE -> CaptureViewport -> StopPIE."""
        self.start_pie(cam_transform=cam_transform, warmup=1.2)
        try:
            return self.capture_viewport(cam_transform=cam_transform, save_path=save_path, show_ui=False)
        finally:
            self.stop_pie()

    def get_current_level(self) -> str:
        return self.call_tool("editor_toolset.toolsets.scene.SceneTools", "get_current_level", {})

    def find_actors(self, name: str = "", tag: str = "") -> List[Dict[str, Any]]:
        return self.call_tool("editor_toolset.toolsets.scene.SceneTools", "find_actors", {
            "name": name,
            "tag": tag,
            "collision_channels": []
        })

    def destroy_actor(self, actor_ref_path: str) -> Any:
        return self.call_tool("editor_toolset.toolsets.actor.ActorTools", "destroy_actor", {
            "actor": {"refPath": actor_ref_path}
        })

    def get_actor_transform(self, actor_ref_path: str) -> Dict[str, Any]:
        return self.call_tool("editor_toolset.toolsets.actor.ActorTools", "get_transform", {
            "actor": {"refPath": actor_ref_path}
        })

    def set_actor_transform(self, actor_ref_path: str, transform: Dict[str, Any]) -> Any:
        return self.call_tool("editor_toolset.toolsets.actor.ActorTools", "set_transform", {
            "actor": {"refPath": actor_ref_path},
            "transform": transform
        })

    def import_texture(self, folder_path: str, asset_name: str, source_file: str) -> Any:
        """Imports an external image file as an Unreal Engine Texture2D asset."""
        return self.call_tool("editor_toolset.toolsets.texture.TextureTools", "import_file", {
            "folder_path": folder_path,
            "asset_name": asset_name,
            "source_file": source_file
        })

    def save_assets(self, asset_paths: List[str]) -> Any:
        """Explicitly saves asset packages to disk to avoid losing changes."""
        return self.call_tool("editor_toolset.toolsets.asset.AssetTools", "save_assets", {
            "asset_paths": asset_paths
        })

    def create_material_instance(self, folder_path: str, asset_name: str, parent: str) -> Any:
        """Creates a MaterialInstanceConstant with the given parent material."""
        return self.call_tool("editor_toolset.toolsets.material_instance.MaterialInstanceTools", "create", {
            "folder_path": folder_path,
            "asset_name": asset_name,
            "parent": {"refPath": parent}
        })

    def set_texture_parameter(self, instance_ref: str, param_name: str, texture_ref: str) -> Any:
        """Sets a texture parameter on a MaterialInstance."""
        return self.call_tool("editor_toolset.toolsets.material_instance.MaterialInstanceTools", "set_texture_parameter", {
            "instance": {"refPath": instance_ref},
            "name": param_name,
            "value": {"refPath": texture_ref}
        })

    def get_mesh_material_slots(self, mesh_ref: str) -> List[str]:
        """Queries the material slot names of a StaticMesh asset."""
        res = self.call_tool("editor_toolset.toolsets.static_mesh.StaticMeshTools", "get_material_slots", {
            "mesh": {"refPath": mesh_ref}
        })
        return res if isinstance(res, list) else []

    def set_mesh_material(self, mesh_ref: str, slot_name: str, material_ref: str) -> Any:
        """Assigns a Material or MaterialInstance to a StaticMesh slot."""
        return self.call_tool("editor_toolset.toolsets.static_mesh.StaticMeshTools", "set_material", {
            "mesh": {"refPath": mesh_ref},
            "slot_name": slot_name,
            "material": {"refPath": material_ref}
        })

    def add_to_scene_from_asset(self, asset_ref: str, transform: Dict[str, Any]) -> Any:
        """Spawns an actor into the active level from a project asset."""
        return self.call_tool("editor_toolset.toolsets.scene.SceneTools", "add_to_scene_from_asset", {
            "asset": {"refPath": asset_ref},
            "transform": transform
        })

