#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESG 周推送完整脚本 weekly_push.py
每周一 09:00 CST 由 openclaw cron 触发
完整流程：
  1. web_search 抓本周 ESG 实时新闻热点
  2. 基于新闻生成 20 个选题
  3. 从 RedBI 拉取 XHS 热搜词 + 热门笔记
  4. 更新 esg-weekly-push.html（覆盖可视化页面）
  5. 发送文字推送 + HTML 链接
"""

import json, os, sys, re, subprocess, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE   = Path("/home/node/.openclaw/workspace")
TOPICS_DIR  = WORKSPACE / "esg-daily-topics"
OUTPUT_DIR  = TOPICS_DIR / "output"
HTML_FILE   = WORKSPACE / "esg-weekly-push.html"
RECIPIENT   = "sunpeichun@xiaohongshu.com"
CHANNEL     = "hiredcity"
HTML_URL    = "http://10.40.21.103:18081/esg-weekly-push.html"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ── 1. 抓本周 ESG 实时新闻 ────────────────────────────────────────────────────
def search_esg_news():
    """调用 OpenClaw web_search 工具抓本周 ESG 热点"""
    log("搜索本周 ESG 新闻热点...")
    queries = [
        "ESG 碳市场 政策 本周 最新",
        "碳中和 双碳 企业 2026 最新动态",
        "ESG投资 绿色金融 可持续 本周",
        "ESG就业 证书 职场 2026",
    ]
    results = []
    for q in queries:
        try:
            # 调用系统 web_search（通过 openclaw CLI）
            cmd = ["openclaw", "search", "--json", q]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if out.returncode == 0:
                data = json.loads(out.stdout)
                results.extend(data.get("results", [])[:3])
        except Exception as e:
            log(f"搜索失败({q[:20]}...): {e}")
    return results[:12]

# ── 2. 从 RedBI 拉取热搜词 + 热门笔记（Socket.IO）────────────────────────────
def get_cookie():
    info_file = WORKSPACE / ".redInfo"
    if info_file.exists():
        try:
            data = json.loads(info_file.read_text())
            token = data.get("accessToken") or data.get("token")
            if token:
                return f"common-internal-access-token-prod={token}"
        except Exception:
            pass
    # 回退：运行 SSO 脚本
    try:
        out = subprocess.run(
            ["/app/skills/data-fe-common-sso/script/run-sso.sh"],
            capture_output=True, text=True, timeout=60
        )
        for line in out.stdout.splitlines():
            if "common-internal-access-token-prod=" in line:
                return line.strip()
    except Exception as e:
        log(f"SSO 失败: {e}")
    return None

NOISE_WORDS = ["碳板鞋","pilates","yesgirl","yesg","goth","分布图",
               "气候类型","地中海气候","热带气候","温带气候","高原气候"]
ESG_KW = ["esg","ESG","碳中和","碳达峰","碳排放","双碳","碳交易","碳市场",
          "可持续","绿色金融","社会责任","CSR","气候变化","低碳","净零",
          "绿色债券","ESG报告","ESG评级","ISSB","TCFD","碳足迹","碳资产"]

def is_esg(text):
    tl = text.lower()
    if any(n.lower() in tl for n in NOISE_WORDS): return False
    return any(k.lower() in tl for k in ESG_KW)

def fetch_redbi(cookie, dataset_id, dimensions, measures, filters, orders, limit=50):
    try:
        import socketio as sio_lib
    except ImportError:
        return None
    import uuid, time

    SLIM = ['fieldId','produced','role','fieldName','alias','dataType','partition',
            'tableId','granularity','defaultAggregator','state','hidden','visible',
            'exprVisible','expr','dateFlag','convert','convertedType','convertArg',
            'mapFunction','realDataType','analysisFilterRequired','analysisMaxQueryDays']
    slim = lambda f: {k:f[k] for k in SLIM if k in f}

    body = {"datasetId":dataset_id,
            "dimensions":[slim(d) for d in dimensions],
            "measures":[slim(m) for m in measures],
            "filters":filters,"orders":orders,"limit":limit,"offset":0}

    sio = sio_lib.SimpleClient()
    try:
        sio.connect("https://redbi.devops.xiaohongshu.com", socketio_path="/ws",
                    headers={"Cookie":cookie}, transports=["websocket"], wait_timeout=30)
    except Exception as e:
        log(f"Socket.IO 连接失败: {e}")
        return None

    tid = str(uuid.uuid4())
    sio.emit("apiRequest",{"requestType":"post","api":"/dashboard/dashboard/data",
        "headers":{"user-email":RECIPIENT,"trace-id":tid,"x-b3-traceid":tid},"body":body})

    rows=None; start=time.time()
    while time.time()-start < 60:
        try:
            resp = sio.receive(timeout=10)
            data = resp[1] if isinstance(resp,list) and len(resp)>1 else resp
            if isinstance(data,dict):
                r = data.get("data",{}).get("rows") or []
                st = data.get("data",{}).get("status","")
                if r: rows=r; break
                if st not in ("RUNNING","WAITING",""): break
        except Exception: pass
    try: sio.disconnect()
    except Exception: pass
    return rows

def fetch_hot_words(cookie):
    log("拉取 XHS 热搜词...")
    today = datetime.now()
    d0 = (today-timedelta(days=7)).strftime("%Y-%m-%d")
    d1 = (today-timedelta(days=1)).strftime("%Y-%m-%d")
    dims=[{"fieldId":814559,"produced":"Existed","role":"Dimension","fieldName":"search_word",
           "alias":"搜索词","dataType":"String","partition":False,"tableId":471434,
           "granularity":"g0","defaultAggregator":"CNT","state":0,"hidden":False,"visible":1,
           "exprVisible":1,"dateFlag":False,"realDataType":"String",
           "analysisFilterRequired":False,"analysisMaxQueryDays":0}]
    meas=[{"fieldId":756615,"produced":"Existed","role":"Measure","fieldName":"query_cnt",
           "alias":"搜索量","dataType":"Whole","partition":False,"tableId":471434,
           "granularity":"g0","defaultAggregator":"SUM","state":0,"hidden":False,"visible":1,
           "exprVisible":1,"dateFlag":False,"realDataType":"Whole",
           "analysisFilterRequired":False,"analysisMaxQueryDays":0}]
    filts=[{"type":"range","field":{"fieldId":756567,"fieldName":"dtm","tableId":471434,
            "dataType":"Whole","partition":True,"convert":"DateParse","convertedType":"Date",
            "convertArg":{"date":"YYYYMMDD"}},"range":{"min":d0,"max":d1}},
           {"type":"matchesLower","field":{"fieldId":814559,"fieldName":"search_word",
            "tableId":471434,"dataType":"String"},
            "values":["ESG","esg","可持续","碳中和","碳排放","双碳","碳达峰",
                      "社会责任","绿色金融","碳交易","气候","低碳","净零",
                      "绿色债券","碳市场","ESG证书","ESG实习","ESG职位"]}]
    orders=[{"fieldId":756615,"direction":"DESC"}]
    rows = fetch_redbi(cookie, 12041, dims, meas, filts, orders, limit=50)
    if not rows: return None
    res=[]
    for row in rows:
        if isinstance(row,dict):
            w=row.get("d0",""); c=row.get("m0",0)
        elif isinstance(row,list):
            w,c=(row+["",0])[:2]
        else: continue
        if w and is_esg(w): res.append({"word":w,"count":int(c) if c else 0})
        if len(res)>=8: break
    return res or None

def fetch_hot_notes(cookie):
    log("拉取 XHS 热门笔记...")
    today = datetime.now()
    d0=(today-timedelta(days=7)).strftime("%Y-%m-%d")
    d1=(today-timedelta(days=1)).strftime("%Y-%m-%d")
    dims=[
        {"fieldId":768608,"produced":"Existed","role":"Dimension","fieldName":"title",
         "alias":"笔记标题","dataType":"String","partition":False,"tableId":471434,
         "granularity":"g0","defaultAggregator":"CNT","state":0,"hidden":False,"visible":1,
         "exprVisible":1,"dateFlag":False,"realDataType":"String",
         "analysisFilterRequired":False,"analysisMaxQueryDays":0},
        {"fieldId":768894,"produced":"Calculated","role":"Dimension","fieldName":"",
         "alias":"笔记链接","dataType":"String",
         "expr":"CONCAT('https://www.xiaohongshu.com/discovery/item/', $$768607)",
         "partition":False,"tableId":471434,"granularity":"g0","defaultAggregator":"CNT",
         "state":0,"hidden":False,"visible":1,"exprVisible":1,"dateFlag":False,
         "realDataType":"String","analysisFilterRequired":False,"analysisMaxQueryDays":0}
    ]
    meas=[{"fieldId":769082,"produced":"Calculated","role":"Measure","fieldName":"",
           "alias":"脱敏社区互动量",
           "expr":"DM_IDEA($$768632+$$768633+$$768634+$$768635+$$768680)",
           "dataType":"Decimal","partition":False,"tableId":471434,"granularity":"g0",
           "defaultAggregator":"SUM","state":0,"hidden":False,"visible":1,"exprVisible":1,
           "dateFlag":False,"realDataType":"Double","analysisFilterRequired":False,
           "analysisMaxQueryDays":0}]
    filts=[{"type":"range","field":{"fieldId":768679,"fieldName":"dtm","tableId":471434,
            "dataType":"Whole","partition":True,"convert":"DateParse","convertedType":"Date",
            "convertArg":{"date":"YYYYMMDD"}},"range":{"min":d0,"max":d1}},
           {"type":"select","field":{"fieldId":768622,"fieldName":"enabled",
            "tableId":471434,"dataType":"Whole"},"values":["1"]},
           {"type":"matchesLowerTrim","field":{"fieldId":768608,"fieldName":"title",
            "tableId":471434,"dataType":"String"},
            "values":["ESG","双碳","碳中和","碳排放","碳达峰","社会责任",
                      "绿色金融","可持续","碳交易","气候变化","低碳","净零","ISSB"]}]
    orders=[{"fieldId":769082,"direction":"DESC"}]
    rows = fetch_redbi(cookie, 12346, dims, meas, filts, orders, limit=50)
    if not rows: return None
    res=[]
    for row in rows:
        if isinstance(row,dict):
            t=row.get("d0",""); l=row.get("d1",""); i=row.get("m0",0)
        elif isinstance(row,list):
            t,l,i=(row+["","",0])[:3]
        else: continue
        if t and is_esg(t): res.append({"title":t,"link":l,"interaction":int(i) if i else 0})
        if len(res)>=10: break
    return res or None

# ── 3. 格式化文字推送 ─────────────────────────────────────────────────────────
def format_text(topics, hot_words, hot_notes, ext_news, date_str):
    lines=[]
    lines.append(f"📬 ESG 周选题速递｜{date_str}")
    lines.append("━"*50)

    lines.append("\n🔍 一、本周小红书 ESG 热搜词（近7天）\n")
    if hot_words:
        for i,w in enumerate(hot_words,1):
            lines.append(f"  {i:2d}. {w['word']}  （{w['count']:,} 次搜索）")
    else:
        lines.append("  数据拉取失败，详见可视化链接")

    lines.append("\n🌐 二、本周外部热议话题\n")
    if ext_news:
        for item in ext_news[:6]:
            lines.append(f"  • {item.get('title','')}")
            if item.get('url'): lines.append(f"    {item['url']}")
    else:
        lines.append("  详见可视化链接")

    lines.append("\n📝 三、本周 ESG 热门笔记 Top10（近7天）\n")
    if hot_notes:
        for i,n in enumerate(hot_notes,1):
            lines.append(f"  {i:2d}. {n['title'][:40]}  互动量：{n['interaction']:,}")
            if n.get('link'): lines.append(f"      {n['link']}")
    else:
        lines.append("  数据拉取失败，详见可视化链接")

    lines.append("\n"+"━"*50)
    lines.append(f"\n✍️  四、本周 ESG 精选选题（20个）\n")
    for i,t in enumerate(topics[:20],1):
        if isinstance(t,dict):
            lines.append(f"  {i:02d}. {t.get('title',t)}")
            if t.get('hook'): lines.append(f"      💡 {t['hook']}")
        else:
            lines.append(f"  {i:02d}. {t}")
        lines.append("")

    lines.append("━"*50)
    lines.append(f"\n🤖 OpenClaw 自动生成｜{datetime.now().strftime('%Y-%m-%d %H:%M')} CST")
    return "\n".join(lines)

# ── 4. 更新 HTML 可视化页面 ───────────────────────────────────────────────────
def update_html(topics, hot_words, hot_notes, ext_news, date_str):
    """
    更新 esg-weekly-push.html。
    先把当前内容写入 esg-content-data.json，再调用 render_html.py 渲染。
    LLM 不直接写 HTML，节省 ~70% output token。
    """
    log("更新 HTML 可视化页面（JSON→渲染）...")

    # 1. 构建 data JSON（把当前选题/新闻/商机 写进去）
    data = {"date": date_str, "subtitle": ""}

    # 封面副标题：取前4条新闻关键词
    if ext_news:
        kws = [n.get('title','')[:20] for n in ext_news[:4] if n.get('title')]
        data["subtitle"] = ' · '.join(kws) + '<br>基于本周真实商业大事件生成，可持续发展是门好生意'
    else:
        data["subtitle"] = '基于本周真实商业大事件生成，可持续发展是门好生意'

    # 事件列表
    data["events"] = []
    for n in (ext_news or [])[:6]:
        data["events"].append({
            "url": n.get('url','#'),
            "title": n.get('title',''),
            "desc": n.get('desc', n.get('snippet','')),
            "src": n.get('src', n.get('source',''))
        })

    # 选题列表
    data["topics"] = []
    for i, t in enumerate(topics[:20], 1):
        if isinstance(t, dict):
            data["topics"].append({
                "n": i,
                "title": t.get('title',''),
                "hook": t.get('hook', t.get('desc','')),
                "tags": t.get('tags', []),
                "stars": t.get('stars', 4),
                "links": t.get('links', [])
            })
        else:
            data["topics"].append({"n": i, "title": str(t), "hook": "", "tags": [], "stars": 4, "links": []})

    # 商机：读取已有 JSON 中的商机（biz 由人工维护，cron 不自动覆盖）
    data_file = TOPICS_DIR / "esg-content-data.json"
    if data_file.exists():
        try:
            old = json.loads(data_file.read_text())
            data["biz"] = old.get("biz", [])
        except Exception:
            data["biz"] = []
    else:
        data["biz"] = []

    # 2. 写入 data JSON
    data_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"已写入 data JSON: {data_file} ({data_file.stat().st_size} bytes)")

    # 3. 调用渲染脚本生成 HTML
    render_script = TOPICS_DIR / "render_html.py"
    if not render_script.exists():
        log("⚠️ render_html.py 不存在，跳过 HTML 渲染")
        return

    out = subprocess.run(
        ["python3", str(render_script), str(data_file), str(HTML_FILE)],
        capture_output=True, text=True, timeout=30
    )
    if out.returncode == 0:
        log(f"HTML 渲染完成: {HTML_FILE} ({HTML_FILE.stat().st_size} bytes)")
    else:
        log(f"⚠️ HTML 渲染失败: {out.stderr}")

# ── 5. 发送推送 ───────────────────────────────────────────────────────────────
def send_message(text):
    """通过 openclaw message 发送"""
    try:
        cmd = ["openclaw", "message", "send",
               "--channel", CHANNEL,
               "--to", RECIPIENT,
               "--message", text]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            log("✅ 消息发送成功")
            return True
        else:
            log(f"❌ 发送失败: {out.stderr}")
            return False
    except Exception as e:
        log(f"❌ 发送异常: {e}")
        return False

# ── 主流程 ────────────────────────────────────────────────────────────────────
def main():
    log("🚀 ESG 周推送开始")
    today = datetime.now()
    date_str = today.strftime("%Y年%m月%d日")

    # 1. 获取 cookie
    cookie = get_cookie()
    if not cookie:
        log("⚠️ 无法获取 RedBI cookie，跳过内部数据")

    # 2. 拉取内部数据
    hot_words = fetch_hot_words(cookie) if cookie else None
    hot_notes = fetch_hot_notes(cookie) if cookie else None
    log(f"热搜词: {len(hot_words) if hot_words else 0} 条 | 热门笔记: {len(hot_notes) if hot_notes else 0} 条")

    # 3. 抓外部新闻
    ext_news = search_esg_news()
    log(f"外部新闻: {len(ext_news)} 条")

    # 4. 读取预生成选题（由 OpenClaw 主会话在 cron 触发前写入）
    pending = TOPICS_DIR / "pending_topics.json"
    topics = []
    if pending.exists():
        try:
            topics = json.loads(pending.read_text(encoding="utf-8"))
            pending.unlink()
            log(f"加载选题 {len(topics)} 个")
        except Exception as e:
            log(f"读取选题失败: {e}")

    if not topics:
        log("⚠️ 未找到预生成选题，使用上周存档")
        last_files = sorted(OUTPUT_DIR.glob("topics_*.txt"), reverse=True)
        if last_files:
            content = last_files[0].read_text(encoding="utf-8")
            log(f"使用存档: {last_files[0].name}")
            # 直接发送存档内容
            send_message(content)
            send_message(f"📊 本期可视化长图：{HTML_URL}")
            return

    # 5. 格式化文字推送
    text_content = format_text(topics, hot_words, hot_notes, ext_news, date_str)

    # 6. 保存
    out_file = OUTPUT_DIR / f"topics_{today.strftime('%Y-%m-%d')}.txt"
    out_file.write_text(text_content, encoding="utf-8")
    log(f"已保存: {out_file}")

    # 7. 更新 HTML
    update_html(topics, hot_words, hot_notes, ext_news, date_str)

    # 8. 发送
    send_message(text_content)
    send_message(f"📊 本期可视化长图：{HTML_URL}")

    log("✅ ESG 周推送完成")

if __name__ == "__main__":
    main()
