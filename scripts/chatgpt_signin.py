"""Project-specific ChatGPT authorization; never reads Codex credentials.

Official flow: https://developers.openai.com/siwc/token-sharing-open-source/sign-in
This utility exchanges authorization and lists model metadata. It cannot run inference.
"""

import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
import uuid

import jwt

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".secrets"
ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
APP_NAME = "Decision Context Benchmark"


def private_json(path, data):
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Refusing a symbolic link for credentials")
    path.parent.mkdir(mode=0o700, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(path.name + "." + secrets.token_hex(12))
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(url, *, body=None, token=None):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(url, data=body, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def callback_values(query, expected_state):
    values = parse_qs(query, keep_blank_values=True)
    # Reject duplicate fields rather than silently accepting one value.
    if any(len(value) != 1 for value in values.values()):
        raise ValueError("Duplicate callback parameters")
    state = values.get("state", [""])[0]
    if not hmac.compare_digest(state, expected_state):
        raise ValueError("Authorization state mismatch")
    if "error" in values:
        raise ValueError("Authorization was not granted")
    code = values.get("code", [""])[0]
    client_id = values.get("client_id", [""])[0]
    if not code or not client_id.startswith("oaiapp_"):
        raise ValueError("Registration did not return an issued client ID")
    return code, client_id


def validate_identity(token, key, client_id, nonce):
    identity = jwt.decode(
        token, key, algorithms=["RS256"], issuer=ISSUER, audience=client_id,
        leeway=5, options={"require": ["sub", "exp", "iat", "nonce"]},
    )
    if not hmac.compare_digest(identity["nonce"], nonce):
        raise ValueError("Identity nonce mismatch")
    if not isinstance(identity["sub"], str) or not identity["sub"]:
        raise ValueError("Identity subject missing")
    return identity


def main():
    credential_path = PRIVATE / "chatgpt.json"
    if credential_path.exists():
        raise ValueError("Project credentials already exist; no new registration started")
    host_path = PRIVATE / "host.json"
    if host_path.is_symlink():
        raise ValueError("Host record cannot be a symbolic link")
    if host_path.exists():
        host_id = json.loads(host_path.read_text())["ext_agent_host_id"]
    else:
        host_id = "urn:uuid:" + str(uuid.uuid4())
        private_json(host_path, {"ext_agent_host_id": host_id})

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = jwt.utils.base64url_encode(hashlib.sha256(verifier.encode()).digest()).decode()
    deadline = time.monotonic() + 20 * 60
    pending = {"used": False, "started": False}
    server = None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Callback URLs contain authorization codes.

        def page(self, status, text):
            body = ("<!doctype html><meta charset=utf-8><title>" + APP_NAME +
                    "</title><h1>" + APP_NAME + "</h1>" + text).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = urlsplit(self.path)
            if route.path == "/":
                self.page(200, "<p>Use your ChatGPT plan for this research project.</p>"
                          "<p>Authorization requests your account identity and permission to use plan tokens. "
                          "Credentials stay in this project's ignored <code>.secrets/chatgpt.json</code>.</p>"
                          "<p>Setup will only list available model names. No inference or paid API key creation.</p>"
                          '<a href="/start">Continue with ChatGPT</a>')
                return
            if time.monotonic() > deadline or pending["used"]:
                self.page(400, "<p>This authorization attempt has expired or was already used.</p>")
                return
            if route.path == "/start":
                if pending["started"]:
                    self.page(400, "<p>Sign-in is already in progress in the other tab.</p>")
                    return
                pending["started"] = True
                parameters = {
                    "client_id": "dynamic_agent_client", "agent_name_hint": APP_NAME,
                    "ext_agent_host_id": host_id, "response_type": "code",
                    "redirect_uri": redirect_uri, "resource": RESOURCE,
                    "scope": "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct",
                    "state": state, "nonce": nonce, "code_challenge_method": "S256",
                    "code_challenge": challenge,
                }
                self.send_response(302)
                self.send_header("Location", ISSUER + "/api/accounts/authorize?" + urlencode(parameters))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            if route.path != "/auth/callback":
                self.page(404, "<p>Unknown setup page.</p>")
                return
            try:
                code, client_id = callback_values(route.query, state)
                pending["used"] = True
                tokens = read_json(ISSUER + "/api/accounts/oauth/token", body=urlencode({
                    "grant_type": "authorization_code", "client_id": client_id,
                    "code": code, "code_verifier": verifier, "redirect_uri": redirect_uri,
                    "resource": RESOURCE,
                }).encode())
                scopes = tokens.get("scope", "").split()
                if "chatgpt.tokens.use.direct" not in scopes:
                    raise ValueError("ChatGPT plan permission was not granted")
                jwks = jwt.PyJWKClient(ISSUER + "/.well-known/jwks.json", timeout=30)
                key = jwks.get_signing_key_from_jwt(tokens["id_token"]).key
                identity = validate_identity(tokens["id_token"], key, client_id, nonce)
                private_json(credential_path, {
                    "issuer": ISSUER, "subject": identity["sub"],
                    "client_id": client_id, "ext_agent_host_id": host_id,
                    "id_token": tokens["id_token"], "access_token": tokens["access_token"],
                    "refresh_token": tokens.get("refresh_token"), "token_type": tokens["token_type"],
                    "expires_in": tokens.get("expires_in"), "scopes": scopes,
                    "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })
                print("ChatGPT credentials validated and saved locally.", flush=True)
                try:
                    catalog = read_json(RESOURCE + "/models", token=tokens["access_token"])
                    models = [{"slug": item["slug"], "display_name": item.get("display_name", item["slug"])}
                              for item in catalog["models"] if item.get("visibility") == "list"]
                    private_json(PRIVATE / "openai-models.json", {"models": models})
                    print(json.dumps({"available_models": models}), flush=True)
                    self.page(200, "<p>Connected. Credentials saved locally; available model names checked. "
                              "No benchmark inference was run.</p>")
                except Exception:
                    print("Credentials saved; model catalog check failed. No inference attempted.", flush=True)
                    self.page(200, "<p>Connected and saved. The model catalog check needs a follow-up. "
                              "No inference was run.</p>")
            except Exception as error:
                pending["used"] = True
                # Avoid outputting server bodies, tokens, claims, or callback URLs.
                kind = "HTTP " + str(error.code) if isinstance(error, HTTPError) else type(error).__name__
                print("ChatGPT setup failed (" + kind + "). No credential values logged.", flush=True)
                self.page(400, "<p>Authorization could not be completed. No credential values are shown. "
                          "Restart the setup utility before trying again.</p>")
            finally:
                threading.Thread(target=server.shutdown, daemon=True).start()

    server = HTTPServer(("127.0.0.1", 0), Handler)
    redirect_uri = "http://127.0.0.1:" + str(server.server_port) + "/auth/callback"
    timer = threading.Timer(20 * 60, server.shutdown)
    timer.daemon = True
    timer.start()
    print("Setup page: http://127.0.0.1:" + str(server.server_port) + "/", flush=True)
    try:
        server.serve_forever()
    finally:
        timer.cancel()
        server.server_close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Setup stopped (" + type(error).__name__ + "). No credentials logged.")
        raise SystemExit(1)
