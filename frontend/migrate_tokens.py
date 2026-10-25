"""One-shot token migration: replace legacy hardcoded colors/fonts in page &
component TSX files with design-system tokens / CSS variables."""
import pathlib

ROOT = pathlib.Path(r"E:\sbn\frontend\src")

REPLACEMENTS = [
    # Accent
    ("rgba(0,113,227,", "rgba(23,131,255,"),
    ("rgba(0, 113, 227,", "rgba(23, 131, 255,"),
    ("#0071e3", "#1783ff"),
    ("#0077ed", "#167ff7"),
    ("#0051a8", "#0d63d8"),
    # Status
    ("#ff3b30", "#ff3849"),
    ("#d6302a", "#f73647"),
    ("#34c759", "#16c456"),
    # Neutral grays -> label tokens
    ("#1d1d1f", "var(--label-1)"),
    ("#6e6e73", "var(--label-2)"),
    ("#aeaeb2", "var(--label-3)"),
    # Hairlines / fills
    ("#d2d2d7", "var(--separator)"),
    ("#e8e8ed", "var(--separator-soft)"),
    ("#e5e5ea", "var(--separator-soft)"),
    ("#f5f5f7", "var(--bg)"),
    ("#f2f2f7", "var(--fill-1)"),
    ("#fafafa", "var(--fill-1)"),
    ("#f0f0f0", "var(--separator-soft)"),
    # Tints
    ("#ffeeee", "rgba(255,56,73,0.1)"),
    ("#fff4e5", "rgba(255,149,0,0.1)"),
    ("#e8f4fd", "rgba(23,131,255,0.1)"),
    ("#e8fde8", "rgba(22,196,86,0.1)"),
    ("#e8f8e8", "rgba(22,196,86,0.1)"),
    # Font stacks
    ("'JetBrains Mono', monospace", "var(--font-mono)"),
    ("'Inter', system-ui, sans-serif", "var(--font-ui)"),
    ("'Inter', sans-serif", "var(--font-ui)"),
]

SKIP_DIRS = {"ui"}  # components/ui/* already token-native
SKIP_FILES = {"Layout.tsx", "SpanWaterfall.tsx"}

changed_files = []
total = 0
for path in sorted(ROOT.rglob("*.tsx")):
    rel = path.relative_to(ROOT)
    if rel.parts[0] == "components" and len(rel.parts) > 1 and rel.parts[1] in SKIP_DIRS:
        continue
    if path.name in SKIP_FILES:
        continue
    text = path.read_text(encoding="utf-8")
    original = text
    hits = 0
    for old, new in REPLACEMENTS:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            hits += n
    if text != original:
        path.write_text(text, encoding="utf-8")
        changed_files.append((str(rel), hits))
        total += hits

for rel, hits in changed_files:
    print(f"{rel}: {hits} replacements")
print(f"\nTotal: {total} replacements across {len(changed_files)} files")
