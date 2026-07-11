# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities **privately**, not via public issues.

- Use GitHub's private vulnerability reporting for this repository
  (Security → Report a vulnerability), or
- email the maintainer at **many.kasiriha@gmail.com** with `[risqlet security]`
  in the subject.

Please include a description, reproduction steps, and the affected version.
You will get an acknowledgement, and we will coordinate a fix and disclosure
timeline with you.

## Scope notes specific to risqlet

- **Generated guardrails and hooks run commands.** `risqlet guardrails` emits
  hooks/permissions from a vetted template library, but installed hooks execute
  in your environment — review before installing (`generate` and `diff` never
  write; `install` is explicit).
- **The human-principal gate is a convention, not authentication.** Register
  lifecycle transitions require a `human:` principal in the event log, but that
  is enforced by `risqlet validate` and code review, not by an auth system.
- **The MCP server performs no external inference** and keeps all state in the
  project's `.risqlet/` files; treat it like any tool with write access to your
  repository.
