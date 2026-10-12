# Design (frontend)

## Upstream

`shop/shop-142-add-promo-codes` @ `a1b2c3d` (system.md смержен 2026-10-07, DoR).

Реализует frontend:
- `checkout/promo-codes/Успешное применение`
- `checkout/promo-codes/Неизвестный промокод`
- `checkout/promo-codes/Истёкший промокод`
- `checkout/promo-codes/Не выполнена минимальная сумма`
- `checkout/promo-codes/Замена промокода`
- `checkout/promo-codes/Удаление промокода`
- `checkout/promo-codes/Лимит использований исчерпан`
- `checkout/cart/Пустая корзина` (регрессия)
- `integration/promo-apply/Промокод стал недействителен до оформления`
- `integration/promo-apply/Повторный запрос применения`

Не затрагивается (считает backend, frontend показывает `total`):
`checkout/cart/Итог без скидки`, `checkout/cart/Итог со скидкой промокода`, `checkout/cart/Скидка больше суммы корзины`.

## Context

Корзина — страница `/cart` (React, `features/cart`), состояние через RTK Query, `cartApi.getCart`.

## Экраны и состояния

Компонент `PromoCodeField` под списком товаров:

| Состояние | UI |
|---|---|
| пусто | поле + кнопка «Применить» (disabled, пока поле пустое) |
| loading | кнопка со спиннером и disabled — защита от двойного клика |
| success | плашка `AUTUMN10 −200 ₽` и крестик «Удалить»; строка «Скидка» в итогах |
| error `422` | текст `message` из ответа под полем, поле подсвечено |
| error `PROMO_MIN_TOTAL` | `message` + ссылка «Вернуться к покупкам» |
| `429` (без тела) | «Слишком много попыток, попробуйте через минуту» |
| `409` при оформлении | возврат на `/cart`, toast с `error.message`, корзина из тела ответа |

При пустой корзине поле промокода не показывается.

## Используемые контракты

- `PUT/DELETE /api/v1/cart/promo` — `contracts/cart.openapi.yaml` 1.1.0, `POST /api/v1/orders` (`409`) —
  `contracts/orders.openapi.yaml` 1.1.0 из store.
- Типы генерируются `openapi-typescript` из контракта store, не из backend.
- До выкатки backend — моки MSW `mocks/promo.ts` по примерам из контракта (по одному на каждый код ошибки).

## Decisions

- Тексты ошибок не дублируем на frontend: показываем `message` из ответа (решение СА в system.md).
- Фича-флаг `promo_codes` (Unleash), без флага поле не рендерится.

## Аналитика

`promo_apply_click`, `promo_applied {code}`, `promo_rejected {code, reason}`, `promo_removed`.

## Доступность

Ошибка связана с полем через `aria-describedby`, объявляется `aria-live="polite"`.

## Risks / Trade-offs

- Если backend выкатится позже, frontend ждёт за флагом — моки позволяют закончить и протестировать UI заранее.

## Вопросы к upstream

—
