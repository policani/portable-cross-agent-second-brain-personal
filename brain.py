#!/usr/bin/env python3
r"""brain.py - deterministic retrieval for a plain-markdown vault.

Zero dependencies (Python 3.8+ stdlib only). One file, two jobs:

Build the index
---------------
    python brain.py --index

Scans the vault's markdown, splits every page into heading-level sections,
and writes a keyword index to ``brain-index.json`` (for this script) and
``brain-index.js`` (for ``vault-map.html``, which loads it from the
filesystem without a server). Root-level ``*.md`` files (CLAUDE.md,
AGENTS.md, README.md) are indexed too, and every indexed page contributes
its outbound relationships — markdown links plus absolute workspace path
references — so the map can show how instruction files and notes actually
connect to folders and files. It also writes a small, durable relationship
ledger: explicit references are ``extracted``; content-neighbour links are
``inferred`` and carry their deterministic similarity score and shared terms.

Answer "where is X?" without spending model tokens
--------------------------------------------------
    python brain.py "which TTS voice did we use"
    python brain.py --show "approval gate rules"
    python brain.py --related "approval gate rules"

Query mode strips the question to keywords, scores every indexed section
against them (tf-idf with heading and filename bonuses), and prints the
top-ranked sections as ``path:line`` targets. ``--show`` also prints the
best section's text, so short factual lookups never require opening a file
at all. If the winning section is only a pointer to another page, the
pointer is followed one hop automatically.

``--related`` resolves the best matching file and prints its durable
relationships. This is deliberately evidence-aware: an explicit source link is
not presented as equivalent to an inferred content neighbour.

The index self-heals: if any scanned markdown file is newer than the index,
query mode rebuilds it before answering. There is no separate maintenance
step.

Configuration (optional)
------------------------
``brain-config.json`` next to this script may override defaults:

    {
      "vault_root": "..",
      "scan_dirs": ["notes/wiki", "notes/indexes", "projects"],
      "census": true,
      "exclude": ["scratch"],
      "applications": [{"name": "Google Drive", "kind": "mcp"}],
      "routines": [{"name": "daily-log", "schedule": "daily"}]
    }

* ``vault_root`` (default ``.``): the workspace the index describes,
  relative to this script. Point it at a parent folder to make the map and
  retrieval workspace-wide.
* ``scan_dirs`` (relative to ``vault_root``): where markdown *content* is
  indexed for retrieval. Defaults to the well-known vault layouts below.
* ``census`` (default false): when true, every file of every type under
  ``vault_root`` (including loose root-level files) is listed (name/size
  only, content not read) so ``vault-map.html`` shows the whole workspace, not just the
  indexed markdown. Census entries cost no retrieval tokens.
* ``exclude``: folder/file names to skip everywhere, merged with the
  defaults (node_modules, .git, __pycache__, build outputs, legacy-*).
* ``applications`` / ``routines`` feed the map's outer rings only.
* ``instructions``: independent nested ``AGENTS.md`` / ``CLAUDE.md`` discovery.
  Its ``root``, filename ``names``, explicit ``exclude`` list, and ``content``
  privacy switch let operational instructions be retrieved without adding all
  neighbouring files to ``scan_dirs``. Instruction scope remains local.
* ``agents``: where subagent definitions live, one entry per tool, e.g.
  ``[{"dir": "ops/cowork-agents", "tool": "cowork"},
     {"dir": "ops/.codex/agents", "tool": "codex"}]``. Both ``.md`` and
  ``.toml`` definitions are read (dot-folders allowed). The same role is
  expected in every tool; ``--index`` warns on roles missing a counterpart,
  and the map flags them. Without config, ``.claude/agents`` and
  ``.codex/agents`` under the vault root are auto-discovered.

Hygiene
-------
    python brain.py --junk            # list cache/swap/temp junk in the vault
    python brain.py --junk --delete   # remove it

Junk (editor swap files, ``__pycache__``, Office lock files, Thumbs.db,
``*.tmp``/``*.bak``) is always excluded from the index and map; ``--junk``
finds what is physically on disk so it can be deleted.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "brain-config.json"
INDEX_JSON = ROOT / "brain-index.json"
INDEX_JS = ROOT / "brain-index.js"
# Directories that count as vault memory when no scan_dirs are configured.
KNOWN_DIRS = ("knowledge-base", "wiki", "indexes")
SKILLS_DIR = "skills"
JUNK_PATTERNS = [
    "__pycache__", "*.pyc", "*.pyo", "*.swp", "*.swo", "*~", "~$*",
    "*.tmp", "*.temp", "Thumbs.db", "desktop.ini", "*.bak", "*.orig",
    "*.rej", "*.lock.tmp",
]
DEFAULT_EXCLUDES = [
    "node_modules", ".git", ".venv", "venv", "dist",
    "build", ".next", ".cache", "legacy-*", "_archive*",
    "brain-index.json", "brain-index.js",
] + JUNK_PATTERNS
# Instruction discovery must not inherit the normal content scanner's ``build``
# exclusion: active projects may put their local rules there. These safety
# exclusions still prevent dependency/cache/archive/temporary traversal.
INSTRUCTION_SAFETY_EXCLUDES = [
    "node_modules", ".git", ".venv", "venv", "dist", ".next", ".cache",
    "legacy-*", "_archive*",
] + JUNK_PATTERNS
DEFAULT_INSTRUCTIONS = {
    "enabled": True,
    "root": ".",
    "names": ["AGENTS.md", "CLAUDE.md"],
    "exclude": ["tmp", "node_modules", ".git", ".venv", "dist", "_archive*"],
    "content": True,
}
MAX_SHOW_LINES = 60          # cap on printed section body
POINTER_MAX_CHARS = 400      # a section this short that links out is a pointer
MAX_CENSUS = 60_000          # hard cap on census entries
MAX_REFS = 40                # per-file cap on outbound relationships
TOP_N = 3
SIMILARITY_THRESHOLD = 0.14  # conservative visual/retrieval-neighbour cutoff
MAX_SIMILAR_PER_FILE = 2     # avoid turning the ledger into a dense web
MAX_SIMILARITY_TERMS = 40    # same compact profile used by the map
MAX_SHARED_TERMS = 5

# File taxonomy used by the console and map.  Markdown files are refined by
# their path/name below; binary and structured formats are unambiguous enough
# to classify by extension first.
SCRIPT_EXT = frozenset("py pyw js mjs cjs jsx ts tsx sh bash zsh fish ps1 psm1 vb vbs sql r lua pl pm php java kt kts c cpp cc cxx h hpp cs fs fsx go rs swift rkt scala dart ex exs erl hrl clj cljs groovy gvy gradle make cmake dockerfile tf hcl bicep asm s sv vhd vhdl ipynb json jsonc json5 yaml yml toml ini cfg conf properties env css scss sass less xml xsl xslt".split())
OFFICE_EXT = frozenset("doc docx docm dot dotx odt rtf pdf xls xlsx xlsm xlsb ods csv tsv ppt pptx pptm pps ppsx odp pub vsd vsdx one".split())
GRAPHIC_EXT = frozenset("png apng jpg jpeg jpe gif bmp dib webp tif tiff heic heif avif ico cur svg ai eps ps psd psb xcf kra ora sketch fig".split())
MEDIA_EXT = frozenset("mp4 m4v mov avi mkv webm mpg mpeg m2ts mts ts wmv flv ogv 3gp 3g2 mp3 wav aiff aif flac m4a aac ogg oga opus wma amr mid midi".split())
SOFTWARE_EXT = frozenset("exe msi msp msix msixbundle appx appxbundle appimage deb rpm pkg dmg apk aab ipa jar war ear bin run com gadget".split())
ARCHIVE_EXT = frozenset("zip zipx rar 7z tar gz tgz bz2 xz zst lz lz4 cab arj lha lzh sit sitx dmg iso img vhd vhdx qcow2 bak backup".split())

HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
WORD_RE = re.compile(r"[a-z0-9][a-z0-9'\-]+")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")
LINK_ALL_RE = re.compile(r"\[[^\]]*\]\(([^)#\s]+)\)")
# Absolute workspace path references in prose/backticks, e.g. D:\Workspace\notes
PATH_REF_RE = re.compile(r"[A-Za-z]:[\\/][^\s`'\")\]>|,;]+")

STOPWORDS = frozenset("""
a about above after again all also am an and any are as at be because been
before being below between both but by can could did do does doing down
during each few file files find for from further had has have having he her
here hers him his how i if in into is it its itself just like me more most
my no nor not now of off on once only or other our ours out over own same
she should so some such than that the their theirs them then there these
they this those through to too under until up very was we were what when
where which while who whom why will with would you your yours yourself
please show tell give list get want need know locate look search using
""".split())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def load_config() -> dict:
    cfg = {"vault_root": ".", "scan_dirs": None, "census": False,
           "exclude": [], "applications": [], "routines": [], "agents": []}
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(read_text(CONFIG_PATH)))
        except json.JSONDecodeError as exc:
            sys.exit(f"brain-config.json is not valid JSON: {exc}")
    cfg["_root"] = (ROOT / cfg["vault_root"]).resolve()
    cfg["_excludes"] = DEFAULT_EXCLUDES + list(cfg.get("exclude") or [])
    instructions = dict(DEFAULT_INSTRUCTIONS)
    instructions.update(cfg.get("instructions") or {})
    instructions["_root"] = (cfg["_root"] / instructions["root"]).resolve()
    instructions["_names"] = {str(name).lower()
                              for name in instructions.get("names", [])}
    instructions["_excludes"] = (INSTRUCTION_SAFETY_EXCLUDES
                                  + list(instructions.get("exclude") or []))
    cfg["instructions"] = instructions
    if not cfg.get("scan_dirs"):
        cfg["scan_dirs"] = [d for d in KNOWN_DIRS
                            if (cfg["_root"] / d).is_dir()]
    return cfg


def excluded(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def walk(base: Path, patterns: list[str]):
    """Permission-tolerant recursive walk honouring exclude patterns."""
    try:
        entries = sorted(base.iterdir())
    except OSError:
        return
    for e in entries:
        if excluded(e.name, patterns) or e.name.startswith("."):
            continue
        if e.is_dir():
            yield from walk(e, patterns)
        elif e.is_file():
            yield e


def tokenize(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower())
            if len(w) > 2 and w not in STOPWORDS]


def file_category(path: Path, rel: str) -> str:
    """Return the console category for a workspace file."""
    ext = path.suffix.lower().lstrip(".")
    if ext in SCRIPT_EXT:
        return "script"
    if ext in OFFICE_EXT:
        return "office"
    if ext in GRAPHIC_EXT:
        return "graphic"
    if ext in MEDIA_EXT:
        return "media"
    if ext in SOFTWARE_EXT:
        return "software"
    if ext in ARCHIVE_EXT:
        return "archive"
    p, name = rel.lower(), path.name.lower()
    if re.search(r"(^|/)(examples/sample-outputs|sample-outputs|generated|indexes)(/|$)", p) or re.search(r"\d{4}-\d{2}-\d{2}", name):
        return "output"
    if re.search(r"(^|/)templates(/|$)", p) or re.search(r"_template\.md$|-template\.md$", name):
        return "template"
    if (name in {"agents.md", "claude.md", "skill.md", "instructions.md"}
            or re.search(r"(^|/)(chatgpt-project|workflow|skills)(/|$)", p)
            or re.search(r"trigger[-_]map|operating[-_]model|handoff[-_]rules|guardrail|runtime|start[-_]here|_prompt\.md$|[-_]prompts?\.md$|routing[-_]rules", name)):
        return "logic"
    return "reference"


def md_files(cfg: dict) -> list[Path]:
    out: list[Path] = []
    # Root-level instruction/readme files are part of the logical graph.
    try:
        out.extend(p for p in sorted(cfg["_root"].glob("*.md"))
                   if not excluded(p.name, cfg["_excludes"]))
    except OSError:
        pass
    for d in cfg["scan_dirs"]:
        base = cfg["_root"] / d
        if base.is_dir():
            out.extend(p for p in walk(base, cfg["_excludes"])
                       if p.suffix.lower() == ".md")
    return out


def instruction_files(cfg: dict) -> list[Path]:
    """Discover scoped instruction sources independently of ``scan_dirs``."""
    spec = cfg["instructions"]
    if not spec.get("enabled") or not spec["_root"].is_dir():
        return []
    return [p for p in walk(spec["_root"], spec["_excludes"])
            if p.name.lower() in spec["_names"]]


def indexed_md_files(cfg: dict) -> list[Path]:
    """Content-indexed Markdown, with instruction paths de-duplicated."""
    paths = list(md_files(cfg))
    if cfg["instructions"].get("content"):
        paths.extend(instruction_files(cfg))
    unique: dict[str, Path] = {}
    for path in paths:
        try:
            unique[rel_to_root(path, cfg)] = path
        except ValueError:
            continue
    return [unique[key] for key in sorted(unique)]


def extract_refs(text: str, path: Path, cfg: dict) -> list[str]:
    """Outbound relationships: relative md links + absolute workspace paths.

    Returned as vault-root-relative posix paths (files or folders). This is
    what lets the map show which folders/files a CLAUDE.md or AGENTS.md
    actually points at. Absolute paths are matched by the vault root string
    OR by top-level folder name, so references keep resolving when the
    vault is copied to another machine or drive.
    """
    refs: set[str] = set()
    base = path.parent
    for m in LINK_ALL_RE.finditer(text):
        t = m.group(1)
        if t.startswith(("http://", "https://", "mailto:")):
            continue
        try:
            p2 = (base / t).resolve()
            refs.add(p2.relative_to(cfg["_root"]).as_posix())
        except (ValueError, OSError):
            continue
    root_str = cfg["_root"].as_posix().lower()
    if "_tops" not in cfg:
        try:
            cfg["_tops"] = {d.name for d in cfg["_root"].iterdir()
                            if d.is_dir() and not d.name.startswith(".")}
        except OSError:
            cfg["_tops"] = set()
    for m in PATH_REF_RE.finditer(text):
        s = re.sub(r"/{2,}", "/", m.group(0).replace("\\", "/")).rstrip("/.:`,)")
        rel = None
        if s.lower().startswith(root_str + "/"):
            rel = s[len(root_str) + 1:].strip("/")
        else:
            segs = s.split("/")
            for i, seg in enumerate(segs):
                if seg in cfg["_tops"]:
                    rel = "/".join(segs[i:])
                    break
        if rel and (cfg["_root"] / rel).exists():
            refs.add(rel)
    try:
        refs.discard(path.resolve().relative_to(cfg["_root"]).as_posix())
    except ValueError:
        pass
    return sorted(refs)[:MAX_REFS]

def split_sections(text: str) -> list[dict]:
    """Split a page into heading-level sections. Pre-heading text = intro."""
    sections: list[dict] = []
    current = {"heading": "(intro)", "line": 1, "lines": []}
    for i, line in enumerate(text.splitlines(), start=1):
        m = HEADING_RE.match(line)
        if m:
            if current["lines"] or current["heading"] != "(intro)":
                sections.append(current)
            current = {"heading": m.group(2), "line": i, "lines": []}
        else:
            current["lines"].append(line)
    sections.append(current)
    for s in sections:
        s["text"] = "\n".join(s.pop("lines")).strip()
    return [s for s in sections if s["text"] or s["heading"] != "(intro)"]


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity for compact, deterministic word-count profiles."""
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(term, 0) for term, v in a.items())
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (norm_a * norm_b or 1.0)


def compact_profile(terms: dict[str, float]) -> dict[str, float]:
    """Keep the strongest terms so similarity stays cheap and explainable."""
    return dict(sorted(terms.items(), key=lambda item: (-item[1], item[0]))
                [:MAX_SIMILARITY_TERMS])


def shared_terms(a: dict[str, float], b: dict[str, float]) -> list[str]:
    """Return a short human-readable explanation for an inferred edge."""
    return [term for term, _ in sorted(
        ((term, min(count, b[term])) for term, count in a.items() if term in b),
        key=lambda item: (-item[1], item[0]))[:MAX_SHARED_TERMS]]


def build_relationships(files: list[dict], profiles: dict[str, dict[str, float]],
                        instruction_registry: dict | None = None) -> list[dict]:
    """Build a queryable relationship ledger with provenance and confidence.

    ``references`` are direct evidence from the source. ``similar_content``
    edges are intentionally labeled inferred: shared vocabulary can indicate a
    useful neighbour, not a verified fact or dependency.
    """
    relationships: list[dict] = []
    indexed = sorted(f["path"] for f in files if f.get("indexed"))
    for f in sorted(files, key=lambda item: item["path"]):
        for target in f.get("links", []):
            relationships.append({
                "source": f["path"],
                "target": target,
                "relation": "references",
                "status": "extracted",
                "confidence": 1.0,
                "evidence": "markdown_link_or_workspace_path",
            })
    similar_seen: set[tuple[str, str]] = set()
    for source in indexed:
        candidates = []
        for target in indexed:
            if source == target:
                continue
            score = cosine_similarity(profiles.get(source, {}),
                                      profiles.get(target, {}))
            if score >= SIMILARITY_THRESHOLD:
                candidates.append((score, target))
        for score, target in sorted(candidates, key=lambda item: (-item[0], item[1]))[:MAX_SIMILAR_PER_FILE]:
            pair = tuple(sorted((source, target)))
            if pair in similar_seen:
                continue
            similar_seen.add(pair)
            relationships.append({
                "source": source,
                "target": target,
                "relation": "similar_content",
                "status": "inferred",
                "confidence": round(score, 3),
                "evidence": "shared_indexed_terms",
                "shared_terms": shared_terms(profiles.get(source, {}),
                                             profiles.get(target, {})),
            })
    for entry in (instruction_registry or {}).get("files", []):
        relationships.append({
            "source": entry["path"], "target": entry["scope"],
            "relation": "governs", "status": "extracted", "confidence": 1.0,
            "evidence": "instruction_filename_and_containing_folder",
        })
        if entry.get("parent"):
            relationships.append({
                "source": entry["path"], "target": entry["parent"],
                "relation": "inherits_from", "status": "extracted", "confidence": 1.0,
                "evidence": "nearest_ancestor_same_client_instruction",
            })
        # Keep the directed relationship client-specific: AGENTS.md identifies
        # its CLAUDE.md sibling; the registry itself records the sibling for both.
        if entry["client"] == "codex" and entry.get("counterpart"):
            relationships.append({
                "source": entry["path"], "target": entry["counterpart"],
                "relation": "counterpart_of", "status": "extracted", "confidence": 1.0,
                "evidence": "same_scope_instruction_filename",
            })
    return relationships


def first_sentence(text: str) -> str:
    for line in text.splitlines():
        line = line.strip().lstrip("-*# ").strip()
        if line and not line.startswith(("|", "<!--", "```", "---")):
            return line[:160]
    return ""


def discover_skills() -> list[dict]:
    skills = []
    base = ROOT / SKILLS_DIR
    if base.is_dir():
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            desc = ""
            skill_md = d / "SKILL.md"
            if skill_md.exists():
                desc = first_sentence(read_text(skill_md))
            skills.append({"name": d.name, "description": desc})
    return skills


def rel_to_root(path: Path, cfg: dict) -> str:
    return path.resolve().relative_to(cfg["_root"]).as_posix()


def instruction_client(path: str) -> str:
    return "codex" if Path(path).name.lower() == "agents.md" else "claude"


def scope_of_instruction(path: str) -> str:
    parent = Path(path).parent.as_posix()
    return "." if parent == "." else parent


def scope_ancestors(scope: str) -> list[str]:
    if scope in ("", "."):
        return ["."]
    parts = scope.split("/")
    return ["."] + ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]


def build_instruction_registry(paths: list[Path], summaries: dict[str, str],
                               cfg: dict) -> dict:
    """Create the provenance-only hierarchy for discovered instruction files."""
    names = cfg["instructions"]["_names"]
    records: list[dict] = []
    for path in paths:
        try:
            rel = rel_to_root(path, cfg)
        except ValueError:
            continue
        if path.name.lower() not in names:
            continue
        records.append({"path": rel, "client": instruction_client(rel),
                        "scope": scope_of_instruction(rel),
                        "summary": summaries.get(rel, ""),
                        "parent": None, "counterpart": None})
    records.sort(key=lambda item: item["path"])
    by_path = {item["path"]: item for item in records}
    by_scope: dict[str, dict[str, dict]] = {}
    for item in records:
        by_scope.setdefault(item["scope"], {})[item["client"]] = item
    for item in records:
        parent = None
        for ancestor in reversed(scope_ancestors(item["scope"])[:-1]):
            candidate = by_scope.get(ancestor, {}).get(item["client"])
            if candidate:
                parent = candidate["path"]
                break
        item["parent"] = parent
        twin = by_scope.get(item["scope"], {}).get(
            "claude" if item["client"] == "codex" else "codex")
        item["counterpart"] = twin["path"] if twin else None
    scopes: dict[str, dict[str, list[str]]] = {}
    for scope in sorted(by_scope):
        scopes[scope] = {}
        for client in ("codex", "claude"):
            chain = []
            for ancestor in scope_ancestors(scope):
                entry = by_scope.get(ancestor, {}).get(client)
                if entry:
                    chain.append(entry["path"])
            scopes[scope][client] = chain
    gaps: list[dict] = []
    for scope, clients in sorted(by_scope.items()):
        present = sorted(clients)
        missing = [client for client in ("codex", "claude") if client not in clients]
        if missing:
            gaps.append({"scope": scope, "kind": "missing_counterpart",
                         "present": present, "missing": missing})
        chains = scopes[scope]
        if bool(chains["codex"]) != bool(chains["claude"]):
            gaps.append({"scope": scope, "kind": "asymmetric_chain",
                         "codex": chains["codex"], "claude": chains["claude"]})
    return {"files": records, "scopes": scopes, "gaps": gaps}


AGENT_SKIP_STEMS = {"claude", "agents", "readme", "install", "license"}


def agent_desc(path: Path) -> str:
    text = read_text(path)
    if path.suffix.lower() == ".toml":
        m = re.search(r'description\s*=\s*"""\s*(.*?)"""', text, re.S)
        if m:
            for ln in m.group(1).splitlines():
                ln = ln.strip().lstrip("-• ").strip()
                if ln and not ln.lower().startswith("when to invoke"):
                    return ln[:160]
        m = re.search(r'description\s*=\s*"([^"]+)"', text)
        return m.group(1)[:160] if m else ""
    # markdown: first meaningful line that is not the title itself
    for line in text.splitlines():
        line = line.strip().lstrip("-*# ").strip()
        if not line or line.lower() == path.stem.lower():
            continue
        if line.startswith(("|", "<!--", "```", "---")):
            continue
        return line.replace("**", "")[:160]
    return ""


def discover_agents(cfg: dict) -> tuple[list[dict], list[dict]]:
    """Read subagent definitions per tool; report roles missing a twin.

    The same role is expected to exist in every configured tool (same
    capability, contextualized per tool). A role present in one tool but
    not another is a tracked gap, not a silent difference.
    """
    entries = list(cfg.get("agents") or [])
    if not entries:  # auto-discovery for unconfigured vaults
        for d, tool in ((".claude/agents", "claude"),
                        (".codex/agents", "codex")):
            if (cfg["_root"] / d).is_dir():
                entries.append({"dir": d, "tool": tool})
    agents: list[dict] = []
    for e in entries:
        base = (cfg["_root"] / e["dir"]).resolve()
        tool = e.get("tool", "agent")
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in (".md", ".toml"):
                continue
            if p.stem.lower() in AGENT_SKIP_STEMS:
                continue
            try:
                rel = rel_to_root(p, cfg)
            except ValueError:
                rel = p.name
            agents.append({"name": p.stem, "tool": tool,
                           "description": agent_desc(p), "path": rel})
    tools = sorted({a["tool"] for a in agents})
    gaps: list[dict] = []
    if len(tools) > 1:
        by_tool = {t: {a["name"] for a in agents if a["tool"] == t}
                   for t in tools}
        for role in sorted(set().union(*by_tool.values())):
            missing = [t for t in tools if role not in by_tool[t]]
            if missing:
                gaps.append({"role": role, "missing_in": missing})
    return agents, gaps


def junk_scan(delete: bool = False) -> int:
    """List (or delete) cache/swap/temp junk the index always ignores."""
    cfg = load_config()
    allow = [p for p in cfg["_excludes"] if p not in JUNK_PATTERNS]
    hits: list[Path] = []
    for path in walk(cfg["_root"], allow):
        if (any(fnmatch.fnmatch(path.name, jp) for jp in JUNK_PATTERNS)
                or "__pycache__" in path.parts):
            hits.append(path)
    if not hits:
        print("brain: no junk found — vault is clean.")
        return 0
    total = 0
    dirs: set[Path] = set()
    failed = 0
    for p in hits:
        size = p.stat().st_size
        total += size
        try:
            rel = rel_to_root(p, cfg)
        except ValueError:
            rel = str(p)
        print(f"  {rel}  ({size // 1024} KB)")
        if delete:
            try:
                p.unlink()
                if p.parent.name == "__pycache__":
                    dirs.add(p.parent)
            except OSError as exc:
                failed += 1
                print(f"    ! could not delete: {exc}")
    for d in dirs:
        try:
            d.rmdir()
        except OSError:
            pass
    if delete:
        verb = f"deleted ({failed} failed)" if failed else "deleted"
    else:
        verb = "found (rerun with --junk --delete)"
    print(f"brain: {len(hits)} junk file(s), {total // 1024} KB {verb}.")
    return 1 if (failed or not delete) else 0


def build_index(verbose: bool = True) -> dict:
    cfg = load_config()
    files, sections = [], []
    df: dict[str, int] = {}
    raw_file_terms: dict[str, dict[str, int]] = {}
    indexed_paths = set()
    discovered_instructions = instruction_files(cfg)
    paths = list(md_files(cfg))
    if cfg["instructions"].get("content"):
        paths.extend(discovered_instructions)
    unique_paths: dict[str, Path] = {}
    for path in paths:
        try:
            unique_paths[rel_to_root(path, cfg)] = path
        except ValueError:
            continue
    summaries: dict[str, str] = {}
    for path in (unique_paths[key] for key in sorted(unique_paths)):
        rel = rel_to_root(path, cfg)
        if rel in indexed_paths:
            continue
        indexed_paths.add(rel)
        text = read_text(path)
        page_secs = split_sections(text)
        files.append({
            "path": rel,
            "dir": rel.split("/", 1)[0] if "/" in rel else "(root)",
            "category": file_category(path, rel),
            "sections": len(page_secs),
            "summary": first_sentence(text),
            "bytes": path.stat().st_size,
            "indexed": True,
            "links": extract_refs(text, path, cfg),
        })
        summaries[rel] = first_sentence(text)
        fname_terms = tokenize(path.stem.replace("-", " ").replace("_", " "))
        page_terms: dict[str, int] = {}
        for sec in page_secs:
            terms: dict[str, int] = {}
            for w in tokenize(sec["text"]):
                terms[w] = terms.get(w, 0) + 1
                page_terms[w] = page_terms.get(w, 0) + 1
            h_terms = tokenize(sec["heading"])
            for w in set(terms) | set(h_terms):
                df[w] = df.get(w, 0) + 1
            sections.append({
                "file": rel,
                "heading": sec["heading"],
                "line": sec["line"],
                "summary": first_sentence(sec["text"]),
                "terms": terms,
                "hterms": h_terms,
                "fterms": fname_terms,
                "chars": len(sec["text"]),
            })
        raw_file_terms[rel] = page_terms
    census_n = 0
    if cfg.get("census"):
        for path in walk(cfg["_root"], cfg["_excludes"]):
            if census_n >= MAX_CENSUS:
                break
            try:
                rel = rel_to_root(path, cfg)
            except ValueError:
                continue
            if rel in indexed_paths:
                continue  # already indexed as markdown content
            files.append({
                "path": rel,
                "dir": rel.split("/", 1)[0] if "/" in rel else "(root)",
                "category": file_category(path, rel),
                "sections": 0,
                "summary": "",
                "bytes": path.stat().st_size,
                "indexed": False,
            })
            census_n += 1
    # Term-frequency alone over-emphasizes generic vault words such as "notes"
    # and "source". Weight each file profile by inverse section frequency so
    # inferred neighbours are anchored in the more distinctive vocabulary.
    n_sections = max(len(sections), 1)
    file_profiles = {
        rel: compact_profile({
            term: count * math.log(1 + n_sections / (df.get(term) or n_sections))
            for term, count in terms.items()
        })
        for rel, terms in raw_file_terms.items()
    }
    agents, agent_gaps = discover_agents(cfg)
    instruction_registry = build_instruction_registry(
        discovered_instructions, summaries, cfg)
    relationships = build_relationships(files, file_profiles, instruction_registry)
    import os
    prefix = "" if cfg["_root"] == ROOT else (
        os.path.relpath(cfg["_root"], ROOT).replace("\\", "/") + "/")
    index = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "root_name": cfg["_root"].name,
        "root_rel": prefix,
        "scan_dirs": cfg["scan_dirs"],
        "n_sections": len(sections),
        "files": files,
        "sections": sections,
        "relationships": relationships,
        "instruction_registry": instruction_registry,
        "df": df,
        "arms": {
            "applications": cfg.get("applications", []),
            "routines": cfg.get("routines", []),
            "skills": discover_skills(),
            "agents": agents,
            "agent_gaps": agent_gaps,
        },
    }
    INDEX_JSON.write_text(json.dumps(index, ensure_ascii=False),
                          encoding="utf-8")
    INDEX_JS.write_text("window.BRAIN_INDEX = "
                        + json.dumps(index, ensure_ascii=False) + ";\n",
                        encoding="utf-8")
    if verbose:
        msg = (f"brain: indexed {len(indexed_paths)} md files / "
               f"{len(sections)} sections from "
               f"{', '.join(cfg['scan_dirs']) or '(nothing found)'}")
        explicit = sum(1 for r in relationships if r["status"] == "extracted")
        inferred = len(relationships) - explicit
        msg += f" + {explicit} extracted / {inferred} inferred relationships"
        if cfg.get("census"):
            msg += f" + census of {census_n} workspace files"
        if agents:
            per_tool = {}
            for a in agents:
                per_tool[a["tool"]] = per_tool.get(a["tool"], 0) + 1
            msg += " + agents " + ", ".join(
                f"{t}:{c}" for t, c in sorted(per_tool.items()))
        if instruction_registry["files"]:
            msg += (f" + {len(instruction_registry['files'])} scoped instruction"
                    f" file(s), {len(instruction_registry['gaps'])} gap signal(s)")
        print(msg + f" -> {INDEX_JSON.name}, {INDEX_JS.name}")
        for g in agent_gaps:
            print(f"WARN  agent role '{g['role']}' has no counterpart in: "
                  f"{', '.join(g['missing_in'])}")
    return index


def load_index() -> dict:
    """Load the index, rebuilding automatically when it is missing/stale."""
    cfg = load_config()
    # Scope inventory is part of the generated index even in privacy mode, so
    # discovered instruction edits must always invalidate it.
    tracked = list(md_files(cfg)) + instruction_files(cfg)
    newest = max((p.stat().st_mtime for p in tracked), default=0.0)
    if not INDEX_JSON.exists() or INDEX_JSON.stat().st_mtime < newest:
        return build_index(verbose=False)
    return json.loads(read_text(INDEX_JSON))


def expand(term: str) -> tuple[str, ...]:
    """Cheap plural/singular tolerance without a stemmer."""
    if term.endswith("s") and len(term) > 3:
        return (term, term[:-1])
    return (term, term + "s")


def score_sections(query: str, index: dict) -> list[tuple[float, dict]]:
    q_terms = tokenize(query)
    if not q_terms:
        return []
    n = max(index["n_sections"], 1)
    df = index["df"]
    scored = []
    for sec in index["sections"]:
        s = 0.0
        for q in q_terms:
            variants = expand(q)
            tf = max(sec["terms"].get(v, 0) for v in variants)
            hit_df = max((df.get(v, 0) for v in variants), default=0)
            idf = math.log(1 + n / (hit_df or n))
            if tf:
                s += (1 + math.log(tf)) * idf
            if any(v in sec["hterms"] for v in variants):
                s += 2.0 * idf
            if any(v in sec["fterms"] for v in variants):
                s += 1.5 * idf
        if s > 0:
            scored.append((s, sec))
    scored.sort(key=lambda t: (-t[0], t[1]["file"], t[1]["line"]))
    return scored


def resolve_path(rel: str, index: dict) -> Path:
    return (ROOT / index.get("root_rel", "") / rel).resolve()


def section_text(sec: dict, index: dict) -> str:
    path = resolve_path(sec["file"], index)
    if not path.exists():
        return ""
    lines = read_text(path).splitlines()
    start = sec["line"] - 1
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if HEADING_RE.match(lines[i]):
            end = i
            break
    body = lines[start:end]
    if len(body) > MAX_SHOW_LINES:
        body = body[:MAX_SHOW_LINES] + [f"... [truncated; open {sec['file']}]"]
    return "\n".join(body).strip()


def follow_pointer(text: str, from_file: str, index: dict) -> str | None:
    """If a short section just links elsewhere, return the target's path."""
    if len(text) > POINTER_MAX_CHARS:
        return None
    m = MD_LINK_RE.search(text)
    if not m:
        return None
    base = resolve_path(from_file, index).parent
    target = (base / m.group(1)).resolve()
    root = (ROOT / index.get("root_rel", "")).resolve()
    try:
        rel = target.relative_to(root).as_posix()
    except ValueError:
        return None
    return rel if target.exists() else None


def print_relationships(path: str, index: dict) -> None:
    """Print relationships touching a file, keeping evidence classes visible."""
    edges = [r for r in index.get("relationships", [])
             if r["source"] == path or r["target"] == path]
    if not edges:
        print(f"\nNo recorded relationships for {path}.")
        return
    print(f"\n--- relationships: {path} ---")
    for edge in sorted(edges, key=lambda r: (
            r["status"] != "extracted", r["relation"],
            r["target"] if r["source"] == path else r["source"])):
        direction = "->" if edge["source"] == path else "<-"
        other = edge["target"] if direction == "->" else edge["source"]
        label = edge["status"].upper()
        print(f"  {label:<9} {direction} {edge['relation']}: {other} "
              f"(confidence {edge['confidence']:.3f})")
        if edge.get("shared_terms"):
            print(f"            shared terms: {', '.join(edge['shared_terms'])}")


def instruction_records(index: dict) -> dict[str, dict]:
    return {item["path"]: item
            for item in index.get("instruction_registry", {}).get("files", [])}


def resolve_instruction_scope(target: str, index: dict) -> str | None:
    """Resolve a workspace-relative file/folder to its containing scope."""
    root = (ROOT / index.get("root_rel", "")).resolve()
    candidate = Path(target)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve()
        rel = resolved.relative_to(root).as_posix()
    except (ValueError, OSError):
        return None
    if resolved.exists() and resolved.is_file():
        return scope_of_instruction(rel) if resolved.name.lower() in {
            "agents.md", "claude.md"} else (Path(rel).parent.as_posix() or ".")
    return rel if rel else "."


def chain_for_scope(scope: str, registry: dict, client: str) -> list[str]:
    """Return root-to-nearest instruction sources for any existing folder."""
    exact = registry.get("scopes", {}).get(scope, {}).get(client)
    if exact is not None:
        return exact
    records = {(item["scope"], item["client"]): item["path"]
               for item in registry.get("files", [])}
    return [records[(ancestor, client)] for ancestor in scope_ancestors(scope)
            if (ancestor, client) in records]


def print_instructions(target: str) -> int:
    index = load_index()
    scope = resolve_instruction_scope(target, index)
    if scope is None:
        print(f"brain: instruction path must stay inside the workspace: {target}")
        return 2
    registry = index.get("instruction_registry")
    if not registry:
        print("brain: this index predates scoped instruction registry support; rebuilding.")
        index = build_index(verbose=False)
        registry = index.get("instruction_registry", {})
    records = instruction_records(index)
    shown = scope or "."
    print(f"brain: effective instructions for {shown}")
    for client in ("codex", "claude"):
        chain = chain_for_scope(scope, registry, client)
        print(f"  {client} (root -> nearest):")
        if not chain:
            print("    (no discovered instruction files)")
            continue
        for path in chain:
            entry = records.get(path, {})
            summary = entry.get("summary") or "(summary unavailable; content indexing is disabled)"
            print(f"    {path}  governs {entry.get('scope', scope)}")
            print(f"      {summary}")
    return 0


def print_instruction_gaps() -> int:
    index = load_index()
    registry = index.get("instruction_registry")
    if registry is None:
        index = build_index(verbose=False)
        registry = index.get("instruction_registry", {})
    gaps = registry.get("gaps", [])
    if not gaps:
        print("brain: no scoped-instruction gap signals.")
        return 0
    print("brain: scoped-instruction gap signals (review cues, not defects)")
    for gap in gaps:
        if gap["kind"] == "missing_counterpart":
            print(f"  {gap['scope']}: missing same-scope {' / '.join(gap['missing'])} "
                  f"counterpart (present: {' / '.join(gap['present'])})")
        else:
            print(f"  {gap['scope']}: asymmetric effective chain "
                  f"(codex {len(gap['codex'])}, claude {len(gap['claude'])})")
    return 0


def run_query(query: str, show: bool, top: int, related: bool = False) -> int:
    index = load_index()
    hits = score_sections(query, index)
    if not hits:
        print(f'brain: no indexed section matches "{query}". '
              "Fall back to Grep/Glob.")
        return 1
    print(f'brain: top matches for "{query}"')
    instructions = instruction_records(index)
    for s, sec in hits[:top]:
        source = instructions.get(sec["file"])
        provenance = (f" [{source['client']} instructions · scope {source['scope']}]"
                      if source else "")
        print(f"  {sec['file']}:{sec['line']}  #{sec['heading']}  "
              f"(score {s:.1f}){provenance}")
        if sec["summary"]:
            print(f"      {sec['summary']}")
    if show:
        best = hits[0][1]
        text = section_text(best, index)
        print(f"\n--- {best['file']}:{best['line']} ---")
        print(text)
        target = follow_pointer(text, best["file"], index)
        if target:
            t_index = {s["file"]: s for s in index["sections"]}
            print(f"\n--- pointer -> {target} ---")
            t_sec = t_index.get(target)
            if t_sec:
                print(section_text(t_sec, index))
            else:
                print(f"(open {target} directly; it is outside the index)")
    if related:
        print_relationships(hits[0][1]["file"], index)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic keyword retrieval over a markdown vault.")
    ap.add_argument("query", nargs="*", help="question or keywords")
    ap.add_argument("--index", action="store_true",
                    help="rebuild brain-index.json / brain-index.js")
    ap.add_argument("--show", action="store_true",
                    help="print the best-matching section body")
    ap.add_argument("--related", action="store_true",
                    help="print extracted and inferred relationships for the best match")
    ap.add_argument("--instructions", metavar="PATH",
                    help="show effective AGENTS.md / CLAUDE.md chains for a file or folder")
    ap.add_argument("--instruction-gaps", action="store_true",
                    help="list missing counterparts and asymmetric instruction chains")
    ap.add_argument("--junk", action="store_true",
                    help="list cache/swap/temp junk files in the vault")
    ap.add_argument("--delete", action="store_true",
                    help="with --junk: delete the junk files")
    ap.add_argument("--top", type=int, default=TOP_N,
                    help=f"number of matches to list (default {TOP_N})")
    args = ap.parse_args()
    if args.junk:
        return junk_scan(delete=args.delete)
    if args.index:
        build_index()
        return 0
    if args.instructions:
        return print_instructions(args.instructions)
    if args.instruction_gaps:
        return print_instruction_gaps()
    if not args.query:
        ap.print_help()
        return 2
    return run_query(" ".join(args.query), args.show, args.top, args.related)


if __name__ == "__main__":
    sys.exit(main())
