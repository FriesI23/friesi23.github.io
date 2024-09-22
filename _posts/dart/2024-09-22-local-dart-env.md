---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 本地多 Dart 环境配置
excerpt: |
  在 Dart Package 开发中, 管理并使用特定 Dart-SDK 版本很有必要.
  常规方法如使用 fvm 不适合纯 Dart Package 开发, 因此需要手动或通过工具 (asdf) 获取 Dart-SDK.
  本文主要分为两部分: 如何获取特定版本的 Dart-SDK 与如何在 VSCode 中进行配置.
author: FriesI23
date: 2024-09-22 14:00:00 +0800
category: dart
tags:
  - dart
  - dart-sdk
  - sdk
  - sdk-manager
  - asdf
---

一般在开发纯 Dart Package 时, 需要一个完整的特定 `Dart-SDK` 环境.
在 Flutter 项目开发中, 可以使用 `fvm` 对不同版本的 flutter 进行管理.
但 `fvm` 中通常不包含完整的 `Dart-SDK`, 且在开发 Dart Package 时, 由于不依赖 flutter, 使用 `fvm` 很不方便.
此时如果需要使用特定版本的 `Dart-SDK` 时, 必须从 [Dart SDK archive][dart-sdks] 处手动下载对应的包并设定相关目录.

下面将分为两个部分来介绍如何正确配置特定版本的 Dart 开发环境:

1. 获取并安装特定的 `Dart-SDK`.
2. 如何在 `vscode` 中正确配置.

## 1. 获取特定版本的 Dart-SDK

### 1.1. 手动下载

可以从 [Dart SDK archive][dart-sdks] 处下载到对应的 Dart-SDK, 解压并放在任意目录, 如下:

```text
/any/path/
└── 3.3.4
    ├── LICENSE
    ├── README
    ├── bin
    ├── dartdoc_options.yaml
    ├── include
    ├── lib
    ├── revision
    └── version
```

### 1.2. 在非 Windows 环境中使用 `asdf` 获取特定版本的 SDK

手工方法显然是很不方便的, 笔者个人更希望使用一些工具和脚本 (如同 `sdkman` 或 `pyenv`) 来管理这些包, 而 `asdf` 恰巧符合这个要求.

需要注意的是 `asdf` 并不支持非 WSL 环境的 Windows, 具体可以查看[这里][asdf-Windows-iss]的讨论.
Windows 环境可以使用手动配置, 也可以使用 [vox][vox] 代替 `asdf`, 具体可以查看该项目文档.

#### 1.2.1. 安装 `asdf`

`asdf` 文档有详细的[安装流程][asdf-guildeline], 这里就不过多赘述, 笔者只在下面简述一下自己环境的配置流程
(`macos + brew + zsh(omz)`):

```shell
# 1. 安装
brew install asdf
# 2. 在 .zshrc 的 plugin 中加入 asdf
plugins = (asdf)
# 3. 配置相关路径
echo 'export PATH="$HOME/.asdf/shims/:$PATH"' >> $HOME/.zshrc
```

#### 1.2.2. 安装 `asdf-dart` Plugin

执行 `asdf plugin add dart https://github.com/patoconnor43/asdf-dart.git` 进行安装.

#### 1.2.3. 下载 `Dart-SDK`

假设需要的版本是 `3.3.4`, 使用 `asdf install dart 3.3.4` 命令进行安装.
安装后在需要使用该 SDK 的目录下执行 `asdf local dart 3.3.4`, 此时目录下会生成一个文件 `.tool_versions`.

检查配置是否生效:

```shell
$ cat .tool-versions
dart 3.3.4
$ asdf current dart                                                                                               130 ↵
dart            3.3.4           /current/path/.tool-versions
$ which dart
/Users/admin/.asdf/shims//dart
```

`asdf` 会将下载的 SDK 存放在对应目录, 具体如下:

```shell
~/.asdf » tree -L 3
.
├── downloads
│   └── ...
├── installs        // 所有安装的sdk都会放在这里
│   └── dart
│       └── 3.3.4
├── plugins         // asdf-dart 代码
│   └── dart
│       ├── LICENSE
│       ├── README.md
│       ├── bin
│       └── tools
└── shims           // 可执行二进制代理存放目录
    ├── dart
    └── dartaotruntime
```

## 2. 在 Vscode 中正确配置 SDK

上节中已经通过任一方式获取到自己需要版本的 SDK, 现在需要在编程环境中使用到这个特定的 SDK
(而不是系统默认安装的或者路径上的其他版本), 还需要做一些额外的工作, 一言蔽之就是要让自己当前的开发环境路径都指向刚刚下载的 `Dart-SDK`.
这里以 `vscode` 为例.

为了保证 `settings.json` 中的配置在不同环境下都尽量可用, 可以先将 SDK 的目录做一个软链到当前路径.
同时由于 `dart publish` 不允许在当前项目的根目录下存在目录级别的软链, 因此将软链放在子目录中:

```shell
mkdir .dart_sdk
ln -sf ~/.asdf/installs/dart/3.3.4 .dart_sdk/3.3.4
# 最后记得将这些目录都添加到 gitignore 防止被版本管理
echo '.dart_sdk/' >> .gitignore
```

此时 SDK 路径被固定在了 `.dart_sdk/3.3.4`, 这会方便后续配置.

在项目工作目录中运行 `mkdir .vscode && touch .vscode/settings.json` 新建一个配置, 并在配置中存在如下内容:

```json
{
  // 如果没有软链过来, 就是用 sdk 所在路径.
  // 固定在特定位置的好处在于多位置使用同一配置的情况, 比如一个项目中上传了配置,
  // 所有机器 pull 代码后不需要修改配置, 而是将自己的 sdk 路径 link 到该配置中的路径即可.
  "dart.sdkPath": ".dart_sdk/3.3.4",
  // 保证在编程时使用的 sdk (比如跳转或语法分析) 和 terminal shell 中使用的版本相同.
  "dart.addSdkToTerminalPath": true,
  // 如果 Sdk 不属于项目代码的一部分, 就不要让各种扫描器排除掉.
  "dart.analysisExcludedFolders": [".dart_sdk"],
  "files.exclude": {
    "**/.git": true,
    "**/.dart_sdk": true
  }
}
```

通过 `Reload Windows` 重载当前环境并通过查看编辑器右下角内容确认 dart 版本, 不出意外应该已经在使用配置中的 SDK 了, 大功告成.

<!-- refs -->

[dart-sdks]: https://dart.dev/get-dart/archive
[asdf-guildeline]: https://asdf-vm.com/guide/getting-started.html
[asdf-Windows-iss]: https://github.com/asdf-vm/asdf/issues/450
[vox]: https://github.com/version-fox/vfox
