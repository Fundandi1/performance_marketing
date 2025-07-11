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
    path('dashboard/enhanced/', EnhancedDashboardView.as_view(), name='enhanced_dashboard'),
    path('api/analytics/<int:campaign_id>/', campaign_analytics_api, name='campaign_analytics_api'),
    path('api/shopify/status/', shopify_connection_status, name='shopify_status'),
    path('api/notifications/', dashboard_notifications, name='dashboard_notifications'),
]