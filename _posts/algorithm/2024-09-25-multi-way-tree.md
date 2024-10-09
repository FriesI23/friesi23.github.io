---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 算法学习 - 多叉树 (Multi-Way Tree) 与 2-3 树 (2-3 Tree)
excerpt: |
  提供了个人对于 2-3 树的一些入门学习笔记, 以及对其与多叉树相关概念的理解.
  里面包含了 2-3 树插入与删除操作的详细说明与个人理解写出的渣渣伪码.
author: FriesI23
date: 2024-09-25 22:00:00 +0800
category: algorithm
tags:
  - algorithm
  - structure
  - tree
  - multi-way-tree
  - 2-3-tree
---

## 什么是多叉树

多叉树也拥有树状结构, 不同于二叉树的是其每一个节点 (Node) 可以最多存储 `n` 个关键字 (Key),
并且可以最多拥有 `n+1` 个子树.

## 为什么要使用多叉树

二叉树数据分散且会创建更多的节点, 只适合在内存中少量创建并使用 (比如实现一些内存算法).
而多叉树可以将多个数据聚合在同一个 Node 上, 可以充分体现顺序读写的优势 (比如: 一次读取一个 Block 的内容);
且相比于二叉树, 多叉树创建是需要的节点更少, 且树的深度在同样平衡时相对较低.
这决定了多叉树更适合大规模场景 (比如各种缓存场景).

`B-Tree` 作为一种平衡多叉树的代表, 可以充分利用其优势使其作为众多数据库的缓存结构
(即使是在 SSD 或者内存中, 可以看[这里][b-tree-ssd]的回答).
不过这里先不讨论他, 而是先专注于一个多叉树结构 -- `2-3 Tree`.

## 2-3 树

`2-3 树` 是一种自平衡查找树，起结合了二叉树和三叉树的特性, 具有以下性质:

1. `2-Node`, 即一个节点只包含一个 Key, 同时只能为叶子节点或者**同时**存在左右孩子.
   左子树上的任一节点 l 都需要满足: `x > l`, 右子树上的任一节点 y 都需要满足: `x <= z`;
2. `3-Node`, 即一个节点包含两个 Key, 同时只能为叶子节点或者**同时**存在三个孩子.
   节点与子树之间需要满足: `l < x <= c < y <= r | l∈{左子树}, c∈{中间子树}, r∈{右子树}`
3. 所有节点都是 `2-Node` 或是 `3-Node`
4. 所有叶子节点都在同一个 layer, 也就是说任意 layer 的子树高度都是相同.

表示如下:

```text
// 2-Node
    |
    x             |
  /  \    或      x
 l    r

// 3-Node
      |
    x   y                  |
  /   |   \      或      x   y
 l    c    r
```

## 2-3 树相关操作

2-3 树的所有操作也都是 `O(lgn)`, 具体与树的高度 `h` 相关. 查找/最大/最小值从树顶递归比较即可,
这里不多赘述, 可以查看[算法学习 - 二叉搜索树 (Binary Search Tree)][blog-binary-search-tree]中的查找部分.

### 插入 (Insert)

`2-3 树` 也与二叉查找树类似, 都需要先找到需要插入的叶子节点.
不过由于其性质要求, 找到叶子节点后的插入分为以下几种情况:

1. 空树
2. 插入到一个 `2-Node` 上
3. 插入到一个 `3-Node` 上

针对情况 1, 直接插入一个 `2-Node` 即可.

针对情况 2, 直接将 `2-Node` 变为一个 `3-Node` 即可.

针对情况 3 则比较复杂, 因为 `3-Node` 已经不能继续插入 Key, 而直接插入为子树则会违反性质 4.
因此我们需要在保证性质的前提下将节点进行一定拆分重组, 已完成整个插座操作.

首先考察树中只有一个 `3-Node` 的情况, 此时插入数据会使节点变为一个 `4-Node`, 这将违反性质 3.
因此我们需要将这个节点拆为一个 `2-Node`, 这个很简单, 将左右两个 Key 作为中间 Key 的左右子树即可.

```text
                                    y
x y  (insert z)  ->  x y z   -->   / \
                                  x   z
```

完成后满足 `2-3 树` 的所有性质.

现在考察在一个 `3-Node` 的非 root 节点进行上述操作, 会违反性质 4, 因为拆分节点引入了新的一层.
不过好在我们的每个节点可以容纳最多 2 个 Key, 因此可以考虑将该节点与父节点进行合并, 此时又分为两种情况:

1. 父节点 p 为 `2-Node`
2. 父节点 p 为 `3-Node`

针对情况 3.1, 我们可以直接将节点合并到父节点, 如下:

```text
// 只给出右子树合并, 左子树镜像操作即可.

    p                   p   y
  /  \                /   |   \
pl   xyz      -->    p1   x    z
```

合并后所有性质都满足.

针对情况 3.2, 我们可以递归的继续完成 `拆分节点 -> 向上合并` 的流程, 直到 root 节点被拆分.

```text
    p1  p2               p1   p2  [y]                 [p2]
  /   |   \             /   |   |   \               /      \
pl   pc   xyz     -->  pl    pc  x    z    -->     p1        y
                                                 /   \      /  \
                                                pl   pc    x    z

                  g  [p2]
                /   |    \
2-Node ~~~    gl    p1     y
                   /  \   /  \
                 pl   pc  x   z

或

                  g1  g2   [p2]                      [g2]
                /    |   |     \                    /    \
3-Node ~~~    gl    gc   p1     y        -->       g1     p2    -->  ...
                        /  \   /  \              /  \    /  \
                       pl   pc  x   z           gl  gc  p1   y
```

可以看到, 每次拆分都会是子树的高度 +1, 但是每次合并后会使子树高度 -1, 因此只要保证子树最后与父节点合并,
就能保证树的高度不被破坏. 而树高度增长的唯一方法就是 root 节点被拆分.

下面给出伪码实现, 使用了递归存储 parent 信息 (z), 可以在实现时展开为迭代形式提高效率:

```text
// Tree 代表一个 2-3 树
// Node 代表节点
// Key 代表节点值，我们假设 Key 是可比较的
INPUT Key k     // 需要插入的 key
INPUT Tree tree

IF (tree.isEmpty)
  tree.newRoot(k)
  RETURN

// 递归找到插入位置并插入 k
root = CALL INSERT_AND_SPLIT(tree.root, k)
IF (root != NULL)
  tree.root = root
  tree.height += 1

// 递归函数：插入节点并处理可能的分裂
FUNCTION INSERT_AND_SPLIT(Node z, Key k)
  IF (z.isLeaf)
    z.add(k)
  ELSE
    z_child = z's child WHERE SHOUD INSERT k
    y = INSERT_AND_SPLIT(z_child, k)
    if (y != NULL)
      z.add(y.key)
      z.addChild(y.left)
      z.addChild(y.right)

  IF (!z.is4Node)
    RETURN NULL

  RETURN SPLIT(z)  // 将 z 分裂，并返回中间键和新右节点
```

### 删除 (Delete)

按照二叉树中删除节点的经验, 删除往往比插入要困难, 主要是由于可能删除非叶子节点, 且删除会导致树的所有性质都可能被破坏.
我们先按照删除节点 k(z) 是否为叶子节点将情况分为以下两种:

> 这里令 k(x) 为 x 节点上任一个 Key. x 上可能有 1-2 个 Key.
> a -- k(x) -- b 中的 k(x) 表示与 a,b 两个子树的 parent.
> e.g. 10 -- [12 (13) 14] -- 15 中, 14 为 13,15 的 parent, 12 为 10,13 的 parent.

1. 删除节点为叶子节点
2. 删除节点为路径上的节点

针对情况 1, 我们可以直接删除节点, 然后尝试自下而上对树的性质进行修复;
对于情况 2, 我们想办法将其转变为情况 1.

查找 k(z) 的中序后驱节点 k(x), 根据中序后驱节点的性质, k(x) 只可能为叶子节点且替换 k(z) 后不会引起 k(z) 所在节点的顺序性质.
将 k(x) 替换 k(z), 然后删除原来位置的 k(x), 这样我们就将情况转变为第一种:

```text
// case 1

|       |            |        |
z  --> null         z y  -->  y

// case 2

|                   |
z            -->    x
 \                   \
  ... - x             ... - null
```

现在考察叶子节点中 k(z) 被删除后的情况:

1. 叶子节点变为 `2-Node`
2. 叶子节点变为 `Null`

针对情况 1, 我们什么都不需要做, 已经满足树的所有性质.

针对情况 2, 我们破坏了性质 3, 因为存在一个为 `Null` 的空节点.
此时需要引入一种新的操作 `Key Rotation` 来修复性质, 该操作将考察删除节点的兄弟节点中的 key 值,
并尝试将多余的 Key 通过旋转的方式旋转到 `Null` 节点上, 以重新满足性质 3. 此时存在以下两种情况:

- 兄弟节点 b 为 `2-Node`
- 兄弟节点 b wei `3-Node`

针对前一种情况, 我们将父节点 k(p) 与兄弟节点 b 进行 `合并 (Merge)`,
然后将 `Null` 节点的子树 (如果有的话) 成为节点 b 的左子树, 最后删除原先的 k(p) 并将待处理节点的指针推进到删除后的节点.
此时如果待处理节点为 `Null` 则重复一次 `Key Rotaion`. 如下:

```text
   k(p)                  (null)
  /   \                    |
null   b       -->      k(p)  b
 |    /  \            /    |   \
 m   bl   br        m     bl    br
```

针对后一种情况, 我们采用 `借用 (Adopt)` 的方式将兄弟节点中一个 Key 通过一条 "借链" 进行移动:

```text
    k(p)                     b1
   /   \           ->      /    \
 null  b1, b2            k(p)    b2
 |    /  |   \          /  \    /  \
 m   bl  bc   br       m   bl  bc  br
```

移动后结束算法, 树的所有属性都已经保持.

下面给出伪码实现, 使用了递归存储 parent 信息 (z), 可以在实现时展开为迭代形式提高效率:

```text
// Tree 代表一个 2-3 树
// Node 代表节点
// Key 代表节点值, 我们假设如果存在 Value 的话, Value 包含在 Key 的结构中且 Key 是可比较的.
INPUT Key k     // 需要删除的 key
INPUT Tree tree

IF (tree.isEmpty)
  RETURN

root = CALL DELETE_AND_FIXED(tree.root, k)
IF (root IS 1-Node)
  tree.root = root.firstChildOrNull
  tree.height -= 1

FUNCTION DELETE_AND_FIXED(Node z, Key k)
  IF (z.has(k))
    IF (z.isLeaf)
      z.delete(k)
      RETURN z

    xk = z(k) right sub-tree's SUCCESSOR Node and Key
    z.replace(k, xk)
    dn = DELETE_AND_FIXED(z's child WHERE SHOUD DELETE xk, xk)
  ELSE
    dn = DELETE_AND_FIXED(z's child WHERE SHOUD DELETE k, k)

  IF (dn IS 1-Node)
    b = z.brother(dn)
    IF (b.is3Node)
       ADOPT(z)

    return MERGE(z)

  RETURN z  // 确保返回当前节点的状态
```

## 参考资料

1. [OI Wiki - 2-3 树](https://oi-wiki.org/ds/2-3-tree/)
2. [多路查找树---2-3 树和 2-3-4 树的深入理解](https://www.cnblogs.com/lishanlei/p/10707791.html)
3. [二叉树与多叉树](https://blog.csdn.net/wangzilong_2019/article/details/106036911)
4. [2-3 Trees \| (Search, Insert and Deletion)](https://www.geeksforgeeks.org/2-3-trees-search-and-insert/)
5. [CMSC 420: Lecture 6 - 2-3 Trees](https://www.cs.umd.edu/class/fall2020/cmsc420-0201/Lects/lect06-23tree.pdf)
6. [Wiki - 2–3 tree](https://en.wikipedia.org/wiki/2%E2%80%933_tree)
<!-- refs -->

[b-tree-ssd]: https://softwareengineering.stackexchange.com/a/114934
[blog-binary-search-tree]: /post/202409/binary-search-tree
