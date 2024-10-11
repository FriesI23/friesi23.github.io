---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 记录一次 Flutter 项目升级依赖后产生的问题与解决方法
excerpt: |
  记录一下升级项目后踩到的坑, 涉及 Gradle, JDK 以及打包时的 Shrink 等,
  日后再遇到同样问题可以按图索骥直接处理掉, 节省节省自己宝贵的时间与绳命.
author: FriesI23
date: 2024-10-11 18:00:00 +0800
category: flutter
tags:
  - flutter
  - flutter-android
  - android
  - openjdk
---

最近决定升级一波自己 `Flutter` 项目的依赖, 然后出现了一些问题, 具体为:

1. `Gradle` 无法同步, 提示需要升级到 `8.5`.
2. 升级后出现兼容性警告 `source value 8 is obsolete and will be removed in a future release`.
3. 升级后在 release 模式打包编译后启动应用报错缺失图标资源, 而 debug 模式可以正常启动.

下面将这几个问题产生的原因和解决方法进行阐述.

## Gradle 无法同步

最近升级 `Android Studio` 到 `Ladybug` 后出现, 应该是版本比较低了, 升级一下就好.
因此将项目依赖版本都进行了一波升级, 具体如下:

| package                            | org-version | version |
| ---------------------------------- | ----------- | ------- |
| gradle                             | 8.0         | 8.9     |
| com.android.application            | 8.1.3       | 8.7.0   |
| androidx.window:window             | 1.0.0       | 1.2.0   |
| androidx.window:window-java        | 1.0.0       | 1.2.0   |
| com.android.tools:desugar_jdk_libs | 1.2.2       | 2.1.2   |

主要是 `Gradle` 的升级

```property
# File at: android/gradle/wrapper/gradle-wrapper.properties
#distributionUrl=https\://services.gradle.org/distributions/gradle-8.0-all.zip
#distributionSha256Sum=f30b29580fe11719087d698da23f3b0f0d04031d8995f7dd8275a31f7674dc01
distributionUrl=https\://services.gradle.org/distributions/gradle-8.9-all.zip
distributionSha256Sum=258e722ec21e955201e31447b0aed14201765a3bfbae296a46cf60b70e66db70
```

> 升级 `Gradle` 安全么, 一般而言是的, 需要关注一下版本升级之间是否存在 **Breaking Change** 即可.
> 变更日志可以看[这里][gradle-changelog].

## 兼容性警告 `source value 8 is obsolete and will be removed in a future release`

可以参考: [flutter/flutter#156111](https://github.com/flutter/flutter/issues/156111)

简单说在编译时出现了如下警告, 且可能会重复很多次:

```log
warning: [options] source value 8 is obsolete and will be removed in a future release
warning: [options] target value 8 is obsolete and will be removed in a future release
warning: [options] To suppress warnings about obsolete options, use -Xlint:-options.
```

其实日志是从 `JDK 21` 编译时开始出现 (这也是构建也来 `Android Studio` 中 `JDK` 的副作用, 它会在自己升级将自带的 `JDK` 也升级),
日志写的很了, `1.8` 已经不建议使用 (太老了), 而 Flutter 的默认模板使用的编译版本为 `1.8`.

> Flutter 以后会修改模板内预设的版本么, 可以看 [@stuartmorgan 这里][flutter-1.8]的回复.
> 简而言之出于一些原因 Flutter 项目组会在稳定版本上强制指定 1.8 版本.

这里有几种解决思路:

1. 将 `Flutter` 构建 `Andoird` 时使用的 `JDK` 版本指定为 `17`
2. 将项目的编译版本提升到 `17`, 同时更新插件 (新版本的插件可能也会更新编译版本, 具体需要看对应插件的 CHANGELOG).

如果有 **"看到 WARNING 就头疼"** 的强迫症话, 强烈建议使用方案1,
因为只要有依赖的插件没有将自己的编译版本修改为 `>1.8` 就会导致 WANRING 产生.

可以使用如下命令为 `Flutter` 指定打包时使用的 `JDK`:

```shell
flutter config --jkd-dir=/path/to/your/custom/jdk
```

如果需要升级项目的编译版本, 看下面代码块 (反正我是顺便升级了):

```groovy
// File at: andoird/app/build.gradle

// ...
def customCompileSdkVersion = localProperties.getProperty('flutter.compileSdkVersion')
if (customCompileSdkVersion == null) {
    // FIXME: url_launcher_android 6.3.0 bump compileSdk version to 34.
    // https://github.com/flutter/packages/blob/main/packages/url_launcher/url_launcher_android/CHANGELOG.md
    customCompileSdkVersion = Math.max(34, flutter.compileSdkVersion)
} else {
    customCompileSdkVersion = customCompileSdkVersion.toInteger()
}
// ...
def customNdkVersion = localProperties.getProperty('flutter.ndkVersion')
if (customNdkVersion == null) {
    customNdkVersion = '27.0.12077973'
    // compareVersions is defined but not shown on this code block.
    customNdkVersion = compareVersions(customNdkVersion, flutter.ndkVersion) > 0 ? customNdkVersion : flutter.ndkVersion
}
// ...

android {
    compileSdkVersion customCompileSdkVersion
    ndkVersion customNdkVersion

    compileOptions {
        // support for the new language APIs
        coreLibraryDesugaringEnabled true
        // sourceCompatibility JavaVersion.VERSION_1_8
        sourceCompatibility JavaVersion.VERSION_17
        // targetCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_17
    }

    kotlinOptions {
        // jvmTarget = '1.8'
        jvmTarget = '17'
    }

    // ...
}
```

对于引入第三方插件带来的警告日志, 现在也没什么版本, 请看:

> from [@stuartmorgan's reply](https://github.com/flutter/flutter/issues/156111#issuecomment-2391674300):
>
> If you're getting it from plugins, including Flutter-team-owned plugins,
> the warning will exist until we release versions of the plugins that no longer support 1.8.

## Release 模式打包后启动应用报错, 显示图标资源缺失

升级后的 Release 包启动时直接报错:

```log
PlatformException: flutter The resource @mipmap/ic_notification could not be found.
```

看起来是 `flutter_local_notification` 引起的, 找不到 `@mipmap/ic_notification` 图标资源.
不过这次我只升级了一些依赖, 并没有动任何资源, 且 Debug 包下功能时完好的 (无报错), 这就比较奇怪了.

由于对 `Andoird` 原生开发不是很熟悉, 找了半天教程,
终于发现原来是 [`shrinkResources`][android-shrink] 功能将我的资源排除掉了.
不过很神奇的是 `Flutter` 一直都是默认使用 `shrink` 选项进行裁剪, 应该是升级改变了一些打包行为,
原先不会排除 `mipmap` 的资源而现在会. 因此需要添加一下排除:

```xml
<!-- File at: andoird/app/src/main/res/raw/keep.xml -->
<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:tools="http://schemas.android.com/tools"
    tools:keep="@mipmap/ic_notification" />
```

添加后资源可以正确被打包, 问题排除.

## 总结

升级需谨慎, 不过有不升级不舒服斯基强迫症, 也为了项目不要年久失修, 不升级是不行滴, 总之大家共勉吧.

<!-- refs -->

[flutter-1.8]: https://github.com/flutter/flutter/issues/156111#issuecomment-2391674300
[gradle-changelog]: https://github.com/realm/realm-java/blob/main/CHANGELOG.md
[android-shrink]: https://developer.android.com/build/shrink-code
