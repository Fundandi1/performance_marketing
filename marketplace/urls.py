# marketplace/urls.py

from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    path('', views.MarketplaceView.as_view(), name='list'),
    path('campaign/<int:pk>/', views.CampaignDetailView.as_view(), name='detail'),
]