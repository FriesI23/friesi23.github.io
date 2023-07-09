---
layout: post
title:  "Flutter 中的是否应该使用 Functional Widgets"
date:   2023-07-09 18:20:00 +0800
categories:
    - flutter
    - android
    - fdroid
    - appstore
---
<!--
 friesi23.github.io (c) by FriesI23

 friesi23.github.io is licensed under a
 Creative Commons Attribution-ShareAlike 4.0 International License.

 You should have received a copy of the license along with this
 work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
-->

在刚开始写 `Flutter` 应用没多久的时候，相信大家（包括我自己）都会有这样一个疑问：
为什么 `Flutter` 官方教程推荐将子组件包装为一个`StatelessWidget`，
如果为了解决 `Widget` 嵌套过深的问题，明明可以使用一个或者多个 `Helper`
函数来将 `build` 中的 `Widget`进行拆分。 正如下面这些代码所示：

```dart
// 原始Widget中的build方式
class Widget0 extends StatelessWidget {
    Widget build(BuildContext context) {
        return Widget1(
            child: Widget2(
                child: Widget3(),
            ),
        );
    }
}
```

```dart
// 使用Stateless Widget进行拆分
class Widget0 extends StatelessWidget {
    Widget build(BuildContext context) {
        return Widget1(child: ChildWidget());
    }
}

class ChildWidget extends StatelessWidget {
    Widget build(BuildContext context) {
        return Widget2(child: Widget3());
    }
}
```

```dart
// 使用Functional Widget进行拆分
class Widget0 extends StatelessWidget {
    Widget _buildChildWidget() {
        return Widget2(child: Widget3());
    }

    Widget build(BuildContext context) {
        return Widget1(child: _buildChildWidget());
    }
}
```

其实第一眼看到这两种代码，在不了解flutter机制的前提下本能进行选择，相信大多数人会
不约而同选择方案二， 既新建一个 `Helper` 方法来分解自己的build方法。理由无外乎这几种：

1. 使用函数的资源消耗比新建一个对象要低
2. 参数调用更加方面
3. 可以让 `Widget Tree` 变得更矮更干净

然而现实情况往往与自己的直觉时相反的，这里推荐大家先去看看 [这里][issue-link], 这是
Github 上一个经典的讨论。或许可以解开大家很多这方面的疑惑。

对于 `@rrousselGit` 对该问题的回应先翻译并列举在下面：

- Class :
    1. 具有热重载 (Hot reload) 功能
    2. 可以集成到小部件检查器中（通过 `debugFillProperties` 方法）
    3. 通过重写 `operator==` 可以减少重新构建的次数
    4. 可以定义键 (Key) 来唯一标识小部件
    5. 确保所有小部件 (Widget) 以相同的方式使用
    6. 确保在两种不同布局之间切换时正确释放相关资源 (Resources)
    7. 可以使用上下文（BuildContext）API
    8. 可以是const（常量）

- Function:
    1. 代码量较少 (可以使用 `functional_widget` Package)

不出意外的话大家第一次看完这些对比后应该和我第一次看完的反应差不多：

> 他说的好像很有道理，但是我认为 `Functional Widget` 的优点似乎都没有反驳的理由，
> 并且 `代码量少` 这个优点又和我的直觉一致，那我还是不明白为什么要切换为 `Stateless Widget`，
> 似乎使用 `Function` 的方式一样可以达成 `Class` 中的这些优点。

如果你和我有相同或者相似的疑问，那就请继续向下看下去吧！

## 0. 说在前面的

首先要说明，其实这个讨论中没有太注明的一个点，就是 `Functional Widget` 的代码时完全
可以做到和 `Stateless Widget` 一致的。官方推荐使用 `Class` 的形式，有时候是为了
`代码可阅读性`, 或者减少因为手滑笔误导致的一些隐形问题。

OK，我们先看一下两段代码

```dart
class MyWidget extends StatelessWidget {
    Widget functionA() => Container()

    @override
    Widget build() {
        return functionA()
    }
}

class MyWidget extends StatelessWidget {
    @override
    Widget build() {
        return Container();
    }
}
```

很明星能看出，这两段代码时完全一致的，那么让我们得例子稍微复杂点

```dart
class ClassWidget extends StatelessWidget{
    @override
    Widget build() {
        return ClassAClassChildWidget();
    }
}

class ClassChildWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container();
  }
}

// 等价
class FunctionalWidget extends StatelessWidget {
    Widget buildChild() {
        return Builer(
            builder: (context) => Container(),
        );
    }

    @override
    Widget build() {
        return buildChild();
    }
}

// 不等价
class UnEquallyFunctionWidget extends StatlessWidget {
    Widget buildChild() {
        return Container();
    }

    @override
    Widget build() {
        return buildChild();
    }
}
```

这个例子很直观的展示了 `Class` 和 `Function` 方式创建 `Widget` 后的区别。`Builer`
在这里既起到了创建一个匿名 `Widget` 的作用，也将 `context` 的范围限制到了他和他的
子部件中。(可以注意到 `Builder` 有一个 `builder` 方法, 他的参数中有一个 `context`,
这个便是 `Builder` 暴露自己的context)

那么我们着重讲一下 `Class` 为什么会有这么多优点（或者说可取之处?），当然，如果可能
的话我会给出对应的 `Functional` 实现等价功能的参考代码，一起对比时会更加直观。

## 1. 可以已更简单的姿势优化 `rebuild` 的次数已提高UI性能，尤其是 `InheritedWidget` 的情况

关于什么是 `InheritedWidget`，大家可以到 Flutter官网上查阅，这里就不赘述了。我这边
直接上一个编写代码中最常用的例子:

```dart
final theme = Theme.of(context);
```

我们都知道这里会获得当前主题Data，但是具体是怎样获得的呢

```dart
// in flutter\lib\src\material\theme.dart
class Theme extends StatelessWidget {
    // ...
    static ThemeData of(BuildContext context) {
        final _InheritedTheme? inheritedTheme = context.dependOnInheritedWidgetOfExactType<_InheritedTheme>();
        // ...
    }
}

// in flutter\lib\src\material\theme.dart
class _InheritedTheme extends InheritedTheme {}

// in flutter\lib\src\widgets\inherited_theme.dart
abstract class InheritedTheme extends InheritedWidget {}
```

其实最关键的就是 `dependOnInheritedWidgetOfExactType`, 他用于在Widget树中依获取
特定类型的 `InheritedWidget`

> `InheritedWidget`是一种特殊类型的小部件，
> 它可以在小部件树中向下传递数据而不必通过显式的传递参数来实现。
>
> `InheritedWidget` 的值发生变化时，依赖它的子小部件会自动更新，这个过程是隐式的。

现在我们知道了在调用 `Theme.of(context)` 时，同时与当前 `context` 创建了隐式的绑定。
`Flutter` 就是使用这种方式实现切换主题时（比如黑暗模式）自动帮我们的 `Widget` 进行
`rebuild` 工作。

OK，现在我们有这样一个小部件 `MyWidget`，他的 `build` 方法内含有非常多的子部件，\
那么 `rebuild` 的时候 `MyWidget` 会发生什么事情呢

```dart
class PrintWidget extends StatelessWidget {
    final Widget? child;
    final Color? color;
    final String text;
    const PrintWidget({this.child, this.color, this.text=''});
    Widget build(context) {
        return Column(
            children: [
                Text(text, color: color),
                if (child != null) child,
            ],
        );
    }
}

class MyWidget extends StatelessWidget {
    Widget build(context) {
        final themeData = Theme.of(context);
        return PrintWidget(
            text: '1',
            child: PrintWidget(
                text: '2',
                child: ...
                    ...
                        ...
                            ...
                                PrintWidget(
                                    text: '999',
                                    color: themeData.primaryColor,
                                ),
            )
        )
    }
}
```

答案是这 `999` 个子孙组件都会被 `rebuild`！但是在现实中，很多组件其实和主题时无关的，
也就是说 `Theme.of(context)` 并不需要刷新所有的子组件, 事实上，上面这个规则中，
我们只需要刷新 `text = '999'` 的那个 `Widget`。那为什么会出现这种情况呢？

首先要说明，Flutter中并不存在任何 `黑魔法`, 所有的一切都是按照规则来的。那么我们的这段
代码实际上便是将 `999` 个小部件都挂载在了 `MyWidget` 这个相对的 `root` 节点上。

而触发 `rebuild` 是从绑定的 `Widget` 开始的，那么这一切就理所当然了，因为这些组件使用
了同一个上下文，所以他们被当做了一个 `MyWidget`的一部分，那当然会被一起刷新了。

一个优雅的解决方法便是，使用 `Class` 方法为 `text=999` 的小组件创建一个新的 `Widget`，
以下是修改后代码

```dart
class _PrintWidget999 extends StatelessWidget {
    // 因为创建了一个针对特定text的 Widget，那么text可以直接写死在 Widget 中

    // 这个为了扩展保留了child
    final Widget? child;
    // 提供一个builder方法，可以为子widget暴露自己的context
    final Function(BuildContext, Widget)? builder;

    const PrintWidget({this.child, this.builder});

    Widget build(context) {
        // 这里的context其实相当于一个subtree，相对context的范围也局限于
        // 这个context以及一起它下面挂载的子 `compoment` 上
        final themeData = Theme.of(context);
        return Column(
            children: [
                Text('999', color: themeData.primaryColor),
                if (builder != null) builder(context, child)

            ],
        );
    }
}

class MyWidget extends StatelessWidget {
    Widget build(context) {
        return PrintWidget(
            text: '1',
            child: PrintWidget(
                text: '2',
                child: ...
                    ...
                        ...
                            ...
                                _PrintWidget999(
                                    child: PrintWidget(text: '1001')
                                    builder: (context, child) {
                                        final x = XXXX.of(context);
                                        return PrintWidget(
                                        text: '1000',
                                        child: child,
                                        )
                                    }
                                ),
            )
        )
    }
}
```

以后每次更新 `Theme` 后，只会更新 `_PrintWidget999` 和挂载在他下面的子widget。可以
注意到我们同时暴露了一个 `builder` 方法，这其实是一个比较良好的实践。如上所示，
`text=1000, text=1001` 都通过这个方式挂载，此时 `XXXX` 如果有更新，也只会影响到
`_PrintWidget999` 以及其子部件。

总之，这种绑定方式之和 `context` 相关，和代码书写方式无关，Flutter中不存在黑魔法。

这里也附上 `Functional` 的解决方案，正如上文所言, `Class` 和 `Function` 是一种实践，
两者都可以达到目的，但是 `Class` 更不容易犯错（比如使用错误的 `context`，
这在代码嵌套深度比较高的时候很容易出现，因为context类型是一样且合法的，
lint检查不出错误，只能依靠运行时测试）

```dart
class MyWidget extends StatelessWidget {
    Widget build999() {
        return Builder(
            builder: (context) {
                final themeData = Theme.of(context);
                return PrintWidget(
                    text: '999',
                    color: themeData.primaryColor,
                );
            }
        );
    }

    Widget build(context) {
        final themeData = Theme.of(context);
        return PrintWidget(
            text: '1',
            child: PrintWidget(
                text: '2',
                child: ...
                    ...
                        ...
                            ...
                                build999(),
            )
        )
    }
}
```

相关 `class` 与 `function` 的比较

- 具有热重载 (Hot reload) 功能
  - 最起码在 `3.7.12` 这个版本，两个都用有 `hot reload` 功能，而release中又不存在热重载，所以这个区别不大
- 可以定义键 (Key) 来唯一标识小部件
  - `Class` 中 `key` 是一个继承的属性，而 `Function` 中使用 `Builder` 创建的匿名小部件也可以使用 `key`。
- 可以使用上下文（BuildContext）API
  - `Function` 需要格外注意传递 `context` 的时候不要使用过时或者错误的 `context`，具体下文会讲到。

## 2. 关于 `context`

每一个 `Widget` 的 `build` 方法都含有一个 `context` 表示该小部件的上下文。
当然如果对 `Flutter` 了解比较深入的话会知道 `context` 其实就是对应的 `compoment`，
这里因为不关键，所以并不准备针对这个详细论述。

如果使用 `Class` 方式组织自己的小部件的话，可以天然拿到当前小部件正确的 `context`，而
`Function` 就不一定了，请看下面简单代码

```dart
class _innerClassWidget extends StatelessWidget {
    Widget build(context) {
        // 这里的 context 肯定是  _innerClassWidget 的 context
        final dataViewModel = context.of<Provider>(listen: false);
        return Text(dataViewModel.name);
    }
}

class ClassWidget extends StatelessWidget {
    Widget build(context) {
        return const _innerClassWidget();
    }
}
```

```dart
class FunctionWidget extends StatelessWidget {
    Widget buildChild(Context context) {
        // 这里的 context 是谁的？是从parent里面传下来的还是某个builder返回。
        final dataViewModel = context.of<Provider>(listen: false);
        return Text(dataViewModel.name);
    }

    Widget build(context) {
        return buildChild(context);
    }
}
```

问题其实已经包含在代码中了，因为上述例子很简单，所以问题不明显，那么想象一下如下代码：
（这个真正的界面设计中很常见）

```dart
class MainPage extends StatelessWidget {
    Widget buildMyColorfulSliverAppbar(BuildContext context) {
        return ....;
    }

    Widget buildSliverAppBar(BuildContext context) {
        return Consumer<XXXX>(
            builder: (contest, provider, child) {
                Theme.of(context);
                return buildMyColorfulSliverAppbar(context);
            }
        );
    }

    Widget build(context) {
        return Scaffold(
            body: CustomScrollView(
                slivers: [
                    buildSliverAppBar(context),
                    ...
                ]
            ),
        );
    }
}
```

这个代码可以运行，但是我们不经意间包含了一个小错误，仔细观察 `buildSliverAppBar` 方法，
`builder` 中 `contest` 拼写错误了。
这导致 `buildMyColorfulSliverAppbar` 中的 `context` 其实是 `MainPage` 而不是 `Comsumer` 的。
这与我们的预期不符。

当然，本段代码仍然可以正常工作，因为我们并没有使用到这个 `context`，
顶多是 `Theme` 导致的 `rebuild` 范围变大。

但是如果这个 `context` 中需要重新绑定一些信息或者删除并重新添加一些信息呢，
并且这个拼写错误处于中间的某一个层级，名字也不是 `contest` 而是 `_`, `dog` 这种。
这种问题很容易通过一般的测试场景，但是在特定场景下就会错误崩溃。这里也引出了另一个问题，
`Functional Widget` 不方便调试。

每一个 `Class Widget` 都是自带命名，而我们在 `debug` 查找 `Widget Tree` 时，
可以直接使用类名进行查找，而 `Function` 没法做到这一点（想象一下，
查找 `MyXXXProfileListTile` 肯定比查找 `ListTile` 方便），
这会在开发和找到bug的时候带来很多不必要的麻烦。

话说回来，这种需要命名上的统一的编程风格在多人协作中也面临更多挑战，请看如下直观代码

```dart
class ClassA extends State<XXX> {
    Widget build(context) {
        // OK,我知道需要使用 context
    }
}
class ClassA extends State<XXX> {
    Widget build(ctx) {
        // Eh,虽然不是Flutter推荐的命名方式，但是我知道需要使用 ctx
        // 对于StatefulWidget而言，这里 context和ctx是等价的
        // 对于StatelessWidget而言，由于没有context属性，所以不会有疑问
    }
}

class Func extends State<XXX> {
    Widget buildXXX(BuildContext c) {
        return Builder(
            builder: (ctx) {
                // 这里很容易用错，尤其是在代码很多的情况下，有时候
                // 一页代码只能看到当前方法体，根本看不到方法定义
                // 对于StatefulWidget，State中是内涵一个`context`属性的
                // 这更加重了这个问题，我到底使用 `context`, `ctx` 还是　`c`
                // 事实上，从最佳实践来说，永远使用距离自己最近Widget的context总没错
                // 所以可以通过统一命名为 context 来消除这种隐患
                // 而只build方法直接避免了这种隐患
            },
        );
    }

    Widget build(context) {
        // OK,我知道需要使用 context
        ...
    }
}
```

针对以上的各种隐含坑，Function就没用了么，其实不是的，请看下面代码

```dart
class MyState extends State<XXX> {
    // 样式类是可以使用方法创建的
    ThemeData getNewThemeData() {}
    TextStyle getMyTitleTextStyle() {}

    // 回调方法可以放在外面而不是在build中，这样也有助于build方法的整洁
    void onMyXXXListTilePressed(bool value) {}
    void onButtonPressed() {}

    // 流程代码也可以放在外面，道理同回调
    void openDialog() async {}

    Widget build(context) {
        // 个人的一些习惯，针对拆分为子部件后嵌套层架还是过深的情况
        // 个人会将一些布局无关的代码拆分到一个子方法中，大概如下：
        Widget buildAppbar(context) {
            return Selector(
                builder: (...) => SomeProvider(
                    builder: (...) => MyAppBar(),
                )
            );
        }
        Widget buildBodyList(context) {}
        Widget buildDebugTile(context) {}

        return Scaffold(
            body: CustomScrollView(
                slivers: [
                    buildAppbar(context),
                    buildBodyList(context),
                    buildDebugTile(context),
                    ...
                ]
            ),
        );
    }
}
```

以上，`Function` 对于 `Widget` 梳理也不是什么洪水猛兽，但是使用起来需要更多的注意力，
并且也存在`Debug` 困难这种问题。所以主力使用 `Class` ，
在不容出错或者 `Class` 不能优雅解决问题的情况下适当使用 `Functional Widget`，
也不失为一种很好的实践，毕竟 `代码量` 少在一些不需要过度包装的时候也是一种优势。

相关 `class` 与 `function` 的比较

- 可以集成到小部件检查器中（通过 `debugFillProperties` 方法）
  - 这个是 `Class` 的优势，方法因为本身不被框架感知，无法达到这种效果
- 通过重写 `operator==` 可以减少重新构建的次数
  - 其实对于 `Functional Widget`, `Provider`也可以提供相同的局部刷新功能，不过这增加嵌套量，并且 `Provider` 本质不是为方法Widget服务的，这样使用多少会让其他人读代码的时候很费劲（Provider中控制的一般都是业务状态，很少会将其用作布局参数存储使用）。况且 `Class Widget` 一样可以使用，这样一比就更没优势了。
- 确保所有小部件 (Widget) 以相同的方式使用
  - `Function Widget`的方法参数可以做到和 `Class` 一致，但是需要更细心，因为在`Widget`定义存在一些问题的时候，lint 会检查`Class` 中的问题并提示，而方法内是不行的。比如 `StatelessWidget` 中使用 `final` 定义属性。
- 确保在两种不同布局之间切换时正确释放相关资源 (Resources)
  - 一般也不会有人闲的蛋疼使用 `Function` 定义带有状态的 `Widget` 吧。属性释放一般不是问题。
- 可以是const（常量）
  - `Functional Widget`不能定义常量，不过 `Dart` 的 `const Widget` 在实践中除特定场景外能过获取的性能优势并不明显，所以这个更多是一种个人选择，毕竟 `MyText(child: const Text('hello'), ...)` 肯定是比 `MyText(str: 'hello') -> Text(str)` 这种实现是要更好的。

## 3. 不同的 Widget 会被识别为不同的 Widget

打眼一看这是一句 “你搁这搁这” 的废话，但是 `Flutter` 其实内部很多组件都是依靠 `runtimeType`
来判断组件是否需要被替换，比如 `AnimatedSwitcher`。请看代码

```dart
// 情况1 MyText1()->Text('1') MyText2()->Text('2')
// 这个组件可以正常工作，根据showText1是否为true来决定显示那个Widget并添加过渡效果
AnimatedSwitcher(
    ...
    child: showText1? MyText1(): MyText2();
);

// 情况2
// showText1切换时字是换了，但是没有过渡效果，WHY?
AnimatedSwitcher(
    ...
    child: showText1? Text('1'): Text('2');
);
```

情况2失去了过度效果，但明明 `MyText1()` 里面就是 `return Text('1')`,
原因就在于 `AnimatedSwitcher` 识别两个 `Widget` 的方式为查看他们 `RuntimeType`，
而情况1中 `RuntimeType` 是不同的，所以  `AnimatedSwitcher` 可以正确的识别这两个 `Widget`
并查过过度动画。

情况2就不一样了，它们的 `RuntimeType` 是相同的，此时  `AnimatedSwitcher`
会尝试比较两个部件的 `key`。很遗憾，这个case中并没有设置key（key默认为null），
此时 `AnimatedSwitcher` 根本没法区分两个小部件（认为他们是一个），
因此也无法为其插入过度动画。

使用 `Functional Widget` 会使这个问题变得更隐蔽

```dart
Widget buildText1() => Text('1');   // Text('1', key=ValueKey<int>(1))
Widget buildText2() => Text('2');   // Text('2', key=ValueKey<int>(2))

// 和上面的情况2其实是等价的，还是不对
// 需要使用注释里面的代码，加上key，才能让这种情况正常工作
// 而 `Class` 的方式天然避免了这个问题
AnimatedSwitcher(
    ...
    child: showText1? buildText1(): buildText2();
);
```

## 4. 总结

简而言之使用 `Class Widget` 好处更多是编程实践上的，并不代表 `Functional Widget`
做不到或者做不了。但是其优势确实可以让我们在编写 `Flutter` 代码时优先使用 `Class`。

为什么会保留 `Functional Widget`, 因为 `函数/方法/闭包` 是 `Dart` 语言的基本功能，
而这个基本`恰好`可以达到我们在 `Flutter` 中某种编排代码的目的。只不过在 `Flutter Widget`
组织中，它大部分时间都不是最佳实践。但我们仍然可以在其他需要编写 `Dart`
代码的时候使用这些功能。

---

本文其实主要也是我个人在学习和编写 `Flutter` 代码中出现的一些问题和经验，其实 `Github`
上那个讨论和 `Stackoverflow` 上找到的回答个人觉得有些激进，并且没有讲明为什么这个问题，
因此写了这边文章希望帮助大家能够更清晰的认识到两者的区别。

个人才疏学浅，如果文章中有疏漏或者错误的地方还往大家能够踊跃提出，我会进行修正和改进。

[issue-link]: https://github.com/flutter/flutter/issues/19269
