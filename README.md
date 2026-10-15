# SDD-методология на OpenSpec

Spec-driven development для продукта из нескольких компонентов (backend, frontend, ...).
Бизнес-спеки (БА) и системные требования (СА) хранятся один раз в **store**, design и tasks —
в репозитории каждого компонента.

Пайплайн: **БА** proposal + specs → **СА** system.md (компоненты, контракты, НФТ) →
**команды** design + tasks → код → archive в компонентах → archive в store.

- [docs/01-storage-adr.md](docs/01-storage-adr.md): где и почему хранятся спеки (решение по store)
- [docs/02-process.md](docs/02-process.md): роли, жизненный цикл фичи, гейты, частные случаи, проверки (pre-push, CI)
- [docs/03-metrics.md](docs/03-metrics.md): метрики процесса — что значат и как считать
- [examples/shop](examples/shop/README.md): пример store, backend и frontend на одной фиче
- [TODO.md](TODO.md): отложенные задачи (тест-кейсы QA в Jira, CI-гейт archive и др.)

Проверено на OpenSpec **1.14.1**. Stores в beta, версия зафиксирована в `scripts/sdd` (`OPENSPEC_PINNED`).

## Состав

```
schemas-src/          исходники схем: overlay поверх встроенной spec-driven
  business/           store: proposal → specs (БА) → system (СА)
  impl-backend/       компонент: design (реализация контрактов, БД) → tasks
  impl-frontend/      компонент: design (экраны/состояния) → tasks
schemas/              собранные схемы (tools/build-schemas.py), копируются в репозитории
templates/store/      config.yaml, components.yaml, скилы store (.gigacode/skills)
templates/component/  config.yaml (references на store), скилы компонента (.gigacode/skills)
examples/shop/        пример трёх репозиториев с заполненными спеками
scripts/sdd           единый CLI (Python 3.8+):
                        init            вся папка продукта: store + все компоненты
                        store-init      создание store
                        component-init  подключение репозитория компонента (интерактивно)
                        setup           настройка клона: store, sdd.home, doctor
                        check           validate --strict + правила SDD (pre-push хук и CI)
hooks/pre-push        pre-push хук: sdd check, если в ветке менялся openspec/
tools/
  build-schemas.py    пересборка схем (после обновления OpenSpec)
  metrics.py          отчёт по метрикам (docs/03-metrics.md) в Markdown, запуск из store
```

## Скилы (GigaCode)

| Скил | Где | Когда |
|---|---|---|
| `sdd-store-bootstrap` | store, БА + СА | первичное наполнение store по коду и документации существующего продукта |
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

## Быстрый старт

Договорённость: store и все репозитории продукта лежат в одной папке (`~/work/<product>/`).

```bash
npm i -g @fission-ai/openspec@1.14.1
pip install --user pyyaml          # нужен init/store-init/component-init/setup; check обходится без него
git clone <sdd> ~/tools/sdd

# склонировать в ~/work/shop репозитории компонентов (и store, если он уже есть), затем:
cd ~/work/shop && ~/tools/sdd/scripts/sdd init
```

`sdd init` делает всё сразу и безопасен при повторном запуске:
- находит store в папке, нет - создаёт (спросит каталог, id и URL репозитория);
- каждый новый репозиторий предлагает добавить в `components.yaml`: тип backend/frontend угадывает
  по файлам сборки, спрашивает id и описание; лишнее (docs, infra) - «пропустить»;
- подключает все компоненты: схема, `openspec/config.yaml` со ссылкой на store, скилы;
- регистрирует store, пишет `git config sdd.home`, ставит pre-push хук, где своего хука нет.

Дальше: запушить store, в компонентах закоммитить `openspec/` и `.gigacode/` (MR), в каждом
компоненте завести `GIGACODE.md` (правила сервиса для агента), наполнить store по коду -
`/sdd-store-bootstrap` в store. `sdd init -y` - без вопросов, ответы по умолчанию.

Новый разработчик клонирует репозитории в такую же папку и запускает там `sdd init -y`.
Новый компонент - клон в папку и снова `sdd init`.

Отдельные команды (CI, нестандартная раскладка):

```bash
sdd store-init <store-id> <path> [remote]          # только store
sdd component-init <repo> --component <id> --store <store-id> [--kind backend|frontend] [--remote URL]
sdd setup <repo>...                                # настройка клона: store, sdd.home, doctor
```

Если в репозитории уже есть свой pre-push хук (husky, Gradle, lefthook), вызовите SDD-хук
первой строкой из него: `"$SDD_HOME/hooks/pre-push" "$@" || exit 1`.

В той же папке компоненты ищет `sdd-initiative-status` (иначе нужен `SDD_WORKSPACE`).

## Обновление OpenSpec

1. Поднять `OPENSPEC_PINNED` в `scripts/sdd`.
2. `tools/build-schemas.py` подтягивает новые базовые инструкции spec-driven.
3. Проверить e2e в песочнице: store → change (proposal, specs, system) → impl-change в двух компонентах →
   `sdd check` → archive компонентов → archive store.
4. Перекатить `schemas/` и скилы в репозитории (`sdd store-init` и `sdd component-init` идемпотентны) и выполнить `openspec update`.
