from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('download/', views.download_video, name='download'),
    path('signup/', views.signup, name='signup'),
    path('preview/', views.get_video_preview, name='preview'),
]
