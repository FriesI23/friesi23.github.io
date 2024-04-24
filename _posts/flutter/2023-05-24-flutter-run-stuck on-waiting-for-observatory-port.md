---
layout: post
title: "Flutter调试日志报错 - waiting for observatory port"
date: 2023-05-24 09:00:00 +0800
category: android
tags:
  - flutter
  - miui
  - android
  - debug
  - logging
---

<!--
 friesi23.github.io (c) by weooh

 friesi23.github.io is licensed under a
 Creative Commons Attribution-ShareAlike 4.0 International License.

 You should have received a copy of the license along with this
 work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
-->

## 问题

近期在真机上调试 flutter 应用时, 虽然 app 已经在机器上安装并且启动，但是始终无法连接调试服务器，
在模拟器上时缺是可以正常连接服务器的，具体日志如下:

```shell
$ flutter run --debug --verbose
...
[   +9 ms] Stopping app 'app-debug.apk' on Redmi Note 7.
[        ] executing: /Path/To/adb -s 4ef1bd95 shell am force-stop org.example.app
[ +129 ms] executing: /Path/To/adb -s 4ef1bd95 shell pm list packages org.example.app
[ +149 ms] package:org.example.app
[   +1 ms] executing: /Path/To/adb -s 4ef1bd95 shell cat /data/local/tmp/sky.org.example.app.sha1
[ +110 ms] 414badd53655760048218d30c949cabe2f90a436
[   +1 ms] Installing APK.
[        ] Installing build\app\outputs\flutter-apk\app-debug.apk...
[        ] executing: /Path/To/adb -s 4ef1bd95 install -t -r D:\Users\weooh\Documents\Projects\mhabit\build\app\outputs\flutter-apk\app-debug.apk
[+5746 ms] Performing Streamed Install
                    Success
[        ] Installing build\app\outputs\flutter-apk\app-debug.apk... (completed in 5.7s)
[        ] executing: /Path/To/adb -s 4ef1bd95 shell echo -n fb80be699d0db784baf5c448f563b4e8af8a4624 > /data/local/tmp/sky.org.example.app.sha1
[  +83 ms] executing: /Path/To/adb -s 4ef1bd95 shell -x logcat -v time -t 1
[ +497 ms] --------- beginning of system
                    05-24 08:35:21.353 W/MiuiPerfServiceClient( 3561): interceptAndQueuing:15974|com.android.settings|284|93|unknown|null|com.android.settings/com.android.settings.SubSettings|862987446123972|Slow main thread|6
[  +13 ms] executing: /Path/To/adb -s 4ef1bd95 shell am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -f 0x20000000 --ez enable-dart-profiling true --ez
enable-checked-mode true --ez verify-entry-points true org.example.app/org.example.app.MainActivity
[ +217 ms] Starting: Intent { act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x20000000 cmp=org.example.app/.MainActivity (has extras) }
[        ] Waiting for observatory port to be available...
```

## 解决方法

个人使用的机器是红米的 `Redmi Note 7`, 由于 `MIUI` 新版默认设置中 `日志记录器缓冲器大小` 为 `off`,
导致 `adb logcat` 无法正确输出日志，解决方案如下：

1. 开启开发者权限，具体查看 [How to Enable Developer Options on Xiaomi Devices](https://xiaomiui.net/how-to-enable-developer-options-on-xiaomi-devices-2504/)

2. 进入开发者选项，将 `日志记录器缓冲器大小` 选项调整为最大

![pic1](https://github.com/FriesI23/friesi23.github.io/assets/20661034/fe286ebd-df0e-4230-8c73-76e9a206a217){:width="200"}
![pic2](https://github.com/FriesI23/friesi23.github.io/assets/20661034/5491ac8b-917e-47ae-b536-dc1bd0db859d){:width="200"}
