# ESG Weekly Push — 安装与配置

## 目录结构（安装后）

```
~/workspace/
├── esg-weekly-push.html          # 渲染输出（HTTP 服务静态文件）
└── esg-daily-topics/
    ├── esg-content-data.json     # 当前内容数据（每次 cron 更新）
    ├── render_html.py            # 渲染脚本
    ├── weekly_push.py            # 推送脚本（可选）
    └── output/                   # 历史存档（topics_YYYY-MM-DD.txt）
```

## HTTP 服务保活

### 方案A：Python 简单启动
```bash
nohup python3 -m http.server 18081 --directory ~/workspace > /tmp/http18081.log 2>&1 &
```

### 方案B：keep-http.sh + cron 保活（推荐）
```bash
# keep-http.sh
#!/bin/bash
PORT=18081
WORKSPACE="/home/node/.openclaw/workspace"
if ! curl -sf "http://localhost:$PORT/" > /dev/null 2>&1; then
  nohup python3 -m http.server $PORT --directory "$WORKSPACE" > /tmp/http$PORT.log 2>&1 &
  echo "[$(date)] HTTP 服务已重启" >> /tmp/http$PORT.log
fi
```

保活 cron（每5分钟检查）：
```json
{
  "name": "HTTP服务保活-18081",
  "schedule": { "kind": "cron", "expr": "*/5 * * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Run this bash command immediately with exec tool, no output needed: bash ~/workspace/scripts/keep-http.sh. Then reply HEARTBEAT_OK."
  }
}
```

## 渲染脚本用法

```bash
# 基本用法（使用默认路径）
python3 ~/workspace/esg-daily-topics/render_html.py

# 自定义数据文件和输出路径
python3 ~/workspace/esg-daily-topics/render_html.py \
  /path/to/esg-content-data.json \
  /path/to/output.html
```

## JSON 数据格式

`esg-content-data.json` 完整字段说明：

```json
{
  "date": "2026年4月7日",
  "subtitle": "热点1 · 热点2 · 热点3<br>基于本周真实商业大事件生成，可持续发展是门好生意",
  "events": [
    {
      "url": "https://example.com/article",
      "title": "文章标题",
      "desc": "150字以内的摘要说明",
      "src": "来源：XX网站 · 4月3日"
    }
    // 共 6 条
  ],
  "topics": [
    {
      "n": 1,
      "title": "选题标题（吸引眼球，含具体数据/冲突点）",
      "hook": "触发热点：X月X日...公式X：...→...对CEO启发：...",
      "tags": ["政策监管"],  // 可选值：政策监管/市场动态/国际视角/科技趋势/投资关注
      "stars": 5,            // 1-5
      "links": [
        {"url": "https://...", "text": "链接文字", "src": "来源 · 日期"}
      ]
    }
    // 共 20 条
  ],
  "biz": [
    {
      "n": 1,
      "priority": "最优先",  // 最优先/高优/跟进/观察
      "name": "公司名称",
      "desc": "一段话：为什么这家公司现在是商机",
      "trigger": "触发：X月X日事件 · 具体原因"
    }
    // 共 10 条
  ]
}
```

## HTML 页面结构

5个 section，连续平滑滚动，右侧导航点自动高亮：

| id | 内容 |
|----|------|
| s1 | 封面：标题/副标题/统计数字/日期 |
| s2 | 本周商业大事件（6条，含链接） |
| s3 | 精选选题 01–10 |
| s4 | 精选选题 11–20 |
| s5 | ESG传播商机 Top N |

选题卡片使用 `<details>` 展开参考链接，支持移动端响应式。

## 渠道配置

修改 `weekly_push.py` 顶部常量即可适配不同环境：

```python
WORKSPACE  = Path("/home/node/.openclaw/workspace")
RECIPIENT  = "yourname@company.com"
CHANNEL    = "hiredcity"   # 或 telegram/discord/slack 等
HTML_URL   = "http://your-server:18081/esg-weekly-push.html"
```

支持的 OpenClaw 渠道：hiredcity、telegram、discord、slack、whatsapp
