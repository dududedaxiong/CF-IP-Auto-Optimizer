import os, re, json, socket, time, concurrent.futures, requests

BASE = os.path.dirname(__file__)
DOCS = os.path.join(BASE, "docs")

with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
    cfg = json.load(f)

PORT = cfg["port"]

def fetch_ips(urls):
    ips = set()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    for url in urls:
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            ips.update(re.findall(r"(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9a-fA-F]*:[0-9a-fA-F:]+)", resp.text))
        except: pass
    return list(ips)

def test(ip):
    try:
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        s = socket.socket(family, socket.SOCK_STREAM)
        s.settimeout(cfg["timeout"])
        t = time.time()
        if family == socket.AF_INET6: s.connect((ip, PORT, 0, 0))
        else: s.connect((ip, PORT))
        s.close()
        return {"ip": ip, "port": PORT, "delay": round((time.time() - t) * 1000, 2)}
    except: return None

def get_isp_name(ip):
    time.sleep(0.3)
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=isp,status&lang=zh-CN", timeout=3).json()
        if resp.get("status") == "success":
            isp = resp.get("isp", "")
            if "Mobile" in isp: return "移动"
            if "Unicom" in isp: return "联通"
            if "Telecom" in isp: return "电信"
        return "优选"
    except: return "优选"

def run_task(urls, filename, label):
    ips = fetch_ips(urls)
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg["threads"]) as ex:
        raw_results = [r for r in ex.map(test, ips) if r]
    
    v4 = sorted([x for x in raw_results if ":" not in x["ip"]], key=lambda x: x["delay"])
    v6 = sorted([x for x in raw_results if ":" in x["ip"]], key=lambda x: x["delay"])
    final = v4[:5] + v6[:5]

    with open(os.path.join(DOCS, filename), "w", encoding="utf-8") as f:
        v4_c, v6_c = 1, 1
        for x in final:
            isp = get_isp_name(x["ip"])
            ip_str = f"[{x['ip']}]" if ":" in x['ip'] else x['ip']
            idx = v6_c if ":" in x['ip'] else v4_c
            f.write(f"{ip_str}:{x['port']}#{isp}{'IPv6' if ':' in x['ip'] else ''}{idx}\n")
            if ":" in x['ip']: v6_c += 1
            else: v4_c += 1

def main():
    os.makedirs(DOCS, exist_ok=True)
    # 跑默认源
    run_task(cfg["sources"], "best_ip.txt", "默认")
    # 跑所有地区
    for area in cfg.get("areasources", []):
        run_task([area["url"]], f"best_ip_{area['name']}.txt", area["name"])

if __name__ == "__main__":
    main()