#!/usr/bin/env python3
# -*- coding:utf-8 -*-

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
            txt = requests.get(url, timeout=10, headers=headers).text
            ips.update(re.findall(r"(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9a-fA-F]*:[0-9a-fA-F:]+)", txt))
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
    """查询 IP 运营商信息，加入延迟防止风控"""
    time.sleep(1) 
    try:
        # 使用 ip-api.com 查询，fields=isp 返回运营商信息
        url = f"http://ip-api.com/json/{ip}?fields=isp,status&lang=zh-CN"
        resp = requests.get(url, timeout=5).json()
        if resp.get("status") == "success":
            isp = resp.get("isp", "未知")
            # 简化运营商名称
            if "Mobile" in isp: return "移动"
            if "Unicom" in isp: return "联通"
            if "Telecom" in isp: return "电信"
            return "优选"
        return "优选"
    except: return "优选"

def main():
    os.makedirs(DOCS, exist_ok=True)
    ips = get_ips()
    result = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg["threads"]) as ex:
        for r in ex.map(test, ips):
            if r: result.append(r)

    result.sort(key=lambda x: x["delay"])

    # 分离并截取：IPv4 前 10，IPv6 前 10
    v4_list = [x for x in result if ":" not in x["ip"]][:10]
    v6_list = [x for x in result if ":" in x["ip"]][:10]
    final_result = v4_list + v6_list

    # 处理命名
    for item in final_result:
        item["isp"] = get_isp_name(item["ip"])

    # 写入文件
    with open(DOCS + "/best_ip.txt", "w", encoding="utf-8") as f:
        v4_cnt, v6_cnt = 1, 1
        for x in final_result:
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