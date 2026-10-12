#!/usr/bin/env python3
"""Отчёт по метрикам SDD-процесса (docs/03-metrics.md) в Markdown.

Запуск из корня store: python3 <sdd>/scripts/metrics.py [--since 3.months] [--ref main]
Репозитории компонентов ищутся в рабочей папке (по умолчанию - родитель store) по полю
dir из components.yaml, как у скила sdd-initiative-status. Нужны только git и Python 3.
Перед запуском сделайте git pull в store и компонентах: считается по их локальной ветке --ref.
"""
import argparse
import datetime as dt
import os
import pathlib
import re
import subprocess
import sys

CHANGES = "openspec/changes"


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} в {repo}: {r.stderr.strip()}")
    return r.stdout


def lines(out):
    return [l for l in out.splitlines() if l]


def first_add(repo, ref, path, fmt="%H %as"):
    """Первый коммит first-parent истории ref, в котором появился path."""
    out = lines(git(repo, "log", "--first-parent", ref, "--diff-filter=A", f"--format={fmt}", "--", path))
    return out[-1].split() if out else None


def days(a, b):
    if not a or not b:
        return None
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def meta_fields(text):
    """created / initiative из .openspec.yaml без зависимости от PyYAML."""
    created = re.search(r"^created:\s*['\"]?(\d{4}-\d{2}-\d{2})", text, re.M)
    init = (re.search(r"^initiative:\s*\n((?:[ \t]+.*\n?)+)", text, re.M)
            or re.search(r"^initiative:\s*\{(.*)\}", text, re.M))  # inline-форма: {store: x, id: y}
    store = iid = None
    if init:
        s = re.search(r"store:\s*['\"]?([\w-]+)", init.group(1))
        i = re.search(r"\bid:\s*['\"]?([\w-]+)", init.group(1))
        store, iid = s and s.group(1), i and i.group(1)
    return (created.group(1) if created else None), store, iid


def components(store_root, workspace):
    text = (store_root / "components.yaml").read_text()
    res = []
    for block in re.split(r"^\s*-\s+(?=id:)", text, flags=re.M)[1:]:
        cid = re.search(r"^id:\s*([\w-]+)", block, re.M)
        cdir = re.search(r"^\s*dir:\s*([\w./-]+)", block, re.M)
        if cid:
            res.append((cid.group(1), workspace / (cdir.group(1) if cdir else cid.group(1))))
    return res


def store_changes(store, ref):
    """id всех бизнес-change store: активные и заархивированные."""
    ids = set()
    for p in lines(git(store, "ls-tree", "--name-only", f"{ref}:{CHANGES}", check=False)):
        if p != "archive":
            ids.add(p)
    for p in lines(git(store, "ls-tree", "--name-only", f"{ref}:{CHANGES}/archive", check=False)):
        m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)", p)
        if m:
            ids.add(m.group(1))
    return sorted(ids)


def impl_metas(repo, ref):
    """{путь .openspec.yaml: (created, store, initiative id)} для всех change компонента в ref."""
    res = {}
    for p in lines(git(repo, "ls-tree", "-r", "--name-only", ref, "--", CHANGES, check=False)):
        if p.endswith("/.openspec.yaml"):
            res[p] = meta_fields(git(repo, "show", f"{ref}:{p}"))
    return res


def change_dirs(paths):
    """Каталоги change (с учётом archive/) из списка путей diff."""
    res = set()
    for p in paths:
        m = re.match(rf"({CHANGES}/(?:archive/)?[^/]+)/", p)
        if m and not m.group(1).endswith("/archive"):
            res.add(m.group(1))
    return res


def metric_mr_share(repo, ref, since, store_id):
    """Метрика 1: first-parent коммиты ref за период = смерженные MR (merge или squash)."""
    spec = tech = plain = 0
    for c in lines(git(repo, "log", "--first-parent", ref, f"--since={since}", "--format=%H")):
        parents = git(repo, "rev-list", "--parents", "-n1", c).split()[1:]
        if not parents:
            continue
        paths = lines(git(repo, "diff", "--name-only", parents[0], c))
        kinds = set()
        for d in change_dirs(paths):
            text = ""
            for rev in (c, parents[0]):  # archive удаляет файлы из старого каталога
                text = git(repo, "show", f"{rev}:{d}/.openspec.yaml", check=False)
                if text:
                    break
            _, st, iid = meta_fields(text)
            kinds.add("spec" if iid and st == store_id else "tech")
        if "spec" in kinds:
            spec += 1
        elif kinds:
            tech += 1
        else:
            plain += 1
    return spec, tech, plain


SCEN = re.compile(r"^#### Scenario:\s*(.+?)\s*$", re.M)
SECTION = re.compile(r"^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements", re.M)


def scenarios_of(text, delta):
    if not delta:
        return SCEN.findall(text)
    res, parts = [], SECTION.split(text)
    for kind, body in zip(parts[1::2], parts[2::2]):
        if kind in ("ADDED", "MODIFIED"):
            res += SCEN.findall(body)
    return res


def all_scenarios(store, ref):
    """Метрика 4: сценарии действующих спек и дельт активных change, id <capability>/<scenario>."""
    res = set()
    for p in lines(git(store, "ls-tree", "-r", "--name-only", ref, "--", "openspec")):
        m = re.match(r"openspec/specs/(.+)/spec\.md$", p)
        d = re.match(rf"{CHANGES}/(?!archive/)[^/]+/specs/(.+)/spec\.md$", p)
        if m or d:
            cap = (m or d).group(1)
            for s in scenarios_of(git(store, "show", f"{ref}:{p}"), delta=bool(d)):
                res.add(f"{cap}/{s}")
    return sorted(res)


def covered_in(repo, ref, ids, tmp):
    """Какие id упомянуты в репозитории вне openspec/ (тесты), одним git grep."""
    tmp.write_text("\n".join(ids) + "\n")
    # без -o: при -o git печатает только одно совпадение, и id-префикс скрыл бы длинный id
    text = git(repo, "grep", "-h", "-F", "-f", str(tmp), ref, "--", ".", ":!openspec", check=False)
    return {i for i in ids if i in text}


def fmt(v, suffix=""):
    return "—" if v is None else f"{v}{suffix}"


def report_mr_share(comps, ref, since, store_id):
    print("\n## 1. Доля MR компонентов со спекой\n")
    print("| Компонент | MR | со спекой | технические change | без change | доля |")
    print("|---|---|---|---|---|---|")
    for cid, p in comps:
        spec, tech, plain = metric_mr_share(p, ref, since, store_id)
        denom = spec + plain
        share = f"{round(100 * spec / denom)}%" if denom else "—"
        print(f"| {cid} | {spec + tech + plain} | {spec} | {tech} | {plain} | {share} |")
    print("\nДоля = со спекой / (со спекой + без change). Технические change (`spec-driven` без "
          "`initiative`) в знаменатель не входят. MR без change — это и код мимо спек, и мелкие "
          "технические правки: их стоит просмотреть глазами.")


def report_features(store, comps, ref, store_id):
    """Метрики 2, 3, 5."""
    metas = {cid: impl_metas(p, ref) for cid, p in comps}
    rows = []
    for change_id in store_changes(store, ref):
        br = first_add(store, ref, f"{CHANGES}/{change_id}/proposal.md")
        dor = first_add(store, ref, f"{CHANGES}/{change_id}/system.md")
        dod = first_add(store, ref, f"{CHANGES}/archive/*-{change_id}/system.md")
        starts = [cr for ms in metas.values() for cr, st, iid in ms.values()
                  if st == store_id and iid == change_id and cr]
        start = min(starts) if starts else None
        ba = sa = None
        if dor:
            log = ["log", "--first-parent", "--diff-filter=d", "--format=%h", f"{dor[0]}..{ref}", "--"]
            ba = len(lines(git(store, *log, f"{CHANGES}/{change_id}/proposal.md", f"{CHANGES}/{change_id}/specs")))
            sa = len(lines(git(store, *log, f"{CHANGES}/{change_id}/system.md", f"{CHANGES}/{change_id}/contracts")))
        rows.append((change_id, br and br[1], dor and dor[1], start, dod and dod[1], ba, sa))

    print("\n## 2, 3, 5. По фичам\n")
    print("| Фича | Business Ready | DoR | старт | DoD | BR→DoR | DoR→старт | DoR→DoD | правки БА / СА после DoR |")
    print("|---|---|---|---|---|---|---|---|---|")
    for f, br, dor, start, dod, ba, sa in rows:
        edits = "—" if ba is None else f"{ba} / {sa}"
        print(f"| {f} | {fmt(br)} | {fmt(dor)} | {fmt(start)} | {fmt(dod)} | {fmt(days(br, dor), ' дн')} "
              f"| {fmt(days(dor, start), ' дн')} | {fmt(days(dor, dod), ' дн')} | {edits} |")
    print("\nСтарт — самая ранняя дата `created` у impl-change с этой `initiative`. Даты "
          "Business Ready / DoR / DoD — первый коммит в `" + ref + "`, где появились proposal.md, "
          "system.md и system.md в archive. «—» — этап ещё не пройден.")


def report_coverage(store, comps, ref):
    """Метрика 4."""
    ids = all_scenarios(store, ref)
    tmp = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / f"sdd-metrics-{os.getpid()}.txt"
    covered = set()
    print("\n## 4. Доля сценариев с тестом\n")
    print("| Компонент | сценариев упомянуто в тестах |")
    print("|---|---|")
    try:
        for cid, p in comps:
            c = covered_in(p, ref, ids, tmp)
            covered |= c
            print(f"| {cid} | {len(c)} |")
    finally:
        tmp.unlink(missing_ok=True)
    share = f"{round(100 * len(covered) / len(ids))}%" if ids else "—"
    print(f"\nВсего сценариев: {len(ids)}, с тестом хотя бы в одном компоненте: {len(covered)} ({share}).")
    print("Считаются сценарии действующих спек и ADDED/MODIFIED активных change; тест — любое "
          "упоминание `<capability>/<scenario>` вне `openspec/`. Распределение по компонентам "
          "смотрите в отчёте sdd-impl-verify.")
    rest = [i for i in ids if i not in covered]
    if rest:
        print("\nБез теста:\n")
        for i in rest[:30]:
            print(f"- `{i}`")
        if len(rest) > 30:
            print(f"- … и ещё {len(rest) - 30}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", default="3.months", help="период для метрики 1 (формат git --since)")
    ap.add_argument("--ref", default="main", help="ветка store и компонентов")
    ap.add_argument("--workspace", help="папка с клонами компонентов (по умолчанию - родитель store)")
    a = ap.parse_args()

    store = pathlib.Path(git(".", "rev-parse", "--show-toplevel").strip())
    ws = pathlib.Path(a.workspace or os.environ.get("SDD_WORKSPACE") or store.parent)
    sy = store / ".openspec-store" / "store.yaml"
    m = sy.exists() and re.search(r"^id:\s*([\w-]+)", sy.read_text(), re.M)
    if not m:
        sys.exit("Запускайте из корня store: нет .openspec-store/store.yaml с id")
    store_id = m.group(1)
    comps, missing = [], []
    for cid, p in components(store, ws):
        if (p / ".git").exists():
            comps.append((cid, p))
        else:
            missing.append(cid)

    print(f"# Метрики SDD: store `{store_id}`, {dt.date.today()}\n")
    print(f"Ветка `{a.ref}`, период метрики 1: `{a.since}`. Расшифровка — docs/03-metrics.md.")
    if missing:
        print(f"\n**Нет клона:** {', '.join(missing)} (ищу в `{ws}`). Их метрики не посчитаны.")

    report_mr_share(comps, a.ref, a.since, store_id)
    report_features(store, comps, a.ref, store_id)
    report_coverage(store, comps, a.ref)


if __name__ == "__main__":
    main()
