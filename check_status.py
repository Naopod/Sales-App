import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'analytics_portal.settings')
django.setup()
from client_analytics.models import Dataset
d = Dataset.objects.get(pk=35)
print(f"status={d.processing_status}")
print(f"file={d.file.name}")
print(f"file_path={d.get_file_path()}")
import os as o
print(f"file_exists={o.path.exists(d.get_file_path()) if d.get_file_path() else False}")
