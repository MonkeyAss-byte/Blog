"""ComfyUI Workflow API Runner
Enables programmatic execution of ComfyUI workflows via HTTP/WebSocket API.
Converts ComfyUI workflow JSON files into executable Python pipelines.
"""

import os
import sys
import json
import time
import random
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List

DEFAULT_COMFY_URL = "http://127.0.0.1:8188"

class ComfyWorkflowRunner:
    def __init__(self, host: str = DEFAULT_COMFY_URL):
        self.host = host.rstrip('/')

    def check_alive(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/system_stats", timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def load_workflow_json(self, json_path: str) -> Dict[str, Any]:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Handle cases where exported JSON wraps prompt in a list or subkey
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and any(isinstance(v, dict) and "class_type" in v for v in item.values()):
                    return item
            return data[0] if data else {}
        if "prompt" in data and isinstance(data["prompt"], dict):
            return data["prompt"]
        return data

    def queue_prompt(self, prompt: Dict[str, Any], client_id: Optional[str] = None) -> str:
        if not client_id:
            client_id = f"pipeline_agent_{random.randint(1000, 9999)}"
        
        extra_data = {}
        try:
            # Dynamically pull credentials from comfy-cli persistent session / API key
            from comfy_cli.credentials import get_session, find_api_key
            cred = find_api_key(purpose="partner") or find_api_key(purpose="cloud")
            if cred and cred.value:
                extra_data["api_key_comfy_org"] = cred.value
            else:
                session = get_session()
                if session and session.access_token:
                    extra_data["auth_token_comfy_org"] = session.access_token
        except Exception:
            pass

        data = {"prompt": prompt, "client_id": client_id}
        if extra_data:
            data["extra_data"] = extra_data

        payload = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            f"{self.host}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            if "prompt_id" not in res:
                raise RuntimeError(f"Failed to queue prompt: {res}")
            return res["prompt_id"]

    def wait_for_execution(self, prompt_id: str, timeout_seconds: int = 1800, poll_interval: float = 1.5) -> Dict[str, Any]:
        start = time.time()
        while time.time() - start < timeout_seconds:
            try:
                with urllib.request.urlopen(f"{self.host}/history/{prompt_id}") as resp:
                    history = json.loads(resp.read().decode('utf-8'))
                    if prompt_id in history:
                        item = history[prompt_id]
                        status = item.get("status", {})
                        if status.get("status_str") == "error":
                            raise RuntimeError(f"ComfyUI execution error: {status.get('messages', '')}")
                        if item.get("outputs"):
                            return item
            except Exception as e:
                if "execution error" in str(e):
                    raise
            time.sleep(poll_interval)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out after {timeout_seconds} seconds.")

    def run_workflow(self, workflow_json_path: str, parameter_overrides: Optional[Dict[str, Dict[str, Any]]] = None, timeout: int = 3600) -> Dict[str, Any]:
        """
        Runs a ComfyUI workflow JSON with dynamic parameter overrides.
        parameter_overrides format:
        {
            "node_id_or_title": {
                "input_name": new_value
            }
        }
        """
        prompt = self.load_workflow_json(workflow_json_path)
        
        # Apply overrides
        if parameter_overrides:
            for target_id, inputs_to_override in parameter_overrides.items():
                matched_id = None
                if target_id in prompt:
                    matched_id = target_id
                else:
                    for nid, nval in prompt.items():
                        title = nval.get("_meta", {}).get("title", "")
                        if title == target_id:
                            matched_id = nid
                            break
                if matched_id:
                    for k, v in inputs_to_override.items():
                        prompt[matched_id]["inputs"][k] = v
                else:
                    print(f"[Warning] Node '{target_id}' not found in workflow for parameter override.")

        prompt_id = self.queue_prompt(prompt)
        print(f"Workflow queued successfully. Prompt ID: {prompt_id}")
        result = self.wait_for_execution(prompt_id, timeout_seconds=timeout)
        print(f"Workflow {prompt_id} completed successfully.")
        return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python comfy_runner.py <workflow.json> [overrides_json]")
        sys.exit(1)
    wf_path = sys.argv[1]
    overrides = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    runner = ComfyWorkflowRunner()
    res = runner.run_workflow(wf_path, overrides)
    print("Outputs:", json.dumps(res.get("outputs", {}), indent=2))
