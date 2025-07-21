---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 为 Flutter 应用打包为 Flatpak 并以正确的姿势上架到 Flathub (上)
excerpt: |
  写在 Table Habit 上架到 Flathub 后，主要作为记录和供其他有需要者进行参考。
  共分为两个部分，本文为上半部分：既如何打包自己的 Single-file bundles。
author: FriesI23
date: 2025-07-20 16:00:00 +0800
category: flutter
tags:
  - flutter
  - flutter-linux
  - flatpak
  - flatpak-bundle
  - flathub
---

[Table Habit][mhabit] 一直有为 Linux 进行适配，但由于自己一般不使用 Linux 桌面环境，所有一直没有动力研究打包方案。
近期看到有 issue: [_"[FEATURE] Release as a Flatpak on Flathub"_][mhabit-issue-290]，
便准备采用其中提到的的 flatpak 方案对应用进行打包.
这篇博客写在上架到 Flathub 后（你可以在[这里][flathub-mhabit]找到我的应用信息），主要作为记录和供其他有需要者进行参考。

准备大体上拆分为两个部分：如何打包自己的 `.Flatpak` Bundle 与上架 Flathub 的正确姿势。本文将介绍上半部分,
如想直接查看 Flathub 上架流程请移步：
[为 Flutter 应用打包为 Flatpak 并以正确的姿势上架到 Flathub (下)][post-flutter-flatpak-and-flathub-2]。

## 什么是 Flatpak

这里不加自己的理解，直接贴上 wiki 的原文：

> Flatpak is a utility for software deployment and package management for Linux.
> It provides a sandbox environment in which users can run application software
> in (partial) isolation from the rest of the system.

[_"Flatpak History "_][flatpak-history] 也可以了解到其简要时间线。

## 将自己的 Flutter 应用打包为可安装的 Flatpak 单文件包（Single-file Bundle）

不论怎样，我都希望能够在应用每个版本发布后的 Release 界面中能够为使用者提供可供下载和安装的二进制文件，
因此需要在自动构建 CI 上增加对 Flatpak 单文件包的支持。当然还是以我自己的应用（Table Habit）为例：

1. [创建必要文件](#1-创建必要文件)
2. [构建产物](#2-构建产物)
3. [自动化](#3-自动化)

## 1. 创建必要文件

对于 GUI 应用，我们在正式打包前需要创建一些必要的元信息来让 Flatpak 知道怎样进行打包，
大致包含以下几个文件：

- `<manifest>.yaml/yml/json`：清单文件，Flakpak 需要。
- `<metainfo>.xml`：元信息，对应的桌面服务（e.g. Xfce）需要，Flakpak 也会读取里面相关信息。
- `<metainfo>.desktop`：桌面文件，对应的桌面服务（e.g. Xfce）需要。

### 1.1. 初始化

具体步骤请参考：[_"Building your first Flatpak"_][flatpak-building-your-first-flatpak]。
简而言之，已 Debian/Xfce 为例，执行如下命令进行初始化：

```shell
# refs: https://flatpak.org/setup/Debian
sudo apt install flatpak flatpak-builder
sudo apt install gnome-software-plugin-flatpak
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
# rebbot
```

### 1.2. Manifests

首先我们需要一个 Manifest （清单）文件，Flatpak 使用 Manifest 文件进行构建，
该文件会提供有关应用程序的基本信息和构建说明。

Flatpak 的文档很详细，可以在 [_"Manifests"_][flatpak-manifests] 中找到每个 key 值的定义。
我的清单文件如下（这是一个典型的自构建 flutter 清单，请与后续提交到 Flathub 的清单进行区分），
里面部分配置会进行注释说明：

```yaml
app-id: io.github.friesi23.mhabit
runtime: org.freedesktop.Sdk
runtime-version: "23.08"
sdk: org.freedesktop.Sdk
command: mhabit
separate-locales: false
finish-args:
  - --share=network
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --device=dri
  - --talk-name=org.freedesktop.portal.Desktop
  - --talk-name=org.freedesktop.Notifications
modules:
  # Required by: flutter_secure_storage
  # https://github.com/flathub/shared-modules/blob/master/libsecret/libsecret.json
  - name: libsecret
    buildsystem: meson
    config-opts:
      - -Dmanpage=false
      - -Dvapi=false
      - -Dgtk_doc=false
      - -Dintrospection=false
    cleanup:
      - /bin
      - /include
      - /lib/pkgconfig
      - /share/man
    sources:
      - type: archive
        url: https://download.gnome.org/sources/libsecret/0.21/libsecret-0.21.6.tar.xz
        sha256: 747b8c175be108c880d3adfb9c3537ea66e520e4ad2dccf5dce58003aeeca090

  - name: jsoncpp
    buildsystem: meson
    config-opts:
      - --buildtype=release
      - --default-library=shared
    sources:
      - type: archive
        url: https://github.com/open-source-parsers/jsoncpp/archive/refs/tags/1.9.6.tar.gz
        sha256: f93b6dd7ce796b13d02c108bc9f79812245a82e577581c4c9aabe57075c90ea2

  - name: mhabit
    buildsystem: simple
    build-options:
      arch:
        x86_64:
          env:
            BUNDLE_PATH: build/linux/x64/release/bundle
        aarch64:
          env:
            BUNDLE_PATH: build/linux/arm64/release/bundle
    build-commands:
      - install -D $BUNDLE_PATH/mhabit /app/bin/mhabit
      - install -Dm644 assets/logo/macos.svg /app/share/icons/hicolor/scalable/apps/io.github.friesi23.mhabit.svg
      - install -Dm644 configs/flatpak_builder/io.github.friesi23.mhabit.metainfo.xml -t /app/share/metainfo
      - install -Dm644 configs/flatpak_builder/io.github.friesi23.mhabit.desktop -t /app/share/applications
      - cp -r $BUNDLE_PATH/lib /app/bin/lib
      - cp -r $BUNDLE_PATH/data /app/bin/data
    sources:
      - type: dir
        path: ../../
```

#### 1.2.1. app-id

也可以使用 id, app-id 是应用的唯一标识，应该与自己构建应用本身的 bundle 保持一致。 该 id 显示如下，
最后启动应用（执行 `flatpak run <your-app-id>`）时也使用的是该 id。

```shell
$flatpak list --app
Name                             Application ID                    Version            Branch         Installation
Table Habit                      io.github.friesi23.mhabit         1.16.22+92         stable         user
Flatpak Builder Flatpak          org.flatpak.Builder               v0-Flathub         stable         user
...
```

#### 1.2.2. runtime, runtime-version && sdk

指名该应用需要的运行时环境，指名后应用安装时（`flatpak install ...`）会自动提示所有依赖的 package 依赖并安装（
如果使用 `-y` 则会自动安装）。

使用 `flatpak remote-ls flathub --runtime --user` 可以查看 `Flathub` 中可支持的所有 runtime。
不知道用哪个就遵循如下：

- GTK: `org.gnome.Platform`
- KDE/Qt: `org.kde.Platform`
- 跨桌面: `org.freedesktop.Platform`
  - 兼容版本：`23.08`
  - \* **Flathub 要求的版本**：`24.08`

选择 `runtime` 后可以选择对应的 sdk，已 `freedesktop` 为例，使用 `org.freedesktop.Sdk`

#### 1.2.3. command

填写程序入口的文件名，flutter 应用的入口就是打包后位于 `build/linux/<arch>/release/bundle/<pubspec.yaml#name>`

#### 1.2.4. finish-args

声明应用所需要的权限，请仔细阅读并参考 [_"Sandbox Permissions"_][flatpak-sandbox-permissions]。
下面只列举个人使用的部分权限：

- `--share=network`：如果应用需要访问网络，则加上这个权限。
- `--socket=wayland` && `--socket=fallback-x11`：对于 GUI 程序，这两个一起使用。
- `--device=dri`：启用图形加速支持，一般都加上。
- `--talk-name=org.freedesktop.portal.Desktop`：portal 权限，用于 freedesktop 与图形系统接口通信。
  - 注意：flathub 上架的应用默认包含这个权限，所以不用添加
- `--talk-name=org.freedesktop.Notifications`：`flutter_local_notification` 需要这个权限进行通知消息弹出。
  - 注意：如果代码使用 `freedesktop.protal` 进行通知通信，则不需要声明这个权限，对于其他 `--talk-name=...` 都适用。
    - e.g. `libsecret1` 支持 `freedesktop.protal` 通信，因此不需要声明 `--talk-name=org.freedesktop.secrets` 权限。

> 注：对于上架 `Flathub` 的应用，权限申请有一些额外规范，请参考 [_"Flatpak builder lint"_][flathub-linter]。

#### 1.2.5. modules

声明需要打包的模块，所有可配置字段参阅文档：[_"Module Sources"_][flatpak-models]。

一般配置本体应用打包即可，如果有额外模块，请参考文档进行源码引入并声明编译流程。一般参考配置方法的两个途径：

1. [flathub/shared-modules][flathub-shared-modules]
2. 以 `jsoncapp` 为例（对应 `apt-get install libjsoncpp-dev`）：`https://github.com/search?q=org:flathub jsoncpp&type=code`

一个需要注意的点是：所有 `path` 字段如果配置相对路径，路径起点都是 `Manifest` 文件所在位置。

> 抄一个好的配置文件是学习的开端，个人推荐：[`flathub/com.visualstudio.code`][flathub-vscode]

### 1.3. Metainfo

`Appstream` 定义了 `metainfo`，旨在为软件在跨平台提供统一的元数据。`Flatpak` 中也建议使用 `metainfo.xml`，
可以参考 [_"MetaInfo files"_][flatpak-metainfo] 章节获得相关信息。

> 注：Flathub 对 GUI 应用的 metainfo 是强制要求，并且有额外的 lint 检查，
> 请注意并参考 [_"Flatpak builder lint"_][flathub-linter]。
>
> 举个栗子：`appstream-missing-screenshots` 要求商家 flathub 的应用必须提供至少一个截图。

下面也贴出自己应用使用的元信息：

```xml
<?xml version="1.0" encoding="utf-8"?>
<component type="desktop">
  <id>io.github.friesi23.mhabit</id>
  <name>Table Habit</name>
  <summary>Micro habit tracker for personal growth</summary>
  <metadata_license>MIT</metadata_license>
  <project_license>Apache-2.0</project_license>
  <developer_name>Fries_I23</developer_name>
  <launchable type="desktop-id">io.github.friesi23.mhabit.desktop</launchable>
  <provides>
    <binary>mhabit</binary>
  </provides>
  <screenshots>
    <screenshot type="default">
      <image>
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/en-US/1.png</image>
      <image xml:lang="zh-CN">
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/zh-CN/1.png</image>
      <caption>Home screen</caption>
      <caption xml:lang="zh-CN">主界面</caption>
    </screenshot>
    <screenshot>
      <image>
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/en-US/2.png</image>
      <image xml:lang="zh-CN">
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/zh-CN/2.png</image>
      <caption>Dark mode</caption>
      <caption xml:lang="zh-CN">深色模式</caption>
    </screenshot>
    <screenshot>
      <image>
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/en-US/3.png</image>
      <image xml:lang="zh-CN">
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/zh-CN/3.png</image>
      <caption>Expanded habit list</caption>
      <caption xml:lang="zh-CN">展开习惯列表</caption>
    </screenshot>
    <screenshot>
      <image>
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/en-US/4.png</image>
      <image xml:lang="zh-CN">
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/zh-CN/4.png</image>
      <caption>Habit detail screen</caption>
      <caption xml:lang="zh-CN">习惯详细信息界面</caption>
    </screenshot>
    <screenshot>
      <image>
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/en-US/5.png</image>
      <image xml:lang="zh-CN">
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/zh-CN/5.png</image>
      <caption>Habit heatmap</caption>
      <caption xml:lang="zh-CN">习惯热力图</caption>
    </screenshot>
    <screenshot>
      <image>
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/en-US/6.png</image>
      <image xml:lang="zh-CN">
        https://raw.githubusercontent.com/FriesI23/mhabit/57cd99697b852b69f6ce9e954aa7827db62ca085/flatpak/screenshots/zh-CN/6.png</image>
      <caption>Batch editing screen</caption>
      <caption xml:lang="zh-CN">批量修改界面</caption>
    </screenshot>
  </screenshots>
  <description>
    <p>"Table Habit" is an app that helps you establish and track your own micro habit.
      It includes a complete set of growth curves and charts to help you build habits more
      effectively,
      and keeps your data in sync across devices (currently via WebDAV, with more options coming
      soon).</p>
    <p>Moreover, this app is completely open source and comes with these features:</p>
    <ul>
      <li>A scoring system to help develop your own micro habits.</li>
      <li>Support both positive and negative habit.</li>
      <li>An easy-to-use interface for habit check in.</li>
      <li>Different colors used to distinguish between various habits.</li>
      <li>Easily export and import habits using a human-readable format (JSON).</li>
      <li>Adapt to Material3 and Dynamic Color for Android 12 and later versions.</li>
      <li>Adaptation for landscape and large screen devices.</li>
      <li>[Experimental] Support network sync with WebDAV.</li>
      <li>No ADs in this app.</li>
    </ul>
  </description>
  <url type="vcs-browser">https://github.com/FriesI23/mhabit</url>
  <url type="bugtracker">https://github.com/FriesI23/mhabit/issues</url>
  <url type="homepage">https://github.com/FriesI23/mhabit</url>
  <url type="donation">https://github.com/FriesI23/mhabit?tab=readme-ov-file#donate</url>
  <url type="translate">https://hosted.weblate.org/engage/mhabit/</url>
  <url type="contribute">https://github.com/FriesI23/mhabit?tab=readme-ov-file#contributing</url>
  <!-- Auto generate by: https://hughsie.github.io/oars/generate.html -->
  <content_rating type="oars-1.1"/>
  <!-- https://specifications.freedesktop.org/menu-spec/latest/category-registry.html -->
  <categories>
    <category>Utility</category>
  </categories>
  <releases>
    <release version="1.16.22+92" date="2025-07-17">
      <url type="details">https://github.com/FriesI23/mhabit/releases/tag/flathub-v1.16.22+92</url>
    </release>
    <release version="1.16.22+91" date="2025-07-16">
      <url type="details">https://github.com/FriesI23/mhabit/releases/tag/v1.16.22+91</url>
    </release>
    <release version="1.16.21+90-pre" date="2025-07-15">
      <url type="details">https://github.com/FriesI23/mhabit/blob/main/CHANGELOG.md</url>
    </release>
  </releases>
</component>
```

其中有几个需要注意：

1. `<component type="desktop">` 对于 GUI 应用是必须且是 rootNode。
2. `id` 标签请与 `manifest` 中保持一致。
3. `<launchable type="desktop-id">` 配置了桌面（Xfce 等）的启动信息，
   如果想要应用能够从桌面菜单通过鼠标点击启动，这个配置是必须的。`.desktop` 文件下个章节会提到。
4. `content_rating` 标签建议自动生成，网址代码中已提及。
5. `categories` 请使用 Freedesktop 支持的标签名，不然 linter 检查会报错，合法标签信息网址也在代码中标注。
6. `releases` 信息需要手动维护，flatpak 在显示应用是会自动使用 `date` 最后的一个，
   可以写一个脚本进行维护（e.g. [scripts/gen_flatpak_info.sh][mhabit-gen-flatpak-info]）。
   当然如果有更好的方案也可以进行分享，终归是不想也不喜欢重复造轮子。

最后通过一下命令检查 `<metainfo>.xml` 是否合法：

```shell
appstreamcli validate --pedantic /path/to/metainfo.xml
```

### 1.4. Desktop

`Desktop` 文件用于向桌面环境提供有关应用的信息，可以手动创建，也可以由 `appstream` 介由 `metainfo.xml` 文件生成。

```shell
appstreamcli make-desktop-file <app-id>.xml <app-id>.desktop
```

Desktop 文件比较简单，如下：

```ini
[Desktop Entry]
Name=Table Habit
Comment=Micro habit tracker for personal growth
Exec=mhabit
Icon=io.github.friesi23.mhabit
Terminal=false
Type=Application
Categories=Utility
StartupNotify=true
```

相关文档也可在 [_"Desktop files"_][flatpak-desktop] 章节中找到。

### 2. 构建产物

目标是构建 Flatpak 单文件包，因此 repo 只作为构造中间产物出现，如果需要已 repo 的形式构建并安装，
请参考：[_"Flatpak/Publishing"_][flatpak-publish].

```shell
# 安装依赖
apt-get install -y flatpak flatpak-builder
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
# 根据 <manifest>.yaml 内的 runtime 获取对应的构建依赖，这里以 freedesktop-23.08 举例
flatpak install -y org.freedesktop.Sdk/x86_64/23.08
flatpak install -y org.freedesktop.Platform/x86_64/23.08
flatpak install -y flathub org.freedesktop.appstream-glib
# 构建 linux 产物
flutter build linux --release
# 构建 flatpak repo
flatpak-builder --force-clean build-dir \
    --repo=repo-dir --default-branch=main \
    <path/to/manifest.yaml>
# 构建 flatpak bundle
flatpak build-bundle repo-dir <custom-name>.flatpak <app-id> main
```

### 3. 自动化

将上面的步骤集成到 `Github Action` 中，每次推送对应 tag 都能自动进行 Release 版本构建并发布。

由于第三方 Workflow `flatpak/flatpak-github-actions/flatpak-builder@v6` 需要使用自定义容器，
因此将构造 Linux 产物和构造 Flatpak 产物分为两个 job 执行，并使用 artifact 传递构造中间产物。

{% raw %}

```yaml
name: Release
on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+\+[0-9]+'

jobs:
  # Step1: 编译 Linux 二进制文件
  build-linux:
    name: "Build Linux Bundle"
    strategy:
      # symbol `g_once_init_enter_pointer`` was introduced in glib>=2.80,
      # fallback build host to ubuntu-22.04 for better compatibility.
      # refs: https://github.com/cirruslabs/docker-images-flutter/issues/337.
      matrix:
        variant:
          - arch: x86_64
            runner: ubuntu-22.04
            bundle_path: build/linux/x64/release/bundle
          - arch: aarch64
            runner: ubuntu-22.04-arm
            bundle_path: build/linux/arm64/release/bundle
    runs-on: ${{ matrix.variant.runner }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Init Flutter
        uses: ...
      - name: Build Linux Bundle
        env:
          BUNDLE_PATH: ${{ matrix.variant.bundle_path }}
        run: flutter build linux --release
      - name: Upload Bundle
        uses: actions/upload-artifact@v4
        with:
          name: linux-bundle-${{ matrix.variant.arch }}
          path: ${{ matrix.variant.bundle_path }}
          if-no-files-found: error
          retention-days: 1

  # Step2: 打包为 Flatpak Bundle
  build-linux-flatpak:
    name: "Build Flatpak Bundle"
    needs:
      - build-linux
    container:
      # https://github.com/flathub-infra/actions-images/pkgs/container/flatpak-github-actions
      # 根据对应 runtime 选择
      image: ghcr.io/flathub-infra/flatpak-github-actions:freedesktop-23.08
      options: --privileged
    strategy:
      matrix:
        variant:
          - arch: x86_64
            runner: ubuntu-22.04
            bundle_path: build/linux/x64/release/bundle
          - arch: aarch64
            runner: ubuntu-22.04-arm
            bundle_path: build/linux/arm64/release/bundle
    runs-on: ${{ matrix.variant.runner }}
    env:
      ARTIFACT_NAME: linux-bundle-${{ matrix.variant.arch }}
      FLATPAK_BUNDLE: output-${{ matrix.variant.arch }}.flatpak
    steps:
      - uses: actions/checkout@v4
      - name: Fetch Bundle
        id: fetch-bundle-step
        uses: actions/download-artifact@v4
        with:
          name: ${{ env.ARTIFACT_NAME }}
          path: ${{ matrix.variant.bundle_path }}
          # 填写一个可用的 Github Token，否则可能找到 API 限制
          # github-token: ${{ secrets.APP_RELEASE_TOKEN }}
      - name: Build .flatpak
        uses: flatpak/flatpak-github-actions/flatpak-builder@v6
        with:
          bundle: ${{ env.FLATPAK_BUNDLE }}
          manifest-path: /path/to/manifest.yml
          arch: ${{ matrix.variant.arch }}
          # branch: main
          upload-artifact: false
      - name: Release
        uses: ncipollo/release-action@v1
        with:
          allowUpdates: true
          omitBodyDuringUpdate: true
          omitDraftDuringUpdate: true
          omitPrereleaseDuringUpdate: true
          artifacts: >
            ${{ env.FLATPAK_BUNDLE }}
          # 填写一个可用的 Github Token，否则可能找到 API 限制
          # token: ${{ secrets.APP_RELEASE_TOKEN }}
```

{% endraw %}

## 结语

以上，便能构造一个 `output.flatpak` 文件，
如果一切正常的话可以通过 `flatpak install --user output.flatpak` 进行安装验证。

下一篇文章会介绍如何以正确的姿势发布到 `Flathub`，由于 `Flathub` 自身有一些特殊发布规则，因此流程也会不太一样。
不过 `Flathub` 建议由上游自行维护 `metainfo.xml` 文件，
因此建议从一开始就保持自己发布的 `metainfo.xml` 与 `Flathub` 要求兼容，具体 lint 检查放在下篇文章中。

- [为 Flutter 应用打包为 Flatpak 并以正确的姿势上架到 Flathub (下)][post-flutter-flatpak-and-flathub-2]

<!-- refs -->

[post-flutter-flatpak-and-flathub-2]: /post/202507/flutter-flatpak-and-flathub-2
[mhabit]: https://github.com/FriesI23/mhabit
[mhabit-issue-290]: https://github.com/FriesI23/mhabit/issues/289
[mhabit-gen-flatpak-info]: https://github.com/FriesI23/mhabit/blob/main/scripts/gen_flatpak_info.sh
[flatpak-history]: https://flatpak.org/about/
[flatpak-building-your-first-flatpak]: https://docs.flatpak.org/en/latest/first-build.html
[flatpak-manifests]: https://docs.flatpak.org/en/latest/manifests.html
[flatpak-sandbox-permissions]: https://docs.flatpak.org/en/latest/sandbox-permissions.html
[flatpak-models]: https://docs.flatpak.org/en/latest/module-sources.html
[flatpak-metainfo]: https://docs.flatpak.org/en/latest/conventions.html#metainfo-files
[flatpak-desktop]: https://docs.flatpak.org/en/latest/conventions.html#desktop-files
[flatpak-publish]: https://docs.flatpak.org/en/latest/publishing.html
[flathub-mhabit]: https://flathub.org/apps/io.github.friesi23.mhabit
[flathub-linter]: https://docs.flathub.org/docs/for-app-authors/linter
[flathub-shared-modules]: https://github.com/flathub/shared-modules
[flathub-vscode]: https://github.com/flathub/com.visualstudio.code/blob/master/com.visualstudio.code.yaml
