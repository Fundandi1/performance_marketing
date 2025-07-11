# payments/views.py

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

class PaymentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add payment dashboard data here
        return context

class PaymentMethodsView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/methods.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add payment methods data here
        return context

class PaymentHistoryView(LoginRequiredMixin, TemplateView):
    template_name = 'payments/history.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add payment history data here
        return context