import os
import sys
import socket
import time
import subprocess

def wait_for_postgres():
    host = os.environ.get('POSTGRES_HOST', 'db')
    port = int(os.environ.get('POSTGRES_PORT', '5432'))
    print('Waiting for PostgreSQL...', flush=True)
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            print('PostgreSQL is ready!', flush=True)
            break
        except (socket.error, ConnectionRefusedError):
            time.sleep(1)

def run(cmd):
    print(f'Running: {cmd}', flush=True)
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f'Command failed with return code {result.returncode}', flush=True)
    return result.returncode

def main():
    wait_for_postgres()
    run('python manage.py makemigrations api --noinput')
    run('python manage.py migrate --noinput')
    print('Queueing data ingestion task...', flush=True)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'credit_approval.settings')
    import django
    django.setup()
    from api.tasks import ingest_all_data
    ingest_all_data.delay()
    print('Data ingestion task queued!', flush=True)
    if len(sys.argv) > 1:
        cmd = ' '.join(sys.argv[1:])
        print(f'Starting: {cmd}', flush=True)
        os.execvp(sys.argv[1], sys.argv[1:])
    else:
        print('Starting gunicorn...', flush=True)
        os.execvp('gunicorn', ['gunicorn', 'credit_approval.wsgi:application', '--bind', '0.0.0.0:8000'])
if __name__ == '__main__':
    main()