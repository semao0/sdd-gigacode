# ADR-001. Хранение спецификаций

Статус: предложено · 2026-10-12 · OpenSpec 1.14.1

## Контекст

- Одно бизнес-требование реализуют несколько компонентов (backend, frontend, позже mobile).
  Если копировать спеку по репозиториям, копии разойдутся.
- design и tasks у каждого компонента свои. План компонента ревьюится и мержится вместе с его кодом.
- В OpenSpec есть **changes** (то, что меняется) и **specs** (то, что действует сейчас).
  При `archive` изменения из change вливаются в specs.

## Решение

**Бизнес- и системные требования лежат в store, design и tasks — в репозитории компонента.**

```
product-specs/            ← STORE, schema: business
  components.yaml         ← реестр компонентов: id, схема, repo
  contracts/              ← действующие OpenAPI/AsyncAPI (СА)
  openspec/
    specs/<domain>/...    ← действующие бизнес-спеки
    specs/integration/... ← поведение на границах компонентов (СА)
    changes/<change>/
      proposal.md         ← БА: зачем, для кого, скоуп
      specs/...           ← БА: бизнес-delta (WHEN/THEN), общая для всех
      system.md           ← СА: компоненты, матрица сценариев, контракты, данные, НФТ
      contracts/          ← СА: изменяемые контракты

backend/                  ← schema: impl-backend (frontend устроен так же: impl-frontend)
  openspec/config.yaml    ← references: [product-specs]
  openspec/changes/<change>-backend/
    .openspec.yaml        ← initiative: {store, id} — ссылка на change в store
    design.md             ← ## Upstream, реализация контрактов, БД, миграции
    tasks.md              ← задачи с covers: capability/scenario
  openspec/specs/         ← (опц.) технические спеки компонента
```

| Что нужно | Механизм OpenSpec | Статус |
|---|---|---|
| Отдельный репозиторий спек | `openspec store setup/register`, `--store <id>` | beta |
| Компонент читает спеки store | `references:` в config.yaml | beta |
| Разные артефакты в store и компонентах | project-local схемы | experimental |
| Артефакт СА | артефакт `system` в схеме `business`; готовность видна через `status --store --json` | experimental |
| Ссылка impl-change → change в store | `initiative: {store, id}`. OpenSpec только проверяет формат, используют скилы и CI | legacy-поле |
| Impl-change без бизнес-delta | `skip_specs: true`, ставится автоматически | stable |

**Почему компоненты не используют `store:`.** С `store:` все команды репозитория уходят в
store, design и tasks оказываются отдельно от кода, а OpenSpec не раскладывает задачи по
репозиториям. Поэтому у компонента свой root, а store подключён через `references` только на чтение.

**Контракт frontend↔backend пишет СА в store**: в `system.md`, большие контракты — файлами
в `changes/<id>/contracts/`. Backend его реализует (`sdd-impl-verify` сверяет OpenAPI с
контрактом). Frontend до готовности backend работает на моках. Так команды идут параллельно.

**Где что живёт.** Пока идёт изменение, контракты лежат в `system.md` и
`changes/<id>/contracts/`. Действующие — в корневом `contracts/` и `specs/integration/`.
При archive скил копирует файлы из `changes/<id>/contracts/` в корневой `contracts/`
(OpenSpec этого не делает). `system.md` уходит в архив как история решений.

**Archive в store — только когда все компоненты из `system.md` заархивировали свои changes
в main.** `specs/` должны описывать то, что уже работает, а не планы. Пока фича в работе,
компоненты читают активный change через `openspec show <change> --store <id>`: индекс
`references` показывает только заархивированные спеки.

## Отвергнутые варианты

| Вариант | Почему нет |
|---|---|
| Всё в монорепо или в репо backend | frontend зависит от чужого репо и ревью, не масштабируется |
| Копия спеки в каждом репо | копии расходятся |
| Всё в store, включая design/tasks | план отдельно от кода, задачи не разложить по репо |
| git submodule | синхронизация вручную, в репозиториях разные версии |
| Confluence/Jira | нельзя валидировать и мержить delta, нет ревью через MR |

## Риски

| Риск | Мера |
|---|---|
| Stores в beta, форматы могут поменяться | версия зафиксирована (`OPENSPEC_PINNED`); обновление идёт отдельной задачей с пересборкой схем и e2e |
| Поле `initiative` может исчезнуть | ссылка продублирована в `## Upstream` design.md; проверка CI находится в одном месте (`ci-check.sh`) |
| Store не синхронизируется сам | скилы делают `git pull` перед работой, CI клонирует store заново |
| Контракт или бизнес-требования меняются в процессе работы | правки через MR с ревью техлидов; resync в `sdd-impl-plan`, расхождения ловит `sdd-impl-verify` |
| Store можно склонировать на машину только один раз | одна рабочая папка `~/work/<product>/` |
