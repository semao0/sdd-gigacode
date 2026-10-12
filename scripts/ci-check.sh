#!/usr/bin/env bash
# CI-проверка для store и репозиториев компонентов. Запуск из корня репозитория.
# В CI store должен быть склонирован и зарегистрирован, если на него есть references:
#   git clone "$STORE_REMOTE" ../store && openspec store register ../store
source "$(dirname "$0")/common.sh"
check_openspec
"$OPENSPEC" validate --all --strict
# Каждый implementation-change в компоненте обязан ссылаться на upstream или быть техническим.
shopt -s nullglob
fail=0
for meta in openspec/changes/*/.openspec.yaml; do
  [ "$(basename "$(dirname "$(dirname "$meta")")")" = "archive" ] && continue
  if grep -q '^schema: impl-' "$meta" && ! grep -q '^initiative:' "$meta"; then
    echo "ERROR: $meta: impl-change без initiative (ссылки на store)"; fail=1
  fi
done
exit $fail
