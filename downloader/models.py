from django.db import models
from django.contrib.auth.models import User

class Download(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    title = models.CharField(max_length=255)
    thumbnail_url = models.URLField(max_length=500, null=True, blank=True)
    video_url = models.URLField(max_length=500)
    format_selected = models.CharField(max_length=50, default='Best MP4')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
