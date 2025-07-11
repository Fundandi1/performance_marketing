from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('setup/<int:campaign_id>/', views.setup_campaign_payment, name='setup_escrow'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('release/<int:campaign_id>/', views.check_payment_release, name='check_release'),
    path('onboarding/', views.agency_onboarding, name='agency_onboarding'),
    path('dashboard/', views.payment_dashboard, name='dashboard'),
]