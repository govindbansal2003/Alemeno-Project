#!/bin/bash

set -e

echo "Waiting for PostgreSQL..."
while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('db', 5432))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready!"

echo "Running migrations..."
python manage.py makemigrations api --noinput
python manage.py migrate --noinput

echo "Ingesting data using background worker..."
python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'credit_approval.settings')
django.setup()
from api.tasks import ingest_all_data
ingest_all_data.delay()
print('Data ingestion task queued!')
"

echo "Starting server..."
exec "$@"
