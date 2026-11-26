"""Démarrage local du tunnel privé Even R1 pour la session macOS de l’utilisateur."""
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
RUNNER = BASE / "tunnel_r1.py"
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
exec /usr/bin/python3 -B "$HOME/Library/Application Support/R1 Bridge/tunnel_r1.py" enregistrer-trousseau
"""


class SetupError(Exception):
    pass


def clean_env():
    return {"HOME": str(Path.home()), "PATH": SYSTEM_PATH}


def read_key(file):
    # Pas de shell ni d'interpolation. Ne décoder que la valeur demandée.
    assignment = re.compile(rb"^[ \t]*(?:export[ \t]+)?OPENAI_API_KEY[ \t]*=[ \t]*(.*)$")
    key = None
    fd = os.open(file, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise SetupError("Le chemin .env doit désigner un fichier ordinaire.")
        for line in stream:
            match = assignment.match(line.rstrip(b"\r\n").removeprefix(b"\xef\xbb\xbf"))
            if not match:
                continue
            raw = match[1].strip()
            # Les guillemets extérieurs du .env sont facultatifs. Une valeur citée
            # doit tenir sur une ligne. Les commentaires après la valeur sont ignorés.
            if raw[:1] in (b"'", b'"'):
                quote = raw[:1]
                close = raw.find(quote, 1)
                if close == -1 or not re.fullmatch(rb"(?:[ \t]*#.*)?", raw[close+1:]):
                    raise SetupError("La valeur OPENAI_API_KEY citée est illisible.")
                raw = raw[1:close]
            else:
                raw = re.split(rb"[ \t]+#", raw, maxsplit=1)[0].strip()
            if not re.fullmatch(rb"[!-~]+", raw) or raw.startswith((b"#", b"$")):
                raise SetupError("OPENAI_API_KEY doit contenir une valeur littérale.")
            key = raw.decode("ascii")
    if key is None:
        raise SetupError("OPENAI_API_KEY est absente du fichier indiqué.")
    return key


def default_keychain():
    default = subprocess.run(["/usr/bin/security", "default-keychain", "-d", "user"],
                             env=clean_env(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=10)
    keychain = os.fsdecode(default.stdout).strip().strip('"')
    if default.returncode or not os.path.isabs(keychain):
        raise SetupError("Trousseau utilisateur par défaut indisponible.")
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
        raise SetupError("Élément « R1 Bridge - OpenAI Tunnel » introuvable dans le trousseau.")
    if result.returncode:
        raise SetupError("Accès au trousseau indisponible. Vérifier le déverrouillage et l’autorisation Apple.")
    if read_password:
        raw = result.stdout.rstrip(b"\r\n")
        if not re.fullmatch(rb"[!-~]+", raw):
            raise SetupError("La clé conservée dans le trousseau est vide ou illisible.")
        return raw.decode("ascii")


def check_keychain():
    keychain_item()
    print("Élément du tunnel présent dans le trousseau utilisateur.")


def store_keychain_key(key, *, keychain=None):
    """Écrit et vérifie l’élément dédié via un tube privé, sans secret dans argv."""
    if not isinstance(key, str) or not re.fullmatch(r"[!-~]+", key):
        raise SetupError("La clé doit être une valeur ASCII sur une seule ligne.")
    path = keychain or default_keychain()
    account = pwd.getpwuid(os.getuid()).pw_name
    # Le parseur interactif d’Apple admet des mots entre guillemets doubles.
    # Restreindre les autres champs à des chaînes compatibles avec ce format.
    for field in (account, KEYCHAIN_SERVICE, path):
        if any(c in field for c in ('"', '\\', '\n', '\r', '\x00')):
            raise SetupError("Chemin de trousseau ou nom de compte non pris en charge.")
    raw = key.encode("ascii")
    # -X décrit les octets natifs à stocker. La ligne n’est jamais fournie à un shell.
    line = ('add-generic-password -U -a "'+account+'" -s "'+KEYCHAIN_SERVICE+
            '" -X '+raw.hex()+' "'+path+'"\n').encode("utf-8")
    if len(line) >= 4096:  # MAX_LINE_LEN du parseur de /usr/bin/security -i
        raise SetupError("La clé dépasse la taille acceptée par l’entrée privée d’Apple.")
    result = subprocess.run(["/usr/bin/security", "-q", "-i"], input=line,
                            env=clean_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=120)
    if result.returncode:
        raise SetupError("Apple n’a pas enregistré l’élément de trousseau du tunnel.")
    saved = keychain_item(read_password=True, keychain=path)
    if not hmac.compare_digest(saved, key):
        raise SetupError("La relecture du trousseau diffère de la clé saisie.")


def configured_tunnel():
    """Read the one literal tunnel ID from the profile emitted by the official client."""
    try:
        yaml = PROFILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SetupError("Préparer le tunnel du compte OpenAI au préalable.")
    ids = re.findall(r'^  tunnel_id: "(' + TUNNEL_ID_PATTERN + r')"\s*$', yaml, re.MULTILINE)
    if len(ids) != 1:
        raise SetupError("Profil de tunnel illisible. Préparer à nouveau le tunnel.")
    return ids[0]


def validate_runtime_key(key):
    """Valide uniquement l’accès au tunnel, sans appel MCP ni donnée R1."""
    conn = http.client.HTTPSConnection("api.openai.com", timeout=12)
    try:
        conn.request("GET", "/v1/tunnels/" + configured_tunnel(),
                     headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
        code = conn.getresponse().status
    finally:
        conn.close()
    if code == 401:
        raise SetupError("OpenAI refuse cette clé (HTTP 401). L’élément du trousseau est conservé.")
    if code == 403:
        raise SetupError("OpenAI refuse l’accès à ce tunnel (HTTP 403). Vérifier Tunnels Read + Use.")
    if code != 200:
        raise SetupError("Vérification du tunnel indisponible (HTTP %d)." % code)


def enroll_keychain():
    print("Even R1 — connexion privée à OpenAI", flush=True)
    print("Collez la clé entière puis appuyez sur Entrée. La saisie reste masquée.", flush=True)
    print("Après validation par OpenAI, elle remplacera la clé dédiée dans le trousseau.", flush=True)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("Clé OpenAI : ")
    except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
        raise SetupError("Saisie masquée annulée ou terminal indisponible.")
    if not re.fullmatch(r"sk-[!-~]+", key):
        raise SetupError("La clé saisie ne correspond pas au format OpenAI.")
    validate_runtime_key(key)
    store_keychain_key(key)
    del key
    activate()
    for _ in range(45):
        if READY.is_file() and PID.is_file() and probe() == 0:
            print("Tunnel prêt. Premier échange avec OpenAI vérifié.")
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
        raise SetupError("L’identifiant du tunnel doit être celui affiché dans OpenAI Platform.")
    client = client.expanduser().resolve()
    if not client.is_file() or not os.access(client, os.X_OK):
        raise SetupError("Sélectionner le binaire tunnel-client exécutable extrait de la distribution OpenAI.")
    server = BASE / "serveur_sommeil.py"
    if not server.is_file() or not RUNNER.is_file():
        raise SetupError("Installer le moteur depuis R1 Bridge avant de préparer le tunnel.")
    TUNNEL.mkdir(parents=True, mode=0o700, exist_ok=True)
    TUNNEL.chmod(0o700)
    TOOL.parent.mkdir(mode=0o700, exist_ok=True)
    if launch("print", SERVICE) == 0 and configured_tunnel() != tunnel_id:
        raise SetupError("Arrêter le tunnel actif avant de choisir un autre identifiant.")
    # Le serveur ne reçoit pas la clé d'exécution du tunnel dans son environnement.
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
    put(TUNNEL / "Enregistrer la clé.command", KEYCHAIN_ENTRY.encode("utf-8"), mode=0o700)
    print("Profil officiel préparé.")


def run(file=None):
    env = clean_env()
    env["CONTROL_PLANE_API_KEY"] = read_key(file) if file is not None else keychain_item(read_password=True)
    os.execve(TOOL, [str(TOOL), "run", "--profile-file", str(PROFILE),
                     "--health.url-file", str(READY), "--pid.file", str(PID)], env)


def launch(*args):
    return subprocess.run(["/bin/launchctl", *args], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=15).returncode


def agent_config(file=None):
    args = ["executer-trousseau"] if file is None else ["executer", str(file)]
    return plistlib.dumps({
        "Label": LABEL, "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 60,
        "LimitLoadToSessionType": "Aqua", "Umask": 0o077, "WorkingDirectory": str(TUNNEL),
        "ProgramArguments": ["/usr/bin/python3", "-B", str(RUNNER), *args],
        "StandardOutPath": "/dev/null", "StandardErrorPath": "/dev/null",
    })


def activate(file=None):
    if not PROFILE.is_file() or not RUNNER.is_file():
        raise SetupError("Préparer le profil du tunnel au préalable.")
    if file is None:
        keychain_item()  # Vérifier l’existence sans demander la valeur au Trousseau.
    else:
        read_key(file)
    config = agent_config(file)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    loaded = launch("print", SERVICE) == 0
    same = PLIST.is_file() and PLIST.read_bytes() == config
    if loaded and same:
        # Relire la clé en mémoire sans supprimer la définition launchd.
        if launch("kickstart", "-k", SERVICE):
            raise SetupError("Impossible de redémarrer le LaunchAgent du tunnel.")
    else:
        if loaded and launch("bootout", SERVICE):
            raise SetupError("Impossible de remplacer le LaunchAgent du tunnel.")
        if not same:
            put(PLIST, config)
        if launch("enable", SERVICE):
            raise SetupError("Impossible d’activer le LaunchAgent dans cette session.")
        # Le bootout peut finir avant que le nom soit libéré par launchd.
        for attempt in range(12):
            if launch("bootstrap", DOMAIN, str(PLIST)) == 0:
                break
            if attempt < 11:
                time.sleep(0.5)
        else:
            raise SetupError("Chargement du tunnel impossible dans cette session.")
    if launch("print", SERVICE):
        raise SetupError("Activation du tunnel impossible dans cette session.")
    print("LaunchAgent du tunnel activé. La commande etat vérifie le premier échange avec OpenAI.")


def status():
    if launch("print", SERVICE):
        print("LaunchAgent du tunnel inactif.")
        return 1
    if not READY.is_file() or not PID.is_file():
        print("LaunchAgent chargé, connexion en attente.")
        return 1
    code = probe()
    if code == 0:
        print("Tunnel prêt, échange avec OpenAI vérifié.")
    else:
        reason = poll_refusal()
        print(reason or "LaunchAgent chargé, connexion à OpenAI à vérifier.")
    return code


def probe():
    return subprocess.run([str(TOOL), "health", "--url-file", str(READY),
                           "--pid-file", str(PID), "--require-control-plane-poll"],
                          env=clean_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          timeout=10).returncode


def poll_refusal():
    """Distinguer les refus HTTP à partir des seuls compteurs du client local."""
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
        return "OpenAI refuse l’authentification du tunnel (HTTP 401)."
    if codes == {"403"}:
        return "OpenAI refuse les droits de la clé pour ce tunnel (HTTP 403)."
    return None


def stop():
    if launch("print", SERVICE) == 0 and launch("bootout", SERVICE):
        raise SetupError("Impossible d’arrêter le LaunchAgent du tunnel.")
    PLIST.unlink(missing_ok=True)
    print("Tunnel arrêté.")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="action", required=True)
    configure = cmds.add_parser("preparer", help="Configurer le tunnel personnel avec le client officiel OpenAI.")
    configure.add_argument("tunnel_id")
    configure.add_argument("--client", required=True, type=Path)
    for action in ("etat", "arreter", "verifier-trousseau", "activer-trousseau", "executer-trousseau", "enregistrer-trousseau"):
        cmds.add_parser(action)
    for action in ("activer", "executer"):
        cmds.add_parser(action).add_argument("dotenv", type=Path)
    args = parser.parse_args()
    if args.action == "preparer":
        return prepare(args.tunnel_id, args.client)
    if args.action in ("activer", "executer"):
        file = args.dotenv.expanduser().absolute()
        return (activate if args.action == "activer" else run)(file)
    return {"etat": status, "arreter": stop,
            "verifier-trousseau": check_keychain, "activer-trousseau": activate,
            "executer-trousseau": run, "enregistrer-trousseau": enroll_keychain}[args.action]()


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except SetupError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    except (OSError, subprocess.SubprocessError) as error:
        print("Échec local (%s)." % type(error).__name__, file=sys.stderr)
        sys.exit(1)
