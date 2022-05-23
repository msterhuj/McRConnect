from json import loads
from time import sleep
from requests import get
from requests.exceptions import ConnectionError
from mcstatus import JavaServer
from pymongo import MongoClient

client = MongoClient("mongodb://mongo:27017/")
db = client["srv"]
col = db["discover"]


def scan(ip):
    try:
        server = JavaServer.lookup(f"{ip}:25565", timeout=5)
        status = server.status()
        print(status.raw)
        col.delete_many({"ip": ip})
        col.insert_one({
            "ip": f"{ip}",
            "version": status.version.name,
            "latency": status.latency,
            "players": status.players.online,
            "max_players": status.players.max,
            "description": status.description,
            "raw": status.raw
        })
        print(f"{ip} server discovered")
        return True
    except Exception:
        return False


def pause(msg):
    print(msg)
    sleep(5)


if __name__ == '__main__':
    print("Start discoverer client")
    while True:
        try:
            reply = get("http://server:8000/discover")
            if reply.status_code == 200:
                ip = loads(reply.text)["ip"]
                if scan(ip):
                    print("[+] Server discovered on ip " + ip)
                else:
                    print("[-] No server discovered on ip " + ip)
            else:
                pause("[-] No ip to scan")
        except ConnectionError:
            pause("[-] Connection error waiting for server become available")
