# performance/urls.py

from django.urls import path
from . import views

app_name = 'performance'

urlpatterns = [
    path('', views.PerformanceDashboardView.as_view(), name='dashboard'),
    path('campaign/<int:campaign_id>/', views.CampaignPerformanceView.as_view(), name='campaign_detail'),
]