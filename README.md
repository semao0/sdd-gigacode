# SDD-методология на OpenSpec

Spec-driven development для продукта из нескольких компонентов (backend, frontend, ...).
Бизнес-спеки (БА) и системные требования (СА) хранятся один раз в **store**, design и tasks —
в репозитории каждого компонента.

Пайплайн: **БА** proposal + specs → **СА** system.md (компоненты, контракты, НФТ) →
**команды** design + tasks → код → archive в компонентах → archive в store.

- [docs/01-storage-adr.md](docs/01-storage-adr.md): где и почему хранятся спеки (решение по store)
- [docs/02-process.md](docs/02-process.md): роли, жизненный цикл фичи, гейты, частные случаи, CI
- [examples/shop](examples/shop/README.md): пример store, backend и frontend на одной фиче

Проверено на OpenSpec **1.14.1**. Stores в beta, версия зафиксирована в `scripts/common.sh`.

## Состав

```
schemas-src/          исходники схем: overlay поверх встроенной spec-driven
  business/           store: proposal → specs (БА) → system (СА)
  impl-backend/       компонент: design (реализация контрактов, БД) → tasks
  impl-frontend/      компонент: design (экраны/состояния) → tasks
schemas/              собранные схемы (scripts/build-schemas.py), копируются в репозитории
templates/store/      config.yaml, components.yaml, скилы store (.gigacode/skills)
templates/component/  config.yaml (references на store), скилы компонента (.gigacode/skills)
examples/shop/        пример трёх репозиториев с заполненными спеками
scripts/
  build-schemas.py    пересборка схем (после обновления OpenSpec)
  bootstrap-store.sh  создание store
  bootstrap-component.sh  подключение репозитория компонента
  ci-check.sh         validate --strict + проверка ссылок на upstream
```

## Скилы (GigaCode)

| Скил | Где | Когда |
|---|---|---|
| `sdd-business-propose` | store, БА | новая фича или правка бизнес-требований |
| `sdd-system-design` | store, СА | system.md: компоненты, матрица сценариев, контракты, данные, НФТ |
| `sdd-initiative-status` | store | сквозной статус фичи по всем компонентам |
| `sdd-business-archive` | store | закрытие фичи: гейт «все компоненты готовы» → archive |
| `sdd-impl-plan` | компонент | design/tasks компонента по бизнес-change, resync при изменении upstream |
| `sdd-impl-verify` | компонент | трассировка сценарий → задача → тест перед MR и archive |

Скилы лежат в `.gigacode/skills/<name>/SKILL.md` (frontmatter: `name`, `description`).
Вызов: `/skills <name>` или `/<name>`; модель также подхватывает их сама по `description`.
Команды OpenSpec (`/opsx-explore`, `/opsx-apply`, `/opsx-archive` и др.) ставятся через
`openspec init --tools gigacode` в `.gigacode/commands/` и используются как есть.

Другой ассистент: `SDD_TOOL=qwen` (или `claude`) перед `bootstrap-*.sh` — скилы лягут в
`.qwen/skills/` (`.claude/skills/`), формат тот же.

## Быстрый старт

```bash
npm i -g @fission-ai/openspec@1.14.1

# 1. store (один раз на продукт)
scripts/bootstrap-store.sh product ~/work/shop/product-specs git@gitlab.example.com:shop/product-specs.git
#    → заполнить components.yaml, git push

# 2. каждый репозиторий компонента (один раз)
scripts/bootstrap-component.sh ~/work/shop/backend  backend  backend  product git@gitlab.example.com:shop/product-specs.git
scripts/bootstrap-component.sh ~/work/shop/frontend frontend frontend product git@gitlab.example.com:shop/product-specs.git

# 3. каждый разработчик (один раз на машину)
git clone git@gitlab.example.com:shop/product-specs.git ~/work/shop/product-specs
openspec store register ~/work/shop/product-specs
openspec doctor        # в репозитории компонента: reference product → ok
```

Рекомендуемая раскладка: store и компоненты лежат рядом в одной папке
(`~/work/<product>/`), там их ищет `sdd-initiative-status` (иначе нужен `SDD_WORKSPACE`).

## Обновление OpenSpec

1. Поднять `OPENSPEC_PINNED` в `scripts/common.sh`.
2. `scripts/build-schemas.py` подтягивает новые базовые инструкции spec-driven.
3. Проверить e2e в песочнице: store → change (proposal, specs, system) → impl-change в двух компонентах →
   `ci-check.sh` → archive компонентов → archive store.
4. Перекатить `schemas/` и скилы в репозитории (`bootstrap-*.sh` идемпотентны) и выполнить `openspec update`.
