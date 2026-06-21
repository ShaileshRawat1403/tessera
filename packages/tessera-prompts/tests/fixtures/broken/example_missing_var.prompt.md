---
name: example_missing_var
description: Example does not supply a required variable.
version: 1.0.0
variables:
  - name: required_a
    type: string
    required: true
  - name: required_b
    type: string
    required: true
examples:
  - input:
      required_a: hello
    expected: missing required_b on purpose
---
{{required_a}} then {{required_b}}.
