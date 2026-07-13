import os, re, json, socket, time, concurrent.futures, requests

BASE = os.path.dirname(__file__)
DOCS = os.path.join(BASE, "docs")

with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
    cfg = json.load(f)

PORT = cfg["port"]

def get_ips():
    ips = set()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    for url in cfg["sources"]:
        try:
            # 增加超时和头部，防止连接中断或被封
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
    time.sleep(0.5) # 轻量延时防止接口风控
    try:
        url = f"http://ip-api.com/json/{ip}?fields=isp,status&lang=zh-CN"
        resp = requests.get(url, timeout=3).json()
        if resp.get("status") == "success":
            isp = resp.get("isp", "")
            if "Mobile" in isp: return "移动"
            if "Unicom" in isp: return "联通"
            if "Telecom" in isp: return "电信"
        return "优选"
    except: return "优选"

def main():
    os.makedirs(DOCS, exist_ok=True)
    ips = get_ips()
    
    # 1. 全部测试
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg["threads"]) as ex:
        raw_results = [r for r in ex.map(test, ips) if r]

    # 2. 先拆分再排序
    v4_list = sorted([x for x in raw_results if ":" not in x["ip"]], key=lambda x: x["delay"])
    v6_list = sorted([x for x in raw_results if ":" in x["ip"]], key=lambda x: x["delay"])

    # 3. 各取前10
    final_result = v4_list[:5] + v6_list[:5]

    # 4. 获取归属地并写入
    with open(DOCS + "/best_ip.txt", "w", encoding="utf-8") as f:
        v4_cnt, v6_cnt = 1, 1
        for x in final_result:
            x["isp"] = get_isp_name(x["ip"]) # 精准识别
            ip_str = f"[{x['ip']}]" if ":" in x['ip'] else x['ip']
            prefix = "IPv6" if ":" in x['ip'] else ""
            idx = v6_cnt if ":" in x['ip'] else v4_cnt
            f.write(f"{ip_str}:{x['port']}#{x['isp']}{prefix}{idx}\n")
            if ":" in x['ip']: v6_cnt += 1
            else: v4_cnt += 1

    with open(DOCS + "/api.json", "w", encoding="utf-8") as f:
        json.dump(final_result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()