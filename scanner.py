from __future__ import annotations

import os
import socket
from base64 import b64decode

from datetime import datetime, timedelta
from multiprocessing import Pool, current_process

from mcstatus import JavaServer
from mcstatus.pinger import PingResponse
from pymongo import MongoClient
from rich import print
from rich.traceback import install

install(show_locals=True)


def syn_ack(ip, port) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        sock.connect((ip, port))
        sock.close()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        sock.close()


def java_server_lookup(ip, port) -> PingResponse | None:
    try:
        server = JavaServer.lookup(f"{ip}:{port}", timeout=5)
        return server.status()
    except Exception as e:
        print(e)
        return None


def favicon_to_img(data, name) -> None:
    if not data or os.path.isfile(f"img/{name}.png"):
        return
    with open(f"img/{name}.png", "wb") as f:
        f.write(b64decode(data.split(",")[1]))
        print(f"[*] Saved favicon of {name}")


def __scan_pool__(offset, limit):
    print(f"[*] Starting scan from {current_process().name} with offset {offset * limit} and limit {limit}")
    client = MongoClient("mongodb://127.0.0.1:27017/")
    db = client["srv"]

    col = db["discover"]

    if col.count_documents({"scanner_process": current_process().name}) == 0:
        print(f"[*] Process {current_process().name} Taking {limit} ip from {offset * limit} offset")
        ips = col.find({
            "scanner_process": {
                "$exists": False,
            }
        }).sort("date", 1).limit(limit).skip(offset * limit)
        col.update_many(
            {
                "ip": {"$in": [ip["ip"] for ip in ips]},
            },
            {
                "$set": {
                    "scanner_process": current_process().name,
                    "date": datetime.now()
                }
            }
        )
    else:
        print(f"[*] Process {current_process().name} have remaining ip to scan skipping taking ip from db")

    for ip in col.find({"scanner_process": current_process().name}):

        print(f"[{current_process().name}] Scanning {ip['ip']}")
        if not syn_ack(ip["ip"], 25565):
            print(f"[{current_process().name}] {ip['ip']} is not reachable")
            col.update_one({
                "ip": ip["ip"],
            }, {
                "$set": {
                    "up": False,
                    "date": datetime.now()
                }, "$unset": {"scanner_process": None}
            })
            continue

        status = java_server_lookup(ip["ip"], 25565)
        if status is None:
            print(f"[{current_process().name}] {ip['ip']} is not a minecraft server")
            col.update_one({
                "ip": ip["ip"],
            }, {
                "$set": {
                    "up": False,
                    "date": datetime.now()
                }, "$unset": {"scanner_process": None}
            })
            continue

        print(f"[{current_process().name}] {ip['ip']} on port 25565 is a minecraft server")
        col.update_one({
            "ip": ip["ip"],
        }, {
            "$set": {
                "version": status.version.name,
                "latency": status.latency,
                "players": status.players.online,
                "max_players": status.players.max,
                "description": status.description,
                "favicon": status.favicon,
                "raw": status.raw,
                "up": True,
                "date": datetime.now()
            }, "$unset": {"scanner_process": None}
        })
        favicon_to_img(status.favicon, ip["ip"])
    client.close()
    print(f"[*] Process {current_process().name} finished")


if __name__ == '__main__':
    # count all docs older than 1 day
    client = MongoClient("mongodb://127.0.0.1:27017/")
    db = client["srv"]
    col = db["discover"]
    to_scan = col.count_documents({'date': {'$lt': datetime.now() - timedelta(hours=12)}})
    left = col.count_documents({"scanner_process": {"$exists": True}})
    client.close()

    if to_scan == 0 and left == 0:
        print("[*] Nothing to scan")
        exit(0)
    if left > 0:
        print(f"[*] {left} docs are currently being scanned by other process restart in a few minutes")
    print(f"[*] {to_scan} docs older than 1 day")

    process = 8
    limit = to_scan // process
    input(f"[*] Starting scan with {process} process and {limit} ip per process, press enter to continue")
    pool = Pool(process)
    pool.starmap(__scan_pool__, [(i, limit) for i in range(process)])
