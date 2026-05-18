#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESG HTML 渲染器
读取 esg-content-data.json，生成 esg-weekly-push.html
这样 LLM 只需输出 JSON，不直接写 HTML，节省 ~70% token
"""

import json, re
from pathlib import Path
from datetime import datetime

WORKSPACE  = Path("/home/node/.openclaw/workspace")
DATA_FILE  = WORKSPACE / "esg-daily-topics/esg-content-data.json"
HTML_OUT   = WORKSPACE / "esg-weekly-push.html"

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&family=Noto+Serif+SC:wght@400;700&display=swap');

*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:'Noto Sans SC',system-ui,sans-serif;background:#f5f5f5}

.slide{width:100%;display:flex;flex-direction:column;justify-content:flex-start;position:relative;padding:clamp(2.5rem,5vw,5rem) clamp(2.5rem,6vw,6rem);padding-bottom:clamp(3rem,6vw,6rem);border-bottom:1px solid #e8ecf0;}
.slide:last-child{border-bottom:none}
.dots{position:fixed;right:18px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:6px;z-index:99}
.dot{width:7px;height:7px;border-radius:50%;background:rgba(0,0,0,.15);cursor:pointer;transition:all .25s;border:none;padding:0}
.dot.on{background:#06874E;transform:scale(1.3)}
#s1{background:linear-gradient(135deg,#e8f5ef 0%,#f0faf5 50%,#e3f2fb 100%)}
#s1::after{content:'';position:absolute;right:-5%;top:-15%;width:52vw;height:52vw;border-radius:50%;background:radial-gradient(circle,rgba(6,135,78,.1) 0%,transparent 65%);pointer-events:none}
.cover-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(6,135,78,.12);border:1.5px solid rgba(6,135,78,.3);color:#06874E;padding:6px 18px;border-radius:99px;font-size:.85rem;font-weight:600;margin-bottom:clamp(14px,3vh,28px)}
.badge-dot{width:8px;height:8px;border-radius:50%;background:#06874E;animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.cover-line{width:52px;height:4px;background:#06874E;border-radius:2px;margin-bottom:clamp(12px,2.5vh,22px)}
.cover-h1{font-family:'Noto Serif SC',serif;font-weight:700;font-size:clamp(2.6rem,6vw,4.8rem);color:#111;line-height:1.15;margin-bottom:clamp(10px,2vh,18px)}
.cover-h1 em{font-style:normal;color:#06874E}
.cover-sub{font-size:clamp(.9rem,1.6vw,1.15rem);color:#444;line-height:1.8;max-width:640px;margin-bottom:clamp(24px,5vh,46px)}
.cover-stats{display:flex;gap:clamp(20px,4vw,52px);flex-wrap:wrap}
.cs-item{display:flex;flex-direction:column;gap:5px}
.cs-lbl{font-size:.8rem;color:#777;letter-spacing:.04em}
.cs-val{font-size:clamp(1.8rem,4vw,3rem);font-weight:900;color:#111;line-height:1}
.cs-val.hi{color:#06874E}
.cs-valc{font-size:1.05rem;font-weight:600;color:#333}
.sh-tag{font-size:.8rem;color:#06874E;letter-spacing:.08em;font-weight:600;text-transform:uppercase;margin-bottom:4px}
.sh-title{font-family:'Noto Serif SC',serif;font-weight:700;font-size:clamp(1.4rem,3vw,2.2rem);color:#111;margin-bottom:4px}
.sh-line{width:44px;height:4px;background:#06874E;border-radius:2px;margin:8px 0 clamp(10px,2vh,20px)}
.snum{position:absolute;right:clamp(2rem,5vw,5rem);top:clamp(1.5rem,4vh,3rem);font-size:clamp(5rem,10vw,9rem);font-weight:900;color:rgba(6,135,78,.06);line-height:1;pointer-events:none;user-select:none}
.ext-list{display:flex;flex-direction:column;gap:7px}
.ext-card{background:#f0f4ff;border:1px solid #dde5f8;border-radius:8px;padding:7px 12px;text-decoration:none;color:inherit;display:block}
.ext-card:hover{border-color:#2563eb;background:#e8eeff;box-shadow:0 2px 8px rgba(37,99,235,.1)}
.ext-kw{font-size:.88rem;font-weight:700;color:#1a3a8f;margin-bottom:2px}
.ext-desc{font-size:.7rem;color:#555;line-height:1.45}
.ext-src{font-size:.6rem;color:#aaa;margin-top:2px}
.tgrid{display:grid;grid-template-columns:1fr 1fr;gap:clamp(5px,0.9vw,9px);margin-top:clamp(6px,1vh,12px)}
.tc{background:#fff;border:1.5px solid #e8ecf5;border-radius:10px;overflow:hidden}
.tc::before{content:'';display:block;height:3px;background:#06874E}
.tc:hover{border-color:#06874E;box-shadow:0 2px 10px rgba(6,135,78,.08)}
.tc summary{list-style:none;padding:clamp(8px,1.1vw,13px) clamp(10px,1.5vw,16px);cursor:pointer;user-select:none}
.tc summary::-webkit-details-marker{display:none}
.tc-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:4px}
.tc-n{font-size:.82rem;font-weight:800;color:#06874E;line-height:1;letter-spacing:.02em;flex-shrink:0}
.tc-t{font-size:clamp(.82rem,1.3vw,1rem);color:#111;font-weight:700;line-height:1.4;margin-bottom:4px}
.tc-h{font-size:clamp(.72rem,.95vw,.82rem);color:#666;line-height:1.5;margin-bottom:6px}
.tc-meta{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px}
.tags{display:flex;flex-wrap:wrap;gap:3px}
.tag{font-size:.65rem;padding:2px 7px;border-radius:99px;font-weight:600}
.tp{background:rgba(6,135,78,.1);color:#06874E}
.tm{background:rgba(230,168,23,.12);color:#c47f00}
.tg{background:rgba(37,99,235,.1);color:#2563eb}
.tc2{background:rgba(124,58,237,.1);color:#7c3aed}
.tt{background:rgba(220,38,38,.1);color:#dc2626}
.stars{font-size:.8rem;letter-spacing:1px;flex-shrink:0}
.stars .s{color:#e6a817}
.stars .e{color:#ddd}
.tc-links{padding:8px clamp(10px,1.5vw,16px) 12px;background:#f8fbf9;border-top:1px solid #e8f0ec}
.tc-links-title{font-size:.7rem;color:#888;font-weight:600;margin-bottom:5px;letter-spacing:.04em}
.tc-link{display:flex;align-items:baseline;gap:6px;margin-bottom:4px}
.tc-link a{font-size:.75rem;color:#06874E;text-decoration:none;line-height:1.4}
.tc-link a:hover{text-decoration:underline}
.tc-link-src{font-size:.65rem;color:#aaa;flex-shrink:0}
.tc-arrow{font-size:.7rem;color:#aaa;flex-shrink:0;transition:transform .2s}
details[open] .tc-arrow{transform:rotate(180deg)}
.biz-card{background:#fff;border-radius:10px;overflow:hidden;border:1.5px solid #e8ecf5}
.biz-card:hover{border-color:#06874E;box-shadow:0 2px 10px rgba(6,135,78,.08)}
.biz-body{padding:clamp(8px,1.1vw,14px) clamp(10px,1.5vw,16px)}
.biz-name{font-size:clamp(.85rem,1.2vw,.95rem);font-weight:700;color:#111;margin-bottom:4px}
.biz-desc{font-size:.75rem;color:#555;line-height:1.5;margin-bottom:6px}
.biz-trigger{font-size:.68rem;color:#888}
@media(max-width:768px){
  .slide{padding:16px 16px 72px;}
  .dots{right:unset;top:unset;transform:none;bottom:18px;left:50%;transform:translateX(-50%);flex-direction:row;gap:8px;background:rgba(255,255,255,.85);padding:8px 16px;border-radius:99px;box-shadow:0 2px 12px rgba(0,0,0,.12);backdrop-filter:blur(8px);}
  .dot.on{width:22px;height:7px;border-radius:4px}
  #s1::after{display:none}
  .cover-h1{font-size:2.4rem}
  .snum{display:none}
  .tgrid{grid-template-columns:1fr;gap:8px}
  .sh-title{font-size:1.3rem}
}
"""

JS = """
var slides = document.querySelectorAll('.slide');
var dots   = document.querySelectorAll('.dot');
function goTo(n){ slides[n].scrollIntoView({behavior:'smooth', block:'start'}); }
var obs = new IntersectionObserver(function(entries){
  entries.forEach(function(e){
    if(e.isIntersecting){
      var i=[].indexOf.call(slides,e.target);
      dots.forEach(function(d,j){d.classList.toggle('on',j===i);});
    }
  });
},{threshold:0.25});
slides.forEach(function(s){obs.observe(s);});
"""

TAG_CLASS = {"政策监管":"tp","市场动态":"tm","国际视角":"tg","科技趋势":"tt","投资关注":"tc2"}

PRIORITY_COLORS = {
    "最优先": ("#e63c3c","linear-gradient(90deg,#e63c3c,#f97316)","rgba(230,60,60,.1)"),
    "高优":   ("#f97316","#f97316","rgba(249,115,22,.1)"),
    "跟进":   ("#06874E","#06874E","rgba(6,135,78,.1)"),
    "观察":   ("#2563eb","#2563eb","rgba(37,99,235,.1)"),
}

def stars_html(n):
    return f'<span class="s">{"★"*n}</span><span class="e">{"★"*(5-n)}</span>'

def render_event(e):
    return f'''    <a class="ext-card" href="{e['url']}" target="_blank">
      <div class="ext-kw">{e['title']}</div>
      <div class="ext-desc">{e['desc']}</div>
      <div class="ext-src">{e['src']}</div>
    </a>'''

def render_topic(t):
    tags_html = ''.join(f'<span class="tag {TAG_CLASS.get(tag,"tm")}">{tag}</span>' for tag in t.get('tags',[]))
    links_html = ''
    if t.get('links'):
        links_inner = '\n'.join(f'      <div class="tc-link"><a href="{l["url"]}" target="_blank">{l["text"]}</a><span class="tc-link-src">{l["src"]}</span></div>' for l in t['links'])
        links_html = f'\n    <div class="tc-links"><div class="tc-links-title">📎 参考资料</div>\n{links_inner}\n    </div>'
    n_str = str(t['n']).zfill(2)
    return f'''    <details class="tc"><summary>
      <div class="tc-head"><span class="tc-n">{n_str}</span><span class="tc-arrow">▾</span></div>
      <div class="tc-t">{t['title']}</div>
      <div class="tc-h">{t['hook']}</div>
      <div class="tc-meta"><div class="tags">{tags_html}</div><div class="stars">{stars_html(t.get('stars',4))}</div></div>
    </summary>{links_html}</details>'''

def render_biz(b):
    color, bar_bg, badge_bg = PRIORITY_COLORS.get(b['priority'], PRIORITY_COLORS['跟进'])
    return f'''    <div class="biz-card">
      <div style="height:3px;background:{bar_bg}"></div>
      <div class="biz-body">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:6px">
          <span style="font-size:.82rem;font-weight:900;color:{color}">{str(b['n']).zfill(2)}</span>
          <span style="font-size:.7rem;background:{badge_bg};color:{color};padding:2px 8px;border-radius:99px;font-weight:700;flex-shrink:0">{b['priority']}</span>
        </div>
        <div class="biz-name">{b['name']}</div>
        <div class="biz-desc">{b['desc']}</div>
        <div class="biz-trigger">{b['trigger']}</div>
      </div>
    </div>'''

def render(data):
    date    = data.get('date', datetime.now().strftime('%Y年%-m月%-d日'))
    subtitle = data.get('subtitle', '')
    events  = data.get('events', [])
    topics  = data.get('topics', [])
    biz     = data.get('biz', [])
    t1_10   = [t for t in topics if t['n'] <= 10]
    t11_20  = [t for t in topics if t['n'] > 10]
    num_slides = 2 + bool(t1_10) + bool(t11_20) + bool(biz)

    events_html  = '\n'.join(render_event(e) for e in events)
    topics1_html = '\n'.join(render_topic(t) for t in t1_10)
    topics2_html = '\n'.join(render_topic(t) for t in t11_20)
    biz_html     = '\n'.join(render_biz(b) for b in biz)

    dots_html = '\n'.join(f'  <div class="dot{"  on" if i==0 else ""}" onclick="goTo({i})"></div>' for i in range(num_slides))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ESG 周选题速递 · {date}</title>
<style>{CSS}</style>
</head>
<body>
<nav class="dots">
{dots_html}
</nav>

<!-- ══ 01 封面 ══ -->
<section class="slide" id="s1">
  <div class="cover-badge"><span class="badge-dot"></span>TouchBase · ESG 周选题速递</div>
  <div class="cover-line"></div>
  <h1 class="cover-h1">本周 <em>ESG</em><br>选题速递</h1>
  <p class="cover-sub">{subtitle}</p>
  <div class="cover-stats">
    <div class="cs-item"><span class="cs-lbl">发布日期</span><span class="cs-valc">{date}</span></div>
    <div class="cs-item"><span class="cs-lbl">本期选题</span><span class="cs-val hi">{len(topics)}</span></div>
    <div class="cs-item"><span class="cs-lbl">商业热议</span><span class="cs-val">{len(events)}</span></div>
    <div class="cs-item"><span class="cs-lbl">传播商机</span><span class="cs-val">{len(biz)}</span></div>
  </div>
</section>

<!-- ══ 02 商业大事件 ══ -->
<section class="slide" id="s2" style="background:#fff">
  <div class="snum">02</div>
  <div class="sh-tag">🌐 本周商业大事件</div>
  <div class="sh-title">本周热议</div>
  <div class="sh-line" style="margin:5px 0 8px"></div>
  <div class="ext-list">
{events_html}
  </div>
</section>

<!-- ══ 03 选题 01–10 ══ -->
<section class="slide" id="s3" style="background:#f7f9ff">
  <div class="snum">03</div>
  <div class="sh-tag">✍️ 本周选题</div>
  <div class="sh-title">精选选题 01 – 10</div>
  <div class="sh-line"></div>
  <div class="tgrid">
{topics1_html}
  </div>
</section>

<!-- ══ 04 选题 11–20 ══ -->
<section class="slide" id="s4" style="background:#f7f9ff">
  <div class="snum">04</div>
  <div class="sh-tag">✍️ 本周选题</div>
  <div class="sh-title">精选选题 11 – 20</div>
  <div class="sh-line"></div>
  <div class="tgrid">
{topics2_html}
  </div>
</section>

<!-- ══ 05 ESG 商机 ══ -->
<section class="slide" id="s5" style="background:#fff">
  <div class="snum">05</div>
  <div class="sh-tag">💼 本月商机雷达</div>
  <div class="sh-title">ESG 传播商机 Top {len(biz)}</div>
  <div class="sh-line"></div>
  <p style="font-size:.8rem;color:#666;margin-bottom:clamp(8px,1.5vh,16px);line-height:1.6">筛选标准：有真实ESG实践但缺乏叙事能力 × 本月有触发事件 × 决策人可触达</p>
  <div class="tgrid">
{biz_html}
  </div>
</section>

<script>{JS}</script>
</body>
</html>"""


if __name__ == '__main__':
    import sys
    data_file = sys.argv[1] if len(sys.argv) > 1 else str(DATA_FILE)
    out_file  = sys.argv[2] if len(sys.argv) > 2 else str(HTML_OUT)

    with open(data_file) as f:
        data = json.load(f)

    html = render(data)

    with open(out_file, 'w') as f:
        f.write(html)

    print(f"✅ 渲染完成: {out_file} ({len(html)} bytes, {len(html)//1024}KB)")
