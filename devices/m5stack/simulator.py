"""M5Stack CoreS3 state-machine simulator using the production API."""
import argparse
import time
import httpx

STATES = ["IDLE", "LISTENING", "UPLOADING", "THINKING", "SPEAKING", "IDLE"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url) as client:
        client.post("/auth/login", json={"email": args.email, "password": args.password}).raise_for_status()
        device = client.post("/devices", params={"name": "CoreS3 simulator"}).json()
        print(client.get(f"/devices/{device['id']}/bootstrap").json())
        for state in STATES:
            response = client.post("/devices/heartbeat", json={"device_id": device["id"], "state": state, "metadata": {"battery": 90}})
            response.raise_for_status()
            print(state, response.json())
            time.sleep(0.3)

if __name__ == "__main__":
    main()

