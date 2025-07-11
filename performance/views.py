# performance/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Avg, Sum, Count
from campaigns.models import Campaign, PerformanceMetric
from accounts.models import Brand, Agency

class PerformanceDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'performance/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.user_type == 'BRAND':
            brand = get_object_or_404(Brand, user=user)
            campaigns = Campaign.objects.filter(brand=brand)
            
            # Get performance metrics for the last 30 days
            end_date = timezone.now().date()
            start_date = end_date - timezone.timedelta(days=30)
            
            metrics = PerformanceMetric.objects.filter(
                campaign__in=campaigns,
                date__range=[start_date, end_date]
            )
            
            # Calculate aggregated metrics
            if metrics.exists():
                context['total_impressions'] = metrics.aggregate(Sum('impressions'))['impressions__sum']
                context['total_clicks'] = metrics.aggregate(Sum('clicks'))['clicks__sum']
                context['total_conversions'] = metrics.aggregate(Sum('conversions'))['conversions__sum']
                context['total_spend'] = metrics.aggregate(Sum('spend'))['spend__sum']
                context['total_revenue'] = metrics.aggregate(Sum('revenue'))['revenue__sum']
                context['avg_roas'] = metrics.aggregate(Avg('roas'))['roas__avg']
                context['avg_cpa'] = metrics.aggregate(Avg('cpa'))['cpa__avg']
                context['avg_ctr'] = metrics.aggregate(Avg('ctr'))['ctr__avg']
            else:
                context.update({
                    'total_impressions': 0, 'total_clicks': 0, 'total_conversions': 0,
                    'total_spend': 0, 'total_revenue': 0, 'avg_roas': 0,
                    'avg_cpa': 0, 'avg_ctr': 0
                })
            
            context['campaigns'] = campaigns[:10]
            
        elif user.user_type == 'AGENCY':
            agency = get_object_or_404(Agency, user=user)
            won_campaigns = Campaign.objects.filter(selected_agency=agency)
            
            # Get performance metrics for agency's campaigns
            end_date = timezone.now().date()
            start_date = end_date - timezone.timedelta(days=30)
            
            metrics = PerformanceMetric.objects.filter(
                campaign__in=won_campaigns,
                date__range=[start_date, end_date]
            )
            
            if metrics.exists():
                context['total_impressions'] = metrics.aggregate(Sum('impressions'))['impressions__sum']
                context['total_clicks'] = metrics.aggregate(Sum('clicks'))['clicks__sum']
                context['total_conversions'] = metrics.aggregate(Sum('conversions'))['conversions__sum']
                context['total_spend'] = metrics.aggregate(Sum('spend'))['spend__sum']
                context['total_revenue'] = metrics.aggregate(Sum('revenue'))['revenue__sum']
                context['avg_roas'] = metrics.aggregate(Avg('roas'))['roas__avg']
                context['avg_cpa'] = metrics.aggregate(Avg('cpa'))['cpa__avg']
                context['avg_ctr'] = metrics.aggregate(Avg('ctr'))['ctr__avg']
            else:
                context.update({
                    'total_impressions': 0, 'total_clicks': 0, 'total_conversions': 0,
                    'total_spend': 0, 'total_revenue': 0, 'avg_roas': 0,
                    'avg_cpa': 0, 'avg_ctr': 0
                })
            
            context['won_campaigns'] = won_campaigns[:10]
            context['agency'] = agency
        
        return context

class CampaignPerformanceView(LoginRequiredMixin, TemplateView):
    template_name = 'performance/campaign_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign_id = kwargs['campaign_id']
        campaign = get_object_or_404(Campaign, pk=campaign_id)
        
        # Check permissions
        user = self.request.user
        if user.user_type == 'BRAND':
            brand = get_object_or_404(Brand, user=user)
            if campaign.brand != brand:
                raise PermissionDenied("You don't have permission to view this campaign")
        elif user.user_type == 'AGENCY':
            agency = get_object_or_404(Agency, user=user)
            if campaign.selected_agency != agency:
                raise PermissionDenied("You don't have permission to view this campaign")
        
        # Get performance metrics
        metrics = PerformanceMetric.objects.filter(campaign=campaign).order_by('-date')
        
        context['campaign'] = campaign
        context['metrics'] = metrics[:30]  # Last 30 days
        
        # Calculate totals
        if metrics.exists():
            context['total_impressions'] = metrics.aggregate(Sum('impressions'))['impressions__sum']
            context['total_clicks'] = metrics.aggregate(Sum('clicks'))['clicks__sum']
            context['total_conversions'] = metrics.aggregate(Sum('conversions'))['conversions__sum']
            context['total_spend'] = metrics.aggregate(Sum('spend'))['spend__sum']
            context['total_revenue'] = metrics.aggregate(Sum('revenue'))['revenue__sum']
            context['avg_roas'] = metrics.aggregate(Avg('roas'))['roas__avg']
            context['avg_cpa'] = metrics.aggregate(Avg('cpa'))['cpa__avg']
            context['avg_ctr'] = metrics.aggregate(Avg('ctr'))['ctr__avg']
        
        return context