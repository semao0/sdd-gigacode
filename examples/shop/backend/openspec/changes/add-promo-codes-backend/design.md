# Design (backend)

## Upstream

`shop/add-promo-codes` @ `a1b2c3d` (system.md смержен 2026-10-07, DoR).

Реализует backend:
- `checkout/promo-codes/Успешное применение`
- `checkout/promo-codes/Неизвестный промокод`
- `checkout/promo-codes/Истёкший промокод`
- `checkout/promo-codes/Не выполнена минимальная сумма`
- `checkout/promo-codes/Замена промокода`
- `checkout/promo-codes/Удаление промокода`
- `checkout/promo-codes/Лимит использований исчерпан`
- `checkout/cart/Итог без скидки` (регрессия)
- `checkout/cart/Пустая корзина` (регрессия)
- `checkout/cart/Итог со скидкой промокода`
- `checkout/cart/Скидка больше суммы корзины`
- `integration/promo-apply/Промокод стал недействителен до оформления`
- `integration/promo-apply/Повторный запрос применения`

Не затрагивается: —

## Context

Корзина хранится в PostgreSQL (`carts`, `cart_items`), расчёт итога — `CartPricingService`.
Оформление заказа — `OrderService.place()` в одной транзакции со списанием остатков.

## Реализация контрактов

- `api/openapi/cart.yaml` и `api/openapi/orders.yaml` — копии 1:1 контрактов 1.1.0 из
  `product-specs/openspec/changes/add-promo-codes/contracts/`, контрактный тест сравнивает схемы.
- `PUT /api/v1/cart/promo`: нормализация `trim().toUpperCase()`, проверки по порядку:
  существование → срок → лимит → минимальная сумма. Первая проваленная → `422` с кодом из контракта.
- `DELETE /api/v1/cart/promo`: всегда `200`.
- `POST /api/v1/orders`: повторная проверка промокода внутри транзакции; при отказе промокод снимается
  с корзины, ответ `409 PROMO_INVALIDATED` с актуальной корзиной.
- Тексты `message` — в `messages_ru.properties`, ключ = код ошибки.

## Хранение данных и миграции

- `V42__promo_codes.sql`: таблица `promo_codes` (code PK, kind, value, starts_at, ends_at, min_total,
  usage_limit, usage_count), `carts.promo_code` FK nullable, `orders.promo_code`, `orders.discount`.
- Миграция только добавляет столбцы — откат без потери данных.

## Decisions

- **Счётчик использований**: `UPDATE promo_codes SET usage_count = usage_count + 1 WHERE code = ? AND usage_count < usage_limit`
  внутри транзакции заказа; 0 обновлённых строк → `PROMO_INVALIDATED`. Без отдельной блокировки,
  гонка исключена условием в `WHERE`. Альтернатива `SELECT ... FOR UPDATE` отвергнута: лишняя блокировка на горячем коде акции.
- **Идемпотентность** `PUT`: операция — установка значения, повтор даёт тот же результат, ключ идемпотентности не нужен.
- **Процентная скидка** округляется вниз до копейки.

## Обеспечение НФТ

- p95 ≤ 200 мс: промокод читается по первичному ключу, кэш не нужен; проверка — k6 на 50 RPS.
- Перебор: rate limiter (bucket4j) на неудачные попытки, 10/мин на покупателя → `429`. См. локальную спеку `api/rate-limiting`.
- Аудит: событие `promo.applied` / `promo.rejected` в общий audit-лог, retention 90 дней настроен в логгинге.

## Risks / Trade-offs

- Покупатель, применивший код в корзине, может получить `409` при оформлении, если лимит выбрали другие → это ожидаемое поведение по спеке `integration/promo-apply`.

## Вопросы к upstream

- ~~[СА] Нужно ли тело `PromoError` у `429`?~~ Нет: без тела, с `Retry-After`; system.md обновлён (2026-10-09).
