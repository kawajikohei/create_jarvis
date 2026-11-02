"""第1ステップの基本ツール。PC操作系は第2ステップで追加します。"""

from __future__ import annotations

import datetime as dt
import os
import platform
import shutil

from .registry import registry

WEEKDAYS = "月火水木金土日"


@registry.tool(
    name="get_current_time",
    description="現在の日付・曜日・時刻（PCのローカル時刻）を返します。",
)
def get_current_time() -> dict:
    now = dt.datetime.now().astimezone()
    return {
        "datetime": now.isoformat(timespec="seconds"),
        "weekday": WEEKDAYS[now.weekday()] + "曜日",
        "timezone": str(now.tzinfo),
    }


@registry.tool(
    name="get_system_info",
    description="このPCのOS、CPU、ディスク空き容量などの基本情報を返します。",
)
def get_system_info() -> dict:
    home = os.path.expanduser("~")
    disk = shutil.disk_usage(home)
    gb = 1024**3
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "home": home,
        "disk_free_gb": round(disk.free / gb, 1),
        "disk_total_gb": round(disk.total / gb, 1),
    }
