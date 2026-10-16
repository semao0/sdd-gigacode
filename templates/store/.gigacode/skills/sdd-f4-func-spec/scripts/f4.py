#!/usr/bin/env python3
"""Детерминированные шаги skill sdd-f4-func-spec.

Jira и Bitbucket вызывает агент через MCP. Скрипт только считает то, что
должно получаться одинаково при каждом запуске: JQL, имена веток, папку
change, проверку готовой функциональной спецификации.

Команды:
  jql                                   JQL поиска задач
  space --project KEY                   настройки пространства (JSON)
  names --improvement KEY --story KEY   ветка, коммит, заголовок PR (JSON)
  story-branch --story KEY              выбрать ветку Story из списка на stdin
  find-change REPO --improvement KEY --story KEY [--changed FILE]
  template REPO                         путь к шаблону func_spec
  validate FUNC_SPEC --improvement KEY [--business-spec F] [--template F]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SKILL_DIR / "spaces.yml"
FALLBACK_TEMPLATE = SKILL_DIR / "assets" / "func_spec.template.md"

SPEC_FILE = "func_spec.md"
BUSINESS_FILE = "business_spec.md"
REPO_TEMPLATE = Path("schemas") / "sdd" / "templates" / "func_spec.md"


# --- конфиг ---------------------------------------------------------------

def _scalar(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [_scalar(x) for x in _split_flow(inner)] if inner else []
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def _split_flow(text: str) -> list[str]:
    items, buf, quote = [], "", ""
    for ch in text:
        if quote:
            buf += ch
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ",":
            items.append(buf)
            buf = ""
        else:
            buf += ch
    items.append(buf)
    return [x.strip() for x in items]


def _strip_comment(line: str) -> str:
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def parse_config(text: str) -> dict:
    """Подмножество YAML, которого хватает spaces.yml: скаляры, списки
    в квадратных скобках и один список словарей. PyYAML не нужен."""
    data: dict = {}
    current_list: list | None = None
    item: dict | None = None
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        if indent == 0:
            key, _, value = body.partition(":")
            if value.strip():
                data[key.strip()] = _scalar(value)
                current_list = None
            else:
                current_list = data[key.strip()] = []
            item = None
            continue
        if current_list is None:
            raise ValueError(f"не разобрать строку конфига: {raw!r}")
        if body.startswith("- "):
            item = {}
            current_list.append(item)
            body = body[2:]
        if item is None:
            raise ValueError(f"не разобрать строку конфига: {raw!r}")
        key, _, value = body.partition(":")
        item[key.strip()] = _scalar(value)
    return data


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    return parse_config(path.read_text(encoding="utf-8"))


# --- JQL и имена ------------------------------------------------------------

def _q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_jql(cfg: dict) -> str:
    projects = [s["jira_project"] for s in cfg["spaces"] if s.get("jira_project") not in (None, "", "TODO")]
    if not projects:
        raise ValueError("в spaces.yml нет ни одного jira_project")
    field = _q(cfg["status_field"])
    if cfg.get("status_field_kind", "text") == "select":
        status_cond = f"{field} = {_q(cfg['status_from'])}"
    else:
        # Текстовое поле ищется только через ~; точное совпадение агент проверяет сам.
        status_cond = f"{field} ~ {_q(_q(cfg['status_from']))}"
    return " AND ".join([
        f"project in ({', '.join(_q(p) for p in projects)})",
        f"issuetype in ({', '.join(_q(t) for t in cfg['issue_types'])})",
        f"labels = {_q(cfg['label'])}",
        f"status = {_q(cfg['status'])}",
        status_cond,
    ]) + " ORDER BY key ASC"


def find_space(cfg: dict, project: str) -> dict:
    for space in cfg["spaces"]:
        if space.get("jira_project", "").upper() == project.upper():
            return space
    raise KeyError(f"пространство с проектом {project} не описано в spaces.yml")


def make_names(cfg: dict, improvement: str, story: str, summary: str = "") -> dict:
    improvement, story = improvement.upper(), story.upper()
    title = f"{improvement}: функциональная спецификация"
    if summary:
        title += f" — {summary.strip()}"
    return {
        "feature_branch": cfg["branch_template"].format(improvement=improvement, story=story),
        "commit_message": f"{improvement}: функциональная спецификация",
        "pr_title": title,
    }


def pick_story_branch(cfg: dict, story: str, branches: list[str]) -> str:
    story = story.upper()
    names = []
    for b in branches:
        b = b.strip()
        if not b:
            continue
        b = b.split("\t")[-1].removeprefix("refs/heads/").removeprefix("origin/")
        names.append(b)
    by_upper = {n.upper(): n for n in names}
    for tpl in cfg["story_branch_templates"]:
        hit = by_upper.get(tpl.format(story=story).upper())
        if hit:
            return hit
    key_re = re.compile(rf"(?<![A-Z0-9]){re.escape(story)}(?![0-9])", re.I)
    hits = sorted({n for n in names if key_re.search(n)})
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise LookupError(f"нет ветки Story {story}")
    raise LookupError(f"несколько веток Story {story}: {', '.join(hits)}")


# --- папка change -----------------------------------------------------------

def _key_in(text: str, key: str) -> bool:
    return re.search(rf"(?<![A-Z0-9]){re.escape(key)}(?![0-9])", text, re.I) is not None


def find_change_dir(repo: Path, spec_root: str, improvement: str, story: str,
                    changed: list[str] | None = None) -> Path:
    changes = repo / spec_root / "changes"
    if not changes.is_dir():
        raise LookupError(f"нет папки {changes}")
    dirs = sorted(d for d in changes.iterdir()
                  if d.is_dir() and d.name != "archive" and (d / BUSINESS_FILE).is_file())
    if not dirs:
        raise LookupError(f"в {changes} нет ни одной папки с {BUSINESS_FILE}")

    if changed:
        prefix = f"{spec_root}/changes/"
        touched = {p.strip()[len(prefix):].split("/")[0] for p in changed if p.strip().startswith(prefix)}
        dirs = [d for d in dirs if d.name in touched]
        if not dirs:
            raise LookupError("ветка Story не меняет ни одной папки change с business_spec.md — PR F3 смержен?")

    keys = [improvement, story]
    steps = [
        lambda d: any(_key_in(d.name, k) for k in keys),
        lambda d: any(_key_in((d / BUSINESS_FILE).read_text(encoding="utf-8"), k) for k in keys),
        lambda d: changed is not None and not (d / SPEC_FILE).exists(),
    ]
    for step in steps:
        hits = [d for d in dirs if step(d)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise LookupError("несколько подходящих папок: " + ", ".join(h.name for h in hits))
    if len(dirs) == 1 and changed:
        return dirs[0]
    raise LookupError("не удалось однозначно найти папку change: " + ", ".join(d.name for d in dirs))


def template_path(repo: Path, spec_root: str) -> Path:
    candidate = repo / spec_root / REPO_TEMPLATE
    return candidate if candidate.is_file() else FALLBACK_TEMPLATE


# --- валидатор --------------------------------------------------------------

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}|\bTODO\b|\bTBD\b")
BR_RE = re.compile(r"\bBR-\d+\b")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _headings(text: str, max_level: int = 2) -> list[str]:
    out, fenced = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        m = HEADING_RE.match(line)
        if m and not fenced and len(m.group(1)) <= max_level:
            out.append(m.group(2).strip())
    return out


def _heading_prefix(heading: str) -> str:
    """Неизменяемая часть заголовка шаблона: до первого плейсхолдера."""
    cut = re.split(r"\{|<[^>]*>|\[[^\]]*\]", heading, maxsplit=1)[0]
    return re.sub(r"\s+", " ", cut).strip(" :—-").casefold()


def validate(spec_text: str, improvement: str, template_text: str | None = None,
             business_text: str | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not spec_text.strip():
        return ["файл пустой"], warnings

    if template_text:
        spec_heads = [re.sub(r"\s+", " ", h).casefold() for h in _headings(spec_text)]
        pos = 0
        for head in _headings(template_text):
            prefix = _heading_prefix(head)
            if not prefix:
                continue
            for i in range(pos, len(spec_heads)):
                if spec_heads[i].startswith(prefix):
                    pos = i + 1
                    break
            else:
                errors.append(f"нет раздела шаблона или нарушен порядок: «{head}»")

    for n, line in enumerate(spec_text.splitlines(), 1):
        m = PLACEHOLDER_RE.search(line)
        if m:
            errors.append(f"строка {n}: незаполненный плейсхолдер {m.group(0)!r}")

    if not _key_in(spec_text, improvement):
        errors.append(f"нет ссылки на задачу {improvement.upper()}")

    if business_text is not None:
        known = set(BR_RE.findall(business_text))
        used = set(BR_RE.findall(spec_text))
        if known:
            for br in sorted(used - known):
                errors.append(f"{br} нет в бизнес-спецификации")
            for br in sorted(known - used):
                warnings.append(f"{br} из бизнес-спецификации не покрыт")
    return errors, warnings


# --- CLI --------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("jql")
    p = sub.add_parser("space")
    p.add_argument("--project", required=True)
    p = sub.add_parser("names")
    p.add_argument("--improvement", required=True)
    p.add_argument("--story", required=True)
    p.add_argument("--summary", default="")
    p = sub.add_parser("story-branch")
    p.add_argument("--story", required=True)
    p = sub.add_parser("find-change")
    p.add_argument("repo", type=Path)
    p.add_argument("--improvement", required=True)
    p.add_argument("--story", required=True)
    p.add_argument("--spec-root", default="openspec")
    p.add_argument("--changed", type=Path, help="файл со списком путей, изменённых в ветке Story")
    p = sub.add_parser("template")
    p.add_argument("repo", type=Path)
    p.add_argument("--spec-root", default="openspec")
    p = sub.add_parser("validate")
    p.add_argument("spec", type=Path)
    p.add_argument("--improvement", required=True)
    p.add_argument("--business-spec", type=Path)
    p.add_argument("--template", type=Path)

    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.cmd == "jql":
            print(build_jql(cfg))
        elif args.cmd == "space":
            print(json.dumps(find_space(cfg, args.project), ensure_ascii=False, indent=2))
        elif args.cmd == "names":
            print(json.dumps(make_names(cfg, args.improvement, args.story, args.summary),
                             ensure_ascii=False, indent=2))
        elif args.cmd == "story-branch":
            print(pick_story_branch(cfg, args.story, sys.stdin.read().splitlines()))
        elif args.cmd == "find-change":
            changed = args.changed.read_text(encoding="utf-8").splitlines() if args.changed else None
            print(find_change_dir(args.repo, args.spec_root, args.improvement, args.story, changed))
        elif args.cmd == "template":
            print(template_path(args.repo, args.spec_root))
        elif args.cmd == "validate":
            tpl = args.template or FALLBACK_TEMPLATE
            errors, warnings = validate(
                args.spec.read_text(encoding="utf-8"),
                args.improvement,
                tpl.read_text(encoding="utf-8"),
                args.business_spec.read_text(encoding="utf-8") if args.business_spec else None,
            )
            for w in warnings:
                print(f"WARN: {w}")
            for e in errors:
                print(f"ERROR: {e}")
            if errors:
                return 1
            print("OK")
    except (LookupError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
