# payments/urls.py

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.PaymentDashboardView.as_view(), name='dashboard'),
    path('methods/', views.PaymentMethodsView.as_view(), name='methods'),
    path('history/', views.PaymentHistoryView.as_view(), name='history'),
]