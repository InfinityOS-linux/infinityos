"""AI controls; credentials stay with the provider CLIs."""
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
import urllib.request


def selected_ai(home=None):
    home = Path(home or Path.home())
    selected = [name for name in ("codex", "claude")
                if (home / f".local/bin/{name}").is_file()
                and (home / f".local/share/applications/infinityos-{name}.desktop").is_file()]
    marker = home / ".config/infinityos/local-ai-model"
    if marker.is_file() and marker.read_text().strip():
        selected.append("local")
    return tuple(selected)


def provider_command(provider, action):
    if provider not in ("codex", "claude") or action not in ("login", "logout"):
        raise ValueError("Unsupported account action")
    command = [str(Path.home() / f".local/bin/{provider}")]
    return command + (["auth"] if provider == "claude" else []) + [action]


def codex_account(binary):
    # Read JSON lines without a buffered readline hiding later replies from select().
    process = subprocess.Popen([binary, "app-server"], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    buffer = b""
    request_id = 0

    def request(method, params=None):
        nonlocal buffer, request_id
        request_id += 1
        message = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        process.stdin.write(json.dumps(message).encode() + b"\n")
        process.stdin.flush()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if b"\n" not in buffer:
                if not selector.select(max(0, deadline - time.monotonic())):
                    break
                data = os.read(process.stdout.fileno(), 65536)
                if not data:
                    raise RuntimeError("Provider disconnected")
                buffer += data
                if len(buffer) > 2_000_000:
                    raise RuntimeError("Provider response too large")
                continue
            line, buffer = buffer.split(b"\n", 1)
            reply = json.loads(line)
            if reply.get("id") == request_id:
                if "error" in reply:
                    raise RuntimeError("Provider request unavailable")
                return reply["result"]
        raise TimeoutError("Provider did not respond")

    try:
        request("initialize", {"clientInfo": {"name": "infinity_config", "version": "1.0"}})
        process.stdin.write(b'{"method":"initialized"}\n')
        process.stdin.flush()
        account = request("account/read", {"refreshToken": False}).get("account")
        result = {"account": account, "limits": {}, "usage": {}}
        if account and account.get("type") == "chatgpt":
            for key, method in (("limits", "account/rateLimits/read"), ("usage", "account/usage/read")):
                try:
                    result[key] = request(method)
                except RuntimeError:
                    pass  # Older CLIs may not support usage yet.
        return result
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stdin.close()
        process.stdout.close()


def provider_status(provider):
    binary = str(Path.home() / f".local/bin/{provider}")
    if provider == "codex":
        return codex_account(binary)
    if provider != "claude":
        raise ValueError("Unknown provider")
    result = subprocess.run([binary, "auth", "status"], capture_output=True, text=True, timeout=20)
    if result.returncode not in (0, 1):
        raise RuntimeError("Provider status unavailable")
    status = json.loads(result.stdout)
    if not isinstance(status.get("loggedIn"), bool):
        raise ValueError("Invalid provider status")
    return {"account": {"email": status.get("email"), "type": status.get("authMethod"),
                        "planType": status.get("subscriptionType")} if status["loggedIn"] else None}


def ollama(path, data=None, timeout=30):
    request = urllib.request.Request("http://127.0.0.1:11434/api/" + path,
                                     data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Content-Type": "application/json"})
    # Local requests must never travel through a configured HTTP proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=timeout) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError("Ollama request failed")
    return result


def valid_model(name):
    return isinstance(name, str) and len(name) <= 200 and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", name)) and ".." not in name


def local_status(home=None):
    home = Path(home or Path.home())
    model = (home / '.config/infinityos/local-ai-model').read_text().strip()
    details = ollama('show', {'model': model})
    parameters = {}
    for line in details.get('parameters', '').splitlines():
        fields = line.split()
        if len(fields) == 2:
            parameters[fields[0]] = fields[1]
    return {'model': model, 'models': [m['name'] for m in ollama('tags')['models']],
            'context': int(parameters.get('num_ctx', 65536)),
            'output': max(1, int(parameters.get('num_predict', 8192))),
            'temperature': float(parameters.get('temperature', 0.8))}


def select_local(model, context, output, temperature, home=None):
    if not valid_model(model) or not 512 <= context <= 262144 or not 1 <= output <= context or not 0 <= temperature <= 2:
        raise ValueError('Invalid model settings')
    home = Path(home or Path.home())
    marker = home / '.config/infinityos/local-ai-model'
    previous = marker.read_text()  # Never enable AI that Setup has disabled.
    ollama('show', {'model': model})
    # Per-user alias avoids changing models used by other local accounts.
    alias = f'infinity-config-{os.getuid()}'
    ollama('create', {'model': alias, 'from': model, 'stream': False,
                     'parameters': {'num_ctx': context, 'num_predict': output, 'temperature': temperature}}, timeout=300)
    if not marker.exists() or marker.read_text() != previous:
        raise RuntimeError('AI selection changed in InfinitySetup')
    temporary = marker.with_suffix('.config-tmp')
    temporary.write_text(alias + '\n')
    temporary.replace(marker)


def import_model(filename):
    import shutil
    import tempfile
    import uuid
    path = Path(filename).resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != '.gguf' or any(c in str(path) for c in '\n\r"'):
        raise ValueError('Choose a GGUF model file')
    binary = shutil.which('ollama')
    if not binary:
        raise RuntimeError('Ollama is unavailable')
    name = 'infinity-import-' + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix='infinity-model-') as directory:
        modelfile = Path(directory) / 'Modelfile'
        modelfile.write_text(f'FROM "{path}"\n')
        subprocess.run([binary, 'create', name, '-f', str(modelfile)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3600)
    return name
