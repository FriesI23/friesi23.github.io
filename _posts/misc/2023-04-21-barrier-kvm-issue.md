---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: "Berrier KVM使用中出现的一些问题"
author: FriesI23
date: 2023-04-21 14:22:00 +0800
category: kvm
tags:
  - kvm
  - barrier
---

## 1. 启动`Barrier`时出现 `ipc connection error, connection refuse` 日志

```log
[2023-04-21T09:10:00] INFO: connecting to service...
[2023-04-21T09:10:04] ERROR: ipc connection error, connection refuse
```

该问题出现可能是因为`Barrier`服务没有启动, 解决方法如下:

1. 打开`Services`, 启动 `Barrier` 服务

![1-1](https://user-images.githubusercontent.com/20661034/233557727-b3b37fb4-fdb2-4d81-8cd6-8cc227f48afd.jpg)

2. 启动 `Barrier.exe`, 点击 `Start` 启动服务

## 2. 在 `Server` 端桌面启动缩放时, 鼠标跨越到另一个客户端后会停留在右下角并无法正常移动鼠标

该问题主要出现于鼠标在不同 DPI 配置的屏幕上移动, `issue` 的讨论在 [这里](https://github.com/debauchee/barrier/issues/94);

问题的原因和解决方法分别在 [这里](https://github.com/debauchee/barrier/issues/94#issuecomment-979628855) 和 [这里](https://github.com/debauchee/barrier/issues/94#issuecomment-934400562)

简单来说, 由于代码中使用了不支持 DPI 变化的 API, 导致鼠标移动到右下角区域时, 对于代码而言实际时超边界行为, 因此会出现无响应的情况.

![2-ref01](https://user-images.githubusercontent.com/1330321/143516839-1593e947-46ad-42de-9164-576fe8635a8c.png)

> Picture Copyright: @yume-chan [here](https://github.com/debauchee/barrier/issues/94#issuecomment-979628855)

1. 找到 `services` 对应的文件位置, 如图

![2-1](https://user-images.githubusercontent.com/20661034/233560061-84b3cd5e-0c38-4c04-9c6d-4daa85b33509.jpg)

2. 右键打开该文件 `Properties`, 切换到 `Compatibility` `(兼容性)` 标签, 点击 `Change high DPI settings`

![2-2](https://user-images.githubusercontent.com/20661034/233561010-8043de68-4b3f-4453-bfc9-d705180d6fd3.jpg)

3. 勾选 `High DPI scaling behaviour`, 保持 `perform` 在 `Application`

![2-3](https://user-images.githubusercontent.com/20661034/233561601-25e0a641-bc28-421a-b854-610757d96dd7.jpg)

4. 打开`Services`, 重新启动 `Barrier` 服务
