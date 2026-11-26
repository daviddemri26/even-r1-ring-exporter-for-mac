"""Read the requested date range from the latest verified local export."""
import argparse
import json
import sys

from collection import BASE
from mcp_server import rpc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start", help="First local wake date (YYYY-MM-DD)")
    parser.add_argument("end", help="Last local wake date, inclusive")
    parser.add_argument("--stages", action="store_true", help="Minutes by sleep stage")
    args = parser.parse_args()
    request = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {
            "name": "sleep_stages" if args.stages else "sleep_durations",
            "arguments": {"start": args.start, "end": args.end},
        },
    }
    response = rpc(request, BASE)
    result = response.get("result", {})
    if "error" in response or result.get("isError"):
        print("Check the dates (up to 31 days) and the last export with r1.py status.",
              file=sys.stderr)
        return 1
    print(result["content"][0]["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
