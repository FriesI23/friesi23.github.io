---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 为 Nginx 反向代理配置 Cache
excerpt:
author: FriesI23
date: 2024-10-10 14:00:00 +0800
category: blog
tags:
  - blog
  - nginx
  - nginx-cache
---

在 [**使用 Nginx 代理 Github Page 并实现 HTTPS 访问**][blog-github-page-proxy] 中,
我们配置了一个为 Github Page 加速的 Nginx 服务, 并且加上了一些简单的缓存.
这篇文章在上面的基础上, 将更加细化配置缓存, 并配置插件使我们可以使用 Plus 版中 PURGE 类似的功能.

<!-- refs -->

[blog-github-page-proxy]: /post/202406/github-page-proxy
