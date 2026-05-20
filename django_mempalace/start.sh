#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "Running Django migrations..."
python manage.py migrate --no-input

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Starting Gunicorn server..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 120
