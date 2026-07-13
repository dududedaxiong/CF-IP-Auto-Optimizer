#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os, re, json, socket, time, concurrent.futures, requests

BASE=os.path.dirname(__file__)
DOCS=os.path.join(BASE,"docs")

with open(os.path.join(BASE,"config.json"),encoding="utf-8") as f:
    cfg=json.load(f)

PORT=cfg["port"]

def get_ips():
    ips=set()
    # 添加请求头以模拟真实浏览器访问，防止被目标网站拦截
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    for url in cfg["sources"]:
        try:
            # 在请求中传入 headers 参数
            response = requests.get(url, timeout=10, headers=headers)
            txt = response.text
            ips.update(re.findall(r"(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9a-fA-F]*:[0-9a-fA-F:]+)", txt))
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            pass
    return list(ips)

def test(ip):
    try:
        family=socket.AF_INET6 if ":" in ip else socket.AF_INET
        s=socket.socket(family,socket.SOCK_STREAM)
        s.settimeout(cfg["timeout"])
        t=time.time()
        if family==socket.AF_INET6:
            s.connect((ip,PORT,0,0))
        else:
            s.connect((ip,PORT))
        s.close()
        return {"ip":ip,"port":PORT,"delay":round((time.time()-t)*1000,2)}
    except:
        return None

def main():
    os.makedirs(DOCS,exist_ok=True)
    result=[]
    ips=get_ips()

    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg["threads"]) as ex:
        for r in ex.map(test,ips):
            if r:
                result.append(r)

    result.sort(key=lambda x:x["delay"])
    result=result[:cfg["top"]]

    with open(DOCS+"/api.json","w",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2)

    with open(DOCS+"/best_ip.txt","w",encoding="utf-8") as f:
        for x in result:
            ip=x["ip"]
            if ":" in ip:
                ip=f"[{ip}]"
            f.write(f"http://{ip}:{x['port']}#{cfg['country']}\n")

    with open(DOCS+"/clash.yaml","w",encoding="utf-8") as f:
        f.write("proxies:\n")
        for i,x in enumerate(result):
            f.write(f'- name: "{cfg["country"]}-{i+1}-{x["delay"]}ms"\n')
            f.write("  type: http\n")
            f.write(f"  server: {x['ip']}\n")
            f.write(f"  port: {x['port']}\n\n")

if __name__=="__main__":
    main()