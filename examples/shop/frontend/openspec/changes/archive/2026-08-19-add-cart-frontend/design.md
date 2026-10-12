# Design (frontend)

## Upstream

`shop/add-cart` @ `9f8e7d6`. Реализует `checkout/cart/Товар в наличии`, `checkout/cart/Товара нет в наличии`,
`checkout/cart/Пустая корзина`. Не затрагивается: `checkout/cart/Итог без скидки` (итог считает backend).

## Context

Новая страница `/cart` (React, `features/cart`).

## Экраны и состояния

loading — скелетон; empty — «Корзина пуста», оформление недоступно; success — список позиций и итог;
error `OUT_OF_STOCK` — `message` из ответа рядом с кнопкой «В корзину».

## Используемые контракты

`contracts/cart.openapi.yaml` 1.0.0 из store, типы через `openapi-typescript`.

## Decisions

Состояние корзины — RTK Query.

## Аналитика

`cart_add`, `cart_view`.

## Доступность

Счётчик корзины в шапке объявляется `aria-live`.

## Risks / Trade-offs

Нет.

## Вопросы к upstream

Нет.
