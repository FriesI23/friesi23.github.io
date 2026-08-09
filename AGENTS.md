# AGENTS.md — friesi23-blog (Jekyll 博客)

基于 GitHub Pages + Jekyll + Minimal Mistakes 主题的个人技术博客。

---

## 项目概述

- **仓库**: [FriesI23/friesi23.github.io](https://github.com/FriesI23/friesi23.github.io)
- **站点**: <https://play4fun.friesi23.cn> / <https://friesi23.icu>
- **分支**: `gh-pages`（默认分支，push 触发 CI/CD）

### 部署架构

```
读者 → 阿里云 Nginx (反向代理 + 缓存) → GitHub Pages (源站)
                                      ↓
                              GitHub Actions (构建 gh-pages 分支)
```

- Nginx 反向代理提供缓存加速，支持按 URL 精确清除缓存（`PURGE` 方法）
- CI 流程在部署后自动清除指定 URL 的缓存，并提交 Sitemap 到百度/必应

---

## 技术栈

- **引擎**: Jekyll 4.x (Ruby) + GitHub Pages
- **主题**: [Minimal Mistakes 4.28.0](https://mmistakes.github.io/minimal-mistakes/)
- **Ruby**: 3.2.2（见 `.ruby-version`）
- **Gem**: `github-pages ~>231`（锁定 GitHub Pages 兼容版本）
- **CI 脚本**: Python 3.12 + Poetry（见 `ci/pyproject.toml`）
- **分支**: `gh-pages`（默认分支，push 触发 CI/CD）

---

## 本地开发

```bash
# 安装依赖
bundle install

# 开发模式（使用本地 gem 主题，无需网络）
make serve

# 含草稿
make serve DRAFT=1

# 生产模式预览（使用 remote_theme）
make serve PROD=1

# 含草稿 + 生产模式
make serve PROD=1 DRAFT=1
```

**关键机制**：`_config.local.yml` 覆盖 `_config.yml`，在本地禁用 `remote_theme`、启用 `future: true`。
生产构建走 `JEKYLL_ENV=production`。

---

## 目录结构

```
blog/
├── _posts/<category>/     # 博文（按分类子目录）
│   ├── ai/                # AI 相关
│   ├── algorithm/         # 算法
│   ├── blog/              # 博客/建站
│   ├── dart/              # Dart 语言
│   ├── deploy/            # 部署运维
│   ├── flutter/           # Flutter
│   ├── misc/              # 杂项
│   ├── nas/               # NAS
│   ├── network/           # 网络
│   └── tools/             # 工具
├── _drafts/               # 草稿（--drafts 时可见）
├── _pages/                # 静态页面（首页、关于、404、监控等）
├── _data/                 # Jekyll 数据文件
│   ├── navigation.yml     # 导航栏
│   ├── authors.yml        # 作者信息
│   └── custom-text.yml    # 自定义文案
├── _includes/             # Liquid 片段（dartpad、github_gist 等）
├── _layouts/              # 自定义布局
├── _sass/                 # 自定义 SCSS
├── _prompts/              # AI Prompt 页面（Jekyll collection）
├── _scripts/              # JS 脚本源码
├── assets/                # 编译后的 CSS/JS/图片
├── ci/                    # CI 脚本（Python + Poetry）
├── templates/             # 文章模板
└── .github/workflows/     # GitHub Actions
    ├── jekyll.yml         # 构建 + 部署 + Sitemap 提交
    └── purge.yml          # 手动清除 Nginx 缓存
```

---

## 写新文章

1. 参考模板 `templates/post.md.template`
2. 在 `_posts/<category>/` 下创建文件
3. 文件名格式: `YYYY-MM-DD-标题slug.md`
4. 正文最高使用 `##`（H2），主题提供 H1

```yaml
---
title:  文章标题
author: FriesI23
date:   2024-01-01 08:00:00 +0800
category: blog
tags:   [tag1, tag2]
# excerpt: 可选摘要（用于列表页）
---
```

分类从以下选择: `ai`, `algorithm`, `blog`, `dart`, `deploy`, `flutter`, `misc`, `nas`, `network`, `tools`

---

## 多语言文章

部分文章提供多语言版本（中文原文 + 英文翻译）。使用独立布局 `single-multilang`，
通过 front matter 一处配置所有语言版本的 URL 和标签。

### 文件命名

- 中文版：`YYYY-MM-DD-slug.md`（默认语言，保持既有命名）
- 英文版：`YYYY-MM-DD-slug-en.md`（`-en` 后缀）

### URL 约定

- 中文版：走全局 permalink `/post/:year:month/:slug`，不添加 `/zh/` 前缀
- 英文版：`permalink: /post/en/:year:month/:slug` 覆盖 URL

### Front matter 配置

中文版（默认语言）：

```yaml
---
layout: single-multilang
lang: zh-CN
locale: zh-CN
translations:
  - lang: zh-CN
    url: /post/202608/slug
    label: 中文
  - lang: en
    url: /post/en/202608/slug
    label: English
---
```

英文版（翻译）：

```yaml
---
layout: single-multilang
lang: en
locale: en
permalink: /post/en/202608/slug
translations:
  - lang: zh-CN
    url: /post/202608/slug
    label: 中文
  - lang: en
    url: /post/en/202608/slug
    label: English
translation:
  note: "This article was translated by GitHub Copilot using the DeepSeek V4 Flash model."
---
```

- `lang` / `locale` 可省略，回退到 `site.locale`（zh-CN）
- `translations` 包含所有语言版本，当前语言高亮显示，其他为链接
- `translation.note`（仅翻译版本需要）：标注 AI 翻译来源，渲染在文章顶部

### 关键文件

| 文件 | 作用 |
|------|------|
| `_layouts/single-multilang.html` | 多语言文章布局（fork MM 4.28.0 single.html） |
| `_layouts/home.html` | 主页过滤非默认语言版本 + 语言指示器 |
| `_includes/post-translations.html` | 文章顶部语言切换条（pill 按钮） |
| `_includes/head/custom.html` | hreflang SEO 标签 |
| `_data/ui-text.yml` | `translations_label` 多语言 UI 文本 |
| `_sass/.../custom/_post_translations.scss` | 语言切换条 + 主页指示器样式 |
| `templates/post.md.template` | 含 `lang` / `locale` / `translations` 注释 |

---

## CI/CD

| 工作流 | 文件 | 触发 |
|--------|------|------|
| 构建部署 | `jekyll.yml` | push `gh-pages` / 手动 |
| 清除缓存 | `purge.yml` | 手动（支持按页面/JS 分别清除） |

- `jekyll.yml` 在构建后自动提交 Sitemap 到百度/必应，并清除 Nginx 反向代理缓存
- CI Python 脚本入口在 `ci/pyproject.toml`，使用 Poetry 管理依赖

---

## 自定义组件

| 功能 | 文件 |
|------|------|
| DartPad 嵌入 | `_includes/dartpad.html` |
| GitHub Gist 嵌入 | `_includes/github_gist.html` |
| Keep Android Open 横幅 | `_includes/keep-android-open-banner.html` |
| Prompt 下载链接 | `_includes/prompt-download-link.html` |
| 自定义侧边栏 | `_includes/sidebar-custom.html` |
| 多语言切换条 | `_includes/post-translations.html` |
| 语言指示器（主页） | `_layouts/home.html` |
| 多语言文章布局 | `_layouts/single-multilang.html` |

---

## 关键约定

- **Markdown 格式**: 行长度不强制（MD013 off），允许内联 HTML（MD033 off）
- **`.gitignore`**: `_site`、`.sass-cache`、`.jekyll-cache`、`vendor`、`.bundle` 不跟踪
- **Prompt 同步**: `make sync-prompts` 将 `_prompts/*.md` frontmatter 同步到 `assets/prompts/`
- **资源清除 URL**: `make gen-asset-purge-urls` 从 `_site/assets` 生成缓存清除 URL 列表

---

## 常见问题

| 问题 | 解决 |
|------|------|
| `remote_theme` 下载失败 | 用 `make serve`（默认使用 `_config.local.yml`） |
| Ruby 版本不匹配 | 检查 `.ruby-version`，用 `chruby` 切换 |
| 本地样式异常 | 确认 `_config.local.yml` 中 `theme: minimal-mistakes-jekyll` 且 gem 已安装 |
