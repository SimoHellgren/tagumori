# Tag Query DSL: Complete Algebra Reference

## Primitives

| Syntax | Name | Meaning |
|--------|------|---------|
| `a` | Tag | Record contains a node named `a` |
| `a[E]` | Nested tag | Record contains `a` with children satisfying `E` |
| `~` | Null/Leaf | No node (leaf marker or root marker depending on position) |
| `*` | Single wildcard | Any single node (anonymous tag) |
| `**` | Path wildcard | Any path of zero or more nodes |
| `*n*` | Bounded wildcard | Any path of at most n nodes |

## Operators (by precedence, highest first)

| Syntax | Name | Meaning |
|--------|------|---------|
| `!E` | Negation | Records NOT matching E |
| `E,F` | Conjunction (AND) | Records matching E AND F |
| `E\|F` | Disjunction (OR) | Records matching E OR F |
| `E^F` | Exclusive or | Records matching exactly one of E, F |
| `xor(E,F,G,...)` | N-ary XOR | Records matching exactly one operand |

---

## Core Distribution Identities

| Identity | Name |
|----------|------|
| `a[X,Y] ≡ a[X],a[Y]` | AND distributes out |
| `a[X\|Y] ≡ a[X]\|a[Y]` | OR distributes out |
| `a[X^Y] ≡ a[X]^a[Y]` | XOR distributes out |

---

## Negation Identities

| Identity | Meaning |
|----------|---------|
| `a[!X] ≡ a,!a[X]` | "a exists and a doesn't have X" |
| `!a[X] ≢ a[!X]` | These are NOT equivalent! |
| `a[!(X,Y)] ≡ a[!X\|!Y]` | De Morgan inside brackets |
| `a[!(X\|Y)] ≡ a[!X,!Y]` | De Morgan inside brackets |
| `!(X,Y) ≡ !X\|!Y` | De Morgan (outer level) |
| `!(X\|Y) ≡ !X,!Y` | De Morgan (outer level) |
| `!!X ≡ X` | Double negation elimination |
| `!a[!X] ≡ !a\|a[X]` | "If a exists, it has X" |

---

## Negation Semantics

| Expression | Meaning |
|------------|---------|
| `!a[x]` | Record does NOT contain a→x |
| `a[!x]` | Record contains `a`, but `a` has no child `x` |
| `a,x,!a[x]` | Record has both `a` and `x`, but not as parent-child |

---

## Null/Leaf Identities

| Identity | Meaning |
|----------|---------|
| `a[~]` | `a` exists and is a leaf (no children) |
| `~[a]` | `a` exists and is a root (no parent) |
| `a[~] ≡ a,leaf(a)` | Leaf equivalence |
| `~[a] ≡ a,root(a)` | Root equivalence |
| `a[!~] ≡ a[*]` | "a has at least one child" |
| `a[~,X] ≡ ∅` | Contradiction (can't be leaf AND have children) |
| `a[~\|X] ≡ a[~]\|a[X]` | "a is leaf OR a has X" |

---

## Wildcard Semantics

**Core principle**: `*` is an anonymous tag. `*[E]` means "there exists a child satisfying E".

| Expression | Meaning |
|------------|---------|
| `*` | Any single node exists here |
| `*[E]` | ∃ child satisfying E |
| `**` | Any path (zero or more nodes) |
| `**[E]` | ∃ descendant satisfying E |
| `*n*` | Any path of ≤n nodes |
| `*n*[E]` | ∃ descendant within n levels satisfying E |

---

## Wildcard Identities

| Identity | Meaning |
|----------|---------|
| `a[*] ≡ a,!leaf(a)` | a has at least one child |
| `a[!*] ≡ a[~]` | a has no children (is leaf) |
| `a[*[~]]` | a has a child that is a leaf |
| `a[**[z]] ≡ a[z] \| a[*[**[z]]]` | Recursive expansion |
| `a[*0*[z]] ≡ a[z]` | 0 levels = direct child |
| `a[*1*[z]] ≡ a[z] \| a[*[z]]` | ≤1 level = child or grandchild |

---

## Wildcard + Negation

| Expression | Meaning |
|------------|---------|
| `*[!x]` | ∃ node that has no child x |
| `!*[x]` | ¬∃ node with child x |
| `a[*[!x]]` | a has a child that has no x-child |
| `a[!*[x]]` | a has no child with x-child (no grandchild x) |
| `a[*,!x]` | a has ≥1 child, and none of them is x |
| `a[**[!x]]` | a has a descendant that has no child x |
| `a[!**[x]]` | a has no descendant x |

---

## Boolean Identities

| Identity | Name |
|----------|------|
| `X,X ≡ X` | AND idempotent |
| `X\|X ≡ X` | OR idempotent |
| `X,!X ≡ ∅` | Contradiction |
| `X\|!X ≡ ALL` | Tautology |
| `X^X ≡ ∅` | XOR self-cancellation |
| `a,(b\|c) ≡ (a,b)\|(a,c)` | AND distributes over OR |
| `a\|(b,c) ≡ (a\|b),(a\|c)` | OR distributes over AND |

---

## XOR Identities

| Identity | Meaning |
|----------|---------|
| `X^Y ≡ (X\|Y),!(X,Y)` | XOR = OR but not both |
| `X^Y ≡ (X,!Y)\|(!X,Y)` | XOR = one or the other |
| `xor(X) ≡ X` | Single operand |
| `xor(X,Y) ≡ X^Y` | Binary case |
| `xor(X,Y,Z)` | Exactly one of X, Y, Z matches |

---

## Simplification Rules

| Before | After | Condition |
|--------|-------|-----------|
| `a[X],a` | `a[X]` | `a[X]` implies `a` |
| `a[X],a[Y]` | `a[X,Y]` | Combine constraints |
| `a[*],a[x]` | `a[x]` | `a[x]` implies `a[*]` |
| `a,!a` | `∅` | Contradiction |
| `a\|!a` | `ALL` | Tautology |

---

## Comparison: Negation Positions

| Query | Interpretation | Example |
|-------|----------------|---------|
| `!a[b]` | No a→b edge exists | "Record lacks a parent of b" |
| `a[!b]` | a exists without b-child | "Record has a, but a doesn't lead to b" |
| `a,b,!a[b]` | Both exist, not linked | "Has a and b separately" |
| `!a[!b]` | If a exists, it has b | "Every a has a b-child" (or no a) |

---

## Quick Reference Card

```
OPERATORS (high to low precedence):
  !     NOT
  ,     AND  
  |     OR
  ^     XOR
  xor() N-ary XOR

PRIMITIVES:
  a       tag exists
  a[X]    tag with children matching X
  ~       null (leaf/root)
  *       any single node
  **      any path (0+ nodes)  
  *n*     any path (≤n nodes)

KEY IDENTITIES:
  a[X,Y]    = a[X],a[Y]         distribute AND
  a[X|Y]    = a[X]|a[Y]         distribute OR
  a[!X]     = a,!a[X]           inner negation
  a[!X]    ≠ !a[X]              NOT equivalent!
  a[~]      = a is leaf
  a[*]      = a has children
  a[*[!x]]  = a has child without x-grandchild
  a[!*[x]]  = a has no grandchild x
```