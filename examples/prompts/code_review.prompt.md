---
name: code_review
description: Review a code diff for correctness, reuse, and clarity at the requested effort level.
version: 0.2.0
lang: en
tags: [engineering, review]
model_hints:
  temperature: 0.1
variables:
  - name: diff
    type: string
    required: true
    description: Unified diff of the change under review.
  - name: effort
    type: string
    required: true
    description: One of low, medium, high, max.
  - name: focus_areas
    type: list
    required: false
    description: Optional list of areas to weigh more heavily.
examples:
  - input:
      diff: |
        --- a/util.py
        +++ b/util.py
        @@
        -def add(a, b): return a+b
        +def add(a, b):
        +    return a + b
      effort: low
    expected: Formatting only; no correctness or reuse concerns at low effort.
---
You are reviewing the following diff at effort level **{{effort}}**.

Focus areas: {{focus_areas}}

```diff
{{diff}}
```

Report bugs, reuse opportunities, and clarity issues. Use bullet points. Quote
specific lines when calling out problems.
