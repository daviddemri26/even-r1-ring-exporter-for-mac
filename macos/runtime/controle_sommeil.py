"""Lire la période demandée dans le dernier export local validé."""
import argparse
import json
import sys

from collecte import BASE
from serveur_sommeil import rpc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("debut", help="Première date locale de réveil (AAAA-MM-JJ)")
    parser.add_argument("fin", help="Dernière date locale de réveil incluse")
    parser.add_argument("--phases", action="store_true", help="Minutes par stade")
    args = parser.parse_args()
    request = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "phases_sommeil" if args.phases else "durees_sommeil",
            "arguments": {"debut": args.debut, "fin": args.fin},
        },
    }
    response = rpc(request, BASE)
    result = response.get("result", {})
    if "error" in response or result.get("isError"):
        print("Vérifier les dates (31 jours maximum) et le dernier export avec r1.py etat.",
              file=sys.stderr)
        return 1
    print(result["content"][0]["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
