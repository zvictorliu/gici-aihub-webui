from flask import Flask, request, jsonify, Response
import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Paths
BACKEND_DIR = Path(__file__).parent
USERS_FILE = BACKEND_DIR / "users.json"
OPENCODE_URL = os.getenv("OPENCODE_URL", "http://127.0.0.1:5000")


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


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    users = load_users()
    if any(u["username"] == username for u in users):
        return jsonify({"error": "用户名已存在"}), 400

    users.append({"username": username, "password": password})
    save_users(users)
    return jsonify({"success": True, "username": username})


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    users = load_users()
    user = next(
        (u for u in users if u["username"] == username and u["password"] == password),
        None,
    )

    if not user:
        return jsonify({"error": "用户名或密码错误"}), 401

    return jsonify({"success": True, "username": username})


@app.route("/api/auth/add_session", methods=["POST"])
def add_session():
    data = request.json
    username = data.get("username")
    session_id = data.get("sessionId")

    if not username or not session_id:
        return jsonify({"error": "缺少参数"}), 400

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if user:
        if "sessions" not in user:
            user["sessions"] = []
        if session_id not in user["sessions"]:
            user["sessions"].append(session_id)
        save_users(users)
        return jsonify({"success": True})
    return jsonify({"error": "用户不存在"}), 404


@app.route("/api/auth/user_sessions", methods=["GET"])
def get_user_sessions():
    username = request.args.get("username")
    if not username:
        return jsonify([]), 400

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if user:
        return jsonify(user.get("sessions", []))
    return jsonify([])


@app.route("/api/auth/remove_session", methods=["POST"])
def remove_session():
    data = request.json
    username = data.get("username")
    session_id = data.get("sessionId")

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    if user and "sessions" in user:
        if session_id in user["sessions"]:
            user["sessions"].remove(session_id)
            save_users(users)
        return jsonify({"success": True})
    return jsonify({"error": "用户或会话不存在"}), 404


@app.route("/api/config/providers", methods=["GET"])
def get_providers():
    try:
        resp = requests.get(f"{OPENCODE_URL}/config/providers")
        data = resp.json()
        providers = data if isinstance(data, list) else data.get("providers", [])

        # Return simplified provider list
        return jsonify(providers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Missing username"}), 400

    try:
        # 1. Get all sessions from OpenCode
        resp = requests.get(f"{OPENCODE_URL}/session")
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
    title = data.get("title", "New Chat Session")

    if not username:
        return jsonify({"error": "Missing username"}), 400

    try:
        # 1. Create session in OpenCode
        resp = requests.post(f"{OPENCODE_URL}/session", json={"title": title})
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
            return jsonify({"id": session_id, "title": title})

        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>/messages", methods=["GET"])
def get_session_messages(session_id):
    try:
        resp = requests.get(f"{OPENCODE_URL}/session/{session_id}/message")
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

                # Handle messages with errors in history
                is_error = False
                if not text and info.get("error"):
                    is_error = True
                    error_info = info.get("error", {})
                    error_msg = (
                        error_info.get("data", {}).get("message")
                        or error_info.get("message")
                        or "AI 引擎返回错误"
                    )
                    text = f"**错误：** {error_msg}"

                if text:
                    simplified.append(
                        {
                            "text": text,
                            "sender": "user" if role == "user" else "assistant",
                            "timestamp": timestamp,
                            "providerID": provider_id,
                            "modelID": model_id,
                            "isError": is_error,
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
            f"{OPENCODE_URL}/session/{session_id}/message", json=opencode_payload
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
                "timestamp": timestamp,
                "providerID": info.get("providerID") or provider_id,
                "modelID": info.get("modelID") or model_id,
                "isError": is_error,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>", methods=["PATCH", "DELETE"])
def handle_session(session_id):
    try:
        if request.method == "PATCH":
            resp = requests.patch(
                f"{OPENCODE_URL}/session/{session_id}", json=request.json
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
            resp = requests.delete(f"{OPENCODE_URL}/session/{session_id}")

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


@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    url = f"{OPENCODE_URL}/{path}"

    # Forward the request to the opencode server
    resp = requests.request(
        method=request.method,
        url=url,
        headers={key: value for (key, value) in request.headers if key != "Host"},
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
