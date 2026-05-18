# esg-weekly-push-skill

> An OpenClaw Agent Skill that auto-generates weekly ESG topic briefs for C-level audiences.

每周自动生成面向 CEO/CMO 的 ESG 选题速递，输出精美 HTML 页面，支持内网访问 + GitHub Pages 公网发布。

## 功能

- 🔍 自动搜索过去7天商业热点（新能源/供应链/大消费等）
- 📝 生成20条 C-level 视角选题 + 10条传播商机
- 🎨 渲染为精美 HTML 周报页面
- 🌐 自动同步到 GitHub Pages 公网链接
- 📬 每周一自动推送通知

## 文件结构

```
├── SKILL.md                          # Skill 主文件（安装说明 + Cron Prompt）
├── scripts/
│   ├── render_html.py                # JSON → HTML 渲染器
│   └── weekly_push.py                # 完整推送流程
├── assets/
│   └── esg-content-data-example.json # 数据结构示例
└── references/
    ├── editorial-framework.md        # 选题框架完整版
    └── setup.md                      # 安装与保活配置
```

## 快速开始

详见 [SKILL.md](./SKILL.md)

## Live Demo

https://sunpeichun4092-crypto.github.io/esg-weekly/

