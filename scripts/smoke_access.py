"""One harmless request to a selected free/subscription model; no retries or fallback.

Run only with explicit permission. This is an access check, not a benchmark.
Uses the standard curl client shown in the providers' REST documentation.
Credentials are passed over stdin, never command-line arguments or logged headers.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "The submitted number is 7. Is the submitted number odd? Reply with exactly YES or NO."
JEV_URL = "https://opencode.ai/inference/systemone/v1/systemone"
JEV_TRIAL_URL = "https://jevmodel.org/v1/systemone"
JEV_TRIAL_MODEL = "jev-1.13.0"


def env_secret(name):
    path = ROOT / ".env.local"
    if path.is_symlink():
        raise ValueError("Credential file cannot be a symbolic link")
    values = [line.split("=", 1)[1] for line in path.read_text().splitlines()
              if line.startswith(name + "=")]
    if len(values) != 1 or not values[0] or any(c.isspace() for c in values[0]):
        raise ValueError("Missing or ambiguous credential")
    return values[0]


def post(url, payload, headers):
    # Do not follow redirects: bearer credentials must stay on the named endpoint.
    with tempfile.TemporaryDirectory(prefix="decision-context-smoke-") as temporary:
        request_path = Path(temporary) / "request.json"
        response_path = Path(temporary) / "response.txt"
        headers_path = Path(temporary) / "response-headers.txt"
        request_path.write_text(json.dumps(payload))
        config = ["url = " + json.dumps(url), 'request = "POST"',
                  'header = "Content-Type: application/json"',
                  "data-binary = " + json.dumps("@" + str(request_path)),
                  "output = " + json.dumps(str(response_path)),
                  "dump-header = " + json.dumps(str(headers_path)),
                  'write-out = "%{http_code}"', "silent", "show-error",
                  "connect-timeout = 10", "max-time = 60"]
        for name, value in headers.items():
            if any(character in value for character in "\r\n"):
                raise ValueError("Invalid credential header")
            config.append("header = " + json.dumps(name + ": " + value))
        started = time.perf_counter()
        result = subprocess.run(["/usr/bin/curl", "--config", "-"],
                                input="\n".join(config) + "\n", text=True,
                                capture_output=True, timeout=65, check=False)
        elapsed = round(time.perf_counter() - started, 3)
        status = int(result.stdout) if result.stdout.isdigit() else 0
        body = response_path.read_text() if response_path.exists() else ""
        safe_headers = {}
        if headers_path.exists():
            for line in headers_path.read_text().splitlines():
                if ":" in line:
                    name, value = line.split(":", 1)
                    if name.lower() in {"x-tokens-remaining", "retry-after"}:
                        safe_headers[name.lower()] = value.strip()
        if result.returncode:
            return {"http_status": status, "elapsed_seconds": elapsed,
                    "transport_exit_code": result.returncode}, None
        return {"http_status": status, "elapsed_seconds": elapsed,
                "response_headers": safe_headers}, body


def parse_openai_stream(body):
    completed = None
    text_deltas = []
    done_text = []
    output_items = []
    # SSE permits several data lines in one event; [DONE] is not completion proof.
    for event in body.replace("\r\n", "\n").split("\n\n"):
        data = "\n".join(line[5:].lstrip(" ") for line in event.splitlines()
                         if line.startswith("data:"))
        if not data or data == "[DONE]":
            continue
        item = json.loads(data)
        if item.get("type") in {"response.failed", "response.incomplete", "error"}:
            raise ValueError("Response stream did not complete successfully")
        if item.get("type") == "response.output_text.delta":
            text_deltas.append(item.get("delta", ""))
        if item.get("type") == "response.output_text.done":
            done_text.append(item.get("text", ""))
        if item.get("type") == "response.output_item.done":
            output_items.append(item["item"])
        if item.get("type") == "response.completed":
            completed = item["response"]
    if completed is None or completed.get("status") != "completed":
        raise ValueError("Missing response.completed")
    text = "".join(content.get("text", "") for item in completed.get("output", [])
                   for content in item.get("content", []) if content.get("type") == "output_text")
    if not text:
        text = "".join(done_text) or "".join(text_deltas)
    return {"response": completed, "stream_output_items": output_items, "stream_output_text": text}


def request_for(provider):
    if provider == "jevmodel":
        verified = json.loads((ROOT / ".secrets/jevmodel-access.json").read_text())
        if verified.get("free_token_balance", 0) < 1000 or verified.get("payment_configured") is not False:
            raise ValueError("Free API trial has not been verified")
        if verified.get("successful_smoke_test_completed"):
            raise ValueError("The authorized tiny trial test is already complete")
        if verified.get("allowed_model") != JEV_TRIAL_MODEL:
            raise ValueError("Pinned model does not match the verified access record")
        return JEV_TRIAL_URL, {
            "model": JEV_TRIAL_MODEL, "state": "The submitted number is 7.",
            "questions": {"is_odd": {"type": "noul", "instructions": "Is the submitted number odd?"}},
        }, {"Authorization": "Bearer " + env_secret("JEVMODEL_API_KEY")}, "Verified free signup token grant; no payment configured"
    if provider == "jev":
        return JEV_URL, {
            "model": "jev-1.13-free", "state": "The submitted number is 7.",
            "questions": {"is_odd": {"type": "noul", "instructions": "Is the submitted number odd?"}},
        }, {"Authorization": "Bearer " + env_secret("OPENCODE_API_KEY")}, "OpenCode promotional free model"
    if provider == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent", {
            "contents": [{"role": "user", "parts": [{"text": PROMPT}]}],
            "generationConfig": {"maxOutputTokens": 128},
        }, {"x-goog-api-key": env_secret("GEMINI_API_KEY")}, "Gemini API project verified as Free tier"
    credential_path = ROOT / ".secrets/chatgpt.json"
    if credential_path.is_symlink():
        raise ValueError("Credential file cannot be a symbolic link")
    credentials = json.loads(credential_path.read_text())
    if "chatgpt.tokens.use.direct" not in credentials.get("scopes", []):
        raise ValueError("ChatGPT plan usage was not authorized")
    catalog = json.loads((ROOT / ".secrets/openai-models.json").read_text())
    if not any(item["slug"] == "gpt-6-luna" for item in catalog["models"]):
        raise ValueError("Requested model absent from authorized account catalog")
    return "https://api.openai.com/v1/responses", {
        "model": "gpt-6-luna", "input": [{"role": "user", "content": PROMPT}],
        "store": False, "stream": True,
    }, {"Authorization": "Bearer " + credentials["access_token"]}, "Authorized ChatGPT subscription; no API-key fallback"


def run(provider):
    url, payload, headers, access = request_for(provider)
    result = {"provider": provider, "started_at": datetime.now(timezone.utc).isoformat(),
              "purpose": "single-request connectivity smoke test; not a benchmark",
              "access_route": access, "endpoint": url, "request": payload,
              "automatic_retries": 0, "paid_fallback": False}
    observation, body = post(url, payload, headers)
    result.update(observation)
    if observation["http_status"] != 200 or body is None:
        result["status"] = "failed"
        if body:
            try:
                error = json.loads(body)
                # Only known diagnostic fields; never record arbitrary server bodies.
                result["error"] = {name: error[name] for name in
                                   ["title", "error_code", "error_name", "error_category", "retryable"]
                                   if name in error}
                if isinstance(error.get("error"), dict):
                    result["error"]["provider_code"] = error["error"].get("code")
                    result["error"]["provider_status"] = error["error"].get("status")
                    result["error"]["provider_type"] = error["error"].get("type")
                    message = str(error["error"].get("message", ""))
                    for secret in headers.values():
                        message = message.replace(secret, "[redacted]")
                        message = message.replace(secret.removeprefix("Bearer "), "[redacted]")
                    result["error"]["provider_message"] = message[:1000]
            except ValueError:
                result["error"] = {"format": "non-JSON response"}
    else:
        try:
            response = parse_openai_stream(body) if provider == "openai" else json.loads(body)
            result["response"] = response
            result["status"] = "response_received"
            if provider == "jevmodel":
                probability = response["answers"]["is_odd"]["noul"]
                if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not 0 <= probability <= 1:
                    raise ValueError("Invalid noul probability")
                result["answer"] = "YES" if probability > 0.5 else "NO"
                result["probability_yes"] = probability
                result["returned_model"] = response.get("model")
                result["version_confirmed"] = response.get("model") == JEV_TRIAL_MODEL
                result["passed"] = result["answer"] == "YES" and result["version_confirmed"]
            elif provider == "gemini":
                candidates = response.get("candidates", [])
                text = "".join(part.get("text", "") for candidate in candidates
                               for part in candidate.get("content", {}).get("parts", [])
                               if not part.get("thought"))
                result["answer"] = text.strip()
                result["passed"] = bool(candidates) and all(c.get("finishReason") == "STOP" for c in candidates) and text.strip() == "YES"
            elif provider == "openai":
                text = response["stream_output_text"]
                result["answer"] = text.strip()
                result["passed"] = text.strip() == "YES"
        except (ValueError, KeyError, TypeError):
            result["status"] = "invalid_or_incomplete_response"
    destination = ROOT / "results/raw/smoke"
    destination.mkdir(parents=True, exist_ok=True)
    filename = provider + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    path = destination / filename
    path.write_text(json.dumps(result, indent=2) + "\n")
    summary = {name: result[name] for name in
               ["provider", "status", "http_status", "elapsed_seconds", "answer", "probability_yes", "returned_model", "version_confirmed", "passed", "error"]
               if name in result}
    summary["record"] = str(path)
    print(json.dumps(summary), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=["jev", "jevmodel", "gemini", "openai"])
    arguments = parser.parse_args()
    try:
        result = run(arguments.provider)
        raise SystemExit(0 if result.get("passed") else 1)
    except Exception as error:
        print(json.dumps({"provider": arguments.provider, "status": "setup_or_transport_error",
                          "error_type": type(error).__name__}))
        raise SystemExit(1)
