import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import f4  # noqa: E402

CFG = f4.load_config()


def test_config_parsed():
    assert CFG["label"] == "автофлоу"
    assert CFG["issue_types"] == ["Улучшение", "Improvement"]
    assert CFG["branch_template"] == "feature/{improvement}-fr"
    assert CFG["story_branch_templates"][-1] == "{story}"
    assert [s["repo"] for s in CFG["spaces"]] == ["evpf_spec", "motiv3_spec", "atrk_spec"]
    assert CFG["spaces"][0]["name"] == "Мотивация 3.0 ЕВПФ"
    assert CFG["clone_url_template"].format(project="pcap-cc360", repo="evpf_spec") == \
        "ssh://git@stash.delta.sbrf.ru:7999/pcap-cc360/evpf_spec.git"


def test_config_matches_pyyaml_if_available():
    yaml = pytest.importorskip("yaml")
    assert f4.load_config() == yaml.safe_load(f4.DEFAULT_CONFIG.read_text(encoding="utf-8"))


def test_jql_skips_todo_projects_and_quotes():
    jql = f4.build_jql(CFG)
    assert 'project in ("EVPF")' in jql
    assert 'labels = "автофлоу"' in jql
    assert 'status = "Анализ"' in jql
    assert '"Текущий статус (краткий комментарий)" ~ "\\"создана бизнес-спецификация\\""' in jql


def test_jql_select_field():
    cfg = dict(CFG, status_field_kind="select")
    assert '"Текущий статус (краткий комментарий)" = "создана бизнес-спецификация"' in f4.build_jql(cfg)


def test_names():
    names = f4.make_names(CFG, "evpf-8090", "EVPF-8100", "Бонус КБ")
    assert names["feature_branch"] == "feature/EVPF-8090-fr"
    assert names["commit_message"] == "EVPF-8090: функциональная спецификация"
    assert names["pr_title"] == "EVPF-8090: функциональная спецификация — Бонус КБ"


def test_find_space():
    assert f4.find_space(CFG, "evpf")["repo"] == "evpf_spec"
    with pytest.raises(KeyError):
        f4.find_space(CFG, "NOPE")


@pytest.mark.parametrize("branches, expected", [
    (["abc\trefs/heads/master", "def\trefs/heads/release/EVPF-81"], "release/EVPF-81"),
    (["refs/heads/feature/EVPF-81", "refs/heads/feature/EVPF-810"], "feature/EVPF-81"),
    (["refs/heads/bugfix/EVPF-81-something"], "bugfix/EVPF-81-something"),
])
def test_story_branch(branches, expected):
    assert f4.pick_story_branch(CFG, "EVPF-81", branches) == expected


def test_story_branch_ambiguous_or_missing():
    with pytest.raises(LookupError, match="несколько"):
        f4.pick_story_branch(CFG, "EVPF-81", ["a/EVPF-81-x", "b/EVPF-81-y"])
    with pytest.raises(LookupError, match="нет ветки"):
        f4.pick_story_branch(CFG, "EVPF-81", ["feature/EVPF-810"])


def _change(root: Path, name: str, business: str = "# БС\n", func: bool = False) -> Path:
    d = root / "openspec" / "changes" / name
    d.mkdir(parents=True)
    (d / "business_spec.md").write_text(business, encoding="utf-8")
    if func:
        (d / "func_spec.md").write_text("x", encoding="utf-8")
    return d


def test_find_change_by_name(tmp_path):
    _change(tmp_path, "motiv3-other")
    target = _change(tmp_path, "motiv3-evpf-8090")
    assert f4.find_change_dir(tmp_path, "openspec", "EVPF-8090", "EVPF-8100") == target


def test_find_change_by_business_text(tmp_path):
    _change(tmp_path, "a")
    target = _change(tmp_path, "b", "Источник: EVPF-8100\n")
    assert f4.find_change_dir(tmp_path, "openspec", "EVPF-8090", "EVPF-8100") == target


def test_find_change_by_story_diff(tmp_path):
    _change(tmp_path, "a")
    target = _change(tmp_path, "b")
    (tmp_path / "openspec" / "changes" / "archive").mkdir()
    changed = ["openspec/changes/b/business_spec.md", "README.md"]
    assert f4.find_change_dir(tmp_path, "openspec", "EVPF-8090", "EVPF-8100", changed) == target


def test_find_change_story_diff_without_changes(tmp_path):
    _change(tmp_path, "a")
    with pytest.raises(LookupError, match="F3"):
        f4.find_change_dir(tmp_path, "openspec", "EVPF-8090", "EVPF-8100", ["README.md"])


def test_find_change_ambiguous(tmp_path):
    _change(tmp_path, "a")
    _change(tmp_path, "b")
    with pytest.raises(LookupError, match="однозначно"):
        f4.find_change_dir(tmp_path, "openspec", "EVPF-8090", "EVPF-8100")


def test_template_path(tmp_path):
    assert f4.template_path(tmp_path, "openspec") == f4.FALLBACK_TEMPLATE
    tpl = tmp_path / "openspec" / "schemas" / "sdd" / "templates" / "func_spec.md"
    tpl.parent.mkdir(parents=True)
    tpl.write_text("# T\n", encoding="utf-8")
    assert f4.template_path(tmp_path, "openspec") == tpl


TEMPLATE = f4.FALLBACK_TEMPLATE.read_text(encoding="utf-8")
BUSINESS = "BR-001 бонус\nBR-002 отчёт\n"
GOOD = """# Функциональная спецификация: Бонус КБ

## Источники

Improvement EVPF-8090, Story EVPF-8100, business_spec.md.

## Область изменений

Меняется расчёт бонуса.

## Компоненты

| Компонент | Что делает |
|---|---|
| motiv3_pg | Рассчитывает бонус |

## Функциональные требования

### FT-001. Расчёт бонуса

Трассировка: BR-001. Результат: Система ДОЛЖНА рассчитать бонус.

## Данные

Нет данных в источниках.

## Нефункциональные требования

Нет данных в источниках.

## Открытые вопросы

| № | Вопрос | Основание |
|---|---|---|
| 1 | Как именно формируется отчёт? | BR-002 |
"""


def test_validate_ok():
    errors, warnings = f4.validate(GOOD, "EVPF-8090", TEMPLATE, BUSINESS)
    assert errors == []
    assert warnings == []


def test_validate_reports_problems():
    bad = GOOD.replace("## Данные\n", "").replace("EVPF-8090", "X").replace("BR-001", "BR-009")
    bad += "\n{{вопрос}} TODO\n"
    errors, warnings = f4.validate(bad, "EVPF-8090", TEMPLATE, BUSINESS)
    text = "\n".join(errors)
    assert "«Данные»" in text
    assert "плейсхолдер" in text
    assert "EVPF-8090" in text
    assert "BR-009 нет в бизнес-спецификации" in text
    assert warnings == ["BR-001 из бизнес-спецификации не покрыт"]


def test_validate_heading_order():
    swapped = GOOD.replace("## Данные", "## TMP").replace("## Нефункциональные требования", "## Данные")
    swapped = swapped.replace("## TMP", "## Нефункциональные требования")
    errors, _ = f4.validate(swapped, "EVPF-8090", TEMPLATE)
    assert any("Нефункциональные" in e or "Данные" in e for e in errors)


def test_validate_empty():
    assert f4.validate("  \n", "EVPF-8090", TEMPLATE) == (["файл пустой"], [])


def test_cli_validate(tmp_path, capsys):
    spec = tmp_path / "func_spec.md"
    spec.write_text(GOOD, encoding="utf-8")
    bs = tmp_path / "business_spec.md"
    bs.write_text(BUSINESS, encoding="utf-8")
    assert f4.main(["validate", str(spec), "--improvement", "EVPF-8090", "--business-spec", str(bs)]) == 0
    assert capsys.readouterr().out.strip() == "OK"
    spec.write_text("# x\n", encoding="utf-8")
    assert f4.main(["validate", str(spec), "--improvement", "EVPF-8090"]) == 1
