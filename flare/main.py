import importlib.resources
import os
import sys
import argparse
import tempfile
import subprocess
import urllib.request
import json
import importlib


def parse_args():
    parser = argparse.ArgumentParser(description="Tunnel command parser")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tunnel_parser = subparsers.add_parser("tunnel", help="Create a tunnel")
    tunnel_parser.add_argument("--port", type=int, required=True, help="Port number for the tunnel")
    tunnel_parser.add_argument("--name", type=str, required=True, help="Name of the tunnel/subdomain")

    tunnel_parser.add_argument("--server", type=str, help="Server address", default=os.environ.get("FLARE_SERVER", "localhost"))

    return parser.parse_args()


def create_tunnel(server, port, name):
    print(f"Creating tunnel on port {port} with name {name}")

    config = {
        "serverAddr": server,
        "serverPort": 7000,
        "proxies": [
            {
                "name": name,
                "type": "http",
                "localPort": port,
                "subdomain": name
            }
        ]
    }

    with open(f"{tempfile.mktemp()}.json", "w") as f:
        f.write(json.dumps(config))

    print("Config: ", f.name)

    frpc_path = importlib.resources.files("data") / "frpc"


    proc = subprocess.run([frpc_path, "-c", f.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for line in proc.stdout.decode().split("\n"):
        print(line)

    if proc.returncode != 0:
        print("frpc failed")

def main():
    args = parse_args()

    if args.command == "tunnel":
        create_tunnel(args.server, args.port, args.name)

if __name__ == '__main__':
    main()