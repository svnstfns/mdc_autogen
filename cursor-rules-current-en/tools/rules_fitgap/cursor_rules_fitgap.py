#!/usr/bin/env python3
"""
cursor_rules_fitgap.py
Scan repository stack -> map to required Cursor .mdc rules -> compare with existing -> generate missing rule files.

Usage:
  python tools/rules_fitgap/cursor_rules_fitgap.py --repo . --plan out/fitgap-plan.json --generate

Outputs:
  - Plan JSON (detections, required rules, existing rules, fit-gap status)
  - Generates missing .mdc files with correct category and rule_id (if --generate)
  - Updates/creates .cursor/rules/INDEX.md
"""
import os, sys, re, json, argparse, glob, pathlib, textwrap
from typing import Dict, List, Tuple, Optional

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

try:
    import tomllib  # Python 3.11+
except Exception:
    tomllib = None

RANGES = {
    "00-foundation": (100, 199),
    "01-frontend": (200, 299),
    "02-backend": (300, 399),
    "03-mobile": (400, 499),
    "04-css": (500, 599),
    "05-state": (600, 699),
    "06-db-api": (700, 799),
    "07-testing": (800, 899),
    "08-build-dev": (900, 999),
    "09-language": (1000, 1999),
    "99-other": (9000, 9999),
}

DEFAULT_DETECTIONS = {
    "vue": [r"\bvue\b", r"@vue/"],
    "vite": [r"\bvite\b"],
    "pinia": [r"\bpinia\b"],
    "typescript": [r"\btypescript\b"],
    "tailwind": [r"\btailwindcss\b"],
    "fastapi": [r"\bfastapi\b"],
    "pydantic": [r"\bpydantic\b"],
    "sqlalchemy": [r"\bsqlalchemy\b"],
    "alembic": [r"\balembic\b"],
    "sqlite": [r"sqlite://", r"\.db\b"],
    "pytest": [r"\bpytest\b"],
    "pre-commit": [r"\bpre-commit\b"],
    "ruff": [r"\bruff\b"],
    "black": [r"\bblack\b"],
    "mypy": [r"\bmypy\b"],
    "openapi": [r"\bopenapi\b", r"\bswagger\b"],
    "json": [r"\.json\b"],
    "jest": [r"\bjest\b"],
    "vitest": [r"\bvitest\b"],
    "python": [r"\.py\b"],
}

def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def load_mapping(repo_root: str) -> Dict:
    mapping_path = os.path.join(repo_root, "tools", "rules_fitgap", "mapping.yaml")
    if os.path.exists(mapping_path) and yaml:
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data
        except Exception:
            pass
    # Fallback: embed a minimal default mapping compatible with the doc
    return {
        "detections": {
            "vue": [
                {"category":"01-frontend","slug":"vue-component-architecture","description":"Standards für Vue-Komponentenarchitektur","tags":["vue","components"],"globs":["**/*.vue"]},
                {"category":"05-state","slug":"pinia-state-management","description":"Pinia-State-Management","tags":["vue","pinia"],"globs":["**/*.{ts,js}"]},
            ],
            "fastapi": [
                {"category":"02-backend","slug":"fastapi-routing-structure","description":"Router-Aufteilung & Lifespan","tags":["fastapi","backend"],"globs":["**/*.py"]},
                {"category":"06-db-api","slug":"fastapi-pydantic-validation","description":"Pydantic v2 Request/Response-Validierung","tags":["fastapi","pydantic"],"globs":["**/*.py"]},
            ],
            "sqlite": [
                {"category":"06-db-api","slug":"sqlalchemy-sqlite-config","description":"SQLAlchemy für SQLite & Alembic","tags":["sqlalchemy","sqlite"],"globs":["**/*.py"]}
            ],
            "python": [
                {"category":"09-language","slug":"python-typing-standards","description":"Typisierung PEP484/561","tags":["python","typing"],"globs":["**/*.py"]},
                {"category":"08-build-dev","slug":"precommit-ruff-black","description":"Lint/Format Pipeline","tags":["pre-commit","ruff","black"],"globs":[".pre-commit-config.yaml","**/*.py"]},
                {"category":"07-testing","slug":"pytest-structure-coverage","description":"pytest-Layout & Coverage","tags":["pytest","testing"],"globs":["tests/**/*.py"]},
            ],
            "openapi": [
                {"category":"06-db-api","slug":"openapi-docs-quality","description":"OpenAPI-Dokumentationsqualität","tags":["openapi","swagger"],"globs":["openapi.*"]}
            ],
        }
    }

def detect_stack(repo_root: str) -> Dict[str, bool]:
    """Heuristic scan of common files to detect technologies."""
    detections: Dict[str, bool] = {k: False for k in DEFAULT_DETECTIONS.keys()}
    interesting_files = [
        "package.json", "pnpm-lock.yaml", "yarn.lock",
        "pyproject.toml", "poetry.lock", "requirements.txt", "requirements-dev.txt",
        ".pre-commit-config.yaml", ".ruff.toml", "mypy.ini", "setup.cfg",
        "openapi.yaml", "openapi.yml", "openapi.json",
        "swagger.yaml", "swagger.yml", "swagger.json",
    ]

    # Gather contents
    corpus = ""
    for f in interesting_files:
        p = os.path.join(repo_root, f)
        if os.path.exists(p):
            corpus += "\n" + read_text(p)

    # Also scan top-level Dockerfiles and compose
    for pat in ["Dockerfile", "Dockerfile.*", "docker-compose*.yml", "docker-compose*.yaml"]:
        for p in glob.glob(os.path.join(repo_root, pat)):
            corpus += "\n" + read_text(p)

    # Keyword scan
    for key, patterns in DEFAULT_DETECTIONS.items():
        for pat in patterns:
            if re.search(pat, corpus, re.IGNORECASE|re.MULTILINE):
                detections[key] = True
                break

    # Quick filesystem hints
    # Vue components
    if not detections["vue"]:
        vue_files = glob.glob(os.path.join(repo_root, "**", "*.vue"), recursive=True)
        if vue_files:
            detections["vue"] = True
    # Python presence
    if not detections["python"]:
        py_files = glob.glob(os.path.join(repo_root, "**", "*.py"), recursive=True)
        if py_files:
            detections["python"] = True
    # SQLite hint by files
    for db_file in glob.glob(os.path.join(repo_root, "**", "*.db"), recursive=True):
        detections["sqlite"] = True
        break

    # JS testing
    if not detections["vitest"]:
        if glob.glob(os.path.join(repo_root, "**", "*.spec.*"), recursive=True) or glob.glob(os.path.join(repo_root, "**", "*.test.*"), recursive=True):
            detections["vitest"] = True

    # Collapse related keys to simpler booleans
    summary = {
        "vue": detections["vue"],
        "pinia": detections["pinia"],
        "vite": detections["vite"],
        "typescript": detections["typescript"],
        "tailwind": detections["tailwind"],
        "fastapi": detections["fastapi"],
        "pydantic": detections["pydantic"],
        "sqlalchemy": detections["sqlalchemy"],
        "alembic": detections["alembic"],
        "sqlite": detections["sqlite"],
        "python": detections["python"],
        "openapi": detections["openapi"],
        "pytest": detections["pytest"],
        "vitest_or_jest": detections["vitest"] or detections["jest"],
        "precommit": detections["pre-commit"],
        "ruff": detections["ruff"],
        "black": detections["black"],
        "mypy": detections["mypy"],
    }
    return summary

def read_existing_rules(repo_root: str) -> Dict[str, Dict]:
    rules_root = os.path.join(repo_root, ".cursor", "rules")
    results = {}
    if not os.path.isdir(rules_root):
        return results
    for path in glob.glob(os.path.join(rules_root, "**", "*.mdc"), recursive=True):
        fn = os.path.basename(path)
        m = re.match(r"^(\d+)-([a-z0-9\-]+)\.mdc$", fn)
        rule_id = None
        slug = None
        if m:
            rule_id = int(m.group(1))
            slug = m.group(2)
        # Try parse frontmatter for category/description
        text = read_text(path)
        category = None
        description = ""
        fm = re.search(r"^---\s*(.*?)\s*---", text, re.DOTALL|re.MULTILINE)
        if fm:
            block = fm.group(1)
            cm = re.search(r'\bcategory:\s*"(.*?)"', block)
            if cm:
                category = cm.group(1).strip()
            dm = re.search(r'\bdescription:\s*"(.*?)"', block)
            if dm:
                description = dm.group(1).strip()
        key = path.replace(repo_root+os.sep, "")
        results[key] = {
            "path": key,
            "filename": fn,
            "rule_id": rule_id,
            "slug": slug,
            "category": category,
            "description": description,
        }
    return results

def next_free_id(existing_ids: List[int], cat_slug: str) -> int:
    r = RANGES.get(cat_slug, (9000, 9999))
    used = set([i for i in existing_ids if r[0] <= i <= r[1]])
    for i in range(r[0], r[1]+1):
        if i not in used:
            return i
    raise RuntimeError(f"No free rule_id left in range {r} for category {cat_slug}")

def ensure_category_folder(repo_root: str, cat_slug: str) -> str:
    path = os.path.join(repo_root, ".cursor", "rules", cat_slug)
    os.makedirs(path, exist_ok=True)
    return path

def make_rule_content(rule_id: int, cat_slug: str, slug: str, description: str, tags: List[str], globs: List[str], always=False) -> str:
    front = {
        "description": description,
        "globs": globs if globs else None,
        "alwaysApply": always,
        "category": cat_slug,
        "rule_id": rule_id,
        "tags": tags,
    }
    # Build YAML frontmatter
    lines = ["---"]
    for k in ["description","globs","alwaysApply","category","rule_id","tags"]:
        v = front[k]
        if v is None:
            continue
        if isinstance(v, list):
            lines.append(f"{k}: {json.dumps(v)}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f'{k}: "{v}"')
    lines.append("---")
    body = textwrap.dedent(f"""
    # {slug.replace('-', ' ').title()}

    ## Ziel
    {description}

    ## Anforderungen
    - Klare, umsetzbare Punkte formulieren (keine Vagheiten)
    - Relevante Beispiele hinzufügen (Good/Bad)
    - Trigger über `globs` verifizieren

    ## Good
    ```txt
    # Beispiel für gutes Muster
    ```

    ## Bad
    ```txt
    # Beispiel für antipattern
    ```
    """).strip()
    return "\n".join(lines) + "\n" + body + "\n"

def plan_required_rules(detections: Dict[str, bool], mapping: Dict) -> List[Dict]:
    required = []
    det_map = mapping.get("detections", {})
    for key, active in detections.items():
        if not active:
            continue
        if key in det_map:
            for spec in det_map[key]:
                required.append(spec.copy())
    # Foundation base rules are always desirable
    required.append({
        "category":"00-foundation",
        "slug":"base-standards",
        "description":"Projektweite Basisstandards (Ordner, Benennung, Security-Basics)",
        "tags":["foundation","standards"],
        "globs":[]
    })
    required.append({
        "category":"00-foundation",
        "slug":"fit-gap-rules",
        "description":"Fit–Gap Governance und Automatisierung",
        "tags":["governance","coverage"],
        "globs":[]
    })
    return required

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repository root")
    ap.add_argument("--plan", default="fitgap-plan.json", help="Output plan json path")
    ap.add_argument("--generate", action="store_true", help="Generate missing rules")
    args = ap.parse_args()

    repo_root = os.path.abspath(args.repo)
    mapping = load_mapping(repo_root)
    detections = detect_stack(repo_root)
    existing = read_existing_rules(repo_root)

    required = plan_required_rules(detections, mapping)

    # Build index for existing ids
    existing_ids = []
    existing_by_slug_cat = {}
    for info in existing.values():
        if info["rule_id"] is not None:
            existing_ids.append(info["rule_id"])
        key = f'{info.get("category")}/{info.get("slug")}' if info.get("category") and info.get("slug") else info["filename"]
        existing_by_slug_cat[key] = info

    plan = {"detections": detections, "required_rules": [], "existing": existing, "actions": []}

    for spec in required:
        cat = spec["category"]
        slug = spec["slug"]
        key = f"{cat}/{slug}"
        # Check if any existing file in this category matches slug by filename pattern
        found = None
        for info in existing.values():
            if info.get("category") == cat and info.get("slug") == slug:
                found = info
                break
            # fallback: filename contains slug
            if slug in info["filename"] and (cat in info.get("path","")):
                found = info
                break

        status = "present" if found else "missing"
        plan["required_rules"].append({"category":cat,"slug":slug,"description":spec["description"],"status":status})

        if status == "missing" and args.generate:
            rid = next_free_id(existing_ids, cat)
            existing_ids.append(rid)
            folder = ensure_category_folder(repo_root, cat)
            filename = f"{rid}-{slug}.mdc"
            path = os.path.join(folder, filename)
            content = make_rule_content(rid, cat, slug, spec["description"], spec.get("tags",[]), spec.get("globs",[]), always=False)
            os.makedirs(folder, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            plan["actions"].append({"action":"create","path":path.replace(repo_root+os.sep,""),"rule_id":rid})

    # Write plan
    with open(os.path.join(repo_root, args.plan), "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    # Update INDEX.md
    index_path = os.path.join(repo_root, ".cursor", "rules", "INDEX.md")
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    rows = []
    # refresh existing after generation
    existing = read_existing_rules(repo_root)
    for info in sorted(existing.values(), key=lambda x: (x["category"] or "", x["rule_id"] or 0, x["filename"])):
        rows.append(f'| {info.get("rule_id","")} | {info.get("category","")} | {info.get("slug","")} | `{info.get("path","")}` | {info.get("description","")} |')
    index_md = "# Cursor Rules Index\n\n| ID | Category | Slug | Path | Description |\n|---:|---|---|---|---|\n" + "\n".join(rows) + "\n"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_md)

    print(f"Detections: {json.dumps(detections, indent=2)}")
    print(f"Wrote plan to: {os.path.join(repo_root, args.plan)}")
    print(f"Updated index: {index_path}")

if __name__ == "__main__":
    main()
