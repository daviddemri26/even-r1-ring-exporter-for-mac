"""Serveur MCP privé pour les durées de sommeil. Aucun accès réseau sortant."""
import argparse
import csv
import hmac
import io
import json
import os
import re
import sqlite3
import stat
import sys
import zipfile
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath

import collecte
import rapport_even
from rapport_even import date_range
from rapprochement_even import DataError, verified_stream


VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
TOOL = {
    "name": "durees_sommeil",
    "description": (
        "Durée totale de sommeil par date locale de réveil, en minutes, sur une plage "
        "inclusive de 1 à 31 dates. Le cumul comprend les sessions distinctes et les "
        "siestes. Une date absente signifie aucune session dans cet export. Une durée "
        "nulle (JSON null) signale des données ambiguës ou incohérentes."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {k: {"type": "string", "format": "date"} for k in ("debut", "fin")},
        "required": ["debut", "fin"],
        "additionalProperties": False,
    },
    "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
}
PHASE_TOOL = {
    **TOOL,
    "name": "phases_sommeil",
    "description": (
        "Minutes d’éveil pendant les sessions de sommeil, de sommeil paradoxal (REM), "
        "léger et profond par date locale de réveil. Plage inclusive de 1 à 31 dates. "
        "Le cumul comprend les siestes distinctes. Les copies identiques ne comptent "
        "qu’une fois. Les quatre valeurs sont null si les phases sont ambiguës ou "
        "incohérentes. Une date absente signifie aucune session dans cet export."
    ),
}
MAX_CSV_BYTES = 32 * 1024 * 1024
MAX_REQUEST_BYTES = 16 * 1024
DURATION_COLUMNS = ("total_time", "wake_time", "rem_time", "light_time", "deep_time")
PHASE_FIELDS = ("eveil_minutes", "paradoxal_minutes", "leger_minutes", "profond_minutes")


def stage_seconds(encoded):
    def unique_fields(pairs):
        result = dict(pairs)
        return result if len(result) == len(pairs) else None

    try:
        stages = json.loads(encoded or "", object_pairs_hook=unique_fields)
    except (ValueError, RecursionError):
        return None
    if not isinstance(stages, list) or not stages:
        return None
    # Codes Even : éveil, paradoxal, léger, profond. Une unité vaut 30 secondes.
    totals = [0, 0, 0, 0]
    for stage in stages:
        if not isinstance(stage, dict):
            return None
        kind = stage.get("type")
        units = stage.get("half_minutes")
        if type(kind) is not int or not 0 <= kind <= 3 or type(units) is not int or units < 0:
            return None
        totals[kind] += units * 30
    return tuple(totals)


def row_seconds(row, interval, detailed):
    values = [(row.get(k) or "").strip() for k in DURATION_COLUMNS]
    if any(not re.fullmatch(r"[0-9]{1,6}", v) for v in values):
        return None
    total, awake, rem, light, deep = map(int, values)
    if total != rem + light + deep or abs(interval - (total + awake)) > 60:
        return None
    if not detailed:
        return (total,)
    phases = (awake, rem, light, deep)
    return phases if stage_seconds(row.get("stages")) == phases else None


def read_sessions(stream, detailed):
    # Les datetimes avec décalage comparent des instants absolus. Conserver
    # séparément la date locale imprimée dans la ligne de chaque source.
    sessions = defaultdict(set)
    with zipfile.ZipFile(stream) as archive:
        members = [m for m in archive.infolist()
                   if PurePosixPath(m.filename).name.lower() == "sleep.csv"
                   and "__MACOSX" not in PurePosixPath(m.filename).parts]
        if len(members) != 1 or members[0].file_size > MAX_CSV_BYTES:
            raise DataError()
        with archive.open(members[0]) as raw, io.TextIOWrapper(
                raw, encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file, strict=True)
            required = {"start_ts", "end_ts", *DURATION_COLUMNS}
            if not required.issubset(reader.fieldnames or []):
                raise DataError()
            for n, row in enumerate(reader):
                if n >= 100_000:
                    raise DataError()
                start = collecte.timestamp(row["start_ts"])
                end = collecte.timestamp(row["end_ts"])
                interval = (end - start).total_seconds()
                if not 0 < interval <= 86400:
                    raise DataError()
                sessions[start, end].add((end.date(), row_seconds(row, interval, detailed)))
    return sessions


def daily_totals(sessions, first, last, fields):
    totals = defaultdict(lambda: [0] * len(fields))
    ambiguous = set()
    active_end = None
    active_days = set()
    for (start, end), observations in sorted(sessions.items()):
        days = {day for day, duration in observations}
        if active_end is None or start >= active_end:
            active_days = set()
            active_end = end
        else:
            # Toute la chaîne d'intervalles qui se chevauchent est ambiguë.
            ambiguous.update(active_days | days)
            active_end = max(active_end, end)
        active_days.update(days)

        if len(observations) == 1:
            day, seconds = next(iter(observations))
            if seconds is not None:
                for i, value in enumerate(seconds):
                    totals[day][i] += value
                continue
        ambiguous.update(days)
    result = []
    for day in sorted(totals.keys() | ambiguous):
        if first <= day <= last:
            record = {"date_reveil": day.isoformat()}
            for i, field in enumerate(fields):
                record[field] = None if day in ambiguous else round(totals[day][i] / 60, 2)
            result.append(record)
    return result


def summary(base, first, last, detailed=False):
    with verified_stream(base) as stream:
        fields = PHASE_FIELDS if detailed else ("duree_minutes",)
        return daily_totals(read_sessions(stream, detailed), first, last, fields)


def rpc(request, base):
    def error(code, message):
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}

    ident = None
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        return error(-32600, "Requête JSON-RPC invalide.")
    method = request.get("method")
    if not isinstance(method, str):
        return error(-32600, "Méthode invalide.")
    if "id" not in request:
        return None  # Notification, sans réponse JSON-RPC.
    if type(request["id"]) not in (int, str):
        return error(-32600, "Identifiant invalide.")
    ident = request["id"]
    params = request.get("params", {})
    if not isinstance(params, dict):
        return error(-32602, "Paramètres invalides.")
    if method == "initialize":
        version = params.get("protocolVersion")
        result = {"protocolVersion": version if version in VERSIONS else VERSIONS[0],
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "r1-bridge", "version": "0.1.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [TOOL, PHASE_TOOL, rapport_even.CARD_TOOL, rapport_even.HISTORY_TOOL]}
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments")
        try:
            if name == rapport_even.HISTORY_TOOL["name"]:
                try:
                    if not isinstance(arguments, dict):
                        raise ValueError()
                    dates = arguments.copy()
                    requested = rapport_even.categories({"categories": dates.pop("categories", None)})
                    first, last = date_range(dates)
                except ValueError:
                    return error(-32602, "Choisir une à six catégories et une période de 1 à 31 dates.")
                data = rapport_even.evolution(base, requested, first, last)
            elif name == rapport_even.CARD_TOOL["name"]:
                try:
                    requested = rapport_even.categories(arguments)
                except ValueError:
                    return error(-32602, "Choisir une à six catégories distinctes.")
                data = rapport_even.last_cards(base, requested)
            elif name in (TOOL["name"], PHASE_TOOL["name"]):
                try:
                    first, last = date_range(arguments)
                except ValueError:
                    return error(-32602, "Deux dates ISO sont requises, sur 1 à 31 jours inclus.")
                data = summary(base, first, last, detailed=name == PHASE_TOOL["name"])
            else:
                return error(-32602, "Outil inconnu.")
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]}
        except rapport_even.SnapshotError:
            result = {"isError": True, "content": [{"type": "text", "text":
                      "Aucune capture locale validée des cartes Even disponible."}]}
        except rapport_even.HistoryError:
            result = {"isError": True, "content": [{"type": "text", "text":
                      "Historique local des cartes indisponible."}]}
        except (DataError, OSError, ValueError, sqlite3.Error, RuntimeError,
                csv.Error, zipfile.BadZipFile, EOFError):
            result = {"isError": True, "content": [{"type": "text", "text":
                      "Aucune archive validée lisible pour cette requête."}]}
    else:
        return error(-32601, "Méthode inconnue.")
    return {"jsonrpc": "2.0", "id": ident, "result": result}


class LocalHandler(BaseHTTPRequestHandler):
    timeout = 10

    def log_message(self, *args):
        pass  # Ne jamais journaliser de requête ni de réponse de santé.

    def reply(self, status, data=None, extra=()):
        body = b"" if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        if body:
            self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra:
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def allowed(self):
        port = self.server.server_port
        allowed_hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port}
        hosts = self.headers.get_all("Host", [])
        origins = self.headers.get_all("Origin", [])
        if len(hosts) != 1 or hosts[0] not in allowed_hosts:
            self.reply(403)
        elif origins and (len(origins) != 1 or origins[0] not in
                          {"http://" + host for host in allowed_hosts}):
            self.reply(403)
        elif self.path != "/mcp":
            self.reply(404)
        else:
            auth = self.headers.get_all("Authorization", [])
            if len(auth) == 1 and hmac.compare_digest(auth[0].encode(), self.server.auth):
                return True
            self.reply(401, extra=(("WWW-Authenticate", "Bearer"),))
        return False

    def do_GET(self):
        if self.allowed():
            self.reply(405, extra=(("Allow", "POST"),))

    do_DELETE = do_GET

    def do_POST(self):
        if not self.allowed():
            return
        if self.headers.get_content_type() != "application/json":
            self.reply(415)
            return
        versions = self.headers.get_all("MCP-Protocol-Version", [])
        if versions and (len(versions) != 1 or versions[0] not in VERSIONS):
            self.reply(400)
            return
        lengths = self.headers.get_all("Content-Length", [])
        if (self.headers.get("Transfer-Encoding") is not None or len(lengths) != 1
                or not re.fullmatch(r"[0-9]{1,8}", lengths[0])):
            self.reply(400)
            return
        length = int(lengths[0])
        if length > MAX_REQUEST_BYTES:
            self.reply(413)
            return
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, RecursionError):
            self.reply(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700, "message": "JSON illisible."}})
            return
        response = rpc(request, self.server.base)
        self.reply(202 if response is None else 200, response)


def private_token(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Le fichier de jeton doit être privé et appartenir à cet utilisateur.")
        raw = stream.read(258).rstrip(b"\n")
        if info.st_size > 257 or not re.fullmatch(rb"[A-Za-z0-9_-]{32,256}", raw):
            raise ValueError("Le fichier doit contenir un jeton aléatoire URL-safe de 32 à 256 caractères.")
        return b"Bearer " + raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8741)
    transport = parser.add_mutually_exclusive_group(required=True)
    transport.add_argument("--jeton", type=Path, help="Fichier privé du jeton pour le serveur HTTP.")
    transport.add_argument("--stdio", action="store_true",
                           help="Pour un client MCP local ou Secure MCP Tunnel, sans port d’écoute.")
    args = parser.parse_args()
    try:
        if args.stdio:
            # Le processus est enfant du client local autorisé. stdout est réservé au protocole.
            while True:
                line = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
                if not line:
                    return
                if len(line) > MAX_REQUEST_BYTES:
                    raise ValueError("Requête trop longue.")
                response = rpc(json.loads(line.decode("utf-8")), collecte.BASE)
                if response is not None:
                    print(json.dumps(response, ensure_ascii=True), flush=True)
        auth = private_token(args.jeton)
        with ThreadingHTTPServer(("127.0.0.1", args.port), LocalHandler) as server:
            server.base = collecte.BASE
            server.auth = auth
            server.serve_forever()
    except (OSError, ValueError) as exc:
        parser.exit(1, "Démarrage impossible (%s).\n" % type(exc).__name__)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
