---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 算法学习 - 二叉 B-树 (Binary B-Tree), 对称二叉 B-树 (Symmetric Binary B-tree) 与红黑树 (Red Black Tree)
excerpt:
author: FriesI23
date: 2024-10-09 16:00:00 +0800
category: algorithm
tags:
  - algorithm
  - structure
  - binary-b-tree
  - red-black-tree
---

红黑树很强大, 但其中很多操作和变换都很 "魔法", 简而言之就是难以直接理解.
现在网络上主流的两种理解方式为: "算法导论" 中的**双黑法**与 2-3-4 树等价的思路.
不过这些文章还是不能让我明白 `红黑树` 为什么要这么设计.
因此这边文章想从另一个角度聊探究以下: 红黑树的前身与现在.

## B-树 (B-Tree)

`B-Tree`, 1970年由 Bayer,R 与 McCreight,E 于 1970 年 ["ORGANIZATION AND MAINTENANCE OF LARG"][paper-btree] 中首次提出.
`B-Tree` 在处理大规模数据时提供高效的搜索, 插入, 删除和范围查询操作, 即使在现在也作为各大数据库的底层存储数据结构.
这里简单复述一下 `B-Tree` 的定义和性质:

- 节点定义, `B-Tree` 有两种节点:
  - 内部节点 (INTERNAL): 存储 Key 及其指向子树的指针.
  - 叶子节点 (LEAF): 只存储 Key.

- 性质, 对于一个 `m` 阶 `B-Tree`, 将满足:
  1. 每个节点最多拥有 `m` 个子节点
  2. 除 ROOT 和 LEAF 外, 每个节点最少看拥有 `cell(m/2)` 个子节点.
  3. ROOT 节点除非是 LEAF, 否则子节点数 `>=2`.
  4. 有 `k` 个子节点的节点拥有 `k-1` 个 Key, 按照升序 (asc) 排序, 即满足 `k[i]<=k[i+1]`
  5. 所有叶子结点都在同一层.

不过这次不深入讨论它, 只是为了引出下面的数据结构.

## 二叉 B-树 (Binary B-Tree)

`Binary B-Tree` 由 Bayer,R 于 1971 年 ["BINARY B-TREES FOR VIRTUAL MEMORY"][paper-bbtree] 中提出.
正如该论文的摘要中所属, 该结构是为了解决 `B-Tree` 遇到的存储开销,
使其更适合在单极存储 ([one-level store][wiki-single-level-store]) 中进行处理.

> Binary B-trees are a modification of B-trees described previously by Bayer and McCreight.
> They avoid the storage overhead encountered with B-trees and are suitable for processing in a one-level store.

不严谨的概述: 更适合在 "内存 (或虚拟内存)" 而不是 "内存-硬盘" 这类多级存储中使用的数据结构.

假设一个 `k=1` 的 `B-Tree`, 则节点可能存在以下两种方式:

```text
| p0 x1 p1 - - |      | p0 x1 p1 x2 p2 |

    x1 | -               x1 | x2
  /    |       or       /   |   \
p0     p1              p0  p1   p2
```

可以看到, 根据上一节提到了**性质2**, 每个节点可能是 "半满" 的, 这在内存中会造成浪费.
并且每个 `B-Tree` 节点在创建时都需要为其分配存储空间, 这在那个内存寸土寸金的年代也是不可接受的.

二叉 B-树提出了一种可能的优化方法: 使用 "线性链表" 而不是数组存储. 因此上面的结构变为如下:

```text
| p0 x1 p1 - - |      | p0 x1 p1 x2 p2 |

    x1                   x1 ->  x2
  /   \        or       /     /   \
p0     p1              p0    p1   p2
```

论文中将 x1 指向 x2 的指针称为 "水平的 (horizontal)" (`σ-pointer`),
而指向 "下一级" (子节点) 的指针称为 "垂直的 (vertical)" (`δ-pointer`).

转化后的如图所示 (Binary B-Tree 很像 AVL, 但是不是 AVL):

![Binary B-Tree](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/binary-b-tree-01.jpg)

下面引出相关定义:

- 节点分为以下两种:
  - NODE: 普通节点, 具有至少一个 `δ-pointer`.
  - LEAF: 叶子节点, 没有 `δ-pointer`.

1. 所有左指针都是 `δ-pointer`.
2. 从 ROOT 到任何叶子节点的每条路径都包含相同数量的 `δ-pointer`.
3. 一些右指针可能是 `σ-pointer`, 但不存在连续的 `σ-pointer`.
   即每一个 `σ-pointer` 指向节点的只能为 LEAF 或者右指针为 `δ-pointer`.

一颗 N 个节点的二叉 B-树的高度为 (计算方法见论文第 222~223 页):

```text
log(N+l) <= h i <= 2log(N+2)-2
```

从上面高度范围可以看出, 二叉 B-树并不是一个 "很平衡" 的树. 下面给出插入和删除的操作概要:

### 插入 (Insert)

将新节点 x 插入叶子节点时, 存在以下情况:

1. LEAF 是孤立的 (case1).
2. LEAF 所在层的路径上存在 `σ-pointer` (case2).

![Binary B-Tree Insertion](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/binary-b-tree-02.jpg)

针对 case1, 插入结束.

针对 case2, 因为违反了 `性质3` (引入了两个 `σ-pointer`), 因此需要通过 TRANSFER 过程将其移除. 这是一个递归的过程,
直到没有连续的 `σ-pointer` 或者到达 ROOT 节点.

```text
// Right, 如果 x0 缺失, 则 x4 成为新的 root.
x0                           x0 - x4        // 提升了一层, 但是这里可能又出现类似 x-x0-x4,
 \                              /   \       // 需要递归处理.
  x2 - x4 - x5   -->          x2     x5
 /    /                      /  \
x1  x3                      x1   x3

// 等价
    x0                           x0 | x4
      \                        /    |   \
  x2 | x4 | x5   -->        ...    x2   x5
 /   |                           /   \
x1   x3                        x1    x3

// Left, 如果 x5 缺失, 则 x3 成为新的 root.
     x5                      x3 - x5
    /                       /    /  \
   x1 - x3 - x4  -->      x1    x4   ...
  /    /                 /  \
x0    x2                x0  x2

// 等价
        x5                  x3 | x5
       /                  /    |   \
  x1 | x3 | x4   -->    x1    x4    ....
 /     |              /   \
x0     x2            x0    x2
```

### 删除 (Deletion)

<!-- refs -->

[paper-btree]: https://infolab.usc.edu/csci585/Spring2010/den_ar/indexing.pdf
[paper-bbtree]: https://dl.acm.org/doi/pdf/10.1145/1734714.1734731
[wiki-single-level-store]: https://en.wikipedia.org/wiki/Single-level_store