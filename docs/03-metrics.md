# Метрики SDD-процесса

Метрики показывают, работает ли процесс на деле или его соблюдают только формально.
Почти всё считается из git: даты merge веток `spec/`, `system/`, `archive/` в store и
`.openspec.yaml` в репозиториях компонентов.

**Готовый отчёт:** из корня store `python3 <sdd>/scripts/metrics.py [--since 3.months]` выводит
все метрики в Markdown. Клоны компонентов он ищет рядом со store по `components.yaml`;
перед запуском сделайте `git pull` везде. Команды ниже — что он считает, их можно
запускать и по отдельности.

| # | Метрика | Главный вопрос |
|---|---|---|
| 1 | Доля MR компонентов с `initiative` | пишут ли код по спекам |
| 2 | Business Ready → DoR, DoR → первый impl-change | где фича ждёт до старта разработки |
| 3 | Правки требований после DoR (БА / СА) | насколько требования готовы к старту |
| 4 | Доля сценариев с тестом | проверяется ли описанное поведение |
| 5 | Lead time DoR → DoD | сколько реально занимает поставка фичи |

## 1. Доля MR компонентов с impl-change, у которого есть `initiative`

**Что значит:** какая часть изменений в коде backend и frontend привязана к требованиям из store.

**Как считать:** берём MR в репозиториях компонентов за период, технические (обновление
зависимостей, инфраструктура) исключаем. Считаем, в скольких есть
`openspec/changes/*/.openspec.yaml` с `initiative`.

```bash
# MR (merge-коммиты) в main за месяц, затронувшие openspec/changes с initiative
git log --merges --since=1.month --first-parent main --format=%H | while read c; do
  git diff --name-only "$c^1" "$c" -- 'openspec/changes/*/.openspec.yaml' \
    | xargs -r -I{} git show "$c:{}" 2>/dev/null | grep -q '^initiative:' && echo "$c"
done | wc -l
```

**О чём говорит:** низкая доля значит, что команды пишут код мимо спек, и store перестаёт
описывать то, что реально работает. Это главная метрика внедрения.

## 2. Время Business Ready → DoR и DoR → первый impl-change

**Что значит:**
- первый отрезок — от merge MR `spec/<id>` (бизнес-требования согласованы) до merge
  `system/<id>` (СА закончил `system.md`);
- второй — от DoR до момента, когда команда завела свой impl-change.

**Как считать:** по датам merge в store и полю `created` в `.openspec.yaml` компонента.

```bash
# в store: даты появления proposal.md и system.md в main
git log --first-parent main --diff-filter=A --format=%as -- 'openspec/changes/<id>/proposal.md' | tail -1
git log --first-parent main --diff-filter=A --format=%as -- 'openspec/changes/<id>/system.md'   | tail -1
# в компоненте: когда завели impl-change
grep -h '^created:' openspec/changes/{,archive/*-}<id>-*/.openspec.yaml 2>/dev/null
```

**О чём говорит:**
- долгий первый отрезок — узкое место в СА: перегружен или требования сырые;
- долгий второй — команды не берут фичу сразу, обычно из-за приоритетов.

## 3. Число правок требований после DoR

Считается отдельно для бизнес-части (БА: `proposal.md`, `specs/`) и для `system.md` (СА).

**Что значит:** сколько раз меняли требования после того, как команды уже начали работу.

**Как считать:** `git log` по файлам change в store после даты merge `system/<id>`.

```bash
# коммит DoR - merge, в котором появился system.md; диапазон DOR..main его не включает,
# --diff-filter=d не считает archive (он переносит файлы change в archive/)
DOR=$(git log --first-parent main --diff-filter=A --format=%H -- openspec/changes/<id>/system.md | tail -1)
# бизнес-правки (БА)
git log --first-parent --diff-filter=d --format=%h "$DOR"..main -- openspec/changes/<id>/proposal.md openspec/changes/<id>/specs | wc -l
# правки system.md и контрактов (СА)
git log --first-parent --diff-filter=d --format=%h "$DOR"..main -- openspec/changes/<id>/system.md openspec/changes/<id>/contracts | wc -l
```

**О чём говорит:** каждая правка — это resync у команд и переделка.
- Много бизнес-правок — БА плохо уточняет требования на старте.
- Много правок `system.md` — контракты продумывают не до конца.

Цель — стремиться к нулю, но не любой ценой: правка лучше, чем код по неверной спеке.

## 4. Доля сценариев с тестом

**Что значит:** у скольких сценариев из спек (`#### Scenario`) есть тест, где упомянуто
`<capability>/<scenario>`.

**Как считать:** это множество C из `sdd-impl-verify`: `git grep` по тестам компонента.
Готовая цифра есть в отчёте скила (таблица «сценарий | задача | тест | статус»).

**О чём говорит:** проверяется ли поведение, которое описано в спеке. Если у сценария нет
теста, спека и код могут незаметно разойтись.

## 5. Lead time DoR → DoD

**Что значит:** от момента, когда требования готовы к разработке (merge `system/<id>`),
до merge `archive/<id>`. К этому моменту фича работает во всех компонентах, и спеки store
обновлены.

**Как считать:** по датам merge `system/<id>` и `archive/<id>` в store.

```bash
git log --first-parent main --diff-filter=A --format=%as -- 'openspec/changes/<id>/system.md' | tail -1   # DoR
git log --first-parent main --diff-filter=A --format=%as -- 'openspec/changes/archive/*-<id>/system.md'  # DoD
```

**О чём говорит:** реальное время поставки фичи целиком. Если оно велико, хотя каждая
команда работает быстро, компоненты ждут друг друга. Тогда стоит проверить, работает ли
frontend на моках по контракту, а не ждёт backend.
