---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 为 Nginx 反向代理配置缓存并在 Docker 中使用 ngx_cache_purge 模块
excerpt: |
  最近优化了一波博客的反代配置, 这里总结了一下. 主要为三个部分: 首先是更细致的 Nginx 缓存配置;
  中间主要为如何构建带有第三方 Module 的 Docker 镜像并进行配置; 最后简要说明了一下 ngx_cache_purge 的使用方法.
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
这篇文章在上面的基础上, 将更加细化配置缓存, 并在 Docker Compose 中配置 `ngx_cache_purge` 插件,
使我们可以使用 Plus 订阅中 `PURGE` 类似的功能.

先贴上优化后的 server 部分的配置, 后续会解释里面的配置:

```nginx
server {
    listen 443 default_server ssl;
    listen [::]:443 ssl;

    server_name friesi23.cn;

    ssl_prefer_server_ciphers on;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_certificate /etc/letsencrypt/live/friesi23.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/friesi23.cn/privkey.pem;

    access_log /var/log/nginx/friesi23cn.access.log;
    error_log /var/log/nginx/friesi23cn.error.log;
    proxy_redirect     off;
    proxy_set_header   Host                       play4fun.friesi23.cn;
    proxy_set_header   X-Real-IP                  $remote_addr;
    proxy_set_header   X-Forwarded-For            $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto          $scheme;
    proxy_set_header   User-Agent                 $custom_user_agent;

    add_header           Nginx-Cache                  "$upstream_cache_status";
    proxy_ignore_headers X-Accel-Expires Cache-Control Expires;

    proxy_cache        blog_cache;
    proxy_cache_lock on;
    proxy_cache_lock_age 1s;
    proxy_cache_lock_timeout 2s;
    proxy_cache_use_stale error timeout updating http_503;
    proxy_cache_key $scheme://$host$uri$is_args$query_string;
    proxy_cache_valid  200 206 304 301 302 1h;
    proxy_cache_valid  any 10m;
    proxy_cache_revalidate on;
    proxy_cache_background_update on;

    limit_req zone=anti_spider burst=2 nodelay;

    location ~* \.(js) {
        proxy_pass https://github-pages;

        proxy_cache_key jscache://$uri;
        proxy_cache_valid any 1d;
    }

    location ~ /purge(/.*) {
        allow       all;
        deny        all;
        proxy_cache_purge blog_cache $scheme://$host$1$is_args$query_string;
        access_log  /var/log/nginx/friesi23cn.cache.log;
    }

    location / {
        proxy_pass https://github-pages;
    }
}
```

## Cache 相关配置项

`proxy_cache` 开头的 key 便是 nginx 中缓存相关的配置.

### 配置项: proxy_cache_lock 相关

```nginx
proxy_cache_lock on;
proxy_cache_lock_age 1s;
proxy_cache_lock_timeout 2s;
```

`proxy_cache_lock` 主要用于防止多个请求同时向后端服务器发起相同请求, 从而避免后端服务器负载增加导致的 "缓存击穿".
开启后, 在没有缓存资源时, 只有第一个请求会去后端获取, 其他资源会等待直到缓存建立后从缓存返回数据.

`proxy_cache_lock_age` 设定如果一个请求没有在该配置设定限时内请求到数据并建立缓存, 则再放行一个请求去后端.

`proxy_cache_lock_timeout` 表示已经请求等待超过配置设定时间, 直接放行且**不缓存**返回内容.

### 配置项: proxy_cache_use_stale 与 proxy_cache_background_update

```nginx
proxy_cache_use_stale error timeout updating http_503;
proxy_cache_background_update on;
```

`proxy_cache_use_stale` 可以让服务器在匹配到配置内容的情况时, 允许使用陈旧的缓存进行响应.
比如配置 `updating` 可以在更新缓存时最大限度减少对代理服务器的访问请求次数.
可配置参数可以查阅 [Nginx - proxy_next_upstream][nginx-proxy_next_upstream].

`proxy_cache_background_update` 启用后, 在请求到达且数据需要更新时,
Nginx 会启动一个子程序后台进行更新, 并将缓存的旧数据作为此次请求的数据返回给客户端.

需要注意使用 `proxy_cache_background_update` 时候, 需要保证 `proxy_cache_use_stale` 有配置 `updating`.

### 配置项: proxy_cache_revalidate

```nginx
proxy_cache_revalidate on;
```

启用后会对 `If-Modified-Since` and `If-None-Match` 请求头进行验证, 如果没有变化则允许返回稍早过期的缓存而不是对后端发起新的请求.

### 头: Nginx-Cache

```nginx
add_header           Nginx-Cache                  "$upstream_cache_status";
```

新增了一个 Response Header `Nginx-Cache`, 可以方便在调试的时候查看客户端是否有命中缓存,
命中的话会在客户端的 Header 中表示为: `Nginx-Cache: Hit`, 否则为: `Nginx-Cache: Miss`

### 位置: js 相关文件

```nginx
location ~* \.(js) {
    proxy_pass https://github-pages;

    proxy_cache_key jscache://$uri;
    proxy_cache_valid any 1d;
}
```

针对一些请求的 `javascript` 脚本, 一般都不会进行变更, 因此可以将缓存的时间拉长一些,
如果脚本有更新可以使用 `purge` 进行缓存清理, 后续会说怎么编译配置并使用.

## ngx_cache_purge 模块

Nginx Plus 订阅中可以通过配置使用 `PURGE` 方法来手动清理缓存, 而我们也可以使用 `ngx_cache_purge` 模块达到类似的目的.

项目地址: [FRiCKLE/ngx_cache_purge][github-ngx_cache_purge]

该 module 并没有被官方集成, 因此我们需要自己将其编译到 Nginx 中.
不过 `Nginx` 在 `1.9.11` 后已经支持 `load_module` 来动态添加模块, 而 `Nginx` 官方镜像也支持我们通过构建自己的镜像来引入第三方模块.
因此下面会已 `构建` -> `运行` -> `配置` 的方式完成 `Nginx` 的部署.

### 构建

第一步, 我们需要通过 `docker-nginx` 的 [官方教程][docker-nginx-module-readme] 构建自己的镜像.
直接按官方教程操作或者下面的 Workflow 皆可.

```shell
# STEP1: Create Folder
# workdir: /
mkdir web
cd web
# workdir: /web
mkdir modules

# STEP2: Download DockerFile (1.27.2 or whatever)
# or master branch: https://raw.githubusercontent.com/nginxinc/docker-nginx/master/modules/Dockerfile
curl -o modules/Dockerfile https://raw.githubusercontent.com/nginxinc/docker-nginx/refs/tags/1.27.2/modules/Dockerfile

# STEP3: Add ngx_cache_purge module
mkdir modules/cache_purge
echo "https://github.com/FRiCKLE/ngx_cache_purge/archive/2.3.tar.gz" > modules/cache_purge/source

# STEP4: Create compose file
cat > compose.yaml << __EOF__
services:
  web:
    build:
      context: ./modules/
      platforms:
        - "linux/amd64"
        # - "linux/arm64"
      args:
        ENABLED_MODULES: cache_purge
    image: nginx-with-cachepurge:v1
__EOF__

# STEP5: build
docker compose build
# ....................................................
# $ docker images
# REPOSITORY              TAG               IMAGE ID       CREATED         SIZE
# nginx-with-cachepurge   v1                3f5b612e4ecd   0 minutes ago    193MB
```

至此我们已经构建好自己的带有 `ngx_cache_purge` 模块的镜像. 如果是在别处构建的镜像, 则需要将镜像打包导入到新机器.

> 注意镜像构筑的平台, 不要搞错了导致导入后无法运行

```shell
# STEP6: Export
# workdir: /web
mkdir export
docker save nginx-with-cachepurge -o export/nginx-with-cachepurge_v1.tar

# scp  export/nginx-with-cachepurge_v1.tar other-host:/path/to/store
# login to other-host
# STEP7: Import
cd /path/to/store
docker load -i nginx-with-cachepurge_v1.tar
# $ docker images
# REPOSITORY              TAG               IMAGE ID       CREATED         SIZE
# nginx-with-cachepurge   v1                3f5b612e4ecd   2 minutes ago    193MB
```

### 运行

首先需要使用 `load_module`, 由于该配置不能位于任何 block 中, 因此默认情况下需要修改顶层的 `/etc/nginx/nginx.conf` 文件.
注意不要直接进 Docker 修改, 而是使用挂载的方式生效配置 (可以启动一个默认的镜像并将里面的配置拷出来).

```shell
# workdir: /web
# Assume nginx.conf at ./nginx/nginx.conf
sed -i '1iload_module modules/ngx_http_cache_purge_module.so;' ./nginx/nginx.conf
```

> Build 镜像后编译好的 module 默认都在 /usr/lib/nginx/modules 中, 可以登录到容器内查看.
>
> ```shell
> root@230a7bce6cd4:/# ls -l /etc/nginx/modules
> lrwxrwxrwx 1 root root 22 Oct  2 15:59 /etc/nginx/modules -> /usr/lib/nginx/modules
> root@230a7bce6cd4:/# ls -l /etc/nginx/modules/ | grep purge
> -rw-r--r-- 1 root root   23224 Oct  9 10:59 /etc/nginx/modules/ngx_http_cache_purge_module-debug.so
> -rw-r--r-- 1 root root   23224 Oct  9 10:59 /etc/nginx/modules/ngx_http_cache_purge_module.so
> ```

然后在 `compose.yml` 中将 `image` 换成刚刚导入的镜像, 且挂载修改后的 `nginx.conf`.

```yaml
services:
  web:
    #image: nginx:latest
    image: nginx-with-cachepurge:v1
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    # Ignore other configs...
```

最后 `docker compose up web` 即可.

## 配置

```nginx
location ~ /purge(/.*) {
    #allow       all;
    allow       127.0.0.1;
    deny        all;
    proxy_cache_purge blog_cache $scheme://$host$1$is_args$query_string;
    access_log  /var/log/nginx/friesi23cn.cache.log;
}
```

没什么好说的, 注意 `proxy_cache_purge` 中配置需要清理缓存的 zone 与 key, 与缓存配置相同即可.
`allow 127.0.0.1; deny all;` 保证清理缓存不能被外界访问, 当然也可以给 location 搞一个复杂隐蔽的名字然后 `allow all`.

## 参考资料

1. [Nginx 学习笔记 (8) - 缓存加速指南 (proxy_cache)](https://www.app-scope.com/tutorial/configure-caching-with-nginx.html)
2. [如何在容器时代高效使用 Nginx 三方模块](https://soulteary.com/2021/03/22/how-to-use-nginx-third-party-modules-efficiently-in-the-container-era.html)
3. [Adding third-party modules to nginx official image](https://github.com/nginxinc/docker-nginx/blob/master/modules/README.md)
4. [Nginx - Module ngx_http_proxy_module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)

<!-- refs -->

[blog-github-page-proxy]: /post/202406/github-page-proxy
[nginx-proxy_next_upstream]: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_next_upstream
[github-ngx_cache_purge]: https://github.com/FRiCKLE/ngx_cache_purge
[docker-nginx-module-readme]: https://github.com/nginxinc/docker-nginx/blob/master/modules/README.md
