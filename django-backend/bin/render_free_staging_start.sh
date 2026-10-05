#!/bin/sh
set -eu

python manage.py collectstatic --noinput
python manage.py migrate --noinput

CELERY_PID=""
GUNICORN_PID=""

shutdown() {
  if [ -n "$GUNICORN_PID" ]; then
    kill -TERM "$GUNICORN_PID" 2>/dev/null || true
  fi
  if [ -n "$CELERY_PID" ]; then
    kill -TERM "$CELERY_PID" 2>/dev/null || true
  fi
}

trap shutdown INT TERM

if [ "${START_CELERY_IN_WEB:-true}" = "true" ]; then
  celery -A config worker --loglevel="${CELERY_LOGLEVEL:-INFO}" --concurrency="${CELERY_WORKER_CONCURRENCY:-1}" &
  CELERY_PID="$!"
fi

gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile - &
GUNICORN_PID="$!"

wait "$GUNICORN_PID"
STATUS="$?"
shutdown
exit "$STATUS"
