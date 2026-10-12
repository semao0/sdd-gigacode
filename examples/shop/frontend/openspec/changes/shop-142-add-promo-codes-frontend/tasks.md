# Tasks

## 1. Подготовка

- [x] 1.1 Типы из `contracts/cart.openapi.yaml` и `orders.openapi.yaml` (store) через `openapi-typescript`
- [x] 1.2 Моки MSW для `PUT/DELETE /cart/promo` и `409` на `/orders`, по моку на каждый код ошибки

## 2. Поле промокода

- [ ] 2.1 `PromoCodeField`: применение, loading с блокировкой кнопки + тесты (covers: checkout/promo-codes/Успешное применение, integration/promo-apply/Повторный запрос применения)
- [ ] 2.2 Ошибки `422` из `message` + тест на каждый код (covers: checkout/promo-codes/Неизвестный промокод, checkout/promo-codes/Истёкший промокод, checkout/promo-codes/Лимит использований исчерпан)
- [ ] 2.3 `PROMO_MIN_TOTAL` со ссылкой «Вернуться к покупкам» + тест (covers: checkout/promo-codes/Не выполнена минимальная сумма)
- [ ] 2.4 Замена и удаление промокода + тесты (covers: checkout/promo-codes/Замена промокода, checkout/promo-codes/Удаление промокода)
- [ ] 2.5 Скрыть поле при пустой корзине + тест (covers: checkout/cart/Пустая корзина)
- [ ] 2.6 Сообщение для `429` + тест

## 3. Оформление заказа

- [ ] 3.1 `409 PROMO_INVALIDATED`: возврат в корзину, toast, корзина из тела ответа + тест (covers: integration/promo-apply/Промокод стал недействителен до оформления)

## 4. Выкатка

- [ ] 4.1 Фича-флаг `promo_codes`
- [ ] 4.2 События аналитики, a11y-проверка (axe)

## 5. Интеграция

- [ ] 5.1 e2e (Playwright) против stage backend после его выкатки: применение, ошибка, оформление со скидкой (covers: checkout/promo-codes/Успешное применение, integration/promo-apply/Промокод стал недействителен до оформления)
