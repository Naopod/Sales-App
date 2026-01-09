from django.urls import path
from . import views

app_name = 'client_analytics'

urlpatterns = [
    path('', views.home, name='home'),
    path('workflow/', views.workflow, name='workflow'),
    path('dataset/<int:pk>/', views.dataset_overview, name='dataset_overview'),
    path('dataset/<int:pk>/stats/', views.stats, name='stats'),
    path('dataset/<int:pk>/modeling/', views.modeling, name='modeling'),
    path('dataset/<int:pk>/clustering/', views.clustering, name='clustering'),
    path('dataset/<int:pk>/clustering/export/', views.clustering_export, name='clustering_export'),
]
