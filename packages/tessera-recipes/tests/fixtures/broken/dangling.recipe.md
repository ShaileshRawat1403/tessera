---
name: dangling
description: A recipe with a dangling step reference and an undeclared input reference.
version: 1.0.0
inputs:
  - name: real_input
steps:
  - id: first
    inputs:
      seed: "${inputs.missing_input}"
    produces: first_out
  - id: second
    inputs:
      from_ghost: "${steps.ghost.output}"
    produces: second_out
---
first references an undeclared input; second references a nonexistent step.
