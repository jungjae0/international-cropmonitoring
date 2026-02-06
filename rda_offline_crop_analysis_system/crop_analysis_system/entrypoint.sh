#!/bin/sh
set -e

cd /app/crop_analysis_system

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
