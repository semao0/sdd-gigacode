---
name: sdd-impl-plan
description: Завести (или пересинхронизировать) implementation-change в репозитории компонента по бизнес-change из store - design.md и tasks.md для этого компонента со ссылкой на upstream. Используй, когда команда берёт в работу фичу из store, или когда бизнес-change в store изменился после начала работы (resync).
---

Ты в репозитории КОМПОНЕНТА. Бизнес-требования читаются из store (read-only), здесь
пишется только КАК: design.md и tasks.md по схеме компонента (`impl-backend`/`impl-frontend`).

## 1. Проверки
1. `openspec doctor` - root локальный, reference на store `ok`. Если store не
   зарегистрирован - покажи fix из вывода doctor и остановись.
2. Обнови store: путь берётся из `openspec store list --json`; `git -C <path> pull --ff-only`.
   Устаревший store = неверные требования; если pull не удался - предупреди пользователя.
3. Определи компонент: `context` в `openspec/config.yaml` и поле schema.

## 2. Выбор upstream
1. Пользователь назвал бизнес-change -> `openspec show <id> --store <store>`.
   Иначе `openspec list --json --store <store>` и предложи активные changes, у которых
   этот компонент есть в разделе "Компоненты" system.md.
2. **Гейт DoR**: `openspec status --change <id> --store <store> --json` - все артефакты
   готовы, включая `system`, и system.md есть в origin/HEAD store. Нет system.md -
   остановись: системный аналитик ещё не закончил (`sdd-system-design`).
3. Если компонента нет в "Компоненты" system.md - скажи об этом и не создавай change,
   пока пользователь не подтвердит (вопрос к СА).
4. Режим: если в `openspec/changes/*/.openspec.yaml` уже есть `initiative.id == <id>` -
   это **resync**, иначе **новый**.

## 3. Новый change
1. `openspec new change <id>-<component>` (например `add-promo-codes-backend`).
2. Допиши в конец `openspec/changes/<name>/.openspec.yaml` (ключи не дублируй):
   ```yaml
   initiative:
     store: <store-id>
     id: <upstream-change-id>
   ```
   `skip_specs: true` OpenSpec ставит сам: в impl-схеме нет артефакта specs, бизнес-delta
   живут в store. Проверь: `openspec validate <name>` не ругается на .openspec.yaml.
3. Для `design`, затем `tasks`: `openspec instructions <artifact> --change <name> --json`,
   пиши строго по инструкции. Код проекта изучай, чтобы design был реальным, но код
   не меняй.
4. Вопросы к бизнес-спеке и к контрактам не додумывай - они идут в "Вопросы к upstream"
   design.md. Блокирующие: по бизнес-поведению - бизнес-аналитику, по контрактам и
   разбиению на компоненты - системному аналитику.
5. `openspec validate <name> --strict`.

## 4. Resync
1. Сравни текущий upstream (`openspec show <id> --store <store>` и system.md) со списком
   сценариев в разделе "## Upstream" design.md и трассировками `covers:` в tasks.md.
   Для system.md используй `git -C <store> log -p -- openspec/changes/<id>/system.md`
   с даты коммита design.md.
2. Покажи diff: добавленные / изменённые / удалённые сценарии и изменения контрактов.
3. После подтверждения пользователя обнови "## Upstream", затронутые разделы design.md
   и задачи. Выполненные задачи (`[x]`) не удаляй: если поведение поменялось, добавь
   новую задачу на доработку.

## 5. Завершение
Ветка `feat/<name>`, коммит артефактов. Дальше реализация - `/opsx-apply`.
Не начинай реализацию в этом же ответе.
