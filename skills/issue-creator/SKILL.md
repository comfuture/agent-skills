---
name: issue-creator
description: Create high-quality GitHub issues or issue drafts from repository evidence, user intent, and external documentation. Use when the user asks an agent to create, draft, file, open, or prepare an implementation issue, bug report, feature request, follow-up issue, or GitHub issue with researched facts, scope, non-goals, suggested direction, acceptance criteria, and validation notes.
license: MIT
compatibility: Works with Agent Skills-compatible coding agents. Creating issues directly requires GitHub CLI or an equivalent GitHub integration.
---

# Issue Creator

Create implementation-ready issues that preserve what was learned during investigation. Treat the issue as an engineering handoff: concrete enough for a future implementer to start safely, scoped enough to avoid accidental broad rewrites, and honest about uncertainties.

## Workflow

1. Inspect issue style before writing.
   - If the target repository or sibling repository has recent issues, read the newest relevant issues first.
   - Mirror the useful level of detail, section shape, and tone without copying irrelevant structure.
   - If there are no existing issues, use the default template in `references/issue-structure.md`.

2. Research from primary evidence.
   - Inspect the current code, docs, tests, workflows, logs, or issue/PR history that define the problem.
   - For platform, API, protocol, or framework behavior, verify against primary sources when facts may be stale or subtle.
   - Record discovered facts in the issue body, not just in the conversation.

3. Separate facts from direction.
   - Use concrete references for observed current behavior.
   - Mark recommendations as suggested direction, not as already proven design.
   - Include assumptions and open questions when they affect implementation choices.

4. Define boundaries.
   - State the goal.
   - State scope and non-goals explicitly.
   - Preserve user-specified constraints and exact nouns.
   - Avoid turning a narrow follow-up into a broad redesign.

5. Write acceptance criteria that can be verified.
   - Prefer observable behavior, commands, CI jobs, manual smoke tests, screenshots, logs, or API responses.
   - Include regression checks for existing behavior.
   - Include platform-specific validation when the issue depends on platform behavior.

6. Create the issue only after reviewing the body.
   - If the user asked to create the issue, use the repository's issue tool or `gh issue create`.
   - If the target repo is ambiguous, resolve it from cwd/remotes before creating.
   - If creation is risky or the user asked for a draft, return the issue body instead.

## Reference Files

- Read `references/issue-structure.md` when drafting any issue body.
- Read `references/research-and-evidence.md` when deciding what investigation to perform or how to word discovered facts.
- Read `references/checklist.md` before creating or returning the final issue.

## Style Rules

- Write GitHub issue titles and bodies in English, even when the user request or source discussion is in another language.
- Translate user-provided requirements, examples, and context into clear English for the issue body.
- Preserve exact non-English product names, UI labels, field values, error text, commands, and quoted strings when those literals are the implementation target or evidence.
- Prefer concise section prose over long bullet piles, but use bullets for facts and criteria.
- Use exact code symbols, routes, file paths, command names, event names, API names, and error messages.
- Do not overpromise. If something was inferred, say it was inferred.
- Do not include private secrets, credentials, tokens, or sensitive local-only paths unless the path is necessary and safe.
- Do not file duplicate issues without checking the target repository's existing issues when practical.
