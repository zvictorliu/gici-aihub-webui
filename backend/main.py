from flask import Flask, request, jsonify, Response
import json
import os
import requests
import tomllib
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Paths
BACKEND_DIR = Path(__file__).parent
ROOT_DIR = BACKEND_DIR.parent
USERS_FILE = BACKEND_DIR / "users.json"
SYSTEM_WS_FILE = BACKEND_DIR / "system-workspaces.json"
CONFIG_DIR = ROOT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "appConfig.toml"
WS_CONFIG_DIR = CONFIG_DIR / "workspaces"
OPENCODE_URL = os.getenv("OPENCODE_URL", "http://127.0.0.1:5000")

# Ensure workspace config dir exists
WS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Load base config
with open(CONFIG_FILE, "rb") as f:
    app_config = tomllib.load(f)

DEFAULT_DIRECTORY = app_config.get("app", {}).get("default_directory", "")


def load_users():
    if not USERS_FILE.exists():
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def load_system_workspaces():
    if not SYSTEM_WS_FILE.exists():
        return []
    with open(SYSTEM_WS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def get_merged_config(workspace_id=None):
    config = json.loads(json.dumps(app_config))  # Deep copy
    if workspace_id:
        ws_config_file = WS_CONFIG_DIR / f"{workspace_id}.toml"
        if ws_config_file.exists():
            with open(ws_config_file, "rb") as f:
                ws_specific = tomllib.load(f)
                for key, value in ws_specific.items():
                    if (
                        key in config
                        and isinstance(config[key], dict)
                        and isinstance(value, dict)
                    ):
                        config[key].update(value)
                    else:
                        config[key] = value
    return config


def get_forward_headers():
    headers = {}
    workspace_path = (
        request.headers.get("x-workspace-path")
        or request.args.get("workspace_path")
        or DEFAULT_DIRECTORY
    )
    if workspace_path:
        headers["x-opencode-directory"] = workspace_path
    return headers


@app.route("/api/config/providers", methods=["GET"])
def get_providers():
    workspace_id = request.headers.get("x-workspace-id")
    current_config = get_merged_config(workspace_id)
    # Note: If providers were in config, we'd use them here.
    # For now, we still proxy to opencode, but we might need config for other UI elements.
    try:
        resp = requests.get(f"{OPENCODE_URL}/config/providers")
        data = resp.json()
        providers = data if isinstance(data, list) else data.get("providers", [])
        return jsonify(providers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/config/ui", methods=["GET"])
def get_ui_config():
    workspace_id = request.headers.get("x-workspace-id")
    return jsonify(get_merged_config(workspace_id))


@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Missing username"}), 400

    try:
        # 1. Get all sessions from OpenCode
        resp = requests.get(f"{OPENCODE_URL}/session", headers=get_forward_headers())
        all_sessions = resp.json()
        if not isinstance(all_sessions, list):
            all_sessions = all_sessions.get("sessions", [])

        # 2. Get allowed session IDs for the user
        users = load_users()
        user = next((u for u in users if u["username"] == username), None)
        if not user:
            return jsonify([])

        allowed_ids = user.get("sessions", [])

        # 3. Filter and simplify
        filtered = [
            {"id": s["id"], "title": s.get("title", "Untitled")}
            for s in all_sessions
            if s["id"] in allowed_ids
        ]
        return jsonify(filtered)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions", methods=["POST"])
def create_session():
    data = request.json
    username = data.get("username")

    if not username:
        return jsonify({"error": "Missing username"}), 400

    try:
        # 1. Create session in OpenCode
        resp = requests.post(
            f"{OPENCODE_URL}/session",
            json={},
            headers=get_forward_headers(),
        )
        session_data = resp.json()
        session_id = session_data.get("id") or session_data.get("session_id")

        if not session_id:
            return jsonify({"error": "Failed to create session in OpenCode"}), 500

        # 2. Link to user
        users = load_users()
        user = next((u for u in users if u["username"] == username), None)
        if user:
            if "sessions" not in user:
                user["sessions"] = []
            if session_id not in user["sessions"]:
                user["sessions"].append(session_id)
            save_users(users)
            return jsonify({"id": session_id, "title": "新会话"})

        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>/messages", methods=["GET"])
def get_session_messages(session_id):
    try:
        resp = requests.get(
            f"{OPENCODE_URL}/session/{session_id}/message",
            headers=get_forward_headers(),
        )
        raw_messages = resp.json()

        simplified = []
        if isinstance(raw_messages, list):
            for msg in raw_messages:
                info = msg.get("info", {})
                role = info.get("role") or msg.get("role")
                timestamp = info.get("time", {}).get("created")

                # Extract providerID and modelID
                provider_id = info.get("providerID")
                model_id = info.get("modelID")

                # Sometimes it might be nested in a model object for user messages?
                # According to message.json: "model": { "providerID": "minimax-cn", "modelID": "MiniMax-M2.1" }
                if not provider_id and "model" in info:
                    provider_id = info["model"].get("providerID")
                if not model_id and "model" in info:
                    model_id = info["model"].get("modelID")

                text = "".join(
                    [
                        part.get("text", "")
                        for part in msg.get("parts", [])
                        if part.get("type") == "text"
                    ]
                )

                parts = []
                reasoning_content = []
                for p in msg.get("parts", []):
                    p_type = p.get("type")
                    if p_type == "reasoning":
                        reasoning_content.append(p.get("text", ""))
                    elif p_type == "text":
                        parts.append(
                            {
                                "id": p.get("id"),
                                "type": "text",
                                "content": p.get("text", ""),
                            }
                        )

                if reasoning_content:
                    parts.insert(
                        0,
                        {
                            "id": "merged-reasoning",
                            "type": "reasoning",
                            "content": "\n\n".join(filter(None, reasoning_content)),
                        },
                    )

                # Handle messages with errors in history
                is_error = False
                if not text and not parts and info.get("error"):
                    is_error = True
                    error_info = info.get("error", {})
                    error_msg = (
                        error_info.get("data", {}).get("message")
                        or error_info.get("message")
                        or "AI 引擎返回错误"
                    )
                    text = f"**错误：** {error_msg}"

                if text or parts:
                    # Check if we can merge with previous assistant message having the same parentID
                    parent_id = info.get("parentID")
                    if (
                        role == "assistant"
                        and parent_id
                        and simplified
                        and simplified[-1]["sender"] == "assistant"
                        and simplified[-1].get("parentID") == parent_id
                    ):
                        # Append text if it exists
                        if text:
                            if simplified[-1]["text"]:
                                simplified[-1]["text"] += "\n" + text
                            else:
                                simplified[-1]["text"] = text

                        # Merge parts: specifically handle reasoning
                        for p in parts:
                            if p["type"] == "reasoning":
                                existing_reasoning = next(
                                    (
                                        item
                                        for item in simplified[-1]["parts"]
                                        if item["type"] == "reasoning"
                                    ),
                                    None,
                                )
                                if existing_reasoning:
                                    if existing_reasoning["content"] and p["content"]:
                                        existing_reasoning["content"] += (
                                            "\n" + p["content"]
                                        )
                                    elif p["content"]:
                                        existing_reasoning["content"] = p["content"]
                                else:
                                    simplified[-1]["parts"].insert(0, p)
                            else:
                                simplified[-1]["parts"].append(p)
                    else:
                        simplified.append(
                            {
                                "text": text,
                                "parts": parts,
                                "sender": "user" if role == "user" else "assistant",
                                "timestamp": timestamp,
                                "providerID": provider_id,
                                "modelID": model_id,
                                "isError": is_error,
                                "parentID": parent_id,
                            }
                        )

        return jsonify(simplified)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>/messages", methods=["POST"])
def send_session_message(session_id):
    data = request.json
    try:
        # Prepare request for OpenCode
        provider_id = data.get("providerID")
        model_id = data.get("modelID")
        opencode_payload = {
            "model": {"providerID": provider_id, "modelID": model_id},
            "mode": data.get("mode"),
            "parts": [{"type": "text", "text": data.get("message")}],
        }

        resp = requests.post(
            f"{OPENCODE_URL}/session/{session_id}/message",
            json=opencode_payload,
            headers=get_forward_headers(),
        )
        resp_data = resp.json()

        if "error" in resp_data:
            return jsonify({"error": resp_data["error"]}), 400

        parts = resp_data.get("parts", [])
        text = "".join([p.get("text", "") for p in parts if p.get("type") == "text"])

        if not text:
            has_tool_call = any(p.get("type") == "tool_call" for p in parts)
            text = (
                "AI 专家正在进行后台分析，请稍候。" if has_tool_call else "收到空回复。"
            )

        # Try to get timestamp and confirm IDs from response if available
        info = resp_data.get("info", {})
        timestamp = info.get("time", {}).get("created")

        # Handle error messages from OpenCode (e.g., Authentication Fails, Model not found)
        is_error = False
        error_info = info.get("error", {})
        if error_info:
            is_error = True
            error_msg = (
                error_info.get("data", {}).get("message")
                or error_info.get("message")
                or "AI 引擎返回错误"
            )
            text = f"**错误：** {error_msg}"

        return jsonify(
            {
                "text": text,
                "parts": [
                    {
                        "id": p.get("id"),
                        "type": p.get("type"),
                        "content": p.get("text", ""),
                    }
                    for p in parts
                    if p.get("type") in ["text", "reasoning"]
                ],
                "timestamp": timestamp,
                "providerID": info.get("providerID") or provider_id,
                "modelID": info.get("modelID") or model_id,
                "isError": is_error,
                "parentID": info.get("parentID"),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>", methods=["PATCH", "DELETE"])
def handle_session(session_id):
    try:
        if request.method == "PATCH":
            resp = requests.patch(
                f"{OPENCODE_URL}/session/{session_id}",
                json=request.json,
                headers=get_forward_headers(),
            )
            headers = [
                (name, value)
                for (name, value) in resp.headers.items()
                if name.lower()
                not in [
                    "content-encoding",
                    "content-length",
                    "transfer-encoding",
                    "connection",
                ]
            ]
            return Response(resp.content, resp.status_code, headers)

        elif request.method == "DELETE":
            # Delete from OpenCode
            resp = requests.delete(
                f"{OPENCODE_URL}/session/{session_id}", headers=get_forward_headers()
            )

            # Also remove from users.json if possible
            username = request.args.get("username")
            if username:
                users = load_users()
                user = next((u for u in users if u["username"] == username), None)
                if user and "sessions" in user and session_id in user["sessions"]:
                    user["sessions"].remove(session_id)
                    save_users(users)

            headers = [
                (name, value)
                for (name, value) in resp.headers.items()
                if name.lower()
                not in [
                    "content-encoding",
                    "content-length",
                    "transfer-encoding",
                    "connection",
                ]
            ]
            return Response(resp.content, resp.status_code, headers)

        return jsonify({"error": "Method not allowed"}), 405

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "缺少用户名或密码"}), 400

    users = load_users()

    if any(u["username"] == username for u in users):
        return jsonify({"error": "用户名已存在"}), 400

    users.append({
        "username": username,
        "password": password,
        "sessions": [],
        "workspaces": []
    })
    save_users(users)

    return jsonify({"username": username, "message": "注册成功"})


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "缺少用户名或密码"}), 400

    users = load_users()
    user = next((u for u in users if u["username"] == username and u["password"] == password), None)

    if not user:
        return jsonify({"error": "用户名或密码错误"}), 401

    return jsonify({"username": username})


@app.route("/api/auth/workspaces", methods=["GET"])
def get_user_workspaces():
    username = request.args.get("username")
    if not username:
        return jsonify({"system": [], "user": []}), 400

    system_workspaces = load_system_workspaces()

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    user_workspaces = user.get("workspaces", []) if user else []

    return jsonify({"system": system_workspaces, "user": user_workspaces})


@app.route("/api/auth/workspaces", methods=["POST"])
def add_user_workspace():
    data = request.json
    username = data.get("username")
    path = data.get("path")
    ws_id = data.get("id")
    name = data.get("name") or (path.split("/")[-1] if path else "New Workspace")

    if not username or not path or not ws_id:
        return jsonify({"error": "缺少参数 (path, id)"}), 400

    if not re.match(r"^[a-zA-Z0-9_-]+$", ws_id):
        return jsonify(
            {"error": "ID 包含非法字符 (仅允许字母、数字、下划线 and 连字符)"}
        ), 400

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if user:
        if "workspaces" not in user:
            user["workspaces"] = []
        # Check if already exists in user workspaces
        if not any(ws["id"] == ws_id for ws in user["workspaces"]):
            user["workspaces"].append({"id": ws_id, "path": path, "name": name})
            save_users(users)

        system_workspaces = load_system_workspaces()
        return jsonify(
            {"success": True, "system": system_workspaces, "user": user["workspaces"]}
        )
    return jsonify({"error": "用户不存在"}), 404


@app.route("/api/auth/workspaces", methods=["DELETE"])
def remove_user_workspace():
    username = request.args.get("username")
    path = request.args.get("path")

    if not username or not path:
        return jsonify({"error": "缺少参数"}), 400

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if user and "workspaces" in user:
        user["workspaces"] = [ws for ws in user["workspaces"] if ws["path"] != path]
        save_users(users)
        return jsonify({"success": True})
    return jsonify({"error": "用户不存在"}), 404


@app.route("/api/config/active", methods=["GET"])
def get_active_config():
    workspace_id = request.args.get("workspace_id")
    return jsonify(get_merged_config(workspace_id))


@app.route("/api/events")
def stream_events():
    """Proxy SSE events from opencode to the frontend."""
    headers = get_forward_headers()

    def generate():
        try:
            # Connect to opencode's global event stream
            # Using stream=True to read chunks
            resp = requests.get(
                f"{OPENCODE_URL}/event", headers=headers, stream=True, timeout=None
            )
            for line in resp.iter_lines():
                if line:
                    # Relaying the SSE line
                    yield line.decode("utf-8") + "\n\n"
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    url = f"{OPENCODE_URL}/{path}"

    # Forward the request to the opencode server
    headers = {key: value for (key, value) in request.headers if key != "Host"}
    workspace_path = request.headers.get("x-workspace-path") or DEFAULT_DIRECTORY
    workspace_id = request.headers.get("x-workspace-id") or "default"

    if workspace_path:
        headers["x-opencode-directory"] = workspace_path

    # Optionally forward ID if opencode server needs it,
    # but the core requirement was directory mapping and local config override.

    resp = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
        params=list(request.args.items(multi=True)),
    )

    # Exclude certain headers from the response
    excluded_headers = [
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    ]
    headers = [
        (name, value)
        for (name, value) in resp.raw.headers.items()
        if name.lower() not in excluded_headers
    ]

    return Response(resp.content, resp.status_code, headers)


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"

    app.run(host=host, port=port, debug=debug)
