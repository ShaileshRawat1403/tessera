---
name: refund_window
description: Explain the refund eligibility window to a customer.
version: 1.0.0
lang: en
tags: [customer-support, billing]
model_hints:
  temperature: 0.2
  max_tokens: 250
variables:
  - name: customer_name
    type: string
    required: true
  - name: days_since_purchase
    type: number
    required: true
    description: Days between purchase and refund request.
examples:
  - input:
      customer_name: Maya
      days_since_purchase: 18
    expected: |
      Hi Maya, your purchase falls inside the 30 day refund window so we can
      process this for you. Here are the next steps.
  - input:
      customer_name: Arjun
      days_since_purchase: 45
    expected: |
      Hi Arjun, your purchase is past the 30 day refund window. We can still
      offer account credit; let me know if that works.
---
Hi {{customer_name}}, thanks for reaching out about a refund.

Your purchase was {{days_since_purchase}} days ago. Our standard refund window
is 30 days. Tell the customer what that means for their specific request, and
offer a next step.
