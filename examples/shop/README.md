# Пример: продукт «shop», три репозитория

Снимок в середине работы над фичей **`shop-142-add-promo-codes`** (промокоды в корзине):
бизнес- и системные требования смержены (DoR пройден), backend наполовину реализован,
frontend работает на моках. Предыдущая фича `shop-101-add-cart` уже закрыта (DoD).

Все три репозитория проходят `openspec validate --all --strict` и `scripts/sdd check`
(OpenSpec 1.14.1). Здесь опущено то, что ставят `sdd store-init` и `sdd component-init`: `.git/`, `.gigacode/`
(скилы) и `openspec/schemas/` (копия `schemas/`).

```
product-specs/                                 ← STORE (БА + СА)
  components.yaml                              ← backend, frontend
  contracts/{cart,orders}.openapi.yaml         ← действующие контракты 1.0.0
  openspec/specs/business_spec.md              ← продукт: глоссарий, роли, домены
  openspec/specs/checkout/{business,func}_spec.md ← домен: правила и сквозные сценарии
  openspec/specs/checkout/cart/spec.md         ← действующая спека (после archive shop-101-add-cart)
  openspec/changes/
    shop-142-add-promo-codes/                  ← АКТИВНАЯ фича
      proposal.md                              ← БА: зачем, скоуп, метрики
      specs/checkout/promo-codes/spec.md       ← БА: новая capability (ADDED)
      specs/checkout/cart/spec.md              ← БА: правка итога (MODIFIED)
      specs/integration/promo-apply/spec.md    ← СА: поведение на границе компонентов
      system.md                                ← СА: компоненты, матрица, контракты, данные, НФТ
      contracts/{cart,orders}.openapi.yaml     ← СА: полные копии с изменениями, 1.1.0
    archive/2026-08-20-shop-101-add-cart/      ← закрытая фича, system.md как история решений

backend/                                       ← schema: impl-backend
  GIGACODE.md                                  ← правила сервиса для агента
  openspec/config.yaml                         ← references: shop
  openspec/changes/shop-142-add-promo-codes-backend/
    .openspec.yaml                             ← initiative: {store: shop, id: shop-142-add-promo-codes}
    design.md                                  ← Upstream, реализация контрактов, миграции, НФТ
    tasks.md                                   ← часть задач [x], covers: …, последняя группа «Интеграция»
  openspec/changes/archive/2026-08-18-shop-101-add-cart-backend/
  openspec/specs/api/rate-limiting/spec.md     ← локальная техническая спека (не бизнес)

frontend/                                      ← schema: impl-frontend
  openspec/changes/shop-142-add-promo-codes-frontend/ ← экраны и состояния, моки MSW, covers: …
  openspec/changes/archive/2026-08-19-shop-101-add-cart-frontend/
```

## На что посмотреть

- **Одна бизнес-спека — два плана.** `checkout/promo-codes` написана один раз в store;
  backend и frontend разложили её на свои `design.md`/`tasks.md`.
- **Матрица сценариев** в `system.md` говорит, какой компонент что реализует. Отсюда раздел
  `## Upstream` в каждом design.md: frontend явно пишет, что расчёт итога «не затрагивается».
- **Трассировка**: каждый сценарий из `## Upstream` встречается в `covers:` в tasks.md.
  Это проверяет `sdd-impl-verify`.
- **Контракты** живут в store (`changes/shop-142-add-promo-codes/contracts/`, полные копии действующих файлов). Backend сверяет с ними
  свой OpenAPI контрактным тестом, frontend генерирует из них типы и моки.
- **Что дальше по процессу:** backend и frontend доделывают задачи → `sdd-impl-verify` →
  merge → `/opsx-archive` в каждом → в store `sdd-business-archive`: delta вольются в
  `openspec/specs/`, контракты 1.1.0 заменят файлы в `contracts/`, change уйдёт в `archive/`.

## Как запустить локально

```bash
SDD=~/Projects/sdd
cp -r $SDD/examples/shop /tmp/shop && cd /tmp/shop
for r in product-specs backend frontend; do mkdir -p $r/openspec/schemas; done
cp -r $SDD/schemas/business      product-specs/openspec/schemas/
cp -r $SDD/schemas/impl-backend  backend/openspec/schemas/
cp -r $SDD/schemas/impl-frontend frontend/openspec/schemas/
openspec store register ./product-specs
(cd backend && openspec validate --all --strict && openspec show shop-142-add-promo-codes --store shop)
```
