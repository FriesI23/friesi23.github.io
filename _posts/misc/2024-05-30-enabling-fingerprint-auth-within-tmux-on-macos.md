---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 在 macOS 中启用 tmux 内的指纹认证
author: FriesI23
date: 2024-05-30 11:10:00 +0800
category: macos
tags:
  - tmux
  - macos
  - fingerprint
---

`sudo` 在 `terminal.app` 下已经有很多方法可以让 `touchID` 生效,
但是如果在 `iterm2` 或者 `tmux` 环境下又需要输入烦人的密码 (尤其在你的密码很长时 \_(:з」∠)\_ ).
那么有放在可以让 `touchID` 这类生物识别可以在上述环境中生效么, 当然是有的, 请使用 [pam_reattach][pam_reattach].

### 1. 下载并安装 `pam_reattach`

```shell
brew install pam-reattach
```

### 2. 将 `pam_reattach.so` 加入到需要的服务中, 比如 `sudo`

需要注意机器是 `x86_64` 还是 `arm64(m1/...)`, 可以使用 `sudo find -L /usr /opt -name pam_reattach.so` 查找文件.

```bash
cp /etc/pam.d/sudo_local.template /etc/pam.d/sudo_local
echo -e "auth  optional  /opt/homebrew/lib/pam/pam_reattach.so\nauth  sufficient  pam_tid.so" >> /etc/pam.d/sudo_local
```

```text
# add lines below at /etc/pam.d/sudo or /etc/pam.d/sudo_local
auth       optional       /opt/homebrew/lib/pam/pam_reattach.so
auth       sufficient     pam_tid.so
```

完整文件内容如下(笔者机器是 2020 年 m1 的 macbookair):

![cat](https://github.com/FriesI23/friesi23.github.io/assets/20661034/89fbc406-7794-46a8-9d8f-9ea5030c0af2){: width="800" }

### 3. 完成

可以 `sudo` 一下测试 `touchID` 是否正确弹出.

[pam_reattach]: https://github.com/fabianishere/pam_reattach
