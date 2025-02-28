import os
import argparse
import tempfile
import subprocess
import json
import importlib
import requests
import shutil
import tarfile


FRP_URL = "https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux_amd64.tar.gz"

def parse_args():
    parser = argparse.ArgumentParser(description="Tunnel command parser")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tunnel_parser = subparsers.add_parser("tunnel", help="Create a tunnel")
    tunnel_parser.add_argument("--port", type=int, required=True, help="Port number for the tunnel")
    tunnel_parser.add_argument("--name", type=str, required=True, help="Name of the tunnel/subdomain")

    tunnel_parser.add_argument("--server", type=str, help="Server address", default=os.environ.get("FLARE_SERVER", "localhost"))

    return parser.parse_args()

def download_and_extract_frpc(url: str, output_path: str = "/tmp/frpc"):
    temp_tar_path = "/tmp/frp.tar.gz"
    extract_path = "/tmp/frp_extracted"
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(temp_tar_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        
        with tarfile.open(temp_tar_path, "r:gz") as tar:
            tar.extractall(extract_path)
        
        for root, _, files in os.walk(extract_path):
            if "frpc" in files:
                frpc_path = os.path.join(root, "frpc")
                shutil.move(frpc_path, output_path)
                os.chmod(output_path, 0o755)  # Make it executable
                break
        else:
            raise FileNotFoundError("frpc file not found in the archive")
        
    finally:
        if os.path.exists(temp_tar_path):
            os.remove(temp_tar_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)

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

    frpc_path = "/tmp/frpc"
    if not os.path.exists(frpc_path):
        download_and_extract_frpc(FRP_URL, frpc_path)

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