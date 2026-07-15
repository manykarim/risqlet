## ADDED Requirements

### Requirement: supported platforms are named and proven per component
risqlet SHALL name the platforms it supports (Linux, macOS, Windows) and SHALL NOT
claim support for a platform its automated checks do not exercise. Support SHALL be
stated per component rather than for the product as a whole, because it differs:
the CLI core, register, `check`, `setup`, and the installed check hook SHALL work on
all three; `risqlet guardrails` is POSIX-only (its hook templates are shell and its
verifier uses POSIX process handling) and SHALL be documented as unsupported on
Windows rather than presented as working.

Where a component is unsupported on a platform, that SHALL be visible in the test
suite as an explicit, reasoned skip — not as an absent test, a silently narrowed
selection, or a passing test that never ran the code.

#### Scenario: Unsupported component is skipped with a reason
- **WHEN** the suite runs on Windows and reaches a guardrail-hook test
- **THEN** the test is skipped with a stated reason naming the POSIX dependency,
  rather than failing or being omitted from the run

#### Scenario: Support claim matches what CI runs
- **WHEN** documentation or packaging metadata claims a platform is supported
- **THEN** CI exercises install, agent setup, and the test suite on that platform

### Requirement: CI covers every supported platform
The `test` workflow SHALL run on Linux, macOS, and Windows on push, pull request,
and manual dispatch. Each platform SHALL run the full test suite — not a hand-picked
subset — so that a green run means the same thing everywhere and no failure is
hidden by selection. Platform differences SHALL be expressed as skips inside the
suite, where they are visible and reasoned, rather than as omissions in the job.

#### Scenario: All three platforms run
- **WHEN** a pull request is opened
- **THEN** the suite runs on Linux, macOS, and Windows, and a failure on any of them
  fails the workflow

#### Scenario: A platform-specific regression is caught
- **WHEN** a change makes an installed hook depend on a shell again
- **THEN** the Windows job fails rather than the bug reaching a user

### Requirement: the built artifact is installed and run on each platform
CI SHALL build the wheel and install it into a fresh environment that has no
development dependencies and no source tree on `sys.path`, then drive the real
`risqlet` console script, on each supported platform. Inspecting a wheel's file list
SHALL NOT be accepted as evidence that it installs or runs.

This SHALL exercise the entry point and the package data the CLI reads at runtime
(agent adapters, CI and guardrail templates, catalog packs, bundled skills), because
a wheel that omits data or whose console script is broken passes every source-tree
test.

#### Scenario: Clean install runs the CLI
- **WHEN** the wheel is installed into a fresh venv on a supported platform
- **THEN** the `risqlet` console script runs and reports its version

#### Scenario: Missing package data is caught
- **WHEN** a wheel ships without an agent adapter or template it loads at runtime
- **THEN** the clean-install job fails on the command that needs it, rather than the
  gap surfacing after release

#### Scenario: The tested install is the shipped one
- **WHEN** the clean-install job runs
- **THEN** it imports risqlet from the installed wheel, not from the checked-out
  source tree

### Requirement: agent setup is smoke-tested from a clean install per platform
CI SHALL run `risqlet setup` against each agent adapter on each supported platform
from the clean install, assert the expected artifacts are written, and assert that no
requested component was skipped for an unintended reason. A component the adapter
genuinely does not support, or that is out of scope at the chosen scope, SHALL be
distinguished from one skipped because it failed verification.

#### Scenario: Hook install regression is caught
- **WHEN** the Claude hook component fails verification on any platform
- **THEN** the smoke job fails naming the skip reason, rather than reporting success
  with a hook silently absent

#### Scenario: Every adapter is exercised
- **WHEN** the smoke job runs
- **THEN** each adapter risqlet ships is set up and its artifacts asserted, so an
  adapter cannot rot unnoticed
