---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
#
# File name format: yyyy-mm-dd-tilte.md
title: Flutter Provider 使用介绍
author: FriesI23
date: 2024-05-10 15:15:00 +0800
category: flutter
tags:
  - flutter
  - provider
  - mvvm
dartpad:
  - comment: Provider 示例
    id: e32f9e3da45e0ec1ede6006ec4859288
    mode: flutter
  - comment: ChangeNotifierProvider 示例
    id: 80b552313b127a54563a1658f9c88ee1
    mode: flutter
  - comment: FutureProvider/SteamProvider 示例
    id: 895c6fb58ce375548e95bbeed6fe2f3e
    mode: flutter
---

作为 `flutter` 官方推荐的状态管理工具 (详见[这里][flutter-rcmd]),
`Provider` 相比于一些状态管理框架 `BloC` 更加轻量, 可以在 app 开发中提供更高的灵活性.
下面将先简单介绍一下 `Provider`, 然后将给出一些简单的使用示例, 最后将简单分析源码.

## 1. Provider

> - [Provider][provider-provider]

`Provider` 作为包中基础的一个 `Widget`, 主要作用为: 向该 `Widget` 树上的所有子孙暴露一个公共的值.

想象一下一个 `Widget` 树中, 有多个 `Widget` 需要共享获取一个变量, 并能够进行更新
(注意, 这里不涉及监听, 监听需要使用 `ListenableProvider` 以及其继承 `Widget`, 比如 `ChangeNotifierProvider`).
此时有几个基础的解决方案:

1. 使用全局变量或者单例, 但是不管哪一种都存在管理数据生命周期的问题.
   过多的全局变量或者单例会是使得代码复杂度快速增长, 最后不得不手动创建一个管理生命周期的模块.
   最后很可能是重复造轮子, 实现了一遍 `bloC` (一点私货, 我个人很不喜欢重复造轮子).
2. 通过 `Widget` 构造参数将数据一路传下去. 很明显, 这一方面会导致 `Widget` 参数快速增长且包含了一堆自身不需要的参数;
   同时随着代码复杂度增加, 增加参数会变得越来越**重**, 可能增加一个参数需要修改十几个 `Widget` 的构造函数,
   但仅仅是为了偷穿参数.
3. 自己实现一个 `InheritedWidget`, 然后在 `Widget` 中使用 `<Your InheritedWidget>.of(context)` 获取.
   这个相比上面两种方法已具备一定可行性, 但是 `Provider Package` 本身就是针对 `InheritedWidget` 的封装;
   So, 不要重复造轮子!
   > A wrapper around InheritedWidget to make them easier to use and more reusable.

有了 `Provider`, 我们便可以写出以下代码:

```dart
/// 这里先创建一个简单对象, 假设该对象有很多 Widget 需要使用其中的值.
class InfoModel {
    final String name;
    final String addr;
    int age;

    YourModel(this.name, this.addr, this.age);
}
```

```dart
/// 这里 Provider Widget 对数据进行初始化
Provider<InfoModel>(
    create: (context) => InfoModel("John", "Earth", 10),
    child: // 这里传入子 Widget
),
```

```dart
/// 使用以下两种方法都可以获取数据, 两者是等级的, 事实上第一行代码就是对第二行代码的包装
final info = context.read<InfoModel>();
final info = Provider.of<InfoModel>(context, listen: false);
info.age += 1; //将 age + 1
```

### 1.1. 完整示例

{% include dartpad.html index=0 width="100%" height="600" %}

### 1.2. 需要注意

`Provider` 生效的范围, 也就是 `context` 的位置. 只有 `Provider` 下面的 `context` 才能获取导数据.
且 `Navigator` 导航到新页面后, 需要使用 `Provider.value` 将对象传递过去.

```dart
/// e.g.1 在 Widget Tree 中
Widget1(
    data: context.read<InfoModel>();    // throw ProviderNotFoundException
    child: Provider<InfoModel>(
        create: (context) => InfoModel("John", "Earth", 10),
        child: Widget2(
            data: context.read<InfoModel>();    // ok
        ),
    ),
);

/// e.g.2 在导航到新界面中, 假设方法是一个StatefulWidget中定一个callback
void _onPressed() async {
    final info = context.read<InfoModel>(); // 注意context, 必须在导航前获取
    final result = Navigator.of(context).push(
        MaterialPageRoute(
            // builder内部已经切换到新的 Widget Tree, 这里使用 `context.read<InfoModel>()` 将会报错
            builder: (context) => Provider.value(
                // 没有 Provider 内部使用时会报错(ProviderNotFoundException)
                value: info,
                child: const NewPage(),
            ),
        ),
    );
}
```

## 2. ChangeNotifierProvider

> - [ChangeNotifierProvider][provider-changenotifierprovider]
> - [ChangeNotifier][flutter-changenotifier]

相对于 [`Provider`](#1-provider), `ChangeNotifierProvider` 提供了监听与通知的功能,
`Widget` 可以监听数据行为并进行刷新. 这种行为使得 `ChangeNotifierProvider`
很适合作为 [MVVM][mvvm] 模式中 `ViewModel` 部分.

首先, 我们和 `Provider` 的示例一样创建一个对象, 但是不同在于这次我们引入一个新类 `ChangeNotifier`.

```dart
// or: class InfoModel extends ChangeNotifier {
class InfoModel with ChangeNotifier {
  final String name;
  final String addr;
  int _age;

  YourModel(this.name, this.addr, int age): _age = age;

  int get age => _age;

  set age(int newAge) {
    _age = newAge;
    // 炸裂我们通知所有监听组件变化行为
    notifyListeners();
  }
}
```

```dart
/// 使用 ChangeNotifierProvider Widget 对数据进行初始化
ChangeNotifierProvider<InfoModel>(
    create: (context) => InfoModel("John", "Earth", 10),
    child: // 这里传入子 Widget
),
```

对于如何使用这个 `Provider`, 最简单的方式就是使用 `context.read<InfoModel>()` 获取数据,
`context.watch<InfoModel>()` 对 `context` 对应的 `Widget` 进行绑定, 或者使用
`context.select<InfoModel，int>(callback)` 对单独的数据进行监听. 不过一般情况下针对后两者,
更推荐使用 `Consumer` 与 `Selector` 这两个 `Widget`, 这会在后面介绍, 这里先列举最简单的使用方法:

```dart
Widget build(BuildContext context) {
  // 只要 InfoModel 内调用了 notifyListeners, 该 build 对应的 Widget 就会被重建.
  final vm = context.watch<InfoModel>();
  return TextButton(onPressed: () => context.read<InfoModel>.age += 1, child: Text(vm.toString()));
}

Widget build(BuildContext context) {
  // 只有 select 中的值发生变化, 该 build 对应的 Widget 才会被重建.
  final age = context.select<InfoModel>((vm) => vm.age);
  return TextButton(onPressed: () => context.read<InfoModel>.age += 1, child: Text(age));
}
```

### 2.1. 完整示例

{% include dartpad.html index=1 width="100%" height="600" %}

### 2.2. 需要注意

`context.watch<T>()`, `context.select<T,R>(cb)`, `Provider.of<T>(context)` 都只能在 `build` 中使用;
如果需要在构建树外或只获取数据结构, 永远使用 `context.read<T>()`, 这些获取函数都是 `O(1)` 的, 不用担心性能问题.

获取和绑定 `Provider` 的时候请务必注意 `context` 的范围, 只有在清楚自己在干什么的时候使用变量引用 `Provider`,
否则请直接使用 `context.read<T>()` 进行获取. 这里留一个问题, 你能看出这段代码片段可能会导致的问题么:

```dart
// 假设方法在一个 StatefulWidget 的 State 中
void _onPressed() async {
  if (!mount) return;
  final Model vm = context.read<Model>();
  final bool result = await openDialog();
  if (!mount || !result) return;
  vm.confirmed = result;
}
```

## 3. FutureProvider / StreamProvider

顾名思义, 这两个就是 [`Provider`](#1-provider) 的 `Future` 和 `Stream` 版本, 使用方法也大差不差,
因此这里就以 `FutureProvider` 为例:

```dart
class InfoModel {
  late final String name;
  late final String addr;
  late int age;
  late final Future<bool> _init;

  InfoModel() {
    Future<bool> init() async {
      name = "John";
      addr = "Earth";
      age = 10;
      return true;
    }

    _init = init();
  }

  Future<bool> get init => _init;
}
```

```dart
FutureProvider<InfoModel?>(
  create: (context) async {
    final info = InfoModel();
    await info.init;
    return info;
  },
  initialData: null,
  child: // 这里传入子 Widget
),
```

```dart
final info = context.read<InfoModel?>();
```

### 3.1. 完整代码

{% include dartpad.html index=2 width="100%" height="600" %}

### 3.2. 需要注意

`FutureProvider` / `SteamProvider` 和 `Provider` 一样只会构建一次数据, 除非这些 `Provider` 被重新构建.

## 关于各种 `Provider` 中的 `lazy` 参数

[flutter-rcmd]: https://docs.flutter.dev/data-and-backend/state-mgmt/simple#accessing-the-state
[mvvm]: https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93viewmodel
[provider-provider]: https://pub.dev/documentation/provider/latest/provider/Provider-class.html
[provider-changenotifierprovider]: https://pub.dev/documentation/provider/latest/provider/ChangeNotifierProvider-class.html
[flutter-changenotifier]: https://api.flutter.dev/flutter/foundation/ChangeNotifier-class.html
