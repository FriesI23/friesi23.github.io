---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 使用 Nginx 代理 Github Page 并实现 HTTPS 访问
description: |
    由于国内访问 Github Pages 的不稳定性以及 Github 对百度爬虫的屏蔽, 导致博客在国内的访问体验不佳.
    本文介绍如何使用 Nginx 反向代理 Github Pages, 并配置 Let's Encrypt 证书，以解决这些问题.
author: FriesI23
date: 2024-06-24 09:00:00 +0800
category: blog
tags:
  - github
  - github-page
  - nginx
  - proxy
---

使用 Github Page 作为个人博客很好, 但是在国内访问时可能存在一问题. 首先是国内对于 github 访问不稳定导致对博客界面访问不稳定;
其次是 Github 对于百度爬虫的屏蔽, 导致百度爬虫无法正确访问. 因此在这里记录一下使用 Nginx 反向代理 Github Page 的方法,
包含 Let's Encrypt 证书申请的方法.

当然, 我个人只作为学习使用, 并没有将 Nginx 部署到海外服务器, 不过原理都是一样的.

## 前置准备

在一切开始前, 需要准备:

- 一台可以正常访问 Github 的服务器, 最好是海外的 (比如阿里云的海外机房), 这个机器用于部署 Nginx.
- 一个自己的域名.

服务器和域名都不在本文讨论之内, 可以自行查找相关文档找到购买方法.

这里假设已经申请到了一个顶级域名 `mydomain.com`, 且服务器为一台 `Debian 12` 且可以正常访问 Github 的虚拟机.

## 1. 安装 Docker

我们将 `Nginx` 和 `certbot` 都放在 docker compose 中, 后者用于自动申请加密证书.
先按照 [docker 官网教程][install-docker-engine]进行安装, 这里将安装命令进行简单 copy & paste, 已 debian 为例:

```shell
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```

```shell
# Install Docker compose
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

```shell
# Verify
sudo docker run hello-world
```

## 2. 配置 Docker Compose 文件

随便找一个空目录创建 一个 `compose.yml` 文件, 并键入以下内容:

```yaml
services:
  web:
    image: nginx:latest
    restart: always
    volumes:
      - ./nginx/conf:/etc/nginx/conf.d:ro # 我们的 nginx 配置放在这里
      - ./certbot/www/:/var/www/certbot/:ro
      - ./certbot/conf/:/etc/letsencrypt/:ro
      - /var/log/nginx-web/:/var/log/nginx/:rw # 日志映射
    ports:
      - 80:80
      - 443:443
    environment:
      - NGINX_PORT=80
  certbot:
    image: certbot/certbot:latest
    volumes:
      - ./certbot/www/:/var/www/certbot/:rw # cerbot 生成需要使用
      - ./certbot/conf/:/etc/letsencrypt/:rw # cerbot 生成的密钥文件目录
```

然后在 `./nginx/conf` 目录下新建一个文件 `50-mydomain.com.conf` 的文件, 这个文件名随意, 目录和上面 compose 文件中配置的目录相同即可.

编辑该文件并添加以下内容, 注意如果是新配置的话不要先配置 https 反向代理, 会导致 nginx 找不到 cert/key 文件而无法启动,
而 certbot 申请证书时需要使用 Nginx 进行代理:

```nginx
server {
    listen 80;
    listen [::]:80;

    server_name mydomain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        rewrite ^(.*) https://$server_name$1 permanent;
        return 301 https://mydomain.com;
    }
}
```

现在我们的目录结构应该是这样的:

```text
.
├── compose.yml
└── nginx
    └── conf
        └── 50-mydomain.com.conf
```

## 3. 申请证书

执行以下命令进行测试:

```shell
sudo docker compose run --rm  certbot certonly --webroot --webroot-path /var/www/certbot/ -d mydomain.com --agree-tos --renew-by-default --dry-run
```

后续一系列交互中, 按照提示进行确认后, 如果没有报错, 这可以输入下面命令正式进行申请,
可以将这个命令放入一个脚本中方便以后复用 (比如 `certbot_new.sh`):

```shell
sudo docker compose run --rm  certbot certonly --webroot --webroot-path /var/www/certbot/ -d mydomain.com --agree-tos --renew-by-default
```

同样执行后如果没有报错, 则说明证书已经申请成功, 此时目录结构应该是这样的:

```text
.
├── certbot
│   ├── conf
│   │   ├── accounts
│   │   ├── archive
│   │   ├── live
│   │   ├── renewal
│   │   └── renewal-hooks
│   └── www
├── certbot_new.sh
├── compose.yml
└── nginx
    └── conf
        └── 50-mydomain.com.conf
```

其中 `live` 目录中便包含前面申请的证书.

### 3.1. 重新申请证书

申请的证书有效期是 90 天, 证书过期后可以使用下面的命令重新申请证书:

```shell
sudo docker compose run --rm certbot renew
```

可以把这个命令放到 `crontab` 中定时执行, 即可实现自动化.

## 4. 配置反向代理

这里直接贴上配置, 相关配置都放在 `conf` 目录下:

```nginx
# file: 1-server.conf

# 对百度爬虫进行单独限速 Zone
limit_req_zone $anti_spider zone=anti_spider:60m rate=200r/m;
# 界面缓存配置 Zone
proxy_cache_path /var/cache/nginx/blog levels=1:2 keys_zone=blog_cache:10m max_size=1g inactive=1d use_temp_path=off;
```

扩展 `50-mydomain.com.conf` 文件, 加入 https 相关配置.

```nginx
# file: 50-mydomain.com.conf

# 定义 github page 对应的 ip, 使用 dig <你的github账户名>.github.io 获取对应的ip地址.
# 获取后将下面的ip地址进行替换.
upstream github-pages {
#  server 185.199.108.153:443;
#  server 185.199.109.153:443;
#  server 185.199.110.153:443;
#  server 185.199.111.153:443;
}

# 定义如何重新映射 User-Agent.
# 由于 github 对百度爬虫针对百度的 User-Agent 进行屏蔽, 因此这里只针对百度爬虫进行替换.
map $http_user_agent $custom_user_agent {
    default $http_user_agent;
    "~*baiduspider" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36";
}

# 定义是否需要使用限速, 这里只针对百度爬虫使用限速.
map $http_user_agent $anti_spider {
    default "";
    "~*baiduspider" $http_user_agent;
}

server {
    listen 80;
    listen [::]:80;

    server_name mydomain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        rewrite ^(.*) https://$server_name$1 permanent;
        return 301 https://mydomain.com;
    }
}

server {
    listen 443 default_server ssl;
    listen [::]:443 ssl;

    server_name mydomain.com;

    ssl_prefer_server_ciphers on;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_certificate /etc/letsencrypt/live/mydomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mydomain.com/privkey.pem;

    access_log /var/log/nginx/mydomain.com.access.log;
    error_log /var/log/nginx/mydomain.com.error.log;

    location / {
        proxy_pass https://github-pages;

        # 反向代理配置
        proxy_redirect     off;
        # 这里需要替换为自己的 github page url
        proxy_set_header   Host                       your.github.io;
        proxy_set_header   X-Real-IP                  $remote_addr;
        proxy_set_header   X-Forwarded-For            $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto          $scheme;
        # 这里使用替换后的 User-Agent
        proxy_set_header   User-Agent                 $custom_user_agent;

        # 缓存配置
        proxy_cache        blog_cache;
        proxy_cache_key    $uri;
        proxy_cache_valid  200 206 304 301 302 2d;
        proxy_cache_valid  any 1d;

        # 限速配置
        limit_req zone=anti_spider burst=2 nodelay;
    }
}
```

### 4.1. proxy_pass 配置

`proxy_pass` 需要使用 github page url 对象的 ip 进行访问, 而不是 github 提供的域名.
我们可以简单认为 github 本身也是一个 nginx, 比如访问 `someone.github.io` 时,
github 其实是根据这个域名进行路由, 已实现少量 ip 提供大量域名. 因此我们需要使用 ip 访问而不是域名, 不然 github 无法进行正确路由.

在配置 nginx 的服务器上使用 `dig` 命令已获取 github 为该域名分配的 ip, 比如:

```shell
$ dig friesi23.github.io

; <<>> DiG 9.18.24-1-Debian <<>> friesi23.github.io
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 33620
;; flags: qr rd ra; QUERY: 1, ANSWER: 4, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;friesi23.github.io.            IN      A

;; ANSWER SECTION:
friesi23.github.io.     10      IN      A       185.199.109.153
friesi23.github.io.     10      IN      A       185.199.108.153
friesi23.github.io.     10      IN      A       185.199.111.153
friesi23.github.io.     10      IN      A       185.199.110.153

;; Query time: 36 msec
;; SERVER: 100.100.2.136#53(100.100.2.136) (UDP)
;; WHEN: Mon Jun 24 15:32:58 CST 2024
;; MSG SIZE  rcvd: 100
```

将上面获取的 ip 配置到 nginx 中即可.

### 4.2. 缓存相关

```nginx
proxy_cache_path /var/cache/nginx/blog levels=1:2 keys_zone=blog_cache:10m max_size=1g inactive=1d use_temp_path=off;

proxy_cache        blog_cache;
proxy_cache_key    $uri;
proxy_cache_valid  200 206 304 301 302 2d;
proxy_cache_valid  any 1d;
```

以上配置可以减轻服务器向 github 请求的压力, 如果不需要可以注释这些块. 如启用后可以在请求时查看是否有命中缓存:

![proxy](https://github.com/FriesI23/friesi23.github.io/assets/20661034/b548274e-3f62-40f3-801d-d9dcb3534f46) {: width="800" }

### 4.3. host 相关

```nginx
proxy_set_header   Host                       your.github.io;
```

其实如果已经有了自己的 domain, 我们便可以使用自己的二级域名而不是 github 提供的默认域名,
具体可以看 github 中的[相关教程][github-custom-domain], 需要注意顶级域名与二级域名之间配置的区别.

配置完成后将 `Host` 配置修改为:

```nginx
proxy_set_header   Host                       blog.mydomain.com;
```

## 5. 最终检查

1. 记得将自己域名的 `A记录` 指向这台配置 nginx 的服务器, 怎样配置需要咨询购买域名的服务提供商.
2. 开启 `80`, `443` 端口, 如果使用的国内服务器的话可能需要备案.

## 6. 启动服务

```shell
sudo docker compose up web
```

THAT'S ALL! 经过上面步骤, 我们便可以使用 `mydomain.com` 进行访问. 如果访问存在问题, 可以查看 nginx 日志看看是哪里出问题.

以下是我个人最终的目录结构:

```shell
.
├── certbot
│   ├── conf
│   │   ├── accounts
│   │   ├── archive
│   │   ├── live
│   │   ├── renewal
│   │   └── renewal-hooks
│   └── www
├── certbot_new.sh
├── certbot_renew.sh
├── compose.yml
└── nginx
    └── conf
        ├── 1-server.conf
        └── 50-friesi23.cn.conf
```

## 一些参考资料

- [How to Set Up letsencrypt with Nginx on Docker](https://phoenixnap.com/kb/letsencrypt-docker)
- [nginx-代理/转发-GitHub Pages 静态页面博客](https://last2win.com/2020/03/16/github-pages-nginx-cdn-proxy/)
- [nginx针对爬虫进行限速配置](https://blog.csdn.net/weixin_33857230/article/details/91547812)

<!-- refs -->

[install-docker-engine]: https://docs.docker.com/engine/install/debian/
[github-custom-domain]: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
