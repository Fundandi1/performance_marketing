# marketplace/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.db.models import Q, Count, Avg
from campaigns.models import Campaign, CampaignBid
from accounts.models import Agency

class MarketplaceView(LoginRequiredMixin, ListView):
    model = Campaign
    template_name = 'marketplace/list.html'
    context_object_name = 'campaigns'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Campaign.objects.filter(
            status__in=['OPEN', 'PUBLISHED'],
            bidding_deadline__gt=timezone.now()
        ).annotate(
            bid_count=Count('bids')
        ).order_by('-is_featured', '-created_at')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(brand__user__company_name__icontains=search)
            )
        
        # Platform filter
        platform = self.request.GET.get('platform')
        if platform:
            queryset = queryset.filter(platforms__contains=[platform])
        
        # Budget filter
        budget_range = self.request.GET.get('budget')
        if budget_range:
            try:
                min_budget, max_budget = map(int, budget_range.split('-'))
                queryset = queryset.filter(
                    budget_min__gte=min_budget,
                    budget_max__lte=max_budget
                )
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['platforms'] = [
            ('META', 'Meta (Facebook & Instagram)'),
            ('TIKTOK', 'TikTok'),
            ('GOOGLE', 'Google Ads'),
            ('LINKEDIN', 'LinkedIn'),
        ]
        
        context['budget_ranges'] = [
            ('0-10000', '0 - 10,000 DKK'),
            ('10000-50000', '10,000 - 50,000 DKK'),
            ('50000-100000', '50,000 - 100,000 DKK'),
            ('100000-500000', '100,000+ DKK'),
        ]
        
        # Get current filter values
        context['current_search'] = self.request.GET.get('search', '')
        context['current_platform'] = self.request.GET.get('platform', '')
        context['current_budget'] = self.request.GET.get('budget', '')
        
        # Add marketplace stats
        context['total_campaigns'] = Campaign.objects.filter(status='OPEN').count()
        context['total_agencies'] = Agency.objects.count()
        context['avg_competitiveness'] = CampaignBid.objects.aggregate(
            avg_score=Avg('competitiveness_score')
        )['avg_score'] or 0
        
        return context

class CampaignDetailView(LoginRequiredMixin, DetailView):
    model = Campaign
    template_name = 'marketplace/detail.html'
    context_object_name = 'campaign'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        
        # Get bids statistics
        bids = CampaignBid.objects.filter(campaign=campaign)
        context['bid_count'] = bids.count()
        
        if bids.exists():
            context['best_roas'] = bids.filter(guaranteed_roas__isnull=False).order_by('-guaranteed_roas').first()
            context['best_cpa'] = bids.filter(guaranteed_cpa__isnull=False).order_by('guaranteed_cpa').first()
            context['lowest_fee'] = bids.order_by('proposed_fee_percentage').first()
            context['avg_competitiveness'] = bids.aggregate(Avg('competitiveness_score'))['competitiveness_score__avg']
        
        # Time remaining
        if campaign.bidding_deadline > timezone.now():
            context['time_remaining'] = campaign.bidding_deadline - timezone.now()
        
        # Check if current user has bid
        if self.request.user.user_type == 'AGENCY':
            agency = get_object_or_404(Agency, user=self.request.user)
            context['user_bid'] = bids.filter(agency=agency).first()
        
        return context