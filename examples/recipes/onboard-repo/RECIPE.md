---
name: onboard-repo
description: Map a new repository, draft docs, and open a tracking issue. The map fans out to two independent steps.
version: 0.3.0
tags: [onboarding, docs]
inputs:
  - name: repo_path
    type: string
    required: true
outputs:
  - name: tracking_issue
steps:
  - id: map
    uses: repo-map
    description: Build a structural map of the repository.
    inputs:
      path: "${inputs.repo_path}"
    produces: repo_map
  - id: draft_readme
    uses: doc-writer
    description: Draft a README from the repo map.
    inputs:
      map: "${steps.map.output}"
    produces: readme_draft
  - id: draft_arch
    uses: doc-writer
    description: Draft an architecture note from the repo map.
    inputs:
      map: "${steps.map.output}"
    produces: arch_draft
  - id: open_issue
    description: Open a tracking issue linking both drafts.
    needs: [draft_readme, draft_arch]
    inputs:
      readme: "${steps.draft_readme.output}"
      arch: "${steps.draft_arch.output}"
    produces: tracking_issue
---
Onboard a new repo: map it, draft README and architecture notes in parallel
off the same map, then open one tracking issue referencing both.
