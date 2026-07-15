## MODIFIED Requirements

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

Supported SHALL mean the data is intact, not merely that the process exited 0. A
platform on which risqlet silently corrupts what it reads or writes is not
supported, however green its test run. Because a passing exit code cannot see a
mojibaked string, platform correctness SHALL be asserted on content — text
round-tripping unchanged — and not on exit status alone.

#### Scenario: Unsupported component is skipped with a reason
- **WHEN** the suite runs on Windows and reaches a guardrail-hook test
- **THEN** the test is skipped with a stated reason naming the POSIX dependency,
  rather than failing or being omitted from the run

#### Scenario: Support claim matches what CI runs
- **WHEN** documentation or packaging metadata claims a platform is supported
- **THEN** CI exercises install, agent setup, and the test suite on that platform

#### Scenario: Silent corruption fails the suite
- **WHEN** a platform decodes shipped data or a register in the host's locale
  encoding rather than UTF-8, mangling characters without raising
- **THEN** a test fails on the mangled content, rather than the suite passing
  because nothing crashed

## ADDED Requirements

### Requirement: encoding-correctness is enforced, not remembered
risqlet SHALL enforce explicit text encoding automatically rather than by review
convention, since an omitted `encoding=` is invisible on the platforms most
development happens on and only misbehaves on Windows.

Enforcement SHALL combine a static check and a runtime check, because neither is
sufficient alone: static linting cannot resolve the type of a path held on an
attribute or passed as a parameter and so misses call sites, while a runtime check
only sees code the tests execute. Where the static rule is unavailable or
incomplete, that gap SHALL be stated rather than assumed covered.

#### Scenario: A new unencoded read is rejected
- **WHEN** a contributor adds a `read_text()` with no `encoding` argument and the
  checks run
- **THEN** it is reported, rather than merging and silently corrupting data on
  Windows only

#### Scenario: Enforcement reaches what linting cannot infer
- **WHEN** an unencoded text call is made through a path held on an object
  attribute, which the static rule cannot resolve
- **THEN** the runtime check fails the test run on that call
