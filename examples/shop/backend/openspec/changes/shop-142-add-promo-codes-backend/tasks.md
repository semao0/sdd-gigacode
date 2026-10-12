# Tasks

## 1. Данные

- [x] 1.1 Миграция `V42__promo_codes.sql`: `promo_codes`, `carts.promo_code`, `orders.promo_code`, `orders.discount`
- [x] 1.2 Сущность `PromoCode`, репозиторий + тест поиска по нормализованному коду (covers: checkout/promo-codes/Успешное применение)

## 2. Применение промокода

- [x] 2.1 `PromoValidator`: существование, срок, лимит, минимальная сумма + unit-тесты на каждый отказ (covers: checkout/promo-codes/Неизвестный промокод, checkout/promo-codes/Истёкший промокод, checkout/promo-codes/Не выполнена минимальная сумма, checkout/promo-codes/Лимит использований исчерпан)
- [x] 2.2 `PUT /api/v1/cart/promo` + API-тест успешного применения (covers: checkout/promo-codes/Успешное применение)
- [ ] 2.3 Замена промокода + API-тест повторного `PUT` (covers: checkout/promo-codes/Замена промокода, integration/promo-apply/Повторный запрос применения)
- [ ] 2.4 `DELETE /api/v1/cart/promo` + API-тест (covers: checkout/promo-codes/Удаление промокода)

## 3. Расчёт итога

- [x] 3.1 `CartPricingService`: скидка percent/fixed, итог не меньше 0 + unit-тесты (covers: checkout/cart/Итог со скидкой промокода, checkout/cart/Скидка больше суммы корзины)
- [x] 3.2 Регрессионные тесты итога (covers: checkout/cart/Итог без скидки, checkout/cart/Пустая корзина)

## 4. Оформление заказа

- [ ] 4.1 Повторная проверка и атомарный инкремент счётчика в `OrderService.place()`, `409 PROMO_INVALIDATED` + API-тест (covers: integration/promo-apply/Промокод стал недействителен до оформления)
- [ ] 4.2 Тест: два параллельных заказа на последнее использование, оформляется только один (covers: integration/promo-apply/Промокод стал недействителен до оформления, checkout/promo-codes/Лимит использований исчерпан)

## 5. НФТ

- [ ] 5.1 Rate limiter на неудачные попытки, `429` с `Retry-After` + тест (локальная спека `api/rate-limiting`)
- [ ] 5.2 Аудит-события `promo.applied` / `promo.rejected`
- [ ] 5.3 k6: `PUT /cart/promo` p95 ≤ 200 мс при 50 RPS

## 6. Интеграция

- [ ] 6.1 Контрактный тест: `api/openapi/cart.yaml` и `orders.yaml` совпадают с контрактами 1.1.0 из store
- [ ] 6.2 Выкатка на stage, frontend переключает e2e с моков на stage
