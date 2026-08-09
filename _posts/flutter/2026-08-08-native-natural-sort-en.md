---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: "From compareTo to native_natural_sort: Flutter String Sorting in Practice"
excerpt: |
  Dart's default compareTo causes a host of problems for human-friendly name sorting: case sensitivity, CJK characters, diacritics, and numeric ordering.
  This article documents the full journey — from discovering the problem, to researching five approaches, to finally developing the native_natural_sort package and integrating it into the mhabit project.
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
locale: en
permalink: /post/en/202608/native-natural-sort
translation:
  note: "This article was translated by GitHub Copilot using the DeepSeek V4 Flash model."
translations:
  - lang: zh-CN
    url: /post/202608/native-natural-sort
    label: 中文
  - lang: en
    url: /post/en/202608/native-natural-sort
    label: English
---

While maintaining [Table Habit][mhabit], I noticed the habit list wasn't sorting properly — items were ordered by name,
yet Chinese habit names had no discernible order and numbers were all over the place. That made me revisit the default
sorting approach the project had been using for a long time, and it turned out that a seemingly simple "sort by name"
hides far more pitfalls than expected.

This article walks through the journey from discovering the problem, to attempts at fixing it, to researching solutions,
and finally to the implementation — hoping to provide some reference for developers facing similar issues.

I'd also love for you to try out and discuss the Flutter Package I wrapped: [**native_natural_sort**][native-natural-sort].

## 1. The Problem

### 1.1. First Version: Default compareTo Sorting

mhabit supports several sorting modes, of which "sort by name" is one of the most commonly used.
The first version was dead simple — it used Dart's built-in `String.compareTo`:

```dart
data.sort((a, b) => a.name.compareTo(b.name));
```

`compareTo` is essentially **lexicographic ordering** — it compares characters one by one by their Unicode code points.
For purely ASCII English it seems to work fine, but once mixed case, non-Latin characters, and numbers enter the picture,
problems start to appear.

### 1.2. First Pitfall: Case Sensitivity

The first issue noticed was case sensitivity. `compareTo` sorts by code points, and uppercase `A` (U+0041)
has a smaller code point than lowercase `a` (U+0061), so all names starting with uppercase letters sort before lowercase ones:

| Input            | `compareTo` Result | Expected Result |
| ---------------- | ------------------ | --------------- |
| `apple, Banana`  | `Banana, apple`    | `apple, Banana` |

An intuitive fix is to normalize to lowercase:

```dart
data.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
```

That solved the case issue. But more problems soon surfaced.

### 1.3. Second Pitfall: CJK, Diacritics, and Numbers

`toLowerCase()` fixed case, but never touched the root cause — Unicode code point order ≠ the order humans expect:

| Scenario       | Input               | `compareTo` Result   | Human Expectation   |
| -------------- | ------------------- | -------------------- | ------------------- |
| Numbers        | `file2, file10`     | `file10, file2`      | `file2, file10`     |
| Diacritics     | `árbol, amor, azul` | `amor, azul, árbol`  | `amor, árbol, azul` |
| Chinese (pinyin) | `张, 李, 王`      | `张, 李, 王`         | `李, 王, 张`        |
| German ß       | `Straße, Strasse`   | `Strasse, Straße`    | Equal (ß = ss)      |

The number issue: the first character `"1"` of `"10"` has a smaller code point than `"2"`, so `"10"` sorts before `"2"`.
The diacritic issue: `á` (U+00E1) has a code point far greater than `z` (U+007A), so `árbol` ends up at the end.
The Chinese issue is more complex — `compareTo` sorts by Unicode code point, and within the CJK Unified Ideographs block,
the order of `张` (U+5F20), `李` (U+674E), `王` (U+738B) has nothing to do with pinyin `lǐ, wáng, zhāng`.

At this point it became clear: **simple case normalization is far from enough — you need a sort that understands language rules**.

## 2. Choosing a Solution

Armed with the problems above, I started systematically researching viable solutions. In the end I narrowed it down to
five directions (plus one seemingly promising but ultimately impractical middle path, discussed separately after Solution A):

### 2.1. Solution Overview

| Solution                                     | Approach                    | Numeric Sort | Language-Aware | Bundle Size Impact | Bridging Method              |
| -------------------------------------------- | --------------------------- | :----------: | :------------: | :----------------: | :--------------------------: |
| [A. Hand-written pure Dart natural sort](#solution-a) | Regex split + collation table | ✅           | ❌             | None               | Synchronous                 |
| [B. `collection.compareNatural`](#solution-b) | Official Dart collection package | ✅           | ❌             | Negligible         | Synchronous                 |
| [C. Bundling traditional ICU data](#solution-c) | FFI linking to ICU library  | ✅           | ✅             | +10~30MB           | Synchronous (FFI)           |
| [D. `icu4x` + `intl4x`](#solution-d)          | Rust ICU4X + Dart FFI wrapper | ✅           | ✅             | **Significant**    | Synchronous (FFI)           |
| [E. Calling the platform-native engine](#solution-e) | Delegate to OS built-in APIs | ✅           | ✅             | Zero               | FFI + Platform Method hybrid |

### 2.2. Solution A: Hand-written Pure Dart Natural Sort {#solution-a}

The most naive idea — implement it yourself. Split the string into text chunks and number chunks with a regex,
compare text chunks with `compareTo`, and compare number chunks numerically.

**Pros**: zero dependencies, fully controllable.

**Cons**:

- Only solves numeric sorting; cannot handle locale-aware comparison (CJK, diacritics)
- Implementing the full Unicode Collation Algorithm (UCA)<sup>[1]</sup> is a huge undertaking — UCA is a complete
  Unicode Technical Standard (UTS #10) that ICU has spent decades polishing
- Sorting rules differ greatly between languages (German ß=ss, Swedish å after z, Chinese by pinyin/strokes),
  and you'd have to maintain a rule set for every language you add

**Conclusion**: workable for simple cases, but impractical for a multi-language app like this.

### 2.3. A Seemingly Great Middle Path: Transliterate to Pinyin Then Sort

During research, one idea was seriously considered: **transliterate non-Latin scripts to Latin letters first, then sort**.
For example, Chinese to pinyin (`张`→`zhang`), Japanese to romanization (`東京`→`toukyou`),
Arabic to Latin transliteration (`سلام`→`salaam`), then sort the transliterated text with `compareTo`.

The appeal: pure Dart, zero platform dependencies, simple logic.
pub.dev also has ready-made pinyin packages (e.g., [`pinyin`][pub-pinyin], [`lpinyin`][pub-lpinyin]),
so it looked like a simple `char→pinyin→compareTo` three-step solution.

But on closer analysis, this path has a few inescapable pitfalls.

#### 2.3.1. Arabic: Transliteration Loses the Sorting Tradition

Arabic letters have their own independent sorting traditions. According to Wikipedia<sup>[2]</sup>,
there are two main Arabic orders: the traditional Abjadi order and the hijāʾī order used by modern dictionaries —
both completely different from the Latin `a b c d...` sequence. Transliterating Arabic letters into Latin
(`ا`→`a`, `ب`→`b`) and sorting by the Latin order yields results that don't match what Arabic speakers recognize as correct.

In other words, transliteration-based sorting for Arabic isn't just "imprecise" — it fundamentally applies the wrong rules.

#### 2.3.2. Chinese: The Maintenance Nightmare of Hardcoded Dictionaries

The core problem with Chinese-to-pinyin isn't the transliteration logic itself, but the **data it depends on**.

Existing pinyin packages (`pinyin`, `lpinyin`, etc.) work by hardcoding the character→pinyin mapping
from Unicode/Unihan into Dart source files.
[`pinyin`][pub-pinyin] was last released 2 years ago, with dictionary data from Unihan 15.0.0;
[`lpinyin`][pub-lpinyin] hasn't been updated for **5 years**. Unihan gets a new release every year — new characters,
fixed readings, additional context for polyphonic characters — but these dictionaries are frozen in time.
New Unicode characters entered by users may fail to transliterate, and officially corrected readings never get synced.

#### 2.3.3. Summary

Transliterate-then-sort looks like a shortcut, but because the process **discards the original language's sorting semantics**,
it produces wrong results for writing systems with independent sorting traditions (such as Arabic's Abjadi/hijāʾī order).
Combined with the poor maintenance status of pinyin packages on pub.dev, this path is a dead end.

### 2.4. Solution B: `collection.compareNatural` {#solution-b}

Dart's official [`collection`][pub-collection] package provides a `compareNatural` function specifically for natural sorting.
It's also listed among the implementations in the Wikipedia "Natural sort order" article<sup>[3]</sup>.

**Pros**: maintained by the Dart team, zero additional dependencies (`collection` is already a transitive dependency of Flutter),
and numeric sorting is correct.

**Cons**: `compareNatural` only solves numeric sorting; it does **not** support locale awareness.
Chinese still sorts by Unicode code point, and diacritics are still unhandled. Essentially it's just "a better Solution A".

**Conclusion**: a reasonable fallback, but not the final answer.

### 2.5. Solution C: Bundling Traditional ICU Data {#solution-c}

ICU (International Components for Unicode) is the Unicode Consortium's official i18n library,
with a complete collation implementation. Some Dart packages link ICU via FFI and bundle collation data into the app.

**Pros**: complete functionality, correct sorting results.

**Cons**:

- ICU collation data is roughly 10~30MB — a significant size cost for mobile apps
- Requires compiling native libraries, complicating cross-platform builds
- The collation data version is fixed and won't improve automatically as the OS updates

**Conclusion**: powerful but too heavy — better suited for scenarios needing full control over ICU.

### 2.6. Solution D: `icu4x` + `intl4x` {#solution-d}

[ICU4X][icu4x] is the Unicode Consortium's next-generation i18n library rewritten in Rust for resource-constrained
environments, designed around "small and modular code" and "pluggable locale data".
On the Dart side, the official [`intl4x`][intl4x] package provides an FFI wrapper that already supports collation.

This is the closest thing to an "official solution" and deserves careful analysis.

See [intl4x/lib/collation.dart][intl4x-collation]:

```dart
final list = ['Z', 'a', 'z', 'ä'];
final german = Collation(locale: Locale.parse('de-DE'));
list.sort(german.compare);
print(list); // [a, ä, z, Z]
```

**Pros**:

- Maintained by the Dart team (`labs.dart.dev`), with long-term support assurance
- Complete functionality: collation + datetime + number + plural + display names
- Built on ICU4X, architecturally more modular than traditional ICU
- Cross-platform support

**Cons**:

- **Significantly larger binary size**: the README explicitly states "This package currently increases binary size
  in non-web builds significantly", mitigable only with the experimental `--enable-experiment=record-use` flag
- **Flathub builds need extra preprocessing**: `intl4x` depends on the `icu4x` FFI native library, which requires compiling
  Rust ICU4X → `.so`/`.dylib`/`.dll`. The Flathub build sandbox is fully offline and cannot run `cargo build`
  to download dependencies — exactly the pitfall encountered in [the previous Flathub post][blog-flathub].
  There are two workarounds: pre-compile each platform's binary and commit it into the source tree (as recommended by the official flow),
  or manually add a Rust vendoring + offline compilation module to the flatpak-builder manifest.
  Either way, Flatpak packaging maintenance complexity increases significantly.
- **Experimental stage**: the current stable version is 0.17.0, the API is still iterating,
  and the `icu4x` Dart binding is only at 0.0.1 stable — it actually depends on a pre-release (2.2.0-dev.3)
- **Heavy dependency**: just for collation, you'd pull in the entire i18n framework
  (datetime, number, plural, case mapping, etc.) — clear over-engineering for a use case that only needs string sorting

**Conclusion**: most powerful and officially endorsed, but too heavy, costly to maintain for Flathub packaging,
and — as of 2026-08 — not yet in a stable release, so using it carries significant risk.

### 2.7. Solution E: Calling the Platform-Native Sorting Engine {#solution-e}

Every operating system already ships a mature sorting engine — Android has `android.icu.text.Collator`,
iOS/macOS have `localizedStandardCompare:`, Linux has `libicui18n`,
Windows has `CompareStringEx`, and the Web has `Intl.Collator`<sup>[4]</sup>.

These APIs have been silently working in the background — Finder sorts files by name, Android file managers sort files,
Windows Explorer sorts files — all thanks to them. So why not call them directly?

This solution takes a **hybrid route**: desktop platforms prefer FFI (synchronous) to call system libraries directly,
while mobile platforms bridge native APIs via Platform Methods (asynchronous), uniformly exposing a `Future` interface.
Linux goes through FFI→`libicui18n`, Windows uses FFI→ICU DLL primarily with Pigeon→`CompareStringEx` as a fallback,
and Android/iOS/macOS — whose docs don't expose FFI-friendly public collation entry points —
use platform bridging for maintainability reasons.

**Pros**:

- **Zero additional size**: no collation data bundled; calls the OS built-in API directly
- **System consistency**: sorting results match the system file manager exactly
- **Automatic updates**: collation data improves as the OS updates, no package version bump needed
- **Flathub-friendly**: no extra downloads/compilation; pure Dart + Pigeon/FFI calls to system APIs
- **All platforms**: every major Flutter platform has a mature system-level collation API

**Cons**:

- Requires writing different bridging code per platform (FFI / Platform Method)
- **Some platforms require async calls**: Android/iOS/macOS go through platform channels (async),
  meaning you can't directly pass the comparator to `List.sort()`.
  That said, Linux (FFI→ICU) and Windows (FFI→ICU DLL) are synchronous under the hood —
  for API consistency, the package uniformly returns `Future`, and callers handle it asynchronously
- Platform API behaviors may differ subtly
- Unified error handling and graceful fallback are needed on the Dart side

**Conclusion**: lightweight, Flathub-compatible, and small in size — a great balance for apps that don't need
absolute control over multi-platform consistency but want quick access to natural-language sorting
or the closest possible consistency with the system experience.

## 3. Implementation

### 3.1. Phase One: Platform Wrappers Inside mhabit

Once Solution E was chosen, the first thing wasn't to create a standalone package immediately —
it was to get each platform's sorting call working inside the app first, validating the feasibility of the approach.

The core idea:

- Define a unified sorting interface on the Dart side (`SortItem` + `NativeSort.sort()`)
- Desktop calls system collation libraries directly via Dart FFI
  - Linux→`libicui18n`
  - Windows→ICU DLL, also providing a Pigeon fallback (`CompareStringEx`)
- Mobile bridges native APIs via Pigeon (Android/iOS/macOS)

```text
NativeSort (Dart API)
├── Android   → Pigeon → android.icu.text.Collator
├── iOS       → Pigeon → localizedStandardCompare:
├── macOS     → Pigeon → localizedStandardCompare:
├── Linux     → Dart FFI → system libicui18n
├── Windows   → Pigeon (CompareStringEx) or FFI (ICU)
└── Web       → Dart → Intl.Collator
```

### 3.2. Phase Two: Extracting a Standalone Package

After getting it working inside the project, I found three reasons this code deserved to be published as a package:

1. **pub.dev has no similar all-platform native sorting solution**. `collection.compareNatural` only solves numeric sorting,
   and `intl4x` is too heavy and experimental — in the "lightweight, all-platform, native sorting" niche, there's a clear gap.

2. **Flathub compatibility is a hard requirement**. mhabit is already published on Flathub, and any dependency
   requiring extra downloads/compilation is unacceptable. `intl4x`/`icu4x` exactly fit that description —
   they need extra FFI compilation, requiring patches or pre-compilation, which is annoying and fragile.
   We've already been burned by this with the `sqlite3` package.

3. **Decoupling and reuse**. Sorting logic is business-agnostic; extracted, it can be tested independently,
   released independently, and referenced by other Flutter projects.

And so [**native_natural_sort**][native-natural-sort] came to be.

### 3.3. Integrating into mhabit

The mhabit integration changes are concentrated in a few files.

See [lib/main.dart][mhabit-main]:

```dart
await NativeSort().config(
  SortOptions(
    windows: SortOptionsWindows.ffi(onLoadFailed: WindowsSort.pigeon),
  ),
);
```

A one-time initialization in `main()`. On Windows, it configures a dual-backend fallback of FFI (ICU) → Pigeon (`CompareStringEx`).

See [lib/extensions/collation_extensions.dart][mhabit-collation-extensions],
which wraps a generic `naturalSort<T>` extension method that accepts `idOf`/`valueOf` functions to adapt to arbitrary data types:

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

At the ViewModel layer, the sorting logic goes through a `SortGuard` with graceful fallback:

- When natural sort is enabled and the sort mode is "by name", take the async native sorting path
- If the async sort fails (e.g., a platform API exception), automatically fall back to the default `compareTo` sort so functionality never crashes
- `SortGuard` ensures that only the latest result survives concurrent re-sort requests

See `_ResortHandler` in [lib/pages/habits_display/_providers/habit_summary.dart][mhabit-habit-summary]:

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

It also exposes a `NaturalSortExperimentalFeature` toggle so users can choose whether to enable native sorting (on by default).

### 3.4. Async Refactor: The SortGuard Pattern

The hybrid route of Solution E brings a practical engineering problem:
FFI sorting on Linux/Windows is synchronous under the hood, but Pigeon sorting on Android/iOS/macOS is asynchronous.
For API consistency, `native_natural_sort` uniformly returns `Future`.
This means the original synchronous sorting logic — which all Solutions A~D could do with a direct `list.sort(compareFn)` — needed an async refactor.

mhabit's approach is to introduce `SortGuard` — a simple counter-based sort guard. The core idea:

- Call `_sortGuard.bump()` before each data reload, incrementing the generation
- Wrap the sort with `_sortGuard.run()`, capturing the current generation
- After the async sort completes, compare generations — if they differ, the data has changed and the result is invalid

See [lib/common/sort_generation.dart][mhabit-sort-generation]:

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

In the ViewModel, `_resortData()`'s return type changed from `void` to `FutureOr<void>` —
the synchronous path (default sort) returns directly, the async path (native sort) returns a `Future`,
and callers handle both uniformly with `await _resortData()`, keeping the interface unchanged.

Combined with a `.catchError((e) => defaultSort())` graceful fallback,
the async refactor is completely transparent to upper layers.

### 3.5. The Final Result

After integrating [`native_natural_sort`][native-natural-sort], the "sort by name" results compared:

| Input                | Dart `compareTo`    | `native_natural_sort` |
| -------------------- | ------------------- | --------------------- |
| `item2, item10`      | `item10, item2`     | `item2, item10`       |
| `árbol, amor, azul`  | `amor, azul, árbol` | `amor, árbol, azul`   |
| `张, 李, 王`         | `张, 李, 王`        | `李, 王, 张` (pinyin) |
| `Straße, Strasse`    | `Strasse, Straße`   | Equal (German ß = ss) |
| `v1, v2, v10`        | `v1, v10, v2`       | `v1, v2, v10`         |

All the problems mentioned earlier are now well resolved.

## 4. Summary

Looking back, the core lesson is: **string sorting looks simple, but once you have multi-language users, don't reinvent the wheel**.

The Unicode Collation Algorithm (UCA) is a standard that has evolved over decades, and every OS already ships
a battle-tested implementation. Instead of bundling ICU data or relying on experimental frameworks,
calling the OS-native API directly is the more pragmatic choice — zero size growth (no ICU database to maintain),
system-level correctness, and automatic improvement as the OS updates.

The package is now published on [pub.dev/native_natural_sort][native-natural-sort].
If you're building a multi-language Flutter app and hitting similar issues, I hope this package helps.

## References

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
