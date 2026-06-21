---
name: cyclic
description: A recipe whose steps form a dependency cycle on purpose.
version: 1.0.0
steps:
  - id: a
    needs: [c]
    produces: out_a
  - id: b
    needs: [a]
    produces: out_b
  - id: c
    needs: [b]
    produces: out_c
---
a needs c, c needs b, b needs a: a cycle.
