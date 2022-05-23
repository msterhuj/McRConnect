from random import randint
from ipaddress import ip_network
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
ip_to_scan = []


class IPS(BaseModel):
    ips: str


@app.get("/discover")
def next_ip():
    try:
        return {'ip': ip_to_scan.pop(randint(0, len(ip_to_scan) - 1))}
    except Exception:
        raise HTTPException(status_code=404, detail="No more IPs to scan")


@app.get("/left")
def left():
    return {"left": len(ip_to_scan)}


@app.get("/flush")
def flush_scan():
    global ip_to_scan
    ip_to_scan = []
    return {"message": "Scan list flushed"}


@app.post("/scan")
def add_to_scan(ips: IPS):
    global ip_to_scan
    ip_to_scan += [ip for ip in ip_network(ips.ips)]
    return {"message": "IP range added to scan list"}
