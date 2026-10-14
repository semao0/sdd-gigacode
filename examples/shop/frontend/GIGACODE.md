# frontend: правила для агента

React 18, TypeScript, TanStack Query. Подробности — в `docs/`.

- Запросы к API — только в `src/api/*`, типы генерируются из контрактов store.
- Серверное состояние — через хуки `src/hooks/use*.ts` на TanStack Query; компоненты не
  вызывают `src/api` напрямую.
- Ошибки контракта показываются по коду ошибки, тексты — в `src/i18n/ru.ts`.
- Тесты — Vitest + Testing Library, рядом с файлом; API мокается через MSW по контракту.
  Имя теста содержит `<capability>/<scenario>`.
