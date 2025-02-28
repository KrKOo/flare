import os
import argparse
import tempfile
import subprocess
import json
import requests
import shutil
import tarfile
import signal

# ENV variables:
# FLARE_SERVER: The frp server address
# FLARE_SERVER_PORT: The frp server port
# FLARE_PUBLIC_URL: The public url to access the services

FRP_URL = "https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux_amd64.tar.gz"

def parse_args():
    parser = argparse.ArgumentParser(description="Tunnel command parser")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tunnel_parser = subparsers.add_parser("tunnel", help="Create a tunnel")
    tunnel_parser.add_argument("--port", type=int, required=True, help="Port number for the tunnel")
    tunnel_parser.add_argument("--name", type=str, required=True, help="Name of the tunnel/subdomain")

    tunnel_parser.add_argument("--server", type=str, help="Server address", default=os.environ.get("FLARE_SERVER", "localhost"))
    tunnel_parser.add_argument("--server-port", type=int, help="Server port", default=os.environ.get("FLARE_SERVER_PORT", 7000))


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

def create_tunnel(server, server_port, local_port, name):
    config = {
        "serverAddr": server,
        "serverPort": server_port,
        "proxies": [
            {
                "name": name,
                "type": "http",
                "localPort": local_port,
                "subdomain": name
            }
        ]
    }

    with open(f"{tempfile.mktemp()}.json", "w") as config_file:
        config_file.write(json.dumps(config))

    frpc_path = "/tmp/frpc"
    if not os.path.exists(frpc_path):
        download_and_extract_frpc(FRP_URL, frpc_path)

    public_url = os.getenv("FLARE_PUBLIC_URL", "")
    
    if public_url:
        print(f"This is the url for accessing your service: https://{name}.{public_url}")
    else:
        print(f'Tunneling service to subdomain "{name}".')

    try:
        proc = subprocess.run([frpc_path, "-c", config_file.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except KeyboardInterrupt:
        proc.send_signal(signal.SIGINT)
        proc.wait()
    finally:
        os.remove(config_file.name)

    if proc.returncode != 0:
        print("frpc failed with return code: ", proc.returncode)
        return


def main():
    args = parse_args()

    if args.command == "tunnel":
        create_tunnel(args.server, args.server_port, args.port, args.name)

if __name__ == '__main__':
    main()