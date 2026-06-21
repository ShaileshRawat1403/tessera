---
name: release-notes
description: Build release notes from recent commits, summarize them, and publish.
version: 1.0.0
tags: [git, release]
inputs:
  - name: since_tag
    type: string
    required: true
    description: The previous release tag to diff against.
outputs:
  - name: published_url
steps:
  - id: collect
    uses: changelog-generator
    description: Gather commits since the previous tag.
    inputs:
      range: "${inputs.since_tag}..HEAD"
    produces: raw_changelog
  - id: summarize
    uses: pr-summary
    description: Condense the raw changelog into highlights.
    needs: [collect]
    inputs:
      text: "${steps.collect.output}"
    produces: summary
  - id: publish
    description: Publish the summarized notes.
    inputs:
      body: "${steps.summarize.output}"
    produces: published_url
---
Generate release notes end to end: collect commits since the last tag,
summarize them into highlights, then publish. Each step feeds the next.
