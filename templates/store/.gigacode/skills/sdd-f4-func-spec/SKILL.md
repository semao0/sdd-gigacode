---
name: sdd-f4-func-spec
description: >-
  Шаг F4 автофлоу SDD. Находит в Jira задачи Improvement с меткой «автофлоу»,
  статусом «Анализ» и «Текущий статус (краткий комментарий)» = «создана
  бизнес-спецификация», от ветки связанной Story создаёт ветку
  feature/<KEY>-fr, генерирует func_spec.md по описанию Improvement и
  бизнес-спецификации, открывает PR в ветку Story, а после мержа ставит
  «создана функциональная спецификация». Use when the user asks to run F4,
  sdd-f4, generate functional specs for autoflow improvements, or check
  merged F4 pull requests.
icon: code
color: cyan
---

# SDD F4: функциональная спецификация по Improvement

Skill самодостаточен: всё, что нужно для работы, лежит в этой папке. Каталог skill — папка, в которой лежит этот `SKILL.md`; ниже он записан как `<skill>`.

Jira и Bitbucket (Stash) вызываются через MCP-инструменты, git — через командную строку. Детерминированные шаги делает `<skill>/scripts/f4.py` (только стандартная библиотека Python 3).

Если `python3` недоступен, те же шаги выполнить вручную по тем же правилам и написать в отчёте, что скрипт не запускался:

- JQL: `project in (<jira_project из spaces.yml, кроме TODO>) AND issuetype in ("Улучшение", "Improvement") AND labels = "автофлоу" AND status = "Анализ" AND "<status_field>" ~ "\"<status_from>\""`.
- Имена: ветка `feature/<IMPR>-fr`, коммит и начало заголовка PR — `<IMPR>: функциональная спецификация`; ключи в верхнем регистре.
- Ветка Story: первая существующая из `release/<STORY>`, `feature/<STORY>`, `<STORY>`; иначе единственная ветка, содержащая ключ (за ключом не идёт цифра). Не одна — пропустить задачу.
- Папка change: среди `<spec_root>/changes/*` с `business_spec.md`, кроме `archive`, затронутых диффом ветки Story, — та, в имени или `business_spec.md` которой есть ключ Improvement или Story; иначе единственная без `func_spec.md`. Не одна — пропустить задачу.
- Проверка: все заголовки `#` и `##` шаблона есть в том же порядке; нет `{{…}}`, `TODO`, `TBD`; есть ключ Improvement; каждый `BR-*` из спеки есть в `business_spec.md`.

## Что прочитать перед запуском

1. `<skill>/spaces.yml` — пространства, репозитории, значения полей и шаблон имени ветки. Если в нём остались `TODO` (ключ проекта, `status_field_id`), сначала уточнить их у пользователя или в Jira. Пространство с `jira_project: TODO` в поиск не попадает.
2. `<skill>/references/jira.md` — какие операции Jira нужны и как менять поле статуса.
3. `<skill>/references/bitbucket.md` — ветки, коммит, PR, проверка мержа.
4. `<skill>/references/func-spec-rules.md` — как писать функциональную спецификацию.

## Режимы

- Обычный запуск: обработать все найденные задачи.
- `dry-run` («проверь», «что найдётся», «без изменений»): выполнить шаги 1–4 и показать план по каждой задаче. Ничего не пушить, PR не создавать, Jira не менять.
- Одна задача: если пользователь назвал ключ, обработать только её, но с теми же проверками условий.

## Порядок работы

### 1. Найти задачи

```bash
python3 <skill>/scripts/f4.py jql
```

Выполнить JQL через Jira MCP (поиск задач). Запросить поля: `summary`, `description`, `issuetype`, `status`, `labels`, `issuelinks`, поле статуса из `status_field_id`.

Если `status_field_kind: text`, JQL ищет через `~`, поэтому отбросить задачи, у которых значение поля после обрезки пробелов не совпадает с `status_from` без учёта регистра.

Если задач нет — сообщить об этом и закончить.

Каждую задачу обрабатывать отдельно. Ошибка в одной задаче не останавливает остальные: записать причину в отчёт и перейти к следующей.

### 2. Определить пространство и Story

```bash
python3 <skill>/scripts/f4.py space --project <JIRA-PROJECT>
```

Story — связанная задача (`issuelinks`) с типом `Story` / `История`. Нужна ровно одна. Ни одной или несколько — пропустить задачу с причиной «нужна ровно одна связанная Story».

```bash
python3 <skill>/scripts/f4.py names --improvement <IMPR> --story <STORY> --summary "<summary Improvement>"
```

Команда возвращает `feature_branch`, `commit_message` и `pr_title`. Использовать их без изменений.

### 3. Найти ветку Story

```bash
git ls-remote --heads <clone_url> | python3 <skill>/scripts/f4.py story-branch --story <STORY>
```

`clone_url` = `clone_url_template` из `spaces.yml` с подстановкой `{project}` (`stash_project` в нижнем регистре) и `{repo}`. Если ветка не найдена или найдено несколько — пропустить задачу.

### 4. Проверить, что уже сделано (идемпотентность)

Через Bitbucket MCP найти PR из `feature_branch` в ветку Story (в любом состоянии):

| Состояние | Действие |
|---|---|
| `MERGED` | Шаг 9: поменять статус в Jira. Больше ничего не делать. |
| `OPEN` | Пропустить: «PR ждёт мержа», ссылка на PR. |
| `DECLINED` | Пропустить: «PR отклонён, нужен человек». Новый PR не создавать. |
| PR нет, `feature_branch` есть | Продолжить с шага 5 на существующей ветке, не пересоздавать её. |
| Нет ни PR, ни ветки | Продолжить с шага 5. |

В `dry-run` здесь остановиться и вывести план по задаче.

### 5. Подготовить ветку

Работать в отдельной временной папке, а не в рабочих клонах пользователя.

```bash
git clone <clone_url> <tmp>/<repo>     # или git fetch, если клон уже есть
cd <tmp>/<repo>
git switch -c <feature_branch> origin/<story_branch>   # ветка новая
git switch <feature_branch>                            # ветка уже есть на сервере
```

Найти папку change, которую F3 создал в ветке Story:

```bash
git diff --name-only origin/<default_branch>...origin/<story_branch> > <tmp>/changed.txt
python3 <skill>/scripts/f4.py find-change . --spec-root <spec_root> \
  --improvement <IMPR> --story <STORY> --changed <tmp>/changed.txt
```

`default_branch` — ветка, на которую указывает `origin/HEAD` (`git symbolic-ref refs/remotes/origin/HEAD`). Если папку не удалось найти однозначно — пропустить задачу и перечислить кандидатов в отчёте.

### 6. Собрать источники

Прочитать целиком:

1. Описание Improvement из Jira (`description`) и `summary`. Если в описании есть ссылки на вложения или Confluence, которые MCP может открыть, прочитать их тоже. Закрытый источник не восстанавливать по догадке, а внести в «Открытые вопросы».
2. `<change>/business_spec.md` — главный источник требований `BR-*`.
3. `<change>/proposal.md`, `<change>/specs/**/spec.md`, `<change>/tasks.md`, если они есть.
4. Текущее состояние: `<spec_root>/specs/<capability>/func_spec.md` и `business_spec.md` тех capability, которые затрагивает change (имена папок в `<change>/specs/`). Функциональная спецификация описывает изменения относительно этого состояния.
5. Правила репозитория: в `<spec_root>/schemas/sdd/schema.yaml` — артефакт функциональной спецификации (`instruction`, `requires`); в `<spec_root>/config.yaml` — `context` и `rules` для этого артефакта. Они важнее общих правил этого skill.
6. Шаблон:

```bash
python3 <skill>/scripts/f4.py template . --spec-root <spec_root>
```

Команда возвращает шаблон репозитория `<spec_root>/schemas/sdd/templates/func_spec.md`, а если его нет — `<skill>/assets/func_spec.template.md`.

### 7. Написать `<change>/func_spec.md`

Если `func_spec.md` уже есть и содержит не только шаблон — не перезаписывать, пропустить задачу: «func_spec.md уже существует».

Скопировать шаблон и заполнить его по `<skill>/references/func-spec-rules.md`. Затем проверить:

```bash
python3 <skill>/scripts/f4.py validate <change>/func_spec.md --improvement <IMPR> \
  --business-spec <change>/business_spec.md --template <путь из шага 6>
```

Исправлять файл, пока команда не вернёт `OK` с кодом 0. Если после трёх исправлений ошибки остаются — не пушить, пропустить задачу и привести ошибки в отчёте. Предупреждения `WARN` о непокрытых `BR` перенести в «Открытые вопросы» спецификации или объяснить в описании PR.

### 8. Коммит, push и PR

```bash
git add <change>/func_spec.md
git commit -m "<commit_message>"
git push -u origin <feature_branch>
```

В коммит попадает только `func_spec.md`. Если `git status` показывает другие изменения — не коммитить их.

Через Bitbucket MCP создать PR: из `feature_branch` в ветку Story, заголовок `pr_title`. Описание — по шаблону из `<skill>/references/bitbucket.md`. Статус в Jira на этом шаге не менять.

### 9. После мержа: статус в Jira

Выполняется только для задач, у которых на шаге 4 PR в состоянии `MERGED`. Через Jira MCP записать в поле `status_field_id` значение `status_to` (формат — в `<skill>/references/jira.md`). Статус задачи («Анализ») и метки не трогать. После записи перечитать задачу и убедиться, что значение сохранилось.

## Жёсткие правила

- Не менять Jira, пока PR не смержен. Единственная запись в Jira — поле статуса на шаге 9.
- Не пушить в ветку Story и в ветку по умолчанию. Пушить только в `feature_branch`.
- Не использовать `--force`, не удалять ветки и не закрывать чужие PR.
- Не создавать второй PR, если PR из `feature_branch` уже есть в любом состоянии.
- Не придумывать требования: всё в спецификации должно следовать из источников шага 6.

## Что ответить пользователю

Таблица по всем найденным задачам:

| Improvement | Story | Пространство | Результат | Ссылка |
|---|---|---|---|---|

Результат — одно из: `PR создан`, `ждёт мержа`, `статус обновлён`, `пропущена: <причина>`, `dry-run: <план>`. Ниже — предупреждения валидатора по созданным PR и значения `TODO` в `spaces.yml`, если они мешали работе.
