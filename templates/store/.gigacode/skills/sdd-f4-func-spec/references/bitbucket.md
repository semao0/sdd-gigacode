# Bitbucket (Stash): ветки и PR

Сервер: `stash_url` из `spaces.yml`. Репозиторий: проект `stash_project`, слаг `repo`.

## Git

- Клон: `clone_url_template` из `spaces.yml`, где `{project}` — `stash_project` в нижнем регистре, `{repo}` — `repo`. По умолчанию SSH, например `ssh://git@stash.delta.sbrf.ru:7999/pcap-cc360/evpf_spec.git`.
- Если SSH не проходит (`Permission denied (publickey)`, таймаут), не менять протокол самостоятельно: пропустить задачу и сообщить ошибку. Протокол меняется только в `spaces.yml`.
- Спецификации лежат в `spec_root` (по умолчанию `openspec/`). Структура:

  ```text
  openspec/
    changes/<change>/business_spec.md   ← создал F3
    changes/<change>/func_spec.md       ← создаёт F4
    changes/<change>/proposal.md, tasks.md, specs/<capability>/spec.md
    changes/archive/
    specs/<capability>/business_spec.md, func_spec.md, ...
    schemas/sdd/schema.yaml
    schemas/sdd/templates/func_spec.md
    config.yaml
  ```

- Ветка F4: `feature/<IMPROVEMENT>-fr` (шаблон `branch_template`). Ветку F3 с суффиксом `-br` не трогать.
- Если push отклонён из-за прав или хуков — не обходить проверки, а пропустить задачу и записать текст ошибки в отчёт.

## Операции MCP

Через Bitbucket MCP нужны:

1. Список PR репозитория с фильтром по исходной ветке `refs/heads/<feature_branch>` в любом состоянии (`OPEN`, `MERGED`, `DECLINED`, или `state=ALL`).
2. Создание PR: `fromRef` = `refs/heads/<feature_branch>`, `toRef` = `refs/heads/<story_branch>`, оба в репозитории `<stash_project>/<repo>`.
3. Чтение PR по id — чтобы получить состояние и ссылку.

Если MCP не умеет фильтровать PR по ветке, взять PR в нужных состояниях и отфильтровать по `fromRef.displayId`.

## Описание PR

```markdown
Функциональная спецификация по [<IMPROVEMENT>](<jira_url>/browse/<IMPROVEMENT>), Story [<STORY>](<jira_url>/browse/<STORY>).

Файл: `<spec_root>/changes/<change>/func_spec.md`
Основа: `business_spec.md` той же папки и описание Improvement.

- FT: <число карточек>
- Покрыты BR: <список>
- Не покрыты BR: <список или «нет»>
- Открытые вопросы: <число>

После мержа skill sdd-f4-func-spec поставит в <IMPROVEMENT> «создана функциональная спецификация».
```
