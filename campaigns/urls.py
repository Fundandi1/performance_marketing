# campaigns/urls.py

from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('campaigns/', views.CampaignListView.as_view(), name='list'),
    path('campaigns/create/', views.CampaignCreateView.as_view(), name='create'),
    path('campaigns/<int:pk>/', views.CampaignDetailView.as_view(), name='detail'),
    path('campaigns/<int:pk>/bid/', views.CreateBidView.as_view(), name='bid'),
]