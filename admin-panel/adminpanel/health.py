"""Sunucu sağlığı: disk, bellek, işlemci, veritabanı."""
import os
import socket
import time

import psutil

from . import config, db

psutil.cpu_percent(interval=None)  # ilk çağrı 0 döner; ısınma


def server() -> dict:
    try:
        d = psutil.disk_usage(config.DISK_PATH)
        disk = {"total": d.total, "used": d.used, "free": d.free, "percent": d.percent, "path": config.DISK_PATH}
    except OSError as e:
        disk = {"error": str(e)}
    m = psutil.virtual_memory()
    try:
        load = os.getloadavg()
    except OSError:
        load = None
    dbinfo = db.one(
        "SELECT pg_database_size(current_database()) AS size, current_database() AS name, "
        "version() AS version, now() - pg_postmaster_start_time() AS uptime"
    )
    runner = db.one(
        "SELECT runner_name, hostname, heartbeat_at, started_at, "
        "extract(epoch FROM now()-heartbeat_at)::int AS age_seconds FROM ops.runner_status "
        "ORDER BY heartbeat_at DESC LIMIT 1"
    )
    return {
        "hostname": socket.gethostname(),
        "disk": disk,
        "memory": {"total": m.total, "used": m.total - m.available, "percent": m.percent},
        "cpu_percent": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(),
        "load": load,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "database": {
            "name": dbinfo["name"],
            "size": dbinfo["size"],
            "version": dbinfo["version"].split(" on ")[0].split(" (")[0],
            "uptime_seconds": int(dbinfo["uptime"].total_seconds()),
        },
        "runner": runner,
    }
