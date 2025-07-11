from django.urls import path
from . import views

app_name = 'shopify_integration'

urlpatterns = [
    # OAuth flow
    path('connect/', views.connect_shopify_store, name='connect'),
    path('callback/', views.shopify_oauth_callback, name='callback'),
    
    # Webhooks
    path('webhooks/orders/', views.shopify_order_webhook, name='order_webhook'),
    
    # Attribution analytics
    path('analytics/<int:campaign_id>/', views.attribution_analytics, name='analytics'),
    path('spend/<int:campaign_id>/', views.manual_spend_entry, name='manual_spend'),
    
    # First-party tracking
    path('api/track/', views.track_conversion_api, name='track_conversion'),
]