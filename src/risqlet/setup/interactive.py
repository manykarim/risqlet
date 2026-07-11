"""Stdlib interactive prompts for `risqlet setup` (no TUI dependency)."""

from __future__ import annotations


def multiselect(title: str, options: list[tuple[str, str]],
                preselected: set[str]) -> list[str]:
    """options: list of (id, label). Returns chosen ids. Toggle by number,
    'a' toggles all, empty line accepts."""
    chosen = set(preselected)
    while True:
        print(f"\n{title}")
        for i, (oid, label) in enumerate(options, 1):
            mark = "x" if oid in chosen else " "
            print(f"  [{mark}] {i}. {label}")
        raw = input("toggle number(s), 'a' all, Enter to accept: ").strip().lower()
        if raw == "":
            return [oid for oid, _ in options if oid in chosen]
        if raw == "a":
            chosen = set() if len(chosen) == len(options) else {oid for oid, _ in options}
            continue
        for tok in raw.replace(",", " ").split():
            if tok.isdigit() and 1 <= int(tok) <= len(options):
                oid = options[int(tok) - 1][0]
                chosen.symmetric_difference_update({oid})


def choose(title: str, options: list[str], default: str) -> str:
    print(f"\n{title}")
    for i, opt in enumerate(options, 1):
        d = " (default)" if opt == default else ""
        print(f"  {i}. {opt}{d}")
    raw = input(f"choose [1-{len(options)}], Enter for default: ").strip()
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1]
    return default


def confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in ("y", "yes")
