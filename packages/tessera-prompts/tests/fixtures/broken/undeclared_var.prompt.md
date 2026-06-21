---
name: undeclared_var
description: Uses a variable that is not declared in variables.
version: 1.0.0
variables:
  - name: declared_var
    type: string
---
Use {{declared_var}} and also {{undeclared_var}}.
