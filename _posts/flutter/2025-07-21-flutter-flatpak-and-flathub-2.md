---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 为 Flutter 应用打包为 Flatpak 并以正确的姿势上架到 Flathub (下)
excerpt: |
  写在 Table Habit 上架到 Flathub 后，主要作为记录和供其他有需要者进行参考。
  共分为两个部分，本文为下半部分：既如何以正确姿势上架到 Flathub。
author: FriesI23
date: 2025-07-21 17:00:00 +0800
category: flutter
tags:
  - flutter
  - flutter-linux
  - flatpak
  - flathub
---

本文紧接[“为 Flutter 应用打包为 Flatpak 并以正确的姿势上架到 Flathub (上)”][post-flutter-flatpak-and-flathub]，
主要记录上架 `Flathub` 的过程。

## 什么是 Flathub

简单理解为在 Linux 中使用 FLatpak 技术，类似 Microsoft Store / Mac App Store / Unbuntu Snap Store 的应用商店。
可以在其[官网][flathub-org]流浪并安装应用，Flathub 也是一个 repo，也可以通过通用命令安装应用：

```shell
APP_ID=<your-app-id>
flatpak install flathub $APP_ID
flatpak run $APP_ID
```

## 从哪里开始

由于 Flathub 相对普通的自打包有诸多额外限制，
因此**强烈**建议从 [_"For app authors"_][flathub-for-app-authors] 开始仔细阅读每一个章节。
本文只从 [_"Table Habit"_][flathub-mhabit] 创建于提交流程出发，记录整个过程和踩到的坑。

## 1. 基本要求

这里是一些基本要求，这里整理了指向官方文档的链接。需要注意的是下面内容只截至到本文发表时间保证有效，如有区别请以 Flathub 官方文档为准：

| 内容                                   | 备注                                                                                                                                          |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| [包容性政策][flathub-inclusion-policy] | 请对照查看软件是否符合上架要求                                                                                                                |
| [App ID][flathub-appid]                | 确保应用 AppID 符合上架要求，Flathub 要求使用 “[reverse-DNS][reverse-dns-name-notation] 命名法”                                               |
| [许可][flathub-license]                | 确保使用可以被合法分发的 license，且必须在 meteinfo.xml 中进行声明                                                                            |
| [权限][flatpak-permission]             | 仔细阅读需要使用的权限，不然很容易被拒绝，详细说明后面章节会叙述；部分权限（e.g. dbus 相关）除非特殊原因**肯定**会被 lint CI 拒绝，请谨慎使用 |

还有一些构建时的限制：

- 构建时无网络访问，即在 `bnuild-options` 中使用 `--share=network` 无效。
  由于 Flutter 默认会在构建时自动下载相关依赖，因此使用 Flathub 官方教程在进行构建时几乎**一定**会失败。
  后续会介绍使用 [`flatpak-flutter`][flatpak-flutter] 进行预处理，保证可以构建成功。
- **尽量**从源码构建。紧接上一条，由于 Flutter 应用依赖外部下载，因此一种解决的方法便是预构建二进制文件，
  再由 Flathub 直接分发。但由于不是由 Flathub 构建，可能出于导致各种各样的兼容性问题的原因，
  Flathub 默认需要从源码构建（私货：个人强烈同意，从源码构建甚至是可重复构建从安全角度对于自由/开源软件是必须的）。
  [`flatpak-flutter`][flatpak-flutter] 可以避免二进制分发，后面会赘述。

## 2. 准备 Repo

使用 Github Cli：

```shell
gh repo fork --clone flathub/flathub
cd flathub
git checkout --track origin/new-pr
git checkout -b my-app-submission new-pr
```

或者手动操作：

1. [Fork Flathub/Flathub](https://github.com/flathub/flathub/fork)，同时取消勾选 "Copy the master branch only"。
2. 执行以下操作：

   ```shell
   git clone --branch=new-pr git@github.com:<your-github-name>/flathub.git && cd flathub
   git checkout -b my-app-submission new-pr
   ```

确保当前分支从 `new-pr` 派生并且命名为 `my-app-submission`。

## 3. 需求文件与内容

确保上面创建的本地 repo 中包含以下文件，可选文件请参考 [_"Required files"_][flathub-required-files]：

1. `manifest.yml/yaml/json`：清单文件必须存在，并以 `<app-id>.yml/yaml/json` 命名。
   如果使用 `flatpak-flutter` 该文件会由对应的 Manifest 模板自动生成。

还有一些必要的文件 Flathub 几乎是**强制要求**在上游 repo 中维护。
不过实际查看中很多应用将这些文件放在了该 repo 中，如有需求请在提交后和维护者沟通，
这里（包含后续）默认这些文件存放在上游 repo：

1. `metadata.xml`：需要通过 Flathub 定制的 appsstream 合法性验证，后续会详细说明。
2. 应用程序图标：要求是 svg 或者 png，后续也会再次说明；对于 GUI 应用是必选的。
3. `<app-id>.desktop`：该文件对 GUI 应用是必选的。

## 4. flatpak-flutter

在[“1. 基本要求”](#1-基本要求)中，说明了 `Flutter` 应用默认在离线环境中几乎无法进行构建，
但 Flathub 又需要尽量避免直接提交二进制文件，
因此我们需要在清单文件中列出需要构建的 Flutter 应用中所有依赖 package 的源码构建信息。

上面如果手动操作的话需要查询 `pubspec.lock` 并手动或写一个脚本生成所有依赖描述，
这无疑是一项大工程，幸好有 [`flatpak-flutter`][flatpak-flutter] 这个现成的轮子。

该项目的简单原理就是将 flutter 中所有需要下载的流程转化为 Manifest 中的描述格式，
一般包含：

- `flutter-sdk-x.y.z.json`：编译 FLutter 需要的依赖
- `pubspec-sources.json`：`pubspec.lock` 中列出的依赖

具体说明和更多用法（比如处理外部依赖）可以直接看该项目的 README。

而对于一个简单的 Flutter 项目，我们需要做的是：

1. 创建一个需要的 Manifest 模板文件，一般命名为 `flatpak-flutter.yml/yaml`
2. 按 [5. Manifest] 中示例编写 Manifest 文件
3. 执行 `flatpak-flutter flatpak-flutter.yml`
4. 成功后，将生成的额外清单文件加入 repo

> 建议在 `.gitignore` 中加入如下内容，这些都是 `flathub / flatpak-flutter` 运行过程中的中间产物：
>
> ```text
> .flatpak-builder/
> build/
> repo/
> ```

## 5. Manifest

与上篇文章中的 ["Manifest"](/post/202507/flutter-flatpak-and-flathub#12-manifests) 大致相同，但有些许区别。

下面还是先贴上 `flathub/io.github.friesi23.mhabit` 中使用的清单文件（`flatpak-flutter.yaml`）：

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/flatpak/flatpak-builder/main/data/flatpak-manifest.schema.json

---
app-id: io.github.friesi23.mhabit
runtime: org.freedesktop.Sdk
runtime-version: "24.08"
sdk: org.freedesktop.Sdk
sdk-extensions:
  - org.freedesktop.Sdk.Extension.llvm19
command: mhabit
separate-locales: false
finish-args:
  - --share=network
  - --share=ipc
  - --device=dri
  - --socket=fallback-x11
  - --socket=wayland
  - --talk-name=org.freedesktop.Notifications
modules:
  - shared-modules/libsecret/libsecret.json
  - name: jsoncpp
    buildsystem: meson
    config-opts:
      - --buildtype=release
      - --default-library=shared
    sources:
      - type: archive
        url: https://github.com/open-source-parsers/jsoncpp/archive/refs/tags/1.9.6.tar.gz
        sha256: f93b6dd7ce796b13d02c108bc9f79812245a82e577581c4c9aabe57075c90ea2
    cleanup:
      - "/lib/*.a"
      - "/include"
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
      append-path: /usr/lib/sdk/llvm19/bin:/run/build/mhabit/flutter/bin
      prepend-ld-library-path: /usr/lib/sdk/llvm19/lib
      env:
        PUB_CACHE: /run/build/mhabit/.pub-cache
    build-commands:
      - flutter build linux --release
      - install -D $BUNDLE_PATH/mhabit /app/bin/mhabit
      - install -Dm644 assets/logo/macos.svg /app/share/icons/hicolor/scalable/apps/io.github.friesi23.mhabit.svg
      - install -Dm644 flatpak/io.github.friesi23.mhabit.metainfo.xml -t /app/share/metainfo
      - install -Dm644 flatpak/io.github.friesi23.mhabit.desktop -t /app/share/applications
      - cp -r $BUNDLE_PATH/lib /app/bin/lib
      - cp -r $BUNDLE_PATH/data /app/bin/data
    sources:
      - type: git
        url: https://github.com/FriesI23/mhabit.git
        tag: flathub-v1.16.22+92
        commit: cbedd98a6e24a6a5cc0a48bcea925928ac2087ae
        disable-submodules: true
      - type: git
        url: https://github.com/flutter/flutter.git
        tag: 3.24.5
        dest: flutter
```

这里列出几个和自己构建不一样的部分：

### 5.1. runtime

截止该文章撰写时，Flathub 要求使用的 freedesktop 版本是 24.08，其他版本可能会被维护者问询或者拒绝，
如无其他必要请确保使用 Flathub 中支持（建议）使用的 runtime 包和对应版本。

```yaml
runtime: org.freedesktop.Sdk
runtime-version: "24.08"
```

### 5.2. llvm19

编译 Flutter 需要使用 `clang`，因此需要引入 `llvm`。
请注意不同 runtime 对应的 llvm 版本，如果不清楚可以使用以下命令查看：

```shell
flatpak remote-ls flathub --user | grep org.freedesktop.Sdk.Extension.llvm
```

```yaml
sdk-extensions:
  - org.freedesktop.Sdk.Extension.llvm19
# ...
modules:
  - name: mhabit
    build-options:
      # ...
      append-path: /usr/lib/sdk/llvm19/bin:...
      prepend-ld-library-path: /usr/lib/sdk/llvm19/lib
    # ...
```

### 5.3. finish-args

权限是个人在提交验证错误的并要求修改的重灾区，因为 Flathub 不光检查清单文件的合法性，
还会有很多额外的限制，具体请看：["Linter"][flathub-linter]，并搜索以 "finish-args-" 开头的语法。
个人在实践中主要遇到了一下几个问题：

- `finish-args-arbitrary-dbus-access`：Fluthub 禁止对任意 dbus 的访问，如有需要请申请具体的 dbus 名称，
  一般不需要申请这个。
- finish-args-portal-talk-name：Flatpak 默认允许 `--talk-name=org.freedesktop.portal.<...>`，无需重复申请。
  Flathub 会检查这些权限，如果存在则报错。

还有一些权限需要仔细检查是否需要：

- `--talk-name=org.freedesktop.Notifications`：如果代码或者依赖包不支持使用 `org.freedesktop.portal` 接口弹出通知则需要该权限。
- `--talk-name=org.freedesktop.<...>`：同上，如果代码使用 `protal` 接口，则都不需要申请权限，反之亦然。

```yaml
finish-args:
  - --share=network
  - --share=ipc
  - --device=dri
  - --socket=fallback-x11
  - --socket=wayland
  - --talk-name=org.freedesktop.Notifications
```

### 5.4. shared-modules

一些 Flathub 中已经定义好的库存放在 [`flathub/shared-modules`][shared-modules] 中，
可以通过使用 submodule 引入后直接使用：

```shell
git submodule add https://github.com/flathub/shared-modules.git
```

```yaml
modules:
  - shared-modules/libsecret/libsecret.json
```

### 5.5. flutter

通过以下方式引入 Flutter，由于 `flakpak-flutter` 脚本限制，
现在 sources 中的 App 和 Flutter 本身都需要使用 git 和 url 的方式引入，
因此如果有特殊需要可以主动修改并提 PR....

```yaml
modules:
  - name: mhabit
    build-options:
      # ...
      append-path: ...:/run/build/mhabit/flutter/bin
      env:
        PUB_CACHE: /run/build/mhabit/.pub-cache
    # ...
    sources:
      - type: git
        url: https://github.com/FriesI23/mhabit.git
        tag: flathub-v1.16.22+92
        commit: cbedd98a6e24a6a5cc0a48bcea925928ac2087ae
        disable-submodules: true
      - type: git
        url: https://github.com/flutter/flutter.git
        tag: 3.24.5
        dest: flutter
```

### 5.6. 其他

- Flathub 现在要求将所有的 modules 都内联（inline），因此如无必要尽量不要手动拆分为多个文件。
- 请务必在文件头引入以下内容保证基本格式符合 flatpak 要求。

  ```yaml
  # yaml-language-server: $schema=https://raw.githubusercontent.com/flatpak/flatpak-builder/main/data/flatpak-manifest.schema.json
  ---
  # manifest content
  # ...
  ```

## 6. Metainfo 和 Desktop

两者请在上游维护，并在 `Manifest` 中引用。以自己的应用为例：

在应用仓库维护如下结构：

```shell
/root/flatpak
├── io.github.friesi23.mhabit.desktop
├── io.github.friesi23.mhabit.metainfo.xml
└── screenshots
    ├── en-US
    │   ├── 1.png
    │   ├── 2.png
    │   ├── 3.png
    │   ├── 4.png
    │   ├── 5.png
    │   └── 6.png
    └── zh-CN
        ├── 1.png
        ├── 2.png
        ├── 3.png
        ├── 4.png
        ├── 5.png
        └── 6.png
```

在 Manifest 的 `build-commands` 中引用：

```yaml
modules:
  - name: mhabit
    build-commands:
      # 编译二进制文件
      - flutter build linux --release
      # 安装主程序
      - install -D $BUNDLE_PATH/mhabit /app/bin/mhabit
      # 安装图标
      - install -Dm644 assets/logo/macos.svg /app/share/icons/hicolor/scalable/apps/io.github.friesi23.mhabit.svg
      # 安装元信息
      - install -Dm644 flatpak/io.github.friesi23.mhabit.metainfo.xml -t /app/share/metainfo
      # 安装桌面文件
      - install -Dm644 flatpak/io.github.friesi23.mhabit.desktop -t /app/share/applications
      # 安装构建依赖
      - cp -r $BUNDLE_PATH/lib /app/bin/lib
      - cp -r $BUNDLE_PATH/data /app/bin/data
    # ...
    sources:
      - type: git
        url: https://github.com/FriesI23/mhabit.git
        tag: flathub-v1.16.22+92
        commit: cbedd98a6e24a6a5cc0a48bcea925928ac2087ae
        disable-submodules: true
      - type: git
        url: https://github.com/flutter/flutter.git
        tag: 3.24.5
        dest: flutter
```

另外自己在实践中有几点需要注意：

1. 必须包含至少一个截图，并描述在 `screenshots/screenshot` 节点中。
2. `releases` 节点必须包含且至少含有一个版本，且不要随意删除版本，否则可能出发 Flathub 审查。

有关元信息相关可以查看官方文档：[_"Appstream Validation Errors"_][flathub-meta-linter]

与其他应用商店类似，Falthub 也存在一个质量文档，可以查看 [_"Quality guidelines"_][flathub-quality] 并遵嘱其中标准以获得更好的产品体验。

## 7. 准备本地构建

此时先保证已经执行了 `flatpak-flutter flatpak-flutter.yml`，此时本地 repo 结构应如下：

```shell
├── .git
├── .gitignore
├── .gitmodules                     # submodule 描述信息，如果引入类似 shared-modules 则需要
├── flatpak-flutter.yml # 模板文件
├── flutter-sdk-3.24.5.json         # 注：这里是你自己配置的 Flutter 版本
├── flutter-shared.sh.patch         # Patch 文件也要包含在内
├── io.github.friesi23.mhabit.yml   # 生成的 Manifest 文件
├── package_config.json
├── pubspec-sources.json            # 第三方 package 的 Manifest 文件
└── shared-modules                  # 如果没有拉取 submodule，则使用 git submodule update --init --recursive 获取
```

```shell
# 检查 Manifest 文件是否符合 Flathub 要求
# 如果执行后有报错则一定要处理，否则后续提 PR 的测试构建 CI 必然会失败
# 理想情况什么都不会输出
# flatpak run --command=flatpak-builder-lint org.flatpak.Builder \
#   manifest your-app-id.yml
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest \
  io.github.friesi23.mhabit.yml

# 检查 Metainfo 文件是否符合 Flathub 要求
# 具体同上，先保证这两个验证可以通过
# flatpak run --command=flatpak-builder-lint org.flatpak.Builder appstream \
#   your-app-id.yml.metainfo.xml
flatpak run --command=flatpak-builder-lint org.flatpak.Builder appstream \
  io.github.friesi23.mhabit.metainfo.xml

# 使用和 Flathub 相同的环境进行构建，如果失败可以尝试时候下面给出的命令尝试构建：
# flatpak-builder --repo=repo --force-clean --sandbox --user \
#   --install --install-deps-from=flathub build your-app-id.yml
# 如果上面命令成功，则可能是环境问题
# e.g. 不要在 vscode 的内建 shell 内执行，建议使用标准的 Terminal
#      或者一个干净的 shell 环境，然后重复下面的 Flathub 构建命令。
#
# flatpak run --command=flathub-build org.flatpak.Builder your-app-id.yml
flatpak run --command=flathub-build org.flatpak.Builder \
  io.github.friesi23.mhabit.yml

# 对构建产物（repo）再进行一次检查
# 具体同上述检查流程，保证没有报错，尽量没有警告
flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo repo
```

## 8. 准备提交

这里引用原文：

> Now open a pull request against the `new-pr` base branch on GitHub.
> The title of the PR should be "Add org.example.MyAwesomeApp".

如图：

![pr](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-flatpak-and-flathub-2-01.jpg){:width="600"}

然后就是按 Review 结构进行修改，最后等待通过即可。

## 9. Done

通过后，该 PR 会被自动关闭，同时新生成一个 `Flathub/<your.app.id>` 的仓库，并会收到一个邀请，接收后即可自行维护，
这也代表该 App 已被 Flathub 接收，稍后便能在 `flathub.org` 中查询到。

后需维护请参考：[_"App Maintenance"_](https://docs.flathub.org/docs/for-app-authors/maintenance)。

## 总结

由于事先以自行查阅大量文档和其他应用的 repo 且已经成功构建出 Flatpak Single-file Bundle，
也因为 App 本省体量较小，因此提交时并没有遇到很多问题。

其中比较容易踩坑的就是权限问题，因为申请的权限即使用不到测试时也不会报错，而做减法永远是有风险的，
因此浪费了一定的时间排查。

应用上架的 PR 可以查看：["Add io.github.friesi23.mhabit #6732"](https://github.com/flathub/flathub/pull/6732)

当然也建议查看其他 Open 或者 Closed 的 PR，参考学习别人的提交流程
（当然超过一两年没更新的应用就算了，可能不符合 Flathub 的最新标准），可以为极大加速应用被合并时间。

最后附赠一些可能有用的链接：

- [Flathub - Requirements](https://docs.flathub.org/docs/for-app-authors/requirements)
- [Flathub - Submission](https://docs.flathub.org/docs/for-app-authors/submission)
- [Flathub - Maintenance](https://docs.flathub.org/docs/for-app-authors/maintenance)
- [Flathub - Flatpak builder lint](https://docs.flathub.org/docs/for-app-authors/linter)
- [Flathub - MetaInfo guidelines](https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines)
- [Flatpak - Manifest](https://docs.flatpak.org/en/latest/manifests.html)
- [Flatpak - Sandbox Permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html)
- [Flatpak - Module Sources](https://docs.flatpak.org/en/latest/module-sources.html)
- [AppStream - MetaInfo Creator](https://www.freedesktop.org/software/appstream/metainfocreator)
- [Debian - appstreamcli](https://manpages.debian.org/buster/appstream/appstreamcli.1)

<!-- refs -->

[post-flutter-flatpak-and-flathub]: /post/202507/flutter-flatpak-and-flathub
[flatpak-permission]: https://docs.flatpak.org/en/latest/sandbox-permissions.html
[flathub-mhabit]: https://flathub.org/apps/io.github.friesi23.mhabit
[flathub-org]: https://flathub.org/
[flathub-for-app-authors]: https://docs.flathub.org/docs/category/for-app-authors
[flathub-inclusion-policy]: https://docs.flathub.org/docs/for-app-authors/requirements#inclusion-policy
[flathub-appid]: https://docs.flathub.org/docs/for-app-authors/requirements#application-id
[flathub-license]: https://docs.flathub.org/docs/for-app-authors/requirements#license
[flathub-required-files]: https://docs.flathub.org/docs/for-app-authors/requirements#required-files
[flathub-linter]: https://docs.flathub.org/docs/for-app-authors/linter
[flathub-meta-linter]: https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines#appstream-validation-errors
[flathub-quality]: https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines/quality-guidelines
[reverse-dns-name-notation]: https://en.wikipedia.org/wiki/Reverse_domain_name_notation
[flatpak-flutter]: https://github.com/TheAppgineer/flatpak-flutter
[shared-modules]: https://github.com/flathub/shared-modules
