---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: OpenWrt 23.05 配置 WireGuard VPN 服务器指南及避坑
excerpt: |
  路由器 OpenVPN 证书到期后决定换成 WireGuard，记录在 OpenWrt 23.05 上配置 WireGuard 服务器的全过程及踩过的坑。
  内容包括安装、服务端与客户端配置、防火墙独立区域方案，以及常见排错。
author: FriesI23
date: 2026-06-10 08:00:00 +0800
category: network
tags:
  - openwrt
  - wireguard
  - vpn
  - network
---

## 前言

最近路由器上的 OpenVPN 证书到期了。

续签的时候突然意识到：维护一整套 PKI 证书体系对于家庭 VPN 场景来说实在有些过重——既要管 CA，又要管客户端证书吊销，过期了还得记得手动续签。
作为家庭环境，真的没必要搞得这么复杂。

我很懒，因此决定换成 WireGuard。理由很简单：

- WireGuard 现在已经足够成熟，主流平台（Android、iOS、Windows、macOS、Linux）都有官方或社区维护的客户端
- 连接体验比 OpenVPN 轻快不少
- 代码量少、易于审计，而且本身就是 FOSS（GPLv2），正合我意

故在这里简单记录一下在 OpenWrt 23.05 上配置 WireGuard 服务器的过程，以及踩过的几个坑。

## 1. 环境说明

- OpenWrt 版本：23.05
- WireGuard 相关包：`wireguard`、`wireguard-tools`、`kmod-wireguard`
- 路由器型号：FriendlyElec NanoPi R6S

## 2. 安装 WireGuard

```bash
opkg update
opkg install wireguard wireguard-tools kmod-wireguard
```

> **踩坑提醒：谨慎安装 `wg-installer-server`**
>
> 在 OpenWrt 上部署 WireGuard 时，我曾安装 `wg-installer-server` 来简化配置，
> 但后续遇到了比较难排查的问题：
>
> - `wg0` 接口最初工作正常；
> - WireGuard 路由能够正确创建；
> - 运行一段时间后，`wg0` 接口和相关路由会被自动删除；
> - VPN 连接随之失效；
> - 问题表现得像是 WireGuard 配置错误，但实际上并非如此。
>
> 排查后发现，问题并不在 WireGuard 本身，
> 而是在 `wg-installer-server` 附带的自动化管理逻辑。
> 该软件包除了生成配置外，还会安装额外的 hotplug 脚本，
> 并可能与动态路由组件（如 Babel、OLSR 等）产生交互，
> 从而自动修改网络配置。
>
> 对于普通家庭 VPN、自建回家网络等场景，
> **强烈建议**直接使用以下三个包即可：
>
> - `kmod-wireguard`
> - `wireguard-tools`
> - `luci-proto-wireguard`（如需 LuCI 界面管理）
>
> 尽量避免引入额外的自动化管理层。
> 如果遇到 WireGuard 配置明明正确，
> 但接口或路由会被自动修改、删除的情况，
> 可以优先检查是否安装了 `wg-installer-server` 或类似的一键安装工具。

## 3. 配置 WireGuard 服务端

### 3.1. 创建接口配置

编辑 `/etc/config/network`，添加 WireGuard 接口配置。
以下以 LuCI 界面操作和 `uci` 命令行两种方式说明。

#### 通过 LuCI 界面配置

1. 进入 **网络** → **接口** → **新建接口**
2. 接口名称填 `wg0`，接口类型选 **WireGuard VPN**
3. **常规设置**下填写以下参数：

   [![接口/wg0/常规设置][ref-pic-01]{:height="600"}][ref-pic-01]

   | 参数       | 说明                               | 示例值               |
   | ---------- | ---------------------------------- | -------------------- |
   | 私钥       | 点击 "生成新的密钥对"              | `<YOUR_PRIVATE_KEY>` |
   | 公钥       | 点击 "生成新的密钥对"              | `<YOUR_PUBLIC_KEY>`  |
   | 监听端口   | WireGuard 服务监听的 UDP 端口      | `51820`              |
   | IP 地址    | 服务端在 WireGuard 虚拟网络中的 IP | `10.0.1.1/24`        |
   | 无主机路由 | 不添加主机路由，服务器下不要勾选   |                      |

4. **防火墙设置**下区域选择 `lan`：

   [![接口/wg0/防火墙设置][ref-pic-02]{:height="600"}][ref-pic-02]

   > **可选**：如需对 VPN 流量做更精细的防火墙控制，
   > 可暂不将 `wg0` 加入 `lan` 区域，转而在第 4 节创建独立的防火墙区域。

#### 通过 `uci` 命令行配置

```bash
# 1. 生成 WireGuard key 并写入文件（可选保留）
umask 077
wg genkey | tee /etc/wireguard/wg0_private.key | wg pubkey > /etc/wireguard/wg0_public.key

# 2. 读取 private key 并直接写入 UCI
PRIVATE_KEY=$(cat /etc/wireguard/wg0_private.key)

uci set network.wg0=interface
uci set network.wg0.proto='wireguard'
uci set network.wg0.listen_port='51820'
uci set network.wg0.private_key="$PRIVATE_KEY"
uci set network.wg0.addresses='10.0.1.1/24'

# 3. 防火墙：加入 LAN 区域（关键）
#    如需独立防火墙区域，可跳过此步，转至第 4 节配置
LAN_ZONE=$(uci show firewall | grep "=zone" | grep "name='lan'" | cut -d. -f2 | cut -d= -f1)

uci add_list firewall.$LAN_ZONE.network='wg0'

# 4. 应用配置
uci commit network
uci commit firewall

/etc/init.d/network restart
/etc/init.d/firewall restart
```

> **注意**：WireGuard 虚拟接口的 IP 地址段**不要**与服务端所在局域网同网段，
> 否则会导致路由冲突，客户端无法正常访问内网资源。详见后文的[坑点说明](#8-关键坑点)。

### 3.2. 启动服务

```bash
ifdown wg0 && ifup wg0
```

重启接口后，可以通过以下命令验证接口是否正常工作：

```bash
wg show
```

正常输出应类似如下：

```text
interface: wg0
  public key: <SERVER_PUBLIC_KEY>
  private key: (hidden)
  listening port: 51820
```

## 4. 防火墙配置（可选：独立区域方案）

> **默认方案已够用**
>
> 在上文第 3 节中，我们已将 `wg0` 加入 `lan` 防火墙区域——
> 对于大多数家庭 VPN 场景，这已经足够：客户端可以正常访问内网和外网。
>
> 本节提供一个可选的高级方案：为 WireGuard 创建独立的防火墙区域。
> 该方案参考了 [upsangel 的文章][ref-upsangel]，
> 适合需要对 VPN 流量做更精细控制（如限制访问范围、独立日志等）的场景。
> 如果默认方案工作正常，可以跳过本节。
>
> **注意**：如果采用独立区域方案，需要将第 3 节中将 `wg0` 加入 `lan` 区域的配置移除，
> 否则 `wg0` 会同时属于两个区域，可能导致规则冲突。

---

下面将介绍独立区域方案的配置方法。
该方案共需配置三个部分：

| 步骤 | 位置          | 作用                                               |
| ---- | ------------- | -------------------------------------------------- |
| 1    | Zone Settings | 创建 wireguard 区域，打通 wireguard ↔ lan 双向转发 |
| 2    | Port Forward  | 将 WAN 口 UDP 51820 映射到路由器本机               |
| 3    | Traffic Rule  | 放行 WAN 入站的 UDP 51820 流量                     |

### 4.1. 通过 LuCI 界面配置

1. 进入 **网络** → **防火墙** → **区域**，新建 `wireguard` 区域

   [![防火墙/常规][ref-pic-03]{:height="600"}][ref-pic-03]
   1. 将 `wg0` 接口分配给该区域
   2. 输入 / 输出 / 转发策略均设为 **接受（Accept）**
   3. 启用 **MSS 钳制（MSS Clamping / mtu_fix）** 以避免分片导致的连接不稳定
   4. 添加转发规则：`wireguard → lan` 以及 `lan → wireguard`

2. 进入 **网络** → **防火墙** → **端口转发**，新建 `wireguard` 规则：

   [![防火墙/端口转发][ref-pic-04]{:height="600"}][ref-pic-04]

   | 字段     | 值                                       |
   | -------- | ---------------------------------------- |
   | 名称     | `wireguard`                              |
   | 协议     | `UDP`                                    |
   | 源区域   | `wan`                                    |
   | 外部端口 | `51820`                                  |
   | 目标区域 | `lan`                                    |
   | 内部 IP  | `192.168.1.1`（替换为路由器实际 LAN IP） |
   | 内部端口 | `51820`                                  |

3. 进入 **网络** → **防火墙** → **通信规则**，新建 `Allow-WireGuard` 规则：

   [![防火墙/通信规则][ref-pic-05]{:height="600"}][ref-pic-05]

   | 字段     | 值                |
   | -------- | ----------------- |
   | 名称     | `Allow-WireGuard` |
   | 协议     | `UDP`             |
   | 源区域   | `wan`             |
   | 目标区域 | `设备（输入）`    |
   | 目标端口 | `51820`           |
   | 动作     | `接受`            |

### 4.2. 通过 `uci` 命令行配置

没什么好说的，直接上命令：

```bash
# 第 1 步 — 创建 WireGuard 专属防火墙区域（Zone Settings）
uci add firewall zone
uci set firewall.@zone[-1].name='wireguard'
uci add_list firewall.@zone[-1].network='wg0'
uci set firewall.@zone[-1].input='ACCEPT'
uci set firewall.@zone[-1].output='ACCEPT'
uci set firewall.@zone[-1].forward='ACCEPT'
uci set firewall.@zone[-1].mtu_fix='1'

# 允许 wireguard ↔ lan 双向转发
uci add firewall forwarding
uci set firewall.@forwarding[-1].src='wireguard'
uci set firewall.@forwarding[-1].dest='lan'

uci add firewall forwarding
uci set firewall.@forwarding[-1].src='lan'
uci set firewall.@forwarding[-1].dest='wireguard'

# 第 2 步 — 将 WAN UDP 51820 映射到本机（Port Forward）
uci add firewall redirect
uci set firewall.@redirect[-1].name='wireguard'
uci set firewall.@redirect[-1].src='wan'
uci set firewall.@redirect[-1].proto='udp'
uci set firewall.@redirect[-1].src_dport='51820'
uci set firewall.@redirect[-1].dest='lan'
uci set firewall.@redirect[-1].dest_ip='192.168.1.1'   # 替换为路由器实际 LAN IP
uci set firewall.@redirect[-1].dest_port='51820'
uci set firewall.@redirect[-1].target='DNAT'

# 第 3 步 — 放行 WAN 入站 UDP 51820（Traffic Rule）
uci add firewall rule
uci set firewall.@rule[-1].name='Allow-WireGuard'
uci set firewall.@rule[-1].src='wan'
uci set firewall.@rule[-1].proto='udp'
uci set firewall.@rule[-1].dest_port='51820'
uci set firewall.@rule[-1].target='ACCEPT'

# 提交并重启防火墙
uci commit firewall
/etc/init.d/firewall restart
```

---

至此，独立区域方案的配置就完成了。流量路径如下：

```text
外网客户端
  → WAN UDP 51820
  → Traffic Rule 放行
  → Port Forward 映射到本机
  → wg0 接口处理 WireGuard 握手
  → Zone Forwarding 打通 wireguard ↔ lan
  → 访问 192.168.1.x 内网设备
```

## 5. 配置 WireGuard 客户端

下面介绍两种为客户端生成配置的方式：通过 LuCI 界面（适合快速导出二维码）和通过 `uci` 命令行。
两种方式最终都会得到一份客户端可用的 `.conf` 配置。

### 5.1. 通过 LuCI 界面配置

1. 进入 **网络** → **接口** → `wg0` → **对端配置**
2. 点击 **添加对端**，填写以下参数：

   [![接口/wg0/编辑对端][ref-pic-06]{:height="600"}][ref-pic-06]

   | 参数          | 说明                                                                 | 示例值                 |
   | ------------- | -------------------------------------------------------------------- | ---------------------- |
   | 描述          | 客户端设备标识                                                       | `my-phone`             |
   | 公钥          | 客户端的 WireGuard 公钥；也可点击 "生成新的密钥对" 由路由器代为生成  | `<CLIENT_PUBLIC_KEY>`  |
   | 私钥          | 若需导出完整配置给客户端使用，需填入客户端私钥；导出完成后可删除此项 | `<CLIENT_PRIVATE_KEY>` |
   | 预共享密钥    | 额外一层对称加密（后量子安全增强）；可点击 "生成" 自动生成           | `<PRESHARED_KEY>`      |
   | 允许的 IP     | 客户端在 WireGuard 网络中的 IP 地址                                  | `10.0.1.2/32`          |
   | 路由允许的 IP | 勾选后客户端可访问路由器上的其他网段（如 `lan`）                     | 勾选                   |
   | 持久保活      | 保持连接活跃，穿 NAT 时有用                                          | `25`                   |

   > **提示**：若客户端尚无任何配置，推荐直接在路由器上点击 "生成新的密钥对" 代为生成密钥，
   > 这样可避免在客户端手动执行命令。

3. 保存后点击底部的 **生成配置** 按钮，系统将弹出一个二维码界面。
   打开手机上的 WireGuard App，选择 "扫描二维码" 即可快速导入配置。

   [![接口/wg0/编辑对端/生成配置][ref-pic-07]{:height="600"}][ref-pic-07]

   > **注意**：每个客户端设备需要单独添加一个对端参数，不能多个设备共用同一组密钥。
   > 导入配置后，建议返回对端配置界面将 "私钥" 字段清空，以免敏感信息留在路由器配置中。

### 5.2. 通过 `uci` 命令行配置

```bash
# 1. 生成客户端密钥对
umask 077
wg genkey | tee /etc/wireguard/client_private.key | wg pubkey > /etc/wireguard/client_public.key

# 2. 读取客户端公钥
CLIENT_PUBLIC_KEY=$(cat /etc/wireguard/client_public.key)

# 3. 在 wg0 接口下添加对端（Peer）
uci add network wireguard_wg0
uci set network.@wireguard_wg0[-1].description='my-phone'
uci set network.@wireguard_wg0[-1].public_key="$CLIENT_PUBLIC_KEY"
uci set network.@wireguard_wg0[-1].allowed_ips='10.0.1.2/32'
uci set network.@wireguard_wg0[-1].route_allowed_ips='1'
uci set network.@wireguard_wg0[-1].persistent_keepalive='25'

# 4. 生成预共享密钥（可选，但推荐）
PRESHARED_KEY=$(wg genpsk)
uci set network.@wireguard_wg0[-1].preshared_key="$PRESHARED_KEY"

# 5. 应用配置
uci commit network
/etc/init.d/network restart
```

若需手动生成客户端 `.conf` 文件（例如通过 SCP 传给客户端），可参考以下模板：

```bash
cat > /tmp/wireguard-client.conf <<'EOF'
[Interface]
PrivateKey = <CLIENT_PRIVATE_KEY>
Address = 10.0.1.2/32
DNS = 10.0.1.1

[Peer]
PublicKey = <SERVER_PUBLIC_KEY>
PresharedKey = <PRESHARED_KEY>
Endpoint = <YOUR_SERVER_DOMAIN_OR_IP>:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
```

配置项说明：

| 字段                  | 说明                                                                    |
| --------------------- | ----------------------------------------------------------------------- |
| `PrivateKey`          | 客户端私钥                                                              |
| `Address`             | 客户端在 WireGuard 网络中的 IP，需与服务端 Peer 配置一致（推荐 `/32`）  |
| `DNS`                 | 可选，填写后可通过 VPN 解析内网域名                                     |
| `PublicKey`           | 服务端公钥                                                              |
| `PresharedKey`        | 预共享密钥，额外对称加密层（可选，但推荐）                              |
| `Endpoint`            | 服务端公网地址和端口                                                    |
| `AllowedIPs`          | `0.0.0.0/0` 表示所有流量走 VPN；如只需访问内网，可改为 `192.168.1.0/24` |
| `PersistentKeepalive` | 保持连接活跃，穿 NAT 时有用（秒）                                       |

### 5.3. 连接测试

配置导入客户端后，启用连接并执行以下验证：

```bash
# 查看路由表，确认流量经过 wg0
ip route get 8.8.8.8

# 测试内网访问
ping 192.168.1.1

# 测试外网访问
ping 8.8.8.8
```

同时在路由器端检查 WireGuard 状态：

```bash
# 查看接口及 Peer 信息
wg show

# 查看接口详情
ip addr show wg0

# 查看路由表
ip route show
```

`wg show` 的输出能直接反映客户端连接状态及传输流量，是验证配置是否生效的最快方式。

## 6. 客户端链接配置

服务端配置完成后，下面介绍在 Android 和 macOS 上配置 WireGuard 客户端的方法。

### 6.1. Android

Android 端推荐使用 WireGuard 官方 App（[Google Play](https://play.google.com/store/apps/details?id=com.wireguard.android) / [F-Droid](https://f-droid.org/en/packages/com.wireguard.android/)）。

1. 安装 WireGuard App 后，点击右下角 `+` 号
2. 选择 **从二维码扫描** 或 **从本地文件导入**
   - 若使用 LuCI 界面配置（第 5.1 节），可直接扫描路由器生成的二维码
   - 若使用命令行配置（第 5.2 节），将 `.conf` 文件传至手机后选择导入
3. 导入后点击右上角开关启用连接
   - [![wireguard-android][ref-pic-08]{:width="300"}][ref-pic-08]

> **提示**：Android 10 及以上版本支持 WireGuard 作为系统级 VPN，
> 连接后所有流量（包括其他 App）都会经过 VPN 隧道。
> 若只需部分流量走 VPN，可在 App 设置中调整 `AllowedIPs`。

### 6.2. macOS

macOS 端推荐使用 WireGuard 官方客户端（[App Store](https://apps.apple.com/us/app/wireguard/id1441195209)）。

1. 从 App Store 安装 WireGuard
2. 打开 App，点击左下角 `+` 号
3. 选择 **导入隧道接口…**
   - 从路由器导出 `.conf` 文件，或手动粘贴配置内容
4. 导入后点击右侧开关启用连接

[![wireguard-macos][ref-pic-09]{:height="600"}][ref-pic-09]

> **注意**：macOS 客户端默认会将所有流量路由至 VPN（`AllowedIPs = 0.0.0.0/0`）。
> 若只需访问内网资源，将 `AllowedIPs` 改为内网网段（如 `192.168.1.0/24`）即可。
>
> **可选替代方案**：如果你不想通过 App Store 安装，
> 可以使用 [mintc2/wireguard-macos-app][ref-mintc2]，
> 这是一个非 App Store 打包的 WireGuard macOS 客户端，
> 功能与官方版本一致，可直接从 GitHub Releases 下载。

## 7. 排错

### 7.1. 常见问题排查

| 问题                 | 可能原因                       | 排查方向                                                                                                            |
| -------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| 客户端无法连接       | 防火墙未放行 UDP 端口          | 检查路由器防火墙规则，确认 WireGuard 监听端口（如 `51820/UDP`）已放行，公网环境下确认端口可达                       |
| 连接后无法访问内网   | 防火墙转发规则未配置或路由错误 | 检查 WireGuard 区域与 LAN 区域之间的转发规则；确认客户端网段已加入允许访问的路由                                    |
| 连接后无法访问外网   | NAT、转发规则或 DNS 配置问题   | 检查 `wireguard → wan` 转发规则是否存在；确认出口区域（通常为 `wan`）已启用 `masq='1'`；检查客户端 DNS 配置是否正确 |
| 连接不稳定           | MTU 问题                       | 启用 `mtu_fix='1'`，或在客户端尝试减小 MTU（如 `1420`、`1380`）                                                     |
| 接口或路由被自动删除 | 安装了 `wg-installer-server`   | 卸载该包，改用 OpenWrt 原生 WireGuard 配置方式                                                                      |

## 8. 关键坑点

### 8.1. Peer IP 地址不要与局域网同网段

**问题描述**：WireGuard 虚拟接口分配的 IP 地址如果与服务端所在局域网处于同一网段，
会导致路由冲突，客户端无法正常访问内网资源。

**示例对比**：

| 场景    | 局域网网段       | WireGuard 分配     | 结果                       |
| ------- | ---------------- | ------------------ | -------------------------- |
| ❌ 错误 | `192.168.1.0/24` | `192.168.1.100/24` | 路由冲突，无法正常访问内网 |
| ✅ 正确 | `192.168.1.0/24` | `10.0.1.0/24`      | 正常工作                   |

**建议**：为 WireGuard 选择一个完全独立的私有网段，
如 `10.x.x.x` 或 `172.16.x.x`。

## 参考资料

1. [一键连回家内网：OpenWrt 上部署 WireGuard VPN 服务器的三个要点][ref-upsangel] — upsangel
2. [OpenWrt 安装 WireGuard][ref-iyzm] — iyzm
3. [OpenWrt 搭建 WireGuard VPN][ref-mingyue] — mingyue5826
4. [OpenWrt 安装 WireGuard][ref-6xyun] — 6xyun

<!-- refs -->

[ref-upsangel]: https://upsangel.com/security/vpn/%E4%B8%80%E9%8D%B5%E9%80%A3%E5%9B%9E%E5%AE%B6%E9%87%8C%E5%85%A7%E7%B6%B2%EF%BC%9Aopenwrt%E4%B8%8A%E9%83%A8%E7%BD%B2wireguard-vpn%E6%9C%8D%E5%8B%99%E5%99%A8%E7%9A%84%E4%B8%89%E5%80%8B%E8%A6%81%E9%BB%9E/
[ref-iyzm]: https://iyzm.net/openwrt/1736.html
[ref-mingyue]: https://www.cnblogs.com/mingyue5826/p/18967121
[ref-6xyun]: https://6xyun.cn/article/openwrt-install-wireguard
[ref-mintc2]: https://github.com/mintc2/wireguard-macos-app
[ref-pic-01]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-01.png
[ref-pic-02]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-02.png
[ref-pic-03]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-03.png
[ref-pic-04]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-04.png
[ref-pic-05]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-05.png
[ref-pic-06]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-06-02.png
[ref-pic-07]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-07.png
[ref-pic-08]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-08.jpg
[ref-pic-09]: https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2025-06-23-configure-wireguard-on-openwrt-23-05-pic-09.png
