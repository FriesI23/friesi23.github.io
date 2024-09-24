---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 算法学习 - 二叉搜索树 (Binary Search Tree)
excerpt: |
  在学习《算法导论》第12章中二叉搜索树 (Binary Search Tree) 后随便码了些字,
  同时提供一个简陋代码实现 (Python) 与部分中练习题的答案.
author: FriesI23
date: 2024-09-24 16:00:00 +0800
category: algorithm
tags:
  - algorithm
  - structure
  - tree
  - binary-search-tree
---

## 什么是二叉搜索树

二叉搜索树由一颗[二叉树][binary-tree-wiki]组织, 且需满足如下特性:

> 对于树中任一节点 x:
>
> - 左子树上的任一节点 y 都需要满足: `x > y`;
> - 右子树上的任一节点 z 都需要满足: `x <= z`;

二叉搜索树具有高效的查找, 插入和删除操作, 同时也能实现排序, 范围查询和查找最大/最小值等功能.
其 (以及其变体, 比如红黑树) 可以用来构造一种有序字典或者优先级队列.

## 树节点 (Node)

二叉树中的每一个节点都都需要包含 `父节点 (parent)`, `左孩子 (left)`, `右孩子 (right)`, `关键字 (key)` 与 `数据 (value)`.
可以使用 Python 定义一个基本节点的接口如下 (以下所有代码包括[完整实现](#bst-完整实现)都省略了 `数据` 部分):

```python
class Node(ABC, Generic[T]):
    """二叉搜索树节点, 包含一个 parent 和 left/right 叶子节点."""

    @property
    @abstractmethod
    def parent(self) -> Self | None:
        """节点的父节点"""
    @parent.setter
    @abstractmethod
    def parent(self, new_parent: Self | None): ...

    @property
    @abstractmethod
    def left(self) -> Self | None:
        """左孩子节点"""
    @left.setter
    @abstractmethod
    def left(self, new_left: Self | None): ...

    @property
    @abstractmethod
    def right(self) -> Self | None:
        """右孩子节点"""
    @right.setter
    @abstractmethod
    def right(self, new_right: Self | None): ...

    @property
    @abstractmethod
    def key(self) -> T:
        """节点存储数值"""
```

## 方法

一颗二叉搜索树可以提供 `search`, `minimum`, `maximum`, `successor`, `predecessor``, insert`, `delete` 等基本操作.

上面这些操作需要的时间与树的高度 `h` 成正比:

- 对于一颗完全搜索二叉树而言, 最坏情况为 `Θ(lgn)`.
- 对于一颗由 n 各节点组成的线性联调, 最坏情况为 `Θ(n)`.
- 对于一颗随机构造的二叉树, 其期望高度为 `O(lgn)`, 操作平均用时为 `Θ(lgn)`.

```text
// 完全二叉树    // 线性链
     a              a
   /   \             \
  b     c             b
 / \   / \             \
d  e   f  g             c
```

下面给出各个方法相关的信息与接口定义:

| 方法名                                                      | 作用                           | 上界 |
| ----------------------------------------------------------- | ------------------------------ | ---- |
| [search](#方法-搜索-search)                                 | 查找存储在树中 key 对应的节点. | O(h) |
| [maximum](#方法-最大值-maximum-与最小值-minimum)            | 查找树中最大 key 对应的节点.   | O(h) |
| [minimum](#方法-最大值-maximum-与最小值-minimum)            | 查找树中最小 key 对应的节点.   | O(h) |
| [successor](#方法-前驱-predecessor-与后继-successor-节点)   | 查找树中 key 的后继结点.       | O(h) |
| [predecessor](#方法-前驱-predecessor-与后继-successor-节点) | 查找树中 key 的前驱结点.       | O(h) |
| [insert](#方法-插入-insert)                                 | 向树中插入 key.                | O(h) |
| [delete](#删除-delete)                                      | 从树删除入 key.                | O(h) |

```python
class Tree(ABC, Generic[T]):
    """二叉搜索树结构和操作定义集"""

    @property
    @abstractmethod
    def root(self) -> Node[T] | None:
        """返回树根"""

    @abstractmethod
    def insert(self, node: Node[T]):
        """将 node 插入到树中, node 的 left/right 必须是空的"""

    @abstractmethod
    def delete(self, node: Node[T]):
        """将 node 从树中删除, node 必须是该树中的一部分"""

    @abstractmethod
    def search(self, key: T) -> Node[T] | None:
        """搜索树中的特定 key"""

    @abstractmethod
    def max(self) -> Node[T] | None:
        """获得树中的最大 key 对应的节点"""

    @abstractmethod
    def min(self) -> Node[T] | None:
        """获得树中的最小 key 对应的节点"""
```

### 方法: 最大值 (Maximum) 与最小值 (Minimum)

利用二叉搜索树的特性, 我们可以通过不断寻找左孩子或者右孩子的方式, 轻易的在 `O(h)` 内递归的寻找到该值.

下面给出 Python 代码片段, 采用递归方式实现:

```python
class _Node(Node[T]):
    # ...

    def max(self) -> Node[T] | None:
        def max_inner(tree: Node[T]):
            if tree.right is None:
                return tree
            return max_inner(tree.right)

        return max_inner(self)

    def min(self) -> Node[T] | None:
        def min_inner(tree: Node[T]):
            if tree.left is None:
                return tree
            return min_inner(tree.left)

        return min_inner(self)


class _Tree(Tree):
    # ...

    def max(self) -> Node[T] | None:
        return self._root.max() if self._root is not None else None

    def min(self) -> Node[T] | None:
        return self._root.min() if self._root is not None else None
```

### 方法: 搜索 (Search)

给定一个节点, 通过递归比较节点左右孩子 key 的方式向下移动, 直到找到节点.

代码如下, 同样使用递归实现, 也可以自行展开为迭代形式:

```python
class _Node(Node[T]):
    # ...

    def search(self, key: T) -> Node[T] | None:
        def search_inner(tree: Node[T] | None):
            if (tree is None) or key == tree.key:
                # 已经遍历到叶子节点, 或者已经找到相同的 key, 则直接返回
                return tree
            if key < tree.key:
                # 需要查找到的 key 比当前所在 node 的 key 小, 所以找 node 的左子树
                return search_inner(tree.left)
            return search_inner(tree.right)

        return search_inner(self)
```

### 方法: 前驱 (Predecessor) 与后继 (Successor) 节点

给定一个 key, 前驱节点为比 key 小的所有 key 中最大的一个, 后继结点为比 key 大的所有key 中最小的一个.
下面给出两者的数学定义和代码实现:

> 设 **S** 是一个有序集合，给定 k∈**S**，前驱节点 `pred(k)` 定义为：`pred(k) = max{x∈S ∣ x<k}`.
>
> 设 **S** 是一个有序集合，给定 k∈**S**，后继节点 `succ(k)` 定义为：`succ(k) = min⁡{x∈S ∣ x>k}`.

```python
class _Node(Node[T]):
    # ...

    def successor(self) -> Node[T] | None:
        if self.right is not None:
            # 如果给定 tree 有右子树, 则说明后继节点就在该子树中,
            # 该子树的最小值便是给定节点的后继节点.
            return self.right.min()

        def successor_inner(parent: Node[T] | None, node: Node[T]):
            # 需要找到这样一个节点: 该节点是其 parent 节点的左孩子.
            # 此时该 parent 节点便比前面查找的所有节点都大,
            # 因此该 parent 就是我们要找到后继节点,
            # 时刻记住的特性:
            #   一个二叉查找做的 left 子树中的所有 key 都比当前节点小,
            #   而 right 子树都比当前节点大, 这个定义是从树顶开始递归的.
            if parent is None or node is parent.left:
                # 没有 parent 说明找到最后也没有找到一个比当前节点大的节点;
                # node 为 parent 的左孩子说明 parent 比当前值大,
                # 而 parent 的所有右孩子都比 parent 大,
                # 因此 parent 就是我们要找的后继结点.
                return parent
            return successor_inner(parent.parent, parent)

        # 递归的沿树向上查找一个比当前节点大的值.
        return successor_inner(self.parent, self)

    def predecessor(self) -> Node[T] | None:
        # 前驱节点和后继节点代码是对应的
        if self.left is not None:
            return self.left.max()

        def predecessor_inner(parent: Node[T] | None, node: Node[T]):
            if parent is None or node is parent.right:
                return parent
            return predecessor_inner(parent.parent, parent)

        return predecessor_inner(self.parent, self)
```

### 方法: 插入 (Insert)

从树根 (root) 触发, 不断比较需要插入的 key 和当前节点 key 的大小以决定插入到节点的左子树还是右子树中.
递归的重复上面的操作, 直到需要插入的位置为空, 则插入到该位置.

下面为实现代码:

```python
class _Tree(Tree):
    # ...

    def insert(self, node: Node[T]):
        assert node.left is None and node.right is None and node.parent is None

        def find_insert_pos(crt_node: Node[T] | None, find_node: Node[T] | None = None):
            # 沿树向下遍历, 寻找需要插入节点的位置.
            if crt_node is None:
                return find_node
            if node.key < crt_node.key:
                return find_insert_pos(crt_node.left, crt_node)
            return find_insert_pos(crt_node.right, crt_node)

        parent_node = find_insert_pos(self._root)

        # 将 node 的父亲节点指向需要被插入的位置, 此时 parent <-- node
        node.parent = parent_node
        if parent_node is None:
            # parent_node 只可能在树为空时为 None, 可以直接讲 Node 作为树根并返回.
            self._root = node
        elif node.key < parent_node.key:
            # 需要插入位置节点的值比被插入 node 的值大, 将 node 放入到左孩子中,
            # 此时 node <--> parent -- null.
            parent_node.left = node
        else:
            # 需要插入位置节点的值比被插入 node 的值小, 将 node 放入到右孩子中,
            # 此时 null -- parent <--> node.
            parent_node.right = node
```

### 删除 (Delete)

假设需要删除的节点为 z, 分为以下几种种情况:

1. 节点 z 为叶子节点, 此时简单删除该节点即可.
2. 节点 z 存在一个孩子节点 r, 则让 r 替换 z 即可.
3. 节点 z 左右都存在子节点, 需要先找到 z 的后继结点y, 此时又分为以下两种情况:
    1. z 的右孩子 r 即为后继结点 y, 此时可以使用 `情况2` 删除 z, 最后将 z 的左孩子 l 成为 y 的左孩子即可.
    2. 其他情况下:
       1. 临时删除 y 节点, 由于 y 必然只有一个子节点, 使用 `情况二` 将 y 的右孩子进行替换.
       2. 使 y 成为 z 的右孩子, 原来的右孩子 z 成为 y 的右孩子. 由于 y 为 z 的后继节点,
          因此 z 的右子树中没有比 y 更小的节点, 固该操作成立.
       3. 此时情况已经转变为 `情况3.1`, 按上述操作删除 z 即可.

下面给出删除的代码实现, 里面包含替换树 (Transplant) 相关的实现:

```python
class _Tree(Tree):
    # ...

    def delete(self, node: Node[T]):
        def transplant(origin_node: Node[T], replaced_node: Node[T] | None):
            # 使用 replaced_node 为根的子树替换 origin_node 为根的子树.
            # 替换完成后 origin_node.parent 对应的节点成为 replaced_node
            # 的父亲节点, 且 replaced_node 称为该节点的孩子.
            # 完成后 origin_node 会被丢弃.
            # e.g. before:
            #        ... <-- node -->
            #                         origin_node -->
            #                                        replaced_node
            #      after:
            #        ... <-- node -->
            #                         replaced_node
            if origin_node.parent is None:
                # 如果 origin_node 就是树根, 则直接使用 replaced_node 替换即可.
                self._root = replaced_node
            elif origin_node is origin_node.parent.left:
                # 如果 origin_node 为父节点的左孩子, 则调换左孩子,
                # 此时 replaced_node <-- origin_node.parent
                origin_node.parent.left = replaced_node
            else:
                # 否则替换右孩子,
                # 此时 origin_node.parent --> replaced_node
                origin_node.parent.right = replaced_node
            # 最后记得设置 replaced_node 的 parent.
            if replaced_node is not None:
                replaced_node.parent = origin_node.parent

        if node.left is None:
            # 如果需要删除的 node 没有左子树, 则直接删除 (使用右子树进行替换).
            transplant(node, node.right)
            return

        if node.right is None:
            # 同理, 使用左子树进行替换从而删除该节点.
            transplant(node, node.left)
            return

        # 找到需要删除 node 的后继结点, 由于 right 一定不为空, 则已 node 的后继节点
        # 一定是 node.right 中的最小值.
        successor_node = node.right.min()
        if successor_node.parent is not node:
            # 如果后继节点 successor_node 不是删除节点 node 的直接(右)孩子,
            # 则先将该后继节点的右孩子旋转上来 (在树结构中暂时剥离了该后继节点),
            # 然后让该后继节点成为被删除子树 node 右子树的父节点.
            # 由于后继节点只比当前节点大, 因此可以直接加入到当前节点的右孩子中,
            # e.g., before:
            #         left <-- node --> right
            #       after:
            #         left <-- node --> successor_node --> right
            # 这样就将树结构回到下下面需要处理的情况.
            transplant(successor_node, successor_node.right)
            successor_node.right = node.right
            successor_node.right.parent = successor_node
        # 后继节点 successor_node 位于需要删除节点 node 的右孩子上,
        # 使用后继节点替换需要删除的节点, 然后将删除节点的左子树恢复到该后继节点上,
        # 由于后继节点一定没有左子树, 所以直接将树接上去即可.
        transplant(node, successor_node)
        successor_node.left = node.left
        successor_node.left.parent = successor_node

```

上述实现中, `successor_node = node.right.min()` 将花费 `O(h)` 寻找后继, 其他均为常数时间.

## 《算法导论》第12章部分习题答案

### 12.3-4 删除操作可交换么?

> 删除操作可交换吗？可交换的含义是，先删除x再删除y留下的结果树与先删除y再删除x留下的结果数完全一样。
> 如果是，说明为什么？否则，给出一个反例。

不可以, 见如下示例:

```text
// 先删除 z, 再删除 l
  z        y        y
 / \      / \        \
l   r    l   r        r
   /        /        /
  y        x        x
   \
    x
```

```text
// 先删除 l, 再删除 z
  z        z        r
 / \        \      /
l   r        r    y
   /        /      \
  y        y        x
   \        \
    x        x
```

从树中删除 'z' 节点需要进行两次旋转, 其中第一次旋转会改变子树的结构 (将后继节点 y 旋转到最上面), 既

```text
    r         y
   /           \
  y             r
   \           /
    x         x
```

而其他三种删除结构并不会改变子树结构, 因此删除操作不是可交换.

本质是同样一组数据的二叉搜索树可会有多重合法的树结构, 可以看 [树同构 (Tree Isomorphism)](https://zh.wikipedia.org/zh-cn/%E6%A0%91%E5%90%8C%E6%9E%84).

### 13.3-5 使用 `后继节点` 而不是 `父节点` 实现的二叉搜索树

> 假设为每个节点换一种设计，属性x.p指向x的双亲，属性x.succ指向x的后继。
> 试给出使用这种表示法的二叉搜索树T上SEARCH, INSERT, DELETE操作的伪代码。
> 这些伪代码应在O(h)时间内执行完，其中h为树T的高度。（提示：应该设计一个返回某个节点的双亲的子过程。）

使用 `successor` 代替 `parent` 后, 我们仍然需要在插入和删除后使用到父节点, 因此 `O(h)` 的耗时从寻找后继节点变换到寻找父节点.
这里给出关键的代码实现片段, 完整实现看[这里](#后继节点版本):

```python
class _Tree(Tree[T]):
    # ...

    def parent(self, node: Node[T]) -> Node[T] | None:
        if node is self._root:
            # 节点已经是根节点了, 没有父节点
            return
        # 寻找当前节点所在子树中的最大值的后继节点. 根据搜索二叉树的性质可知,
        # 这个后继节点一定不在该子树中, 且比该子树内所有的 key 都要大.
        parent = node.max().succ
        if parent is None:
            # 该节点已经是自己子树中的最大节点 (没有右子树), 因此用树根 (root) 开始找.
            parent = self._root
        else:
            if parent.left == node:
                # 节点的左孩子为当前节点说明该节点就是 node 的父节点:
                # node <-- parent
                return parent
            # parent 肯定比 node 所在的子树大, 因此从 parent 的左子树中寻找.
            parent = parent.left

        def fetch_right_child(parent: Node[T]):
            if parent.right == node:
                return parent
            return fetch_right_child(parent.right)

        # 假设 node 位于 parent 的左孩子的左子树上, 则有 n.key < p.l.key < p.key.
        # 而 p 定义为 n 所在子树中最大值的后继节点, 因此有 n.key < n_max.key < p.l.ley < p.key.
        # 而这是不可能的, 因为此时 n_max.key 的后继节点应为 p.l.key 而不是 p.key.
        # 因此 n 必然存在于 p.left 节点 (此时 n.key == n_max.key == p.left.key < p.key )
        # 或是 p.left 节点的右子树中 (此时 n.key < m_max.key < p.left.key < p.left.<right>.key < p.key)
        # 特别的, 当没有后继节点时, 该子树一定包含整个树中最大的节点. 此时从 root 一直寻找右子树即可
        return fetch_right_child(parent)

    def predecessor(self, node: Node[T]) -> Node[T] | None:
        if node.left is not None:
            # 前驱节点肯定是当前节点左子树中的最大值
            return node.left.max()

        def find(tree: Node[T] | None, pred: Node[T] | None = None):
            if tree is None or tree.key == node.key:
                # 已经遍历到底或者遍历到当前节点, 说明上一次遍历的值就是前驱节点.
                return pred
            if tree.key < node.key:
                # 由小到大逐渐逼近 node 的值, 此时记录 tree 为暂定的前驱节点.
                return find(tree.right, tree)
            else:
                return find(tree.left, pred)

        return find(self._root)

    def insert(self, node: Node[T]):
        assert node.left is None and node.right is None and node.succ is None

        def find_insert_pos(crt_node: Node[T], find_node: Node[T] | None = None):
            if crt_node is None:
                return find_node
            if node.key < crt_node.key:
                return find_insert_pos(crt_node.left, crt_node)
            return find_insert_pos(crt_node.right, crt_node)

        parent_node = find_insert_pos(self._root)
        if parent_node is None:
            self._root = node
        elif node.key < parent_node.key:
            parent_node.left = node
            node.succ = parent_node
        else:
            parent_node.right = node
            node.succ = parent_node.succ
            parent_node.succ = node

    def delete(self, node: Node[T]):
        def transplant(origin_node: Node[T], replaced_node: Node[T] | None):
            # 使用 parent 方法获得父节点, 然后与普通实现一致, 该子方法为 O(h), h 为树的高度
            parent = self.parent(origin_node)
            if parent is None:
                self._root = replaced_node
            elif origin_node is parent.left:
                parent.left = replaced_node
            else:
                parent.right = replaced_node

        pred = self.predecessor(node)
        pred.succ = node.succ
        if node.left is None:
            transplant(node, node.right)
            return

        if node.right is None:
            transplant(node, node.left)
            return

        succ_node = node.right.min()
        # 与标准实现的is路一致, 如果不是删除节点 node 的直接(右)孩子,
        # 则先将右孩子旋转上来, 然后在进行子树替换. succ_node 保证节点没有左子树.
        if self.parent(succ_node) is not node:
            transplant(succ_node, succ_node.right)
            succ_node.right = node.right
        transplant(node, succ_node)
        succ_node.left = node.left
```

### 13.3-6 使用前驱节点代替后继节点

> 当TREE−DELETE中的节点z有两个孩子时，应该选择节点y作为它的前驱，而不是作为它的后继。
> 如果这样做，对TREE−DELETE应该做些什么必要的修改？一些人提出一个公平策略，
> 为前驱和后继赋予相等的优先级，这样得到了较好的实验性能。如何对TREE−DELETE进行修改来实现这样一种公平策略？

将[标准实现](#标准实现)中的 `delete` 方法修改如下:

```python
class _Tree(Tree[T]):
    # ...

    def delete(self, node: Node[T]):
        """删除节点, 但是使用 前驱节点 代替 后继节点 `node.right.min()`,
        并修改替换的 left/right 节点"""

        def transplant(origin_node: Node[T], replaced_node: Node[T] | None):
            if origin_node.parent is None:
                self._root = replaced_node
            elif origin_node is origin_node.parent.left:
                origin_node.parent.left = replaced_node
            else:
                origin_node.parent.right = replaced_node
            if replaced_node is not None:
                replaced_node.parent = origin_node.parent

        if node.left is None:
            transplant(node, node.right)
            return

        if node.right is None:
            transplant(node, node.left)
            return

        predecssor_node = node.left.max()
        if predecssor_node.parent is not node:
            # 使用前驱节点时, 旋转如下
            #     q             q                     q
            #     |             |                     |
            #     z             z        y            y
            # / \            \      /             / \
            # l   r   -->      r    l      -->    l   r
            # \                     \             \
            #     y                     x             x
            # / \
            # x  nil
            #
            # 1. 将 y(前驱节点)旋转上来
            # 2. 使用 y 替换 z
            transplant(predecssor_node, predecssor_node.left)
            predecssor_node.left = node.left
            predecssor_node.left.parent = predecssor_node
        transplant(node, predecssor_node)
        predecssor_node.right = node.right
        predecssor_node.right.parent = predecssor_node
```

## BST 完整实现

### 标准实现

{% include github_gist.html id="4a897a26694807e66c8eb270a8828caa" %}

### 后继节点版本

{% include github_gist.html id="84e9dc5628b1352dce2eaba82853746c" %}

<!-- refs -->

[binary-tree-wiki]: https://en.wikipedia.org/wiki/Binary_tree
