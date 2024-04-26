---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: "如何将 Flutter 应用上架到 F-Droid"
author: FriesI23
date: 2023-06-08 18:00:00 +0800
category: fdroid
tags:
  - flutter
  - android
  - fdroid
  - app-store
---

最近在 `F-Droid` 上架了自己的第一款开源应用 `Table Habit`, 在这里记录一下上架的大概流程和
遇到的一些问题, 一方面方便自己以后上架其他应用, 另一边放也希望大家遇到类似问题的时候能够有一个
可行的 `workflow`, 如果想查看具体细节可以看 [这里][fdroid-mr-url] 的讨论.

这里也允许推销一下自己这款习惯养成的 app, [Table Habit][mhabit-fdroid-url] 是一款方便自己
进行习惯追踪和记录的 App, 交互适配最新的 `Material3` 并且完全开源免费.

[![pic1][mhabit-pic-1]{:width="200"}][mhabit-pic-1]
[![pic2][mhabit-pic-2]{:width="200"}][mhabit-pic-2]

## 1. 一些前置的准备

在向 `F-Droid` 仓库提交合并请求前, 可以根据自己的需求和实际情况先接入一些 `F-Droid` 项目中
推荐的项目. (这些接入的内容也是我和 `F-Droid` 维护者在合并中讨论并修改最多的地方) 其中分为
`必要` `强烈推荐` `推荐` 三个等级, 当然如果条件允许, 最好是可以全部接入的.

### 必要::应用程序应符合收录标准

具体的收录标准可以查看 [这里](https://f-droid.org/docs/Inclusion_Policy/). 简而言之,
就是:

- 在编码,构建中不要包含任何非自由的代码和工具 (e,g. googleAD, OracleSDK, etc.)
- 不要提供应用内更新的功能 (应用更新应当由 F-Droid 接管)
- 应用 ID 应该使用自己独一无二的 ID (如果没有自己的域名或者不想使用自己的域名,
  就使用托管仓库的域名把, 比如 `io.github.foo.bar` )
- 依赖必须使用源码构建, 或者能够从 `Debian` 库中直接获得.

### 必要::需要通知原 app 作者

当然, 如果自己就是 app 的作者 (比如我的 [Table Habit][mhabit-github-url]), 这条可以直接
略过.

### 必要::合并请求(MR)中已引用所有相关的 `fdroiddata` 和 `RFP` 问题

对于新 App, 一般不会存在这些 `issue`, 所以可以跳过.

### 必要::使用 `fdroid build` 构建

由于 F-Droid 使用 `fdroid build` 命令构建 `repo` 下的所用应用, 因此必须可以通过执行
`fdroid build io.github.foo.bar` 并成功构建 app 来保证最终服务器的构建流程可以顺利通过.

我们通过配置正确的元数据(metadata)让 `fdroidserver` 可以正确的构建出自己的应用, 如使用过
`Github Action` 在云端构建自己的应用, 那么恭喜, 他们本质上(几乎)是同一种东西.

关于相关 `metadata.yml` 文件的编写与本地测试, 可以查看 [这里](#3-metadata-如何填写) 和
[这里](#21-本地测试-fdroid-build)

### 强烈推荐::App metadata

需要在项目的根目录建立一个 `fastlane` 目录结构, 可以参考 [这里][fastlane-structure]

为什么需要`fastlane`, 比如对于我的应用, frdoird 会在 website 构建时读取项目目录中的 fastlane
结构, 并根据其中的信息生成应用网页, 比如 [我的应用主页][mhabit-fdroid-url]

按照官方给出的目录创建即可, 其中有几点需要注意(也包含一个我踩过的坑)

- `en-US` 是必须的, 这个是默认目录, 如果其他语言的相关信息没有找到就会去这个目录寻找
- locale 是大小写敏感的 (e.g. 应该是 `en-US` 而不是 `en-us`), 这里需要特别注意.
- 具体的 locale 值可以在 [这里](https://www.andiamo.co.uk/resources/iso-language-codes/)
  找到, 还是要注意大小写 (`xx-YY`).

### 强烈推荐::Releases are tagged

每个版本打上 tag 即可, 比如 `git tag v1.0.0+1`

### 推荐::外部仓库被添加为 `submodule` 而不是 `srclibs`

使用 `submodule` 可以自行更新 fdroid 构建时使用的依赖(比如 flutterSDK) 在更新依赖版本时只
需要更新 `submodule`, 而不需要更新 metadata 并重新向 fdroid/data 提交一个 MR (省事)

可以查看 [3. `metadata` 如何填写](#3-metadata-如何填写) 了解更多 `submodule` 使用姿势

### 推荐::可重复构建

F-Droid 官方的可重复构建文档有一些冗余, 这里主要解答一下 `什么是`, `为什么`, `怎么做` 这三个
问题, 也可以参考 [官方文档][fdroid-rebuild-doc].

大白话说就是, 任何人在他们的目标机器上使用相同的构建环境和步骤, 最终生成的二进制文件和你自己本
地环境构建出来的二进制完全相同, 这样做的目的主要还是为了防止二进制被不法分子篡改并进行非法发布.

F-Droid 默认使用自己的 key 对构建的软件进行签名, 而安卓 app 升级的一个硬性要求便是需要保证签名来源
是一致的, 否则会禁止安装. 因此默认情况下自己构建的出来的 app 除非使用从 F-Droid 中提取的 key 进行
签名, 否则是无法和 F-Droid 商店内应用进行覆盖升级的.

但实现可重构构建后, F-Droid 就会直接将自签名(而不是 fdroid 签名)的 APP 发布到商店, 这样就可以进行
升级.

```text
未接入可重复构建

fdoird build --> 生成APK --> 上架 fdroid store

接入可重复构建

fdoird build --> 生成APK \
--> 和自己构建的APK进行对比(需要在meta文件中配置`Binaries`来向fdroid告知需要对比APK的路径) \
--> 对比二进制一致 --> 上架 froid store
```

对于 `FLutter` 应用来说, 主要需要保证

1. 构建路径相同 (比如我是在 `/home/runner/foo` 目录下执行 `flutter build` 进行构建,
   对方也必须保证目录一致, 否则生成的二进制会不一致)
2. `JDK` 版本一致. F-Droid 要求使用 `JDK17`.
3. `NDK` 版本一致, Flutter 内部默认托管 `NDK` 版本, 因此没有特殊原因不需要指定.
4. 其他环境, 包括操作系统最好保持一致(windows/macos/linux), 不同发行版之间可能并不重要,
   但也最好能够保持一致防止一些奇奇怪怪的问题.

如果你要上架的应用和我一样(使用 flutter, 使用 vx.y.z+n 的版本号. 并在 `Github Action` 构建),
那不妨直接抄我的作业, 可以节省很多时间. 具体可以查阅 [`metadata` 如何填写](#3-metadata-如何填写)

## 2. 如何让自己的 App 可以被 `F-Droid` 收录

官方其实已经给出了比较详细的 [教程][fdroid-submitting-url], 我这边根据自己接入 App 的实际
情况, 对这个教程做出一些补充:

1. `fork` [Data](https://gitlab.com/fdroid/fdroiddata) 到自己的库中
2. `git clone --depth=1 https://gitlab.com/YOUR_ACCOUNT/fdroiddata /path/to/your/fdroiddata`
3. `cd /path/to/your/fdroiddata`
4. `git checkout -b io.github.foo.bar`
5. 将 `template` 中的 `yml` 选取一个复制到 `metadata/io.github.foo.bar.yml`
   (不要复制哪一个? 当然选取和自己 app 最合适的, 比如我的应用是一个 Flutter 应用, 当然选择
   [build-flutter.yml][fdroid-flutter-template] 作为模板构建)
6. 补全`io.github.foo.bar.yml`, 这里涉及的问题最多, 我会在
   [3. `metadata` 如何填写](#3-metadata-如何填写) 中详细说明一些涉及的问题
7. 本地测试, 具体可以查课 [2.1. 本地测试 `fdroid build`](#21-本地测试-fdroid-build)
8. 使用 `New App: io.github.foo.bar` 作为标签提交到自己的分支中, 并创建一个合并请求.

### 2.1. 本地测试 `fdroid build`

这部分按照 [提交快速指南](fdroid-submitting-url) 操作即可, 这里只指出几个遇到的问题

```sh
git clone --depth=1 https://gitlab.com/fdroid/fdroidserver ~/fdroidserver
#sudo sh -c 'apt-get update &&apt-get install -y docker.io'
sudo docker run --rm -itu vagrant --entrypoint /bin/bash \
  -v ~/fdroiddata:/build:z \
  -v ~/fdroidserver:/home/vagrant/fdroidserver:Z \
  registry.gitlab.com/fdroid/fdroidserver:buildserver

# inside container
# 对于这种方式启动的server, 是不会执行 `metadata.yml` 中 `sudo` 内的命令, 如果有这些命令
# (比如对于可重复构建来说, 由于需要安装对应JDK, 这里必然会有一些命令) 则需要手动执行之.
# 当然手写一个临时脚本并挂载到docker内一键执行也是可行的.
. /etc/profile
export PATH="$fdroidserver:$PATH" PYTHONPATH="$fdroidserver"
cd /build
fdroid readmeta
fdroid rewritemeta io.github.foo.bar
# 对于新应用, checkoutupdates可能会报错(因为repo根本没有可能outdate的内容, 可以跳过)
fdroid checkupdates --allow-dirty io.github.foo.bar
fdroid lint io.github.foo.bar
# 对于中国大陆地区, 强烈建议挂上对应的vpn或者加速器, 否则会因为各种网络问题build失败.
# 一旦build失败, 需要退出容器后重启容器并重新执行上述操作
# 如果 /build/build 中有残留build文件 (比如 io.github.foo.bar 目录), 则先删除它们后再
# 执行重新上面的命令
# 如果遇到stuck流程的问题, 可以加上 -v 或 --verbose 执行命令并查看具体日志.
fdroid build io.github.foo.bar

```

## 3. `metadata` 如何填写

直接上一个实例, 还是我的应用为基础, 里面包含了一些重要字段的用途, 更多元数据字段可以参考
[build metadata](https://f-droid.org/en/docs/Build_Metadata_Reference/)

```yaml
# 分类, 这里的分类填写必须是fdroid已知的
Categories:
  - Sports & Health
License: Apache-2.0
AuthorName: FriesI23
AuthorEmail: FriesI23@outlook.com
SourceCode: https://github.com/FriesI23/mhabit
IssueTracker: https://github.com/FriesI23/mhabit/issues
Changelog: https://github.com/FriesI23/mhabit/blob/main/CHANGELOG.md
Donate: https://www.buymeacoffee.com/d49cb87qgww

AutoName: Table Habit

RepoType: git
Repo: https://github.com/FriesI23/mhabit
# 这个是可重复构建需要的字段, 关于可重复构建可以参考本文可重复构建部分
# 这里主要是提供一个自己签名构建的apk文件, fdroid需要将`fdroid build`构建出来的未签名apk
# 和这个apk进行二进制对比, 如果所有二进制文件一致, fdroid就可以使用你签名的apk发布应用
# (而不是fdroid签名的apk)
Binaries: https://github.com/FriesI23/mhabit/releases/download/v%v%2B%c/app-release.apk

Builds:
  - versionName: 1.3.0
    versionCode: 8
    commit: v1.3.0+8
    # 使用submodule而不是srclib进行构建
    # 关于为什么使用submodule, fdoird给出了详细的解释, 具体可以查看:
    # https://gitlab.com/fdroid/fdroiddata/-/merge_requests/13058#note_1408914197
    # 简而言之: 使用submodule可以自行更新fdoird构建时使用的依赖(比如flutterSDK)
    # 在更新依赖版本时只需要更新submodule, 而不需要更新metadata并重新向fdroid/data提交
    # 一个MR (省事)
    submodules: true
    # 这里主要预处理一些事项, 对于flutter应用, 可重复构建的前提之一就是需要保证构建路径相同
    # (不同的路径, e.g. /path1/flutterapp/ /path2/flutterapp, 会产生不同的二进制文件)
    # 创建 `/home/runner/` 路径是为了与 `Github Action`中的路径保持一致
    # (我自己构建的apk使用github action中的checkout@v3进行构建, 如果你是用其他方式或者
    # 其他checkout版本进行构建, 请自定义这里的内容, 总之保证构建路径是一致的即可)
    sudo:
      - apt-get update
      - apt-get install -y openjdk-17-jdk-headless
      - update-java-alternatives -a
      - mkdir -p /home/runner/
      - chown vagrant /home/runner/
    output: build/app/outputs/flutter-apk/app-release.apk
    rm:
      - .vscode
      - demo
      - ios
    # server中拉取的仓库默认在 `/build/build/io.github.foo.bar`, 将该目录移动到
    # `/home/runner/work/...` 也是为了可重复构建中保持路径一致
    prebuild:
      - sed -i -e '/signingConfig /d' android/app/build.gradle
      - export repo=/home/runner/work/mhabit
      - mkdir -p $repo
      - cd ..
      - mv io.github.friesi23.mhabit $repo/mhabit
      - pushd $repo/mhabit
      - export PUB_CACHE=$(pwd)/.pub-cache
      - .flutter/bin/flutter config --no-analytics
      - .flutter/bin/flutter pub get
      - popd
      - mv $repo/mhabit io.github.friesi23.mhabit
    scanignore:
      - .flutter/packages/flutter_tools/gradle/flutter.gradle
      - .flutter/bin/cache
    scandelete:
      - .flutter
      - .pub-cache
    # 这里移动目录的目的和 `prebuild` 中是一致的
    build:
      - export repo=/home/runner/work/mhabit
      - cd ..
      - mv io.github.friesi23.mhabit $repo/mhabit
      - pushd $repo/mhabit
      - export PUB_CACHE=$(pwd)/.pub-cache
      - .flutter/bin/flutter build apk
      - popd
      - mv $repo/mhabit io.github.friesi23.mhabit

# 可以使用 `apksigner verify --print-certs app-relaese.apk | grep SHA-256` 获取
# 本地环境可以在fdoirdserver提供的docker中执行, 或者自己本地部署fdoirdserver并执行,
# 或者就联系frdoid维护人员协助生成吧(他们都很友善的)
AllowedAPKSigningKeys: 4a31e799063f721d62135f0925f316c2f5e5ab08b462fc4b957673c9b40869b5

# 这里执行fdroid如何可以知道你的app更新了, 配置后fdroid就可以通过规则自动更新metadata文件
# 不配置的话每次升级版本就需要手动更新文件并提交一个MR (和submodule一样, 可以将版本更新和
# fdorid仓库MR解耦, 可以节省很多时间)
AutoUpdateMode: Version
UpdateCheckMode: Tags ^v.*$
UpdateCheckData: pubspec.yaml|version:\s.+\+(\d+)|.|version:\s(.+)\+
CurrentVersion: 1.3.2
CurrentVersionCode: 10
```

## 4. 总结

以上就是本次接入 `F-Droid` 的一些个人经验, 如果有什么问题可以在 `issue` 中直接指出. 也希望
能够帮助到同样开发自由软件但是没有接入商店相关经验的同僚么.

[mhabit-github-url]: https://github.com/FriesI23/mhabit
[mhabit-fdroid-url]: https://f-droid.org/en/packages/io.github.friesi23.mhabit
[mhabit-pic-1]: https://github.com/FriesI23/mhabit/blob/main/fastlane/metadata/android/en-US/images/phoneScreenshots/1.png?raw=true
[mhabit-pic-2]: https://github.com/FriesI23/mhabit/blob/main/fastlane/metadata/android/en-US/images/phoneScreenshots/3.png?raw=true
[fdroid-mr-url]: https://gitlab.com/fdroid/fdroiddata/-/merge_requests/13058
[fdroid-submitting-url]: https://f-droid.org/en/docs/Submitting_to_F-Droid_Quick_Start_Guide
[fdroid-flutter-template]: https://gitlab.com/fdroid/fdroiddata/-/blob/master/templates/build-flutter.yml
[fastlane-structure]: https://gitlab.com/-/snippets/1895688
[fdroid-rebuild-doc]: https://f-droid.org/zh_Hans/docs/Reproducible_Builds/
