---
name: sdd-business-archive
description: Заархивировать бизнес-change в store (влить его delta-спеки в основные бизнес-спеки) после того, как все компоненты реализовали и выкатили его. Используй, когда фича выпущена или пользователь просит закрыть/заархивировать бизнес-change.
---

Бизнес-спеки в `openspec/specs/` store описывают то, что ПРАВДА в продукте. Поэтому
бизнес-change архивируется только когда поведение реально работает во всех компонентах.

## Гейт
1. `git pull --ff-only` в store.
2. Выполни шаги скила `sdd-initiative-status` для этого change.
3. Archive разрешён, только если каждый компонент из "Компоненты" system.md в статусе `готов`.
   Если нет - покажи блокеры и остановись. Обход гейта возможен только по явному
   решению БА (например, компонент исключён из скоупа) - тогда сначала поправь раздел
   "Компоненты" и матрицу в system.md (это делает СА) отдельным коммитом с причиной.
4. `openspec validate <change-id> --strict`.

## Archive
1. Работа идёт в ветке `archive/<change-id>` (см. шаг 6), в main не коммить.
2. Если в `openspec/changes/<change-id>/contracts/` есть файлы, скопируй их в `contracts/`
   в корне store (замена целиком): это действующие контракты продукта. OpenSpec сам этого
   не делает.
3. `openspec archive <change-id> -y`.
4. У новой capability (в том числе `integration/` от СА) `openspec archive` пишет в
   `## Purpose` заглушку, и `validate --strict` её не пропускает. Замени заглушку в
   `openspec/specs/<capability>/spec.md` на назначение capability: возьми его из proposal
   или system.md.
5. Проверь результат: `git diff --stat`, `openspec list --specs` - изменились спеки из
   Capabilities proposal и `integration/` из change. `openspec validate --specs --strict`
   должен пройти: иначе после merge упадёт ci-check в main store.
6. Ветка `archive/<change-id>`: `git switch -c archive/<change-id>` от актуального main
   (уже есть - `git switch archive/<change-id>`;
   незакоммиченные файлы переходят вместе с ней).
   В main не коммить: `git branch --show-current` должен вернуть `archive/<change-id>`.
7. Коммит `spec: archive <change-id>`, `git push -u origin archive/<change-id>`.
8. PR в main открывает и мержит человек, ты не мержишь.
   Назови ветку и ревьюеров: БА и СА.
9. Сообщи: после merge сводка бизнес-спек в referenced-индексе компонентов обновится
   у всех после `git pull` store.
