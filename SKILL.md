---
name: esg-weekly-push
description: 每周一 09:00 CST 自动推送 ESG 周选题速递 HTML 链接。为「着陆TouchBase」ESG 叙事咨询公司（Cindy 主理）生成面向 C-level 的 20 条商业视角选题 + 10 条传播商机。触发词：ESG周推送、ESG选题、每周ESG、esg-weekly-push、帮我生成ESG选题。
---

# ESG Weekly Push Skill v3.1

## 核心设计

**LLM 只输出 JSON，不直接写 HTML。** HTML 由 `render_html.py` 渲染，节省 ~70% output token，避免超时。

## 新环境安装（5步）

### 1. 复制文件
```bash
WORKSPACE=~/workspace  # 改成你的工作区路径
mkdir -p $WORKSPACE/esg-daily-topics/output
cp scripts/render_html.py $WORKSPACE/esg-daily-topics/render_html.py
cp scripts/weekly_push.py $WORKSPACE/esg-daily-topics/weekly_push.py
cp assets/esg-content-data-example.json $WORKSPACE/esg-daily-topics/esg-content-data.json
```

### 2. 首次渲染 HTML
```bash
python3 $WORKSPACE/esg-daily-topics/render_html.py \
  $WORKSPACE/esg-daily-topics/esg-content-data.json \
  $WORKSPACE/esg-weekly-push.html
```

### 3. 启动 HTTP 服务（端口 18081）
```bash
nohup python3 -m http.server 18081 --directory $WORKSPACE > /tmp/http18081.log 2>&1 &
```
> 或用 keep-http.sh + cron 保活，见 references/setup.md

### 4. 注册 Cron Job
用 `cron` tool 新增 job：
- schedule: `{ "kind": "cron", "expr": "0 1 * * 1", "tz": "Asia/Shanghai" }`
- sessionTarget: `isolated`
- payload.timeoutSeconds: `600`
- payload.message: 见下方「Cron Prompt」

### 5. 修改配置常量
编辑 `weekly_push.py` 顶部：
```python
WORKSPACE  = Path("/home/node/.openclaw/workspace")  # 改成你的路径
RECIPIENT  = "sunpeichun@xiaohongshu.com"             # 改成接收人
CHANNEL    = "hiredcity"                               # 改成你的渠道
HTML_URL   = "http://10.40.21.103:18081/esg-weekly-push.html"  # 改成你的 URL
```

### 6. 配置 GitHub Pages（公网访问，可选）
让每期页面自动同步到公网链接，外部可直接访问。

**前置步骤：**
1. 在 [github.com/settings/tokens/new](https://github.com/settings/tokens/new) 生成 PAT，勾选 `repo` 权限
2. 用 GitHub API 创建 repo 并开启 Pages：
```bash
TOKEN="ghp_xxx"
USER="your-github-username"
REPO="esg-weekly"

# 创建 repo
curl -s -X POST -H "Authorization: token $TOKEN" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO\",\"private\":false,\"auto_init\":false}"

# 上传初始 HTML
SHA=""  # 首次上传不需要 SHA
CONTENT=$(base64 -w 0 /path/to/esg-weekly-push.html)
curl -s -X PUT -H "Authorization: token $TOKEN" \
  https://api.github.com/repos/$USER/$REPO/contents/index.html \
  -d "{\"message\":\"init\",\"content\":\"$CONTENT\"}"

# 开启 GitHub Pages
curl -s -X POST -H "Authorization: token $TOKEN" \
  https://api.github.com/repos/$USER/$REPO/pages \
  -d '{"source":{"branch":"main","path":"/"}}'
```
3. 约 1-2 分钟后公网链接生效：`https://<USER>.github.io/<REPO>/`

---

## Cron Prompt（每周一触发的 agentTurn）

```
执行ESG周推送。读 memory/esg-editorial-framework.md 了解框架。

**步骤1：搜商业热点**
web_search 搜索过去7-15天4类真实商业大事件（禁止直接搜ESG）：
- 新能源/动力电池出海/碳关税/数字护照
- 大型制造业/汽车新能源转型/财报
- AI数据中心/绿色算力/减碳
- 大消费/绿色供应链政策

**步骤2：生成内容 JSON**
套用三公式(A/B/C)，严格输出以下结构，用 write tool 写入 `esg-daily-topics/esg-content-data.json`：
（格式见 assets/esg-content-data-example.json）
- date: 本周日期
- subtitle: 4个热点关键词用·连接
- events: 6条真实热议，含url/title/desc/src
- topics: 20条选题，每条含n/title/hook/tags/stars/links
- biz: 10条商机，每条含n/priority/name/desc/trigger

禁止：ESG报告通稿/种树捐款/无业务落地的学术黑话

**步骤3：渲染HTML**
exec 执行：`python3 <WORKSPACE>/esg-daily-topics/render_html.py`

**步骤4：推送到 GitHub Pages（如已配置）**
exec 执行以下命令，将最新 HTML 同步到公网：
```bash
TOKEN="<GITHUB_PAT>"
USER="<GITHUB_USER>"
REPO="<GITHUB_REPO>"
FILE="<WORKSPACE>/esg-weekly-push.html"

SHA=$(curl -s -H "Authorization: token $TOKEN" \
  https://api.github.com/repos/$USER/$REPO/contents/index.html \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")

CONTENT=$(base64 -w 0 $FILE)
WEEK=$(date +%Y-%m-%d)
curl -s -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$USER/$REPO/contents/index.html \
  -d "{\"message\":\"update ESG weekly $WEEK\",\"content\":\"$CONTENT\",\"sha\":\"$SHA\"}"
```

**步骤5：发送**
message工具发送给 <RECIPIENT>（<CHANNEL>渠道），同时附上内网版和公网版链接：
- 内网版：<HTML_URL>
- 公网版：https://<GITHUB_USER>.github.io/<GITHUB_REPO>/
```

---

## 选题生成规范

- **读者定位**：上市公司董事长/CEO/CMO/战略负责人，极度务实
- **核心基调**：可持续发展是门好生意，不脱离商业逻辑
- **工作流**：先搜商业热点（不直接搜"ESG"）→ 套三公式 → 输出含5要素的选题
- **三公式**：A=SDG+供应链成本 / B=人文关怀S+组织效能 / C=气候E+新增收引擎
- **雷区**：ESG报告通稿 / 种树捐款软文 / 学术黑话
- **选题5要素**：触发热点(含时间) + 切入点 + 对标企业 + 真实链接 + C-level启发

完整框架见 `references/editorial-framework.md`

---

## 商机优先级规则

| 颜色 | 级别 | 标准 |
|------|------|------|
| 🔴 | 最优先 | 已有合作信号，本月可闭环 |
| 🟠 | 高优 | 近期触发事件强+决策周期短 |
| 🟢 | 跟进 | 匹配度高但需建立联系 |
| 🔵 | 观察 | 长线布局 |

目标客户画像：制造/供应链/新能源/大消费，有真实ESG实践但缺叙事能力。

---

## 文件结构

```
esg-weekly-push/
├── SKILL.md
├── scripts/
│   ├── render_html.py        # JSON → HTML 渲染器（主要）
│   └── weekly_push.py        # 完整推送流程（含 RedBI 热词拉取）
├── assets/
│   └── esg-content-data-example.json  # 标准 JSON 数据结构示例
└── references/
    ├── editorial-framework.md  # 《Touch》选题框架完整版
    └── setup.md                # 详细安装与保活配置
```

## 手动触发推送

已安装后，手动触发一次推送：
```bash
# 方法1：直接跑推送脚本（不发消息，只生成 HTML）
python3 ~/workspace/esg-daily-topics/render_html.py

# 方法2：用 cron tool 立即触发 cron job
openclaw cron run <job-id>
```

## 当前部署配置（sunpeichun）

| 配置项 | 值 |
|---|---|
| GitHub 账号 | sunpeichun4092-crypto |
| GitHub Repo | esg-weekly |
| 公网链接 | https://sunpeichun4092-crypto.github.io/esg-weekly/ |
| 内网链接 | http://10.40.22.208:18081/esg-weekly-push.html |
| Cron Job ID | c37f5e94-2d39-4a59-80fd-00c8e8e03faa |
| 推送时间 | 每周一 01:00 CST |

> GitHub PAT 存储在 Cron Job payload 中，有效期30天，到期需在 github.com/settings/tokens 重新生成并更新 Cron Job。

## 版本历史

| 版本 | 变更 |
|---|---|
| v3.1 | 新增 GitHub Pages 公网发布步骤，Cron 自动同步 |
| v3.0 | LLM 只输出 JSON，HTML 由 render_html.py 渲染 |
