---
name: sdd-initiative-status
description: Показать сквозной статус бизнес-change из store по всем компонентам - у кого заведён implementation-change, прогресс задач, что уже в main и заархивировано. Используй, когда спрашивают "что с фичей X", "готово ли к archive", или перед sdd-business-archive.
---

Вход: id бизнес-change в store (если не назван - `openspec list --json` и спроси).

## Как искать репозитории компонентов
Рабочая папка `WS = ${SDD_WORKSPACE:-<родитель каталога store>}`. Для каждого компонента
из раздела "Компоненты" system.md бизнес-change берём `dir` из `components.yaml`:
репозиторий ожидается в `$WS/<dir>`. Если каталога нет - статус "нет клона", подскажи
`git clone <repo> $WS/<dir>`; не клонируй сам без согласия пользователя.

## Для каждого компонента
1. `git -C $WS/<dir> fetch -q` (если не получилось - продолжай по локальному состоянию
   и пометь это в отчёте).
2. Найди implementation-changes, ссылающиеся на бизнес-change:
   - в main: `git -C $WS/<dir> grep -l -e "id: <change-id>" origin/HEAD -- 'openspec/changes/*/.openspec.yaml' 'openspec/changes/archive/*/.openspec.yaml'`
   - локально (в т.ч. в рабочих ветках): `grep -l -e "id: <change-id>" $WS/<dir>/openspec/changes/*/.openspec.yaml $WS/<dir>/openspec/changes/archive/*/.openspec.yaml`
   Проверяй, что найденный файл содержит `initiative:` с этим `store` - совпадение `id`
   в другом поле не считается.
3. Для активного change: `(cd $WS/<dir> && openspec status --change <impl-id> --json)` -
   прогресс артефактов и задач.
4. Статус компонента:
   - `не начат` - нет impl-change;
   - `планирование` - нет tasks.md или design не готов;
   - `в работе N/M` - задачи частично выполнены;
   - `готов, не в main` - всё выполнено/заархивировано, но только в ветке;
   - `готов` - impl-change заархивирован и это есть в origin/HEAD.

Нет system.md - статус всего change `ждёт СА`, компоненты не проверяй.

## Отчёт
Таблица: компонент | impl-change | статус | ветка/MR. Затем вывод:
"готов к archive", если все компоненты `готов`, иначе - что блокирует. Ничего не меняй.
