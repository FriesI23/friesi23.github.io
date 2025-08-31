---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 通过环境变量为 Flutter Windows 增加 Flavor 支持
excerpt: |
  Flutter 已经为 Android / Darwin 增加 Flavor 支持，这有助于分离开发与发布环境构建，
  但 Windows 和 Linux 上的推进接近三年似乎也没有什么进展。
  本文将介绍如果通过使用 env 达到近似效果。
author: FriesI23
date: 2025-08-31 09:00:00 +0800
category: flutter
tags:
  - flutter
  - flutter-build
  - flutter-windows
  - flutter-flavor
---

Flutter 已经为 Android / Darwin 增加 Flavor 支持，这有助于分离开发与发布环境构建，并可以为不同渠道的 Package 分离配置。
但 Windows 和 Linux 上的推进接近三年似乎也没有什么进展（详见 ["Support flavors for Windows #98994"][flutter-support-flavor-for-windows]）。

为了方便在 Windows 上进行开发，Flavor 的存在很有必要，所以有了这篇文章。下面将介绍通过使用**环境变量**来达到类似 `--flavor` 的效果。

## 1. 在 CMake 中引入 Flavor 环境变量

CMake 中可以读取当前构建的环境变量，FLutter flavor 使用 `FLUTTER_APP_FLAVOR` 环境变量处理不同的 Flavor，
不过我们不能使用这个变量，会提示这些变量由 Flutter 框架管理，构建无法进行。
因此这里使用 `APP_FLAVOR_WIN` 进行区分，将以下内容按需添加到 `windows/CMakeLists.txt` 中：

```cmake
set(APP_NAME "<YOUR_APP_NAME>")
add_definitions(-DAPP_NAME="${APP_NAME}")

if(DEFINED ENV{APP_FLAVOR_WIN})
  # CMake 中定义 FLAVOR 区分不同的 flavor
  set(FLAVOR "$ENV{APP_FLAVOR_WIN}")
  # 将其引入 cpp 编译中
  add_definitions(-DFLAVOR="${FLAVOR}")
  # 下面区分不同的 flavor，请按照自己要求进行添加/删除/修改
  if(FLAVOR STREQUAL "f_dev")
    # 定义 FLAVOR_NAME，这里作为 FLAVOR 的别名用于区分路径，后面会用到
    set(FLAVOR_NAME "dev")
    # 引入 APP_TITLE_SUFFIX，用于在 cpp 中修改 windows title，后面会用到
    add_definitions(-DAPP_TITLE_SUFFIX=" - ${FLAVOR_NAME}")
  # elseif(FLAVOR STREQUAL "f_store")
  #   set(FLAVOR_NAME "store")
  # elseif(FLAVOR STREQUAL "f_generic")
  #   set(FLAVOR_NAME "")
  else()
    # 不支持的 flavor 就报错退出，当然也可以设置默认值不退出
    message(FATAL_ERROR "Flavor:${FLAVOR} is not support, abort CMake.")
  endif()
  message("Building Windows with flavor: '${FLAVOR}'")
  # 和 flutter 现有支持的 flavor 风格保持相同，将不同的 flavor 最终构建目录进行区分
  # 注意：flutter run 只支持默认构建目录，其他目录不被识别，后面将使用软链进行处理
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/runner/Debug-${FLAVOR}")
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/runner/Release-${FLAVOR}")
endif()
```

## 2. 根据不同 Flavor 处理相关内容

为 windows 引入 flavor 的初衷是 [`path_provider`][pub-path-provider] 在 windows 上的路径由 `windows/runner/Runner.rc` 中的配置确定，
具体为 `%AppData%\Roaming\<CompanyName>\<ProductName>`，比如 `%AppData%\Roaming\io.github.friesi23\mhabit`。

而这导致默认开发时启动的应用也会读取实际使用时的用户数据，这显然不合理。一个直观的方案是在代码中进行处理，不过这显然很不优雅，
我希望能够获得在 macos 或者 linux 上一样的开发体验（macos 上拥有 flavor，linux 在分发时可以通过各种容器方案比如 appimage 或者 flatpak 对配置进行隔离）。
因此本节内容主要用于解决 `path_provider` 对应的路径问题，如果由其他需求也可以通过下面的内容举一反三。

首先修改 `windows/runner/Runner.rc` 文件，将其命名为 `windows/runner/Runner.rc.in`，然后内部修改如下：

```rc
// ...
    BLOCK "StringFileInfo"
    BEGIN
        BLOCK "040904e4"
        BEGIN
            VALUE "CompanyName", "<org.example.company>" "\0"
            VALUE "FileDescription", "{FILE_DESCRIPTION}" "\0"
            VALUE "FileVersion", VERSION_AS_STRING "\0"
            VALUE "InternalName", "{INTERNAL_NAME}" "\0"
            VALUE "LegalCopyright", "Copyright (C) 2024 io.github.friesi23. All rights reserved." "\0"
            VALUE "OriginalFilename", "<app>.exe" "\0"
            VALUE "ProductName", "{PRODUCT_NAME}" "\0"
            VALUE "ProductVersion", VERSION_AS_STRING "\0"
        END
    END
// ...
```

将 `FileDescription`，`InternalName`，`ProductName` 使用占位符进行替换，然后修改 `windows/runner/CMakeLists.txt`，添加如下内容：

```cmake
set(ORIGINAL_RC "Runner.rc.in")
set(GENERATED_RC "Runner.rc")
file(READ ${ORIGINAL_RC} RC_CONTENT)
# FLAVOR_NAME 在 windows/CMakeLists.txt 中定义
# 下面代码的工作是对占位符进行替换
if(FLAVOR_NAME)
    string(REPLACE "{PRODUCT_NAME}" "${BINARY_NAME}-${FLAVOR_NAME}" RC_CONTENT "${RC_CONTENT}")
    string(REPLACE "{FILE_DESCRIPTION}" "${BINARY_NAME}-${FLAVOR_NAME}" RC_CONTENT "${RC_CONTENT}")
    string(REPLACE "{INTERNAL_NAME}" "${BINARY_NAME}-${FLAVOR_NAME}" RC_CONTENT "${RC_CONTENT}")
else()
    string(REPLACE "{PRODUCT_NAME}" "${BINARY_NAME}" RC_CONTENT "${RC_CONTENT}")
    string(REPLACE "{FILE_DESCRIPTION}" "${BINARY_NAME}" RC_CONTENT "${RC_CONTENT}")
    string(REPLACE "{INTERNAL_NAME}" "${BINARY_NAME}" RC_CONTENT "${RC_CONTENT}")
endif()
# 写入 windows/runner/Runner.rc 保证路径与修改前一致
file(WRITE ${GENERATED_RC} "${RC_CONTENT}")
```

同文件找到 `add_executable(${BINARY_NAME} WIN32 ...` 调用，并修改如下：

```cmake
# 将 "Runner.rc" 替换为 GENERATED_RC 变量，主要为了保持代码一致，逻辑上当然也可以不改
add_executable(${BINARY_NAME} WIN32
  "flutter_window.cpp"
  "main.cpp"
  "utils.cpp"
  "win32_window.cpp"
  "${FLUTTER_MANAGED_DIR}/generated_plugin_registrant.cc"
  "${GENERATED_RC}"
  "runner.exe.manifest"
)
```

至此已经可以让构建流程根据 `APP_FLAVOR_WIN` 变量达到 flavor 的效果，下面一节会解决 `flutter run` 的问题。

## 3. 兼容标准 flutter 相关命令

在[第一节](#1-在-cmake-中引入-flavor-环境变量)中修改 `windows/CMakeLists.txt` 中包含如下：

```cmake
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/runner/Debug-${FLAVOR}")
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/runner/Release-${FLAVOR}")
```

这会将构建后的产物输出至非标准目录，而由于 flutter 本身没有实际支持 windows 下的 flavor，
因此相关执行程序需要寻找的目录是固定的，即 `build\windows\<ARCH\runner\Release(Debug)`。

可以简单注释掉这两条命令来规避问题，但会导致本地每次构建不同 flavor 时都需要重新构建。如果希望和标准的 `--flavor` 行为保持一致，
一个可行的方案是使用软链将输出目录指向标准目录，具体操作如下：

1. 在 `windows/CMakeLists.txt` 下增加如下命令，作用为每次构建前删除软链，防止无 Flavor 时写入错误的目录：

   ```cmake
   function(safe_remove path)
     if(IS_SYMLINK "${path}")
       message("Removing symlink: ${path}")
       file(REMOVE "${path}")
     # elseif(EXISTS "${path}")
     #   message("Removing directory: ${path}")
     #   file(REMOVE_RECURSE "${path}")
     endif()
   endfunction()

   if(DEFINED FLAVOR)
     # safe_remove("${CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG}")
     # safe_remove("${CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE}")
   else()
     safe_remove("${CMAKE_BINARY_DIR}/runner/Debug")
     safe_remove("${CMAKE_BINARY_DIR}/runner/Release")
   endif()
   ```

2. 在 `windows/runner/CMakeLists.txt` 下增加如下命令，用于在构建完成后创建软链：

   ```cmake
   if(FLAVOR)
     add_custom_command(TARGET ${BINARY_NAME} POST_BUILD
       COMMAND ${CMAKE_COMMAND} -E rm -rf
         "$<IF:$<CONFIG:Debug>,${CMAKE_BINARY_DIR}/runner/Debug,${CMAKE_BINARY_DIR}/runner/Release>"
       COMMAND ${CMAKE_COMMAND} -E create_symlink
         "$<IF:$<CONFIG:Debug>,${CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG},${CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE}>"
         "$<IF:$<CONFIG:Debug>,${CMAKE_BINARY_DIR}/runner/Debug,${CMAKE_BINARY_DIR}/runner/Release>"
     )
   endif()
   ```

至此，完成所有构建流程的修改。

## 4. 使用不同的 Flavor 进行构建

上面修改完成后，我们便可以使用如下命令为不同 Flavor 进行构建：

```powershell
$env:APP_FLAVOR_WIN=<YOUR_FLAVOR_NAME>
flutter build windows
# ...
# Building Windows with flavor: <YOUR_FLAVOR_NAME>
# Building Windows application...
# √ Built build\windows\x64\runner\Release\<app>.exe
Remove-Item Env:\APP_FLAVOR_WIN
```

Flavor 构建后的目录结构如下（以 arch=x86_64 build=release 为例）：

```text
build\windows\x64\runner\Release-<YOUR_FLAVOR_NAME>
build\windows\x64\runner\Release --> build\windows\x64\runner\Release-<YOUR_FLAVOR_NAME>
```

当然无 Flavor 的构建也是允许的：

```powershell
flutter build windows
# ...
# Building Windows application...
# √ Built build\windows\x64\runner\Release\<app>.exe
```

### 4.1. vscode launcher 配置

如果使用 vscode 进行开发，可以考虑在 `launch.json` 中增加如下内容，方便调试使用：

```json
{
  {
    "name": "debug (<YOUR_FLAVOR_NAME>)",
    "request": "launch",
    "type": "dart",
    "flutterMode": "debug",
    "args": [
      "--flavor",
      "<YOUR_FLAVOR_NAME>"
    ],
    "env": {
      "APP_FLAVOR_WIN": "<YOUR_FLAVOR_NAME>"
    }
  },
  {
    "name": "profile (<YOUR_FLAVOR_NAME>)",
    "request": "launch",
    "type": "dart",
    "flutterMode": "profile",
    "args": [
      "--flavor",
      "<YOUR_FLAVOR_NAME>"
    ],
    "env": {
      "APP_FLAVOR_WIN": "<YOUR_FLAVOR_NAME>"
    }
  },
  {
    "name": "release (<YOUR_FLAVOR_NAME>)",
    "request": "launch",
    "type": "dart",
    "flutterMode": "release",
    "args": [
      "--flavor",
      "<YOUR_FLAVOR_NAME>"
    ],
    "env": {
      "APP_FLAVOR_WIN": "<YOUR_FLAVOR_NAME>"
    }
  },
}
```

如此便可以获得兼顾 `windows` `linux` `macos` 三端的统一运行配置。

## 5. 总结

完整修改可以参考[“该 PR”](https://github.com/FriesI23/mhabit/pull/327/files)，里面缺少了 `Profile` 的支持，
如有需要也可以很方便的进行添加。

## F1. 为不同的 Flavor 修改对应的 Windows Title

在[第一节](#1-在-cmake-中引入-flavor-环境变量)中，我们使用 `-D` 传递了一些定义，可以在 windows 的入口处使用。
定位到 `windows/runner/main.cpp`，增加并修改如下：

```cpp
#ifndef APP_NAME
#define APP_NAME L"<YOUR_DEFAULT_APP_NAME>"
#endif

#ifdef APP_TITLE_SUFFIX
#define WINDOW_TITLE APP_NAME APP_TITLE_SUFFIX
#else
#define WINDOW_TITLE APP_NAME
#endif

// ...
//if (!window.Create(L"<YOUR_DEFAULT_APP_NAME>", origin, size)) {
  if (!window.Create(L"" WINDOW_TITLE, origin, size)) {
    return EXIT_FAILURE;
  }
  window.SetQuitOnClose(true);
// ...
```

<!-- refs -->

[flutter-support-flavor-for-windows]: https://github.com/flutter/flutter/issues/98994
[pub-path-provider]: https://pub.dev/packages/path_provider
