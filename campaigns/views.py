# campaigns/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import models
from .models import Campaign, CampaignBid, PerformanceMetric
from .forms import CampaignForm, BidForm
from accounts.models import Brand, Agency

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'campaigns/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.user_type == 'BRAND':
            brand = get_object_or_404(Brand, user=user)
            context['campaigns'] = Campaign.objects.filter(brand=brand)[:5]
            context['total_campaigns'] = Campaign.objects.filter(brand=brand).count()
            context['active_campaigns'] = Campaign.objects.filter(brand=brand, status='IN_PROGRESS').count()
            
            # Calculate performance metrics
            recent_metrics = PerformanceMetric.objects.filter(
                campaign__brand=brand,
                date__gte=timezone.now() - timezone.timedelta(days=30)
            )
            
            if recent_metrics.exists():
                context['avg_roas'] = recent_metrics.aggregate(models.Avg('roas'))['roas__avg'] or 0
                context['avg_cpa'] = recent_metrics.aggregate(models.Avg('cpa'))['cpa__avg'] or 0
                context['total_spend'] = recent_metrics.aggregate(models.Sum('spend'))['spend__sum'] or 0
            else:
                context['avg_roas'] = 0
                context['avg_cpa'] = 0
                context['total_spend'] = 0
                
        elif user.user_type == 'AGENCY':
            agency = get_object_or_404(Agency, user=user)
            context['bids'] = CampaignBid.objects.filter(agency=agency)[:5]
            context['won_campaigns'] = Campaign.objects.filter(selected_agency=agency)[:5]
            context['total_bids'] = CampaignBid.objects.filter(agency=agency).count()
            context['won_campaigns_count'] = Campaign.objects.filter(selected_agency=agency).count()
            context['success_rate'] = agency.success_rate
            context['competitiveness_score'] = agency.competitiveness_score
        
        return context

class CampaignListView(LoginRequiredMixin, ListView):
    model = Campaign
    template_name = 'campaigns/list.html'
    context_object_name = 'campaigns'
    paginate_by = 10
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'BRAND':
            brand = get_object_or_404(Brand, user=user)
            return Campaign.objects.filter(brand=brand).order_by('-created_at')
        else:
            # Agencies see all open campaigns
            return Campaign.objects.filter(status='OPEN').order_by('-created_at')

class CampaignCreateView(LoginRequiredMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = 'campaigns/create.html'
    success_url = reverse_lazy('campaigns:list')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'BRAND':
            messages.error(request, 'Only brands can create campaigns.')
            return redirect('campaigns:list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        brand = get_object_or_404(Brand, user=self.request.user)
        form.instance.brand = brand
        messages.success(self.request, 'Campaign created successfully!')
        return super().form_valid(form)

class CampaignDetailView(LoginRequiredMixin, DetailView):
    model = Campaign
    template_name = 'campaigns/detail.html'
    context_object_name = 'campaign'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        
        # Get all bids for this campaign
        context['bids'] = CampaignBid.objects.filter(campaign=campaign).order_by('-competitiveness_score')
        
        # Check if current user has bid
        if self.request.user.user_type == 'AGENCY':
            agency = get_object_or_404(Agency, user=self.request.user)
            context['user_bid'] = CampaignBid.objects.filter(campaign=campaign, agency=agency).first()
        
        return context

class CreateBidView(LoginRequiredMixin, CreateView):
    model = CampaignBid
    form_class = BidForm
    template_name = 'campaigns/bid.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.user_type != 'AGENCY':
            messages.error(request, 'Only agencies can create bids.')
            return redirect('campaigns:list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campaign'] = get_object_or_404(Campaign, pk=self.kwargs['pk'])
        return context
    
    def form_valid(self, form):
        campaign = get_object_or_404(Campaign, pk=self.kwargs['pk'])
        agency = get_object_or_404(Agency, user=self.request.user)
        
        # Check if agency already has a bid
        existing_bid = CampaignBid.objects.filter(campaign=campaign, agency=agency).first()
        if existing_bid:
            messages.error(self.request, 'You have already submitted a bid for this campaign.')
            return redirect('campaigns:detail', pk=campaign.pk)
        
        form.instance.campaign = campaign
        form.instance.agency = agency
        
        # Calculate competitiveness score (simplified)
        score = self.calculate_competitiveness_score(form.instance, campaign)
        form.instance.competitiveness_score = score
        
        messages.success(self.request, 'Bid submitted successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('campaigns:detail', kwargs={'pk': self.kwargs['pk']})
    
    def calculate_competitiveness_score(self, bid, campaign):
        """Calculate a competitiveness score based on bid metrics"""
        score = 50  # Base score
        
        # ROAS factor
        if bid.guaranteed_roas and campaign.target_roas:
            if bid.guaranteed_roas >= campaign.target_roas:
                score += 20
            else:
                score -= 10
        
        # CPA factor  
        if bid.guaranteed_cpa and campaign.target_cpa:
            if bid.guaranteed_cpa <= campaign.target_cpa:
                score += 20
            else:
                score -= 10
        
        # Fee factor (lower is better)
        if bid.proposed_fee_percentage <= 10:
            score += 10
        elif bid.proposed_fee_percentage >= 20:
            score -= 10
        
        return max(0, min(100, score))