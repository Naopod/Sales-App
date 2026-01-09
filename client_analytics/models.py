from django.db import models
from django.utils import timezone


class Dataset(models.Model):
    """Model representing a dataset (uploaded or stored demo)"""
    
    SOURCE_TYPE_CHOICES = [
        ('upload', 'Upload'),
        ('stored', 'Stored'),
    ]
    
    name = models.CharField(max_length=255, help_text="Dataset name")
    source_type = models.CharField(
        max_length=10,
        choices=SOURCE_TYPE_CHOICES,
        default='upload',
        help_text="Source type: upload or stored demo"
    )
    file = models.FileField(
        upload_to='datasets/',
        blank=True,
        null=True,
        help_text="Uploaded file (for upload type)"
    )
    stored_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stored dataset key (for stored type)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Dataset"
        verbose_name_plural = "Datasets"
    
    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"
    
    def get_file_path(self):
        """Return the full path to the file"""
        if self.source_type == 'upload' and self.file:
            return self.file.path
        elif self.source_type == 'stored' and self.stored_key:
            import os
            from django.conf import settings
            demo_path = os.path.join(
                settings.BASE_DIR,
                'client_analytics',
                'demo_data',
                self.stored_key
            )
            return demo_path
        return None
