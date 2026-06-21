---
name: translate
description: Translate input text into the target language, preserving tone and named entities.
version: 1.1.0
lang: en
tags: [translation, content]
model_hints:
  temperature: 0.3
  max_tokens: 800
variables:
  - name: text
    type: string
    required: true
  - name: target_language
    type: string
    required: true
    description: Target language code or name (e.g. "fr", "Hindi").
  - name: preserve_entities
    type: boolean
    required: false
    description: When true, leave proper nouns and brand names untranslated.
examples:
  - input:
      text: The release ships on Monday and the team is celebrating.
      target_language: French
      preserve_entities: true
    expected: La sortie a lieu lundi et l'équipe fête cela.
---
Translate the following text into {{target_language}}.

If preserve_entities is set, leave brand names and proper nouns in the
original language.

Text:
{{text}}
