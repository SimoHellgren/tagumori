from filetags.models.node import Node


def test_creation():
    n = Node("value")

    assert n
    assert n.value == "value"
    assert n.parent is None
    assert n.children == []


def test_children_1():
    """test creating children by specifying their parent"""
    parent = Node("parent")
    child1 = Node("child1", parent=parent)
    child2 = Node("child2", parent=parent)

    assert child1 in parent.children
    assert child2 in parent.children

    assert child1.parent is parent
    assert child2.parent is parent


def test_children_2():
    """test creating children by specifying them as children for parent"""
    child1 = Node("child1")
    child2 = Node("child2")
    parent = Node("parent", children=[child1, child2])

    assert child1 in parent.children
    assert child2 in parent.children

    assert child1.parent is parent
    assert child2.parent is parent


def test_path():
    n1 = Node("1")
    n2 = Node("2", parent=n1)
    n3 = Node("3", parent=n2)
    n4 = Node("4", parent=n3)

    assert n1.path() == (n1,)
    assert n2.path() == (n1, n2)
    assert n3.path() == (n1, n2, n3)
    assert n4.path() == (n1, n2, n3, n4)


def test_ancestors():
    n1 = Node("1")
    n2 = Node("2", parent=n1)
    n3 = Node("3", parent=n2)
    n4 = Node("4", parent=n3)

    assert n1.ancestors() == tuple()
    assert n2.ancestors() == (n1,)
    assert n3.ancestors() == (n1, n2)
    assert n4.ancestors() == (n1, n2, n3)


def test_siblings():
    n1 = Node("1")
    n2 = Node("2", parent=n1)
    n3 = Node("3", parent=n1)
    n4 = Node("4", parent=n1)

    assert not n1.siblings()
    assert n1 not in n2.siblings()
    assert n2 not in n2.siblings()
    assert n3 in n2.siblings()
    assert n4 in n2.siblings()


def test_add_child():
    n1 = Node("1")
    n2 = Node("2", parent=n1)
    n3 = Node("3")

    n1.add_child(n3)

    # ensure n2 is unchanged
    assert n2 in n1.children
    assert n2.parent is n1

    # ensure n3 is correct
    assert n3 in n1.children
    assert n3.parent is n1


def test_attach():
    n1 = Node("1")
    n2 = Node("2", parent=n1)
    n3 = Node("3")

    n3.attach(n1)

    # ensure n2 is unchanged
    assert n2 in n1.children
    assert n2.parent is n1

    # ensure n3 is correct
    assert n3 in n1.children
    assert n3.parent is n1


def test_detach():
    n1 = Node("1")
    n2 = Node("2", parent=n1)
    n3 = Node("3", parent=n1)

    n2.detach()

    # ensure n3 is unchanged
    assert n3 in n1.children
    assert n3.parent is n1

    # ensure n2 is correct
    assert n2 not in n1.children
    assert n2.parent is None


def test_preorder(nodes: list[Node]):
    tree = nodes[0]

    assert [n.value for n in tree.preorder()] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_descendants(nodes: list[Node]):
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes

    assert [n.value for n in n1.descendants()] == [2, 3, 4, 5, 6, 7, 8]
    assert [n.value for n in n2.descendants()] == [3, 4]
    assert [n.value for n in n3.descendants()] == []
    assert [n.value for n in n4.descendants()] == []
    assert [n.value for n in n5.descendants()] == []
    assert [n.value for n in n6.descendants()] == [7, 8]
    assert [n.value for n in n7.descendants()] == [8]
    assert [n.value for n in n8.descendants()] == []


def test_root(nodes: list[Node]):
    root = nodes[0]

    assert root.is_root

    # test that "root" is the root for all children
    for node in root.preorder():
        assert node.root is root


def test_leaves(nodes: list[Node]):
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes

    leaves = list(n1.leaves())

    assert n1 not in leaves
    assert n2 not in leaves
    assert n3 in leaves
    assert n4 in leaves
    assert n5 in leaves
    assert n6 not in leaves
    assert n7 not in leaves
    assert n8 in leaves


def test_get_path(nodes: list[Node]):
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes
    tree = n1

    # happy paths
    assert tree.get_path([1]) is n1
    assert tree.get_path([1, 2]) is n2
    assert tree.get_path([1, 2, 3]) is n3
    assert tree.get_path([1, 2, 4]) is n4
    assert tree.get_path([1, 5]) is n5
    assert tree.get_path([1, 6]) is n6
    assert tree.get_path([1, 6, 7]) is n7
    assert tree.get_path([1, 6, 7, 8]) is n8

    # sad paths
    assert tree.get_path([]) is None
    assert tree.get_path([1, 2, 3, 4]) is None
    assert tree.get_path([-1]) is None
    assert tree.get_path([8]) is None


def test_get_path_remainder(nodes: list[Node]):
    tree = n1 = nodes[0]

    assert tree.get_path_remainder([1]) == (n1, [])
    assert tree.get_path_remainder([1, 3]) == (n1, [3])

    assert tree.get_path_remainder([]) == (None, [])


def test_from_path():
    p = [1, 2, 3]

    node = Node.from_path(p)

    assert node.value == 1
    assert [n.value for n in node.preorder()] == [1, 2, 3]


def test_find_all(nodes: list[Node]):
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes
    tree = n1

    result = list(tree.find_all(lambda x: x.value > 5))

    assert n1 not in result
    assert n2 not in result
    assert n3 not in result
    assert n4 not in result
    assert n5 not in result
    assert n6 in result
    assert n7 in result
    assert n8 in result

    assert list(tree.find_all(lambda x: x.value < 0)) == []


def test_find(nodes: list[Node]):
    tree = nodes[0]
    n6 = nodes[5]

    result = tree.find(lambda x: x.value > 5)

    assert n6 == result

    assert tree.find(lambda x: x.value < 0) is None


def test_paths_down(nodes: list[Node]):
    tree = nodes[0]

    paths = [tuple(map(lambda x: x.value, path)) for path in tree.paths_down()]

    assert (1, 2, 3) in paths
    assert (1, 2, 4) in paths
    assert (1, 5) in paths
    assert (1, 6, 7, 8) in paths

    n6 = nodes[5]
    n7 = nodes[6]
    n8 = nodes[7]

    (path,) = n6.paths_down()
    assert path == (n6, n7, n8)


def test_glob(nodes: list[Node]):
    tree = nodes[0]
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes

    # should return all paths if wilcard root
    result = list(tree.glob(["*"]))

    for path in tree.paths_down():
        assert path in result

    # should return all paths if matches root
    result = list(tree.glob([1]))

    for path in tree.paths_down():
        assert path in result

    # should only match paths with 2
    result = list(tree.glob(["*", 2]))

    assert len(result) == 2
    assert (n1, n2, n3) in result
    assert (n1, n2, n4) in result


def test_find_path(nodes: list[Node]):
    tree = nodes[0]
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes

    result = list(n1.find_path([7, 8]))
    assert result

    result = list(n1.find_path([8, 7]))
    assert not result

    result = list(n1.find_path([2, 5]))
    assert not result

    result = list(n1.find_path([999]))
    assert not result


def test_is_rooted_subtree(nodes: list[Node]):
    tree = nodes[0]
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes

    assert tree.is_rooted_subtree(tree)

    # roots must be same
    assert not n2.is_rooted_subtree(n1)

    # matches even when other has "extra" branches
    assert Node(n1.value, [n2]).is_rooted_subtree(n1)

    assert Node(1, [Node(2)]).is_rooted_subtree(n1)

    # skipping a level shouldn't match
    assert not Node(1, [Node(3)]).is_rooted_subtree(n1)

    # non-existent child should not match
    assert not Node(1, [Node(1000)]).is_rooted_subtree(n1)


def test_is_subtree(nodes: list[Node]):
    tree = nodes[0]
    [n1, n2, n3, n4, n5, n6, n7, n8] = nodes

    assert tree.is_subtree(tree)

    # roots may be different
    for n in nodes:
        assert n.is_subtree(tree)

    assert not n2.is_subtree(n3)

    # skipping a level shouldn't match
    assert not Node(1, [Node(3)]).is_subtree(n1)

    # non-existent child should not match
    assert not Node(1, [Node(1000)]).is_subtree(n1)


def test_merge():
    a = Node("A", [Node("a")])
    b = Node("A", [Node("b")])

    a.merge(b)

    x, y = a.children

    assert x.value == "a"
    assert y.value == "b"


def test_merge_nested():
    a = Node("A", [Node("a")])
    b = Node("A", [Node("a", [Node("aa")])])

    a.merge(b)

    assert a.children[0].children[0].value == "aa"


def test_merge_overlap():
    a = Node("A", [Node("a"), Node("b")])
    b = Node("A", [Node("b"), Node("c")])

    a.merge(b)

    assert sorted(n.value for n in a.children) == ["a", "b", "c"]


def test_merge_fail():
    a = Node("A", [Node("a"), Node("b")])
    b = Node("B", [Node("b"), Node("c")])

    a.merge(b)

    # nothing should change
    assert sorted(n.value for n in a.children) == ["a", "b"]
    assert sorted(n.value for n in b.children) == ["b", "c"]


def test_str():
    tree = Node("A", [Node("B", [Node("C")]), Node("D")])

    assert str(tree) == "A[B[C],D]"


def test_repr():
    tree = Node("A", [Node("B", [Node("C")]), Node("D")])

    assert repr(tree) == "Node('A')"


def test_hash():
    a1 = Node("A", [Node("b"), Node("c")])
    a2 = Node("A", [Node("c"), Node("d")])

    b = Node("B")

    # hash should be consistent
    assert hash(a1) == hash(a1)

    # hash is only dependent on node.value, not children
    # (silly as it may be)
    assert hash(a1) == hash(a2)

    # hash is different for different values
    assert hash(a1) != hash(b)
