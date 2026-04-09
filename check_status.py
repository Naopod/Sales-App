import django, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'analytics_portal.settings')
django.setup()
from client_analytics.models import Dataset

if len(sys.argv) > 1 and sys.argv[1] == 'reset':
    pk = int(sys.argv[2]) if len(sys.argv) > 2 else 35
    Dataset.objects.filter(pk=pk).update(processing_status='error')
    print(f"Dataset {pk} reset to 'error'")
else:
    for d in Dataset.objects.all():
        exists = os.path.exists(d.get_file_path()) if d.get_file_path() else False
        print(f"pk={d.pk} status={d.processing_status} file={d.file.name} exists={exists}")
