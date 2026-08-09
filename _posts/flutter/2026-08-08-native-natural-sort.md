---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 从 compareTo 到 native_natural_sort —— Flutter 字符串排序实践
excerpt: |
  Dart 默认的 compareTo 在人类友好的名称排序场景下问题重重：大小写、CJK 字符、变音符号、数字排序。
  本文记录从发现问题到调研五种技术方案，最终开发出 native_natural_sort 包并接入 mhabit 项目的完整过程。
author: FriesI23
date: 2026-08-08 14:00:00 +0800
category: flutter
tags:
  - flutter
  - dart
  - natural-sort
  - native-natural-sort
  - collation
layout: single-multilang
locale: zh-CN
translations:
  - lang: zh-CN
    url: /post/202608/native-natural-sort
    label: 中文
  - lang: en
    url: /post/en/202608/native-natural-sort
    label: English
---

最近在维护 [Table Habit][mhabit] 时，发现习惯列表的排序不太对劲——明明是按名称排序，
但中文习惯名的顺序毫无规律，数字也排得乱七八糟。这让我开始重新审视项目中用了很久的默认排序方式，
结果发现，一个看似简单的「按名称排序」，背后的坑远比想象的多。

本文将从问题的发现开始，依次介绍修复尝试、方案调研以及最终的实现方案，希望能为遇到类似问题的开发者提供一些参考。

同时，也欢迎体验和交流我封装的 Flutter Package: [**native_natural_sort**][native-natural-sort]。

## 1. 问题

### 1.1. 第一版：compareTo 默认排序

mhabit 支持多种排序方式，其中「按名称排序」是最常用的之一。
第一版实现非常简单，就是 Dart 内置的 `String.compareTo`：

```dart
data.sort((a, b) => a.name.compareTo(b.name));
```

`compareTo` 本质上是**字典序**——按 Unicode 码点逐字符比较。对于纯 ASCII 英文来说似乎工作正常，
但一旦涉及混合大小写、非英文字符、数字，问题就来了。

### 1.2. 第一个坑：大小写

最早被注意到的是大小写问题。`compareTo` 按码点排序，大写字母 `A`（U+0041）的码点小于小写 `a`（U+0061），
导致所有大写开头的名称排在小写前面：

| 输入            | `compareTo` 结果 | 期望结果        |
| --------------- | ---------------- | --------------- |
| `apple, Banana` | `Banana, apple`  | `apple, Banana` |

一个直观的修复是统一转为小写：

```dart
data.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
```

大小写问题解决了。但很快更多的问题出现了。

### 1.3. 第二个坑：CJK、变音符号、数字

`toLowerCase()` 修好了大小写，但根本没有触及排序的根本问题——Unicode 码点顺序 ≠ 人类期望的排序顺序：

| 场景         | 输入                | `compareTo` 结果    | 人类期望            |
| ------------ | ------------------- | ------------------- | ------------------- |
| 数字         | `file2, file10`     | `file10, file2`     | `file2, file10`     |
| 变音符号     | `árbol, amor, azul` | `amor, azul, árbol` | `amor, árbol, azul` |
| 中文（拼音） | `张, 李, 王`        | `张, 李, 王`        | `李, 王, 张`        |
| 德语 ß       | `Straße, Strasse`   | `Strasse, Straße`   | 相等（ß = ss）      |

数字的问题在于 `"10"` 的第一个字符 `"1"` 码点小于 `"2"`，所以 `"10"` 排在 `"2"` 前面。
变音符号 `á`（U+00E1）的码点远大于 `z`（U+007A），所以 `árbol` 被排到了末尾。
中文的问题更复杂——`compareTo` 按 Unicode 码点排序，对于 CJK 统一表意文字区块，
`张`（U+5F20）、`李`（U+674E）、`王`（U+738B）的顺序与拼音 `lǐ, wáng, zhāng` 完全不同。

至此，必须承认：**简单的大小写归一化远远不够，需要一种理解语言规则的排序方式**。

## 2. 方案选择

带着上面的问题，我开始系统性地调研可行的解决方案。最终梳理出五种方向（外加一种看似美好但实际不太可行的折中方案，
在方案 A 之后单独讨论）：

### 2.1. 方案概览

| 方案                                          | 思路                        | 数字排序 | 语言感知 |  包体积影响  |          桥接方式          |
| --------------------------------------------- | --------------------------- | :------: | :------: | :----------: | :------------------------: |
| [A. 手写纯 Dart 自然排序](#solution-a)        | 正则拆分数字 + collation 表 |    ✅    |    ❌    |      无      |            同步            |
| [B. `collection.compareNatural`](#solution-b) | Dart 官方 collection 包     |    ✅    |    ❌    |     极小     |            同步            |
| [C. 打包传统 ICU 数据](#solution-c)           | FFI 链接 ICU 库             |    ✅    |    ✅    |   +10~30MB   |         同步 (FFI)         |
| [D. `icu4x` + `intl4x`](#solution-d)          | Rust ICU4X + Dart FFI 封装  |    ✅    |    ✅    | **显著增加** |         同步 (FFI)         |
| [E. 调用平台原生引擎](#solution-e)            | 委托 OS 内置 API            |    ✅    |    ✅    |      零      | FFI + Platform Method 混合 |

### 2.2. 方案 A：手写纯 Dart 自然排序 {#solution-a}

最朴素的想法——自己实现。按正则将字符串拆分为文本块和数字块，
文本块用 `compareTo` 比较，数字块按数值比较。

**优点**：零依赖，完全可控。

**缺点**：

- 只能解决数字排序，无法处理 locale 感知的比较（CJK、变音符号）
- 要实现完整的 Unicode Collation Algorithm (UCA)<sup>[1]</sup> 工作量巨大——UCA 是一个完整的 Unicode 技术标准（UTS #10），ICU 用了数十年才打磨成熟
- 不同语言的排序规则差异很大（德语 ß=ss、瑞典语 å 在 z 之后、中文按拼音/笔画），每加一种语言就要维护一份规则

**结论**：对简单场景可行，但对这种多语言应用不实际。

### 2.3. 一个看似美好的折中路线：转拼音再排序

在调研过程中，有一个思路曾经认真考虑过：**先把非拉丁文字转写为拉丁字母，再排序**。
比如中文转拼音（`张`→`zhang`）、日文转罗马字（`東京`→`toukyou`）、
阿拉伯文转拉丁转写（`سلام`→`salaam`），转写后用 `compareTo` 排序。

这个方案的诱惑力在于：纯 Dart 实现、零平台依赖、逻辑简单。
pub.dev 上也有现成的拼音转换包（如 [`pinyin`][pub-pinyin]、[`lpinyin`][pub-lpinyin]），
看起来只要 `char→pinyin→compareTo` 三步就能解决问题。

但仔细分析后，这条路有几个绕不开的坑。

#### 2.3.1. 阿拉伯文：转写 = 丢失排序传统

阿拉伯字母有自己独立的排序传统。根据 Wikipedia<sup>[2]</sup>，
阿拉伯文存在两种主要排序：传统的 Abjadi 序和现代词典使用的 hijāʾī 序，
两者都与拉丁字母 `a b c d...` 的排列完全不同。将阿拉伯字母转写为拉丁字母
（如 `ا`→`a`、`ب`→`b`）后按拉丁序排列，得到的结果与阿拉伯语使用者认知中的
正确顺序不相符。

换句话说，转写排序对阿拉伯文不只是「不精确」，而是从根本上用错了排序规则。

#### 2.3.2. 中文：硬编码字典的维护困境

中文转拼音的核心问题不在转写逻辑本身，而在于**依赖的数据**。

现有拼音包（`pinyin`、`lpinyin` 等）的工作方式是
把 Unicode/Unihan 的字符→拼音映射表硬编码到 Dart 源文件中。
[`pinyin`][pub-pinyin] 最新版发布于 2 年前，字典数据来自 Unihan 15.0.0；
[`lpinyin`][pub-lpinyin] 更是**5 年**未曾更新。Unihan 每年都有新版本——新增字符、
修正读音、补充多音字语境——但字典就此冻结。用户输入的新 Unicode 汉字可能转拼音失败，
官方修正的读音错误也不会被同步。

#### 2.3.3. 小结

转拼音再排序看上去是一条捷径，但因为转写过程**丢弃了原始语言的排序语义**，
对于有独立排序传统的书写系统（如阿拉伯文的 Abjadi/hijāʾī 序）会得到错误结果。
加上 pub.dev 上拼音包的维护现状堪忧，这条路走不通。

### 2.4. 方案 B：`collection.compareNatural` {#solution-b}

Dart 官方的 [`collection`][pub-collection] 包提供了 `compareNatural` 函数，
专门用于自然排序。从 Wikipedia Natural Sort Order<sup>[3]</sup> 列出的各语言实现中也能看到它。

**优点**：Dart 官方维护，零额外依赖（`collection` 已是 Flutter 的传递依赖），数字排序正确。

**缺点**：`compareNatural` 只解决数字排序，**不支持 locale 感知**。
它对中文仍然按 Unicode 码点排序，对变音符号也无力处理。本质上只是「更好的方案 A」。

**结论**：可以作为 fallback，但不能作为最终方案。

### 2.5. 方案 C：打包传统 ICU 数据 {#solution-c}

ICU（International Components for Unicode）是 Unicode 官方的 i18n 库，
包含完整的 collation 实现。部分 Dart 包通过 FFI 链接 ICU，将 collation 数据打包进 App。

**优点**：功能完整，排序结果正确。

**缺点**：

- ICU collation 数据约 10~30MB，对移动端应用是显著的体积代价
- 需要编译原生库，跨平台构建复杂
- collation 数据版本固定，不会随 OS 更新自动改善

**结论**：功能强但太重，更适合需要完全掌控 ICU 的场景。

### 2.6. 方案 D：`icu4x` + `intl4x` {#solution-d}

[ICU4X][icu4x] 是 Unicode 官方用 Rust 重写的、面向资源受限环境的新一代 i18n 库，
设计目标包含「small and modular code」「pluggable locale data」。
Dart 侧由官方 [`intl4x`][intl4x] 包提供 FFI 封装，已支持 collation。

这是最接近「官方方案」的选择，需要重点分析。

参考 [intl4x/lib/collation.dart][intl4x-collation]:

```dart
final list = ['Z', 'a', 'z', 'ä'];
final german = Collation(locale: Locale.parse('de-DE'));
list.sort(german.compare);
print(list); // [a, ä, z, Z]
```

**优点**：

- Dart 官方维护（`labs.dart.dev`），长期支持有保障
- 功能完整：collation + datetime + number + plural + display names
- 基于 ICU4X，设计上比传统 ICU 更模块化
- 全平台支持

**缺点**：

- **二进制体积显著增加**：README 明确声明「This package currently increases binary size in non-web builds significantly」，需使用 `--enable-experiment=record-use` 实验性标志缓解
- **Flathub 构建需额外预处理**：`intl4x` 依赖 `icu4x` FFI 原生库，后者需要编译
  Rust ICU4X → `.so`/`.dylib`/`.dll`。而 Flathub 构建沙箱完全离线，无法
  直接 `cargo build` 下载依赖——这正是 [上篇 Flathub 博客][blog-flathub]
  中踩过的坑。可行的绕过方案有两种：一是按官方推荐的流程预先编译各平台
  二进制并随源码入库；二是在 flatpak-builder manifest 中手动添加
  Rust vendoring + offline 编译模块。无论哪种，都大幅增加了 Flatpak
  打包的维护复杂度。
- **实验阶段**：当前稳定版 0.17.0，API 仍在迭代，`icu4x` Dart 绑定更是只有 0.0.1 稳定版，实际依赖 pre-release（2.2.0-dev.3）
- **重量级依赖**：仅为了 collation 功能，需要引入整个 i18n 框架（datetime、number、plural、case mapping 等），对只需要字符串排序的场景是明显的过度引入

**结论**：功能最强、官方背书，但太重且 Flathub 打包维护成本高，且自身（截至 2026-08）来说还没有进入稳定版本的 Release，使用风险大。

### 2.7. 方案 E：调用平台原生排序引擎 {#solution-e}

每个操作系统都已经内置了成熟的排序引擎——Android 有 `android.icu.text.Collator`，
iOS/macOS 有 `localizedStandardCompare:`，Linux 有 `libicui18n`，
Windows 有 `CompareStringEx`，Web 有 `Intl.Collator`<sup>[4]</sup>。

这些 API 一直在系统后台默默工作——Finder 按名称排列文件、Android 文件管理器排序、
Windows 资源管理器排序，靠的都是它们。那能不能直接调它们呢？

这个方案走的是**混合路线**：桌面端优先用 FFI（同步）直调系统库，
移动端用 Platform Method（异步）桥接原生 API，对外统一封装为 `Future` 接口。
Linux 走 FFI→`libicui18n`，Windows FFI→ICU DLL 优先、Pigeon→`CompareStringEx` 作为 fallback，
Android/iOS/macOS 因为文档没暴露 FFI 友好的公开 collation 入口，出于维护性考虑走平台桥接。

**优点**：

- **零额外体积**：不打包任何 collation 数据，直接调用 OS 内置 API
- **系统一致性**：排序结果与系统文件管理器完全一致
- **自动更新**：collation 数据随 OS 更新自动改善，无需升级包版本
- **Flathub 友好**：无额外下载/编译依赖，纯 Dart + Pigeon/FFI 调用系统 API
- **全平台**：Flutter 支持的主流平台都有成熟的系统级 collation API

**缺点**：

- 需要为每个平台编写不同的桥接代码（FFI / Platform Method）
- **部分平台需要异步调用**：Android/iOS/macOS 走平台通道（异步），
  这意味着不能直接把比较函数传给 `List.sort()`。
  不过 Linux（FFI→ICU）和 Windows（FFI→ICU DLL）在底层是同步的——
  为了 API 一致性，包对外统一返回 `Future`，上层按异步处理即可
- 不同平台的 API 行为可能有细微差异
- 需要在 Dart 侧做统一的错误处理和 Degrade Fallback

**结论**：这个方案轻量、Flathub 兼容好，体积小，是一个很好的平衡点，适合对多平台统一没有对决掌控力需求，但希望可以快速获得自然语言排序能力或者希望可以和系统体验尽量一致的应用。

## 3. 落地

### 3.1. 阶段一：在 mhabit 内部实现平台封装

确定了方案 E 之后，第一件事不是立刻创建独立 package——
而是先在应用内部把各平台的排序调用跑通，验证方案的可行性。

实现的核心思路：

- 在 Dart 侧定义一个统一的排序接口（`SortItem` + `NativeSort.sort()`）
- 桌面端通过 Dart FFI 直调系统 collation 库
  - Linux→`libicui18n`
  - Windows→ICU DLL，也提供 Pigeon fallback（`CompareStringEx`）
- 移动端则通过 Pigeon（Android/iOS/macOS）桥接原生 API

```text
NativeSort (Dart API)
├── Android   → Pigeon → android.icu.text.Collator
├── iOS       → Pigeon → localizedStandardCompare:
├── macOS     → Pigeon → localizedStandardCompare:
├── Linux     → Dart FFI → system libicui18n
├── Windows   → Pigeon (CompareStringEx) 或 FFI (ICU)
└── Web       → Dart → Intl.Collator
```

### 3.2. 阶段二：提取为独立 package

在自己项目内部跑通后，发现这段代码有三个理由值得独立为 Publish Package：

1. **pub.dev 上没有类似的全平台原生排序方案**。`collection.compareNatural` 只解决数字排序，
   `intl4x` 太重且实验性——在「轻量、全平台、原生排序」这个细分定位上，存在明显的空白。

2. **Flathub 兼容是刚需**。mhabit 已经上架 Flathub，任何需要额外下载/编译的依赖都是不可接受的。
   而 `intl4x`/`icu4x` 正是需要额外 FFI 编译，处理需要 Patch 或者预编译，相当麻烦和脆弱，已经在 sqlite3 package 上踩过坑。

3. **解耦与复用**。排序逻辑与业务无关，独立出去后可以单独测试、独立发版，
   其他 Flutter 项目也可以直接引用。

于是 [**native_natural_sort**][native-natural-sort] 便顺势出现了。

### 3.3. mhabit 项目接入

mhabit 接入 `native_natural_sort` 的改动集中在几个文件。

参考 [lib/main.dart][mhabit-main]:

```dart
await NativeSort().config(
  SortOptions(
    windows: SortOptionsWindows.ffi(onLoadFailed: WindowsSort.pigeon),
  ),
);
```

在 `main()` 中做一次性初始化。Windows 上配置了 FFI（ICU）→ Pigeon（`CompareStringEx`）的双后端 fallback。

参考 [lib/extensions/collation_extensions.dart][mhabit-collation-extensions]，
封装了一个通用的 `naturalSort<T>` 扩展方法，接收 `idOf`/`valueOf` 函数来适配任意数据类型：

```dart
extension NaturalSortExtension on NativeSort {
  Future<List<T>> naturalSort<T>({
    required List<T> items,
    required String Function(T) idOf,
    required String Function(T) valueOf,
    bool descending = false,
    String? locale,
  }) async {
    if (items.isEmpty) return items;
    final sortItems = items
        .map((e) => SortItem(id: idOf(e), value: valueOf(e)))
        .toList();
    final sorted = await sort(sortItems, /* ... */);
    // Map sorted IDs back to original items.
    // ...
  }
}
```

在 ViewModel 层，排序逻辑通过 `SortGuard` 做了 degrade fallback：

- 当 natural sort 启用且排序方式是「按名称」时，走异步的原生排序路径
- 如果异步排序失败（如平台 API 异常），自动退回到 `compareTo` 默认排序，保证功能不崩溃
- `SortGuard` 确保并发重排请求只保留最新一次的结果

参考 [lib/pages/habits_display/\_providers/habit_summary.dart][mhabit-habit-summary] 中 `_ResortHandler`：

```dart
class _ResortHandler {
  FutureOr<_HabitsSortableCache> call() {
    final needHabitNatural =
        cache.sortType == HabitDisplaySortType.name &&
        _vm._naturalSortEnabled;
    final needGroupNatural = /* ... */;

    if (!needHabitNatural && !needGroupNatural) return defaultSort();
    return _guardedNaturalSort(needHabitNatural, needGroupNatural);
  }
}
```

同时还通过 `NaturalSortExperimentalFeature` 提供了一个开关，
让用户可以自行选择是否启用原生排序（默认开启）。

### 3.4. 异步改造：SortGuard 模式

方案 E 的混合路线带来了一个工程上的实际问题：
Linux/Windows 的 FFI 排序在底层是同步的，但 Android/iOS/macOS 的 Pigeon 排序是异步的。
为了 API 一致性，`native_natural_sort` 对外统一返回 `Future`。
这意味着原有的同步排序逻辑——所有方案 A~D 都能直接 `list.sort(compareFn)` ——需要异步化改造。

mhabit 的做法是引入 `SortGuard`——一个简单的基于计数的排序守卫。
核心思路：

- 每次数据重载前调用 `_sortGuard.bump()`，递增代数
- 排序时用 `_sortGuard.run()` 包装，捕获当前代数
- 异步排序完成后比对代数——如果不一致，说明数据已变，结果作废

参考 [lib/common/sort_generation.dart][mhabit-sort-generation]：

```dart
class SortGuard {
  int _generation = 0;

  void bump() { _generation++; }

  FutureOr<T?> run<T>(FutureOr<T> Function() sort) {
    final token = _generation;
    final result = sort();
    return result is Future<T>
        ? result.then((r) => _generation == token ? r : null)
        : (_generation == token ? result : null);
  }
}
```

在 ViewModel 中，`_resortData()` 的返回类型从 `void` 改为 `FutureOr<void>`——
同步路径（默认排序）直接返回，异步路径（原生排序）返回 `Future`，
调用方用 `await _resortData()` 统一处理，接口不变。

配合 `.catchError((e) => defaultSort())` 的 degrade fallback，
异步改造对上层完全透明。

### 3.5. 最终效果

接入 [`native_natural_sort`][native-natural-sort] 后，按名称排序的结果对比：

| 输入                | Dart `compareTo`    | `native_natural_sort` |
| ------------------- | ------------------- | --------------------- |
| `item2, item10`     | `item10, item2`     | `item2, item10`       |
| `árbol, amor, azul` | `amor, azul, árbol` | `amor, árbol, azul`   |
| `张, 李, 王`        | `张, 李, 王`        | `李, 王, 张`（拼音）  |
| `Straße, Strasse`   | `Strasse, Straße`   | 相等（德语 ß = ss）   |
| `v1, v2, v10`       | `v1, v10, v2`       | `v1, v2, v10`         |

可以看到前面提到的问题都得到了很好的解决。

## 4. 总结

回头看整个过程，核心教训是：**字符串排序看似简单，一旦涉及多语言用户，就不要自己造轮子**。

Unicode Collation Algorithm（UCA）是一个发展了数十年的标准，各操作系统已经内置了经过充分测试的实现。
与其打包 ICU 数据或依赖实验性框架，直接调用 OS 原生 API 是更务实的选择——0体积增长（无需维护 ICU Database）、系统级正确性、随 OS 更新自动改善。

该 Package 目前已在 [pub.dev/native_natural_sort][native-natural-sort] 发布，如果你也在做多语言 Flutter 应用且遇到了类似的问题，希望这个 Package 能有所帮助。

## 参考文献

1. [Unicode Collation Algorithm (UCA)][wiki-uca] — Wikipedia
2. [Abjad numerals][wiki-abjad-numerals] — Wikipedia
3. [Natural sort order][wiki-natural-sort-order] — Wikipedia
4. [Intl.Collator][mdn-intl-collator] — MDN Web Docs

<!-- refs -->

[wiki-uca]: https://en.wikipedia.org/wiki/Unicode_collation_algorithm
[wiki-abjad-numerals]: https://en.wikipedia.org/wiki/Abjad_numerals
[wiki-natural-sort-order]: https://en.wikipedia.org/wiki/Natural_sort_order
[mdn-intl-collator]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/Collator
[mhabit]: https://github.com/FriesI23/mhabit
[native-natural-sort]: https://pub.dev/packages/native_natural_sort
[pub-collection]: https://pub.dev/packages/collection
[pub-pinyin]: https://pub.dev/packages/pinyin
[pub-lpinyin]: https://pub.dev/packages/lpinyin
[icu4x]: https://github.com/unicode-org/icu4x
[intl4x]: https://github.com/dart-lang/i18n/tree/main/pkgs/intl4x
[intl4x-collation]: https://github.com/dart-lang/i18n/blob/main/pkgs/intl4x/lib/collation.dart
[blog-flathub]: /post/202507/flutter-flatpak-and-flathub/
[mhabit-main]: https://github.com/FriesI23/mhabit/blob/main/lib/main.dart
[mhabit-collation-extensions]: https://github.com/FriesI23/mhabit/blob/main/lib/extensions/collation_extensions.dart
[mhabit-habit-summary]: https://github.com/FriesI23/mhabit/blob/main/lib/pages/habits_display/_providers/habit_summary.dart
[mhabit-sort-generation]: https://github.com/FriesI23/mhabit/blob/main/lib/common/sort_generation.dart
