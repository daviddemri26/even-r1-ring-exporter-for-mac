"""Manage the user's private Even R1 tunnel in the current macOS session."""
import argparse
import getpass
import hmac
import http.client
import os
import plistlib
import pwd
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import warnings
from urllib.parse import urlsplit
from pathlib import Path

BASE = Path.home() / "Library/Application Support/R1 Bridge"
TOOL = BASE / "bin/tunnel-client"
RUNNER = BASE / "tunnel.py"
TUNNEL = BASE / "tunnel"
PROFILE = TUNNEL / "even-r1.yaml"
READY = TUNNEL / "health.url"
PID = TUNNEL / "client.pid"
LABEL = "local.r1bridge.tunnel"
DOMAIN = "gui/" + str(os.getuid())
SERVICE = DOMAIN + "/" + LABEL
PLIST = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
TUNNEL_ID_PATTERN = r"tunnel_[A-Za-z0-9_-]{1,128}"
KEYCHAIN_SERVICE = "R1 Bridge - OpenAI Tunnel"
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
KEYCHAIN_ENTRY = """#!/bin/zsh
exec /usr/bin/python3 -B "$HOME/Library/Application Support/R1 Bridge/tunnel.py" store-key
"""


class SetupError(Exception):
    pass


def clean_env():
    return {"HOME": str(Path.home()), "PATH": SYSTEM_PATH}


def read_key(file):
    # Parse only the requested literal value without invoking a shell.
    assignment = re.compile(rb"^[ \t]*(?:export[ \t]+)?OPENAI_API_KEY[ \t]*=[ \t]*(.*)$")
    key = None
    fd = os.open(file, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise SetupError("The .env path must point to a regular file.")
        for line in stream:
            match = assignment.match(line.rstrip(b"\r\n").removeprefix(b"\xef\xbb\xbf"))
            if not match:
                continue
            raw = match[1].strip()
            # Optional quotes must close on the same line. Ignore comments
            # that follow the value.
            if raw[:1] in (b"'", b'"'):
                quote = raw[:1]
                close = raw.find(quote, 1)
                if close == -1 or not re.fullmatch(rb"(?:[ \t]*#.*)?", raw[close+1:]):
                    raise SetupError("Invalid quoted OPENAI_API_KEY value.")
                raw = raw[1:close]
            else:
                raw = re.split(rb"[ \t]+#", raw, maxsplit=1)[0].strip()
            if not re.fullmatch(rb"[!-~]+", raw) or raw.startswith((b"#", b"$")):
                raise SetupError("OPENAI_API_KEY must contain a literal value.")
            key = raw.decode("ascii")
    if key is None:
        raise SetupError("The specified file does not contain OPENAI_API_KEY.")
    return key


def default_keychain():
    default = subprocess.run(["/usr/bin/security", "default-keychain", "-d", "user"],
                             env=clean_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=10)
    keychain = os.fsdecode(default.stdout).strip().strip('"')
    if default.returncode or not os.path.isabs(keychain):
        raise SetupError("The default user Keychain is unavailable.")
    return keychain


def keychain_item(read_password=False, *, keychain=None):
    account = pwd.getpwuid(os.getuid()).pw_name
    keychain = keychain or default_keychain()
    cmd = ["/usr/bin/security", "find-generic-password", "-a", account, "-s", KEYCHAIN_SERVICE]
    if read_password:
        cmd.append("-w")
    cmd.append(keychain)
    result = subprocess.run(cmd, env=clean_env(), stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE if read_password else subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=60)
    if result.returncode == 44:  # errSecItemNotFound
        raise SetupError("Could not find the R1 Bridge - OpenAI Tunnel item in Keychain.")
    if result.returncode:
        raise SetupError("Could not access Keychain. Check that it is unlocked and that access is allowed.")
    if read_password:
        raw = result.stdout.rstrip(b"\r\n")
        if not re.fullmatch(rb"[!-~]+", raw):
            raise SetupError("The stored Keychain value is empty or unreadable.")
        return raw.decode("ascii")


def check_keychain():
    keychain_item()
    print("The tunnel key is present in the user Keychain.")


def store_keychain_key(key, *, keychain=None):
    """Write and verify the dedicated Keychain item through a private pipe."""
    if not isinstance(key, str) or not re.fullmatch(r"[!-~]+", key):
        raise SetupError("The key must be a single line of ASCII text.")
    path = keychain or default_keychain()
    account = pwd.getpwuid(os.getuid()).pw_name
    # The security tool accepts double-quoted words in interactive mode.
    # Restrict the remaining fields to literals that format can represent.
    for field in (account, KEYCHAIN_SERVICE, path):
        if any(c in field for c in ('"', '\\', '\n', '\r', '\x00')):
            raise SetupError("The Keychain path or account name contains unsupported characters.")
    raw = key.encode("ascii")
    # The -X argument encodes the raw bytes as hex. No shell receives the command.
    line = ('add-generic-password -U -a "'+account+'" -s "'+KEYCHAIN_SERVICE+
            '" -X '+raw.hex()+' "'+path+'"\n').encode("utf-8")
    if len(line) >= 4096:  # MAX_LINE_LEN in /usr/bin/security -i
        raise SetupError("The key exceeds the size accepted by the Keychain input.")
    result = subprocess.run(["/usr/bin/security", "-q", "-i"], input=line,
                            env=clean_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=120)
    if result.returncode:
        raise SetupError("Keychain could not store the tunnel key.")
    saved = keychain_item(read_password=True, keychain=path)
    if not hmac.compare_digest(saved, key):
        raise SetupError("The stored Keychain value did not match the supplied key.")


def configured_tunnel():
    """Read the one literal tunnel ID from the profile emitted by the official client."""
    try:
        yaml = PROFILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SetupError("Prepare your OpenAI tunnel first.")
    ids = re.findall(r'^  tunnel_id: "(' + TUNNEL_ID_PATTERN + r')"\s*$', yaml, re.MULTILINE)
    if len(ids) != 1:
        raise SetupError("Could not read the tunnel profile. Prepare the tunnel again.")
    return ids[0]


def validate_runtime_key(key):
    """Check access to the tunnel without making an MCP call or sending ring data."""
    conn = http.client.HTTPSConnection("api.openai.com", timeout=12)
    try:
        conn.request("GET", "/v1/tunnels/" + configured_tunnel(),
                     headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
        code = conn.getresponse().status
    finally:
        conn.close()
    if code == 401:
        raise SetupError("OpenAI rejected this key (HTTP 401). The existing Keychain item was retained.")
    if code == 403:
        raise SetupError("OpenAI denied access to this tunnel (HTTP 403). Check the Tunnels Read and Use permissions.")
    if code != 200:
        raise SetupError("Tunnel verification failed (HTTP %d)." % code)


def enroll_keychain():
    print("Even R1 private connection to OpenAI", flush=True)
    print("Paste the complete key and press Return. Input is hidden.", flush=True)
    print("Once OpenAI verifies the key, it will replace the dedicated Keychain item.", flush=True)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("OpenAI key: ")
    except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        raise SetupError("Secure input was canceled or the terminal is unavailable.")
    if not re.fullmatch(r"sk-[!-~]+", key):
        raise SetupError("The key does not match the OpenAI key format.")
    validate_runtime_key(key)
    store_keychain_key(key)
    del key
    activate()
    for _ in range(45):
        if READY.is_file() and PID.is_file() and probe() == 0:
            print("Tunnel ready. The first exchange with OpenAI was verified.")
            return
        time.sleep(2)
    return status()


def put(path, data, mode=0o600):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(data)
            os.fchmod(f.fileno(), mode)
            f.flush()
            os.fsync(f.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def prepare(tunnel_id, client):
    if not re.fullmatch(TUNNEL_ID_PATTERN, tunnel_id):
        raise SetupError("Enter the tunnel ID shown on OpenAI Platform.")
    client = client.expanduser().resolve()
    if not client.is_file() or not os.access(client, os.X_OK):
        raise SetupError("Select the executable tunnel-client binary from the OpenAI release.")
    server = BASE / "mcp_server.py"
    if not server.is_file() or not RUNNER.is_file():
        raise SetupError("Install the runtime from R1 Bridge before configuring the tunnel.")
    TUNNEL.mkdir(parents=True, mode=0o700, exist_ok=True)
    TUNNEL.chmod(0o700)
    TOOL.parent.mkdir(mode=0o700, exist_ok=True)
    if launch("print", SERVICE) == 0 and configured_tunnel() != tunnel_id:
        raise SetupError("Stop the active tunnel before selecting another tunnel ID.")
    # Start the MCP server with an empty environment so it cannot inherit the tunnel key.
    cmd = shlex.join(["/usr/bin/env", "-i", "PATH=/usr/bin:/bin", "/usr/bin/python3",
                      "-B", str(server), "--stdio"])
    with tempfile.TemporaryDirectory(dir=TUNNEL) as stage:
        staged_client = Path(stage) / "tunnel-client"
        shutil.copy2(client, staged_client)
        staged_client.chmod(0o700)
        subprocess.run([str(staged_client), "init", "--sample", "sample_mcp_stdio_local",
                        "--profile", "even-r1", "--profile-dir", stage,
                        "--tunnel-id", tunnel_id, "--mcp-command", cmd,
                        "--health-listen-addr", "127.0.0.1:0"],
                       env=clean_env(), check=True, stdout=subprocess.DEVNULL, timeout=30)
        os.replace(staged_client, TOOL)
        put(PROFILE, (Path(stage) / PROFILE.name).read_bytes())
    put(TUNNEL / "Store Key.command", KEYCHAIN_ENTRY.encode("utf-8"), mode=0o700)
    print("The OpenAI tunnel profile is ready.")


def run(file=None):
    env = clean_env()
    env["CONTROL_PLANE_API_KEY"] = read_key(file) if file is not None else keychain_item(read_password=True)
    os.execve(TOOL, [str(TOOL), "run", "--profile-file", str(PROFILE),
                     "--health.url-file", str(READY), "--pid.file", str(PID)], env)


def launch(*args):
    return subprocess.run(["/bin/launchctl", *args], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=15).returncode


def agent_config(file=None):
    args = ["run-keychain"] if file is None else ["run", str(file)]
    return plistlib.dumps({
        "Label": LABEL, "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 60,
        "LimitLoadToSessionType": "Aqua", "Umask": 0o077, "WorkingDirectory": str(TUNNEL),
        "ProgramArguments": ["/usr/bin/python3", "-B", str(RUNNER), *args],
        "StandardOutPath": "/dev/null", "StandardErrorPath": "/dev/null",
    })


def activate(file=None):
    if not PROFILE.is_file() or not RUNNER.is_file():
        raise SetupError("Prepare the tunnel profile first.")
    if file is None:
        keychain_item()  # Check for the item without reading its secret.
    else:
        read_key(file)
    config = agent_config(file)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    loaded = launch("print", SERVICE) == 0
    same = PLIST.is_file() and PLIST.read_bytes() == config
    if loaded and same:
        # Reload the key while keeping the existing launchd definition.
        if launch("kickstart", "-k", SERVICE):
            raise SetupError("Could not restart the tunnel LaunchAgent.")
    else:
        if loaded and launch("bootout", SERVICE):
            raise SetupError("Could not replace the tunnel LaunchAgent.")
        if not same:
            put(PLIST, config)
        if launch("enable", SERVICE):
            raise SetupError("Could not enable the LaunchAgent in this session.")
        # bootout may return before launchd releases the service name.
        for attempt in range(12):
            if launch("bootstrap", DOMAIN, str(PLIST)) == 0:
                break
            if attempt < 11:
                time.sleep(0.5)
        else:
            raise SetupError("Could not load the tunnel in this session.")
    if launch("print", SERVICE):
        raise SetupError("Could not activate the tunnel in this session.")
    print("Tunnel LaunchAgent enabled. Run status to check the first exchange with OpenAI.")


def status():
    if launch("print", SERVICE):
        print("The tunnel LaunchAgent is inactive.")
        return 1
    if not READY.is_file() or not PID.is_file():
        print("The LaunchAgent is loaded and waiting for the connection.")
        return 1
    code = probe()
    if code == 0:
        print("Tunnel ready. The connection to OpenAI was verified.")
    else:
        reason = poll_refusal()
        print(reason or "The LaunchAgent is loaded. Check the connection to OpenAI.")
    return code


def probe():
    return subprocess.run([str(TOOL), "health", "--url-file", str(READY),
                           "--pid-file", str(PID), "--require-control-plane-poll"],
                          env=clean_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          timeout=10).returncode


def poll_refusal():
    """Identify HTTP authorization errors using local client counters."""
    try:
        url = urlsplit(READY.read_text().strip())
        if url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port:
            return None
        conn = http.client.HTTPConnection("127.0.0.1", url.port, timeout=2)
        try:
            conn.request("GET", "/metrics")
            response = conn.getresponse()
            if response.status != 200:
                return None
            metrics = response.read(1024 * 1024).decode("utf-8")
        finally:
            conn.close()
    except (OSError, ValueError, http.client.HTTPException):
        return None
    route = 'http_route="/v1/tunnels/' + configured_tunnel() + '/poll"'
    codes = set()
    for line in metrics.splitlines():
        if line.startswith("http_client_request_duration_seconds_count{") and route in line:
            match = re.search(r'http_response_status_code="([0-9]{3})"', line)
            if match:
                codes.add(match[1])
    if codes == {"401"}:
        return "OpenAI rejected the tunnel credentials (HTTP 401)."
    if codes == {"403"}:
        return "OpenAI denied this key access to the tunnel (HTTP 403)."
    return None


def stop():
    if launch("print", SERVICE) == 0 and launch("bootout", SERVICE):
        raise SetupError("Could not stop the tunnel LaunchAgent.")
    PLIST.unlink(missing_ok=True)
    print("Tunnel stopped.")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="action", required=True)
    configure = cmds.add_parser("prepare", help="Configure your tunnel with the official OpenAI client.")
    configure.add_argument("tunnel_id")
    configure.add_argument("--client", required=True, type=Path)
    for action in ("status", "stop", "check-keychain", "activate-keychain", "run-keychain", "store-key"):
        cmds.add_parser(action)
    for action in ("activate", "run"):
        cmds.add_parser(action).add_argument("dotenv", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        return prepare(args.tunnel_id, args.client)
    if args.action in ("activate", "run"):
        file = args.dotenv.expanduser().absolute()
        return (activate if args.action == "activate" else run)(file)
    return {"status": status, "stop": stop,
            "check-keychain": check_keychain, "activate-keychain": activate,
            "run-keychain": run, "store-key": enroll_keychain}[args.action]()


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except SetupError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    except (OSError, subprocess.SubprocessError) as error:
        print("Local operation failed (%s)." % type(error).__name__, file=sys.stderr)
        sys.exit(1)
