from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from datetime import datetime, timedelta
import json

from .models import Campaign, CampaignPerformance, ShopifyOrder, EscrowPayment
from accounts.models import Brand, Agency

class EnhancedDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'campaigns/enhanced_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Date range for analytics
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        if user.user_type == 'BRAND':
            context.update(self.get_brand_context(user, start_date, end_date))
        elif user.user_type == 'AGENCY':
            context.update(self.get_agency_context(user, start_date, end_date))
        
        return context
    
    def get_brand_context(self, user, start_date, end_date):
        """Get dashboard context for brands"""
        brand = get_object_or_404(Brand, user=user)
        
        # Campaign overview
        campaigns = Campaign.objects.filter(brand=brand)
        active_campaigns = campaigns.filter(status='ACTIVE')
        
        # Performance metrics
        performance_data = CampaignPerformance.objects.filter(
            campaign__brand=brand,
            date__range=[start_date, end_date]
        ).aggregate(
            total_spend=Sum('total_spend'),
            total_revenue=Sum('attributed_revenue'),
            total_orders=Sum('attributed_orders')
        )
        
        total_spend = performance_data['total_spend'] or 0
        total_revenue = performance_data['total_revenue'] or 0
        total_orders = performance_data['total_orders'] or 0
        overall_roas = total_revenue / total_spend if total_spend > 0 else 0
        
        # Attribution analytics
        recent_orders = ShopifyOrder.objects.filter(
            brand=brand,
            order_created_at__gte=start_date
        )
        
        attribution_stats = {
            'total_orders': recent_orders.count(),
            'attributed_orders': recent_orders.filter(is_attributed=True).count(),
            'attribution_rate': 0,
            'avg_confidence': recent_orders.aggregate(Avg('attribution_confidence'))['attribution_confidence__avg'] or 0,
            'total_revenue': recent_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0,
            'attributed_revenue': recent_orders.filter(is_attributed=True).aggregate(Sum('total_price'))['total_price__sum'] or 0
        }
        
        if attribution_stats['total_orders'] > 0:
            attribution_stats['attribution_rate'] = (attribution_stats['attributed_orders'] / attribution_stats['total_orders']) * 100
        
        # Source breakdown
        source_breakdown = recent_orders.filter(is_attributed=True).values('utm_source').annotate(
            order_count=Count('id'),
            revenue=Sum('total_price')
        ).order_by('-revenue')[:5]
        
        # Campaign performance breakdown
        campaign_performance = []
        for campaign in active_campaigns:
            perf = CampaignPerformance.objects.filter(
                campaign=campaign,
                date__range=[start_date, end_date]
            ).aggregate(
                spend=Sum('total_spend'),
                revenue=Sum('attributed_revenue'),
                orders=Sum('attributed_orders')
            )
            
            spend = perf['spend'] or 0
            revenue = perf['revenue'] or 0
            current_roas = revenue / spend if spend > 0 else 0
            
            campaign_performance.append({
                'campaign': campaign,
                'spend': spend,
                'revenue': revenue,
                'orders': perf['orders'] or 0,
                'current_roas': current_roas,
                'target_roas': campaign.target_roas,
                'is_meeting_targets': current_roas >= campaign.target_roas if spend > 0 else None,
                'agency': campaign.selected_agency,
                'utm_campaign': campaign.utm_campaign
            })
        
        # Payment overview
        escrows = EscrowPayment.objects.filter(brand=brand)
        payment_overview = {
            'total_escrowed': escrows.filter(status='HELD').aggregate(Sum('total_budget'))['total_budget__sum'] or 0,
            'total_released': escrows.filter(status='RELEASED').aggregate(Sum('total_budget'))['total_budget__sum'] or 0,
            'pending_campaigns': escrows.filter(status='HELD').count()
        }
        
        return {
            'user_type': 'brand',
            'brand': brand,
            'campaigns': campaigns.order_by('-created_at')[:5],
            'active_campaigns': active_campaigns,
            'total_spend': total_spend,
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'overall_roas': overall_roas,
            'attribution_stats': attribution_stats,
            'source_breakdown': source_breakdown,
            'campaign_performance': campaign_performance,
            'payment_overview': payment_overview,
            'recent_orders': recent_orders.order_by('-order_created_at')[:10],
            'shopify_connected': brand.shopify_connected,
        }
    
    def get_agency_context(self, user, start_date, end_date):
        """Get dashboard context for agencies"""
        agency = get_object_or_404(Agency, user=user)
        
        # Campaign overview
        active_campaigns = Campaign.objects.filter(selected_agency=agency, status='ACTIVE')
        won_campaigns = Campaign.objects.filter(selected_agency=agency).exclude(status__in=['DRAFT', 'BIDDING'])
        
        # Performance metrics
        performance_data = CampaignPerformance.objects.filter(
            campaign__selected_agency=agency,
            date__range=[start_date, end_date]
        ).aggregate(
            total_spend=Sum('total_spend'),
            total_revenue=Sum('attributed_revenue'),
            total_orders=Sum('attributed_orders')
        )
        
        total_spend = performance_data['total_spend'] or 0
        total_revenue = performance_data['total_revenue'] or 0
        overall_roas = total_revenue / total_spend if total_spend > 0 else 0
        
        # Earnings overview
        escrows = EscrowPayment.objects.filter(agency=agency)
        earnings_data = {
            'total_earned': 0,  # From PaymentRelease model
            'pending_earnings': 0,
            'setup_fees_earned': 0
        }
        
        for escrow in escrows:
            if escrow.status == 'HELD':
                # Calculate potential earnings
                potential = total_spend * (escrow.commission_rate / 100)
                earnings_data['pending_earnings'] += potential
            elif escrow.status == 'RELEASED':
                released_amount = escrow.total_budget * (escrow.commission_rate / 100)
                earnings_data['total_earned'] += released_amount
        
        # Campaign performance tracking
        campaign_performance = []
        for campaign in active_campaigns:
            perf = CampaignPerformance.objects.filter(
                campaign=campaign,
                date__range=[start_date, end_date]
            ).aggregate(
                spend=Sum('total_spend'),
                revenue=Sum('attributed_revenue'),
                orders=Sum('attributed_orders')
            )
            
            spend = perf['spend'] or 0
            revenue = perf['revenue'] or 0
            current_roas = revenue / spend if spend > 0 else 0
            
            # Calculate potential earnings
            escrow = getattr(campaign, 'escrow', None)
            potential_commission = spend * (escrow.commission_rate / 100) if escrow else 0
            
            campaign_performance.append({
                'campaign': campaign,
                'spend': spend,
                'revenue': revenue,
                'orders': perf['orders'] or 0,
                'current_roas': current_roas,
                'target_roas': campaign.target_roas,
                'guaranteed_roas': campaign.selected_bid.guaranteed_roas if campaign.selected_bid else 0,
                'is_meeting_targets': current_roas >= campaign.target_roas if spend > 0 else None,
                'potential_commission': potential_commission,
                'tracking_links': campaign.generate_tracking_links(agency) if spend == 0 else None
            })
        
        # Available opportunities
        available_campaigns = Campaign.objects.filter(
            status='BIDDING',
            bidding_deadline__gt=timezone.now()
        ).exclude(
            bids__agency=agency  # Exclude campaigns already bid on
        ).order_by('-created_at')[:5]
        
        # Recent bids
        from .models import CampaignBid
        recent_bids = CampaignBid.objects.filter(agency=agency).order_by('-created_at')[:5]
        
        return {
            'user_type': 'agency',
            'agency': agency,
            'active_campaigns': active_campaigns,
            'won_campaigns': won_campaigns,
            'available_campaigns': available_campaigns,
            'recent_bids': recent_bids,
            'total_spend': total_spend,
            'total_revenue': total_revenue,
            'overall_roas': overall_roas,
            'campaign_performance': campaign_performance,
            'earnings_data': earnings_data,
            'stripe_connected': hasattr(agency, 'stripe_account_id') and agency.stripe_account_id,
        }

@login_required
def campaign_analytics_api(request, campaign_id):
    """API endpoint for detailed campaign analytics"""
    
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    # Check permissions
    if request.user.user_type == 'BRAND':
        if campaign.brand.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
    elif request.user.user_type == 'AGENCY':
        if campaign.selected_agency.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Performance over time
    daily_performance = CampaignPerformance.objects.filter(
        campaign=campaign,
        date__range=[start_date, end_date]
    ).order_by('date')
    
    performance_chart = {
        'dates': [],
        'spend': [],
        'revenue': [],
        'roas': [],
        'orders': []
    }
    
    cumulative_spend = 0
    cumulative_revenue = 0
    
    for perf in daily_performance:
        cumulative_spend += float(perf.total_spend)
        cumulative_revenue += float(perf.attributed_revenue)
        cumulative_roas = cumulative_revenue / cumulative_spend if cumulative_spend > 0 else 0
        
        performance_chart['dates'].append(perf.date.strftime('%Y-%m-%d'))
        performance_chart['spend'].append(cumulative_spend)
        performance_chart['revenue'].append(cumulative_revenue)
        performance_chart['roas'].append(cumulative_roas)
        performance_chart['orders'].append(perf.attributed_orders)
    
    # Attribution breakdown
    orders = ShopifyOrder.objects.filter(
        campaign=campaign,
        order_created_at__gte=start_date
    )
    
    attribution_breakdown = {
        'by_source': list(orders.values('utm_source').annotate(
            count=Count('id'),
            revenue=Sum('total_price')
        ).order_by('-revenue')),
        'by_confidence': {
            'high': orders.filter(attribution_confidence__gte=80).count(),
            'medium': orders.filter(attribution_confidence__gte=50, attribution_confidence__lt=80).count(),
            'low': orders.filter(attribution_confidence__lt=50).count()
        },
        'total_orders': orders.count(),
        'attributed_orders': orders.filter(is_attributed=True).count()
    }
    
    # Recent order details
    recent_orders = orders.order_by('-order_created_at')[:20].values(
        'order_number', 'total_price', 'utm_source', 'utm_campaign',
        'is_attributed', 'attribution_confidence', 'order_created_at'
    )
    
    return JsonResponse({
        'campaign': {
            'id': campaign.id,
            'title': campaign.title,
            'status': campaign.status,
            'utm_campaign': campaign.utm_campaign
        },
        'performance_chart': performance_chart,
        'attribution_breakdown': attribution_breakdown,
        'recent_orders': list(recent_orders),
        'target_roas': float(campaign.target_roas),
        'current_roas': cumulative_roas if 'cumulative_roas' in locals() else 0
    })

@login_required
def shopify_connection_status(request):
    """Check Shopify connection status and provide setup instructions"""
    
    if request.user.user_type != 'BRAND':
        return JsonResponse({'error': 'Only brands can connect Shopify'}, status=403)
    
    brand = get_object_or_404(Brand, user=request.user)
    
    return JsonResponse({
        'connected': brand.shopify_connected,
        'domain': brand.shopify_domain or '',
        'orders_tracked': ShopifyOrder.objects.filter(brand=brand).count(),
        'setup_instructions': {
            'step1': 'Connect your Shopify store using OAuth',
            'step2': 'We automatically set up order tracking webhooks',
            'step3': 'Start campaigns and track attribution in real-time'
        }
    })

# Real-time notifications system
from django.contrib.sessions.models import Session

@login_required
def dashboard_notifications(request):
    """Get real-time notifications for dashboard"""
    
    notifications = []
    
    if request.user.user_type == 'BRAND':
        brand = get_object_or_404(Brand, user=request.user)
        
        # Check for low attribution rates
        recent_orders = ShopifyOrder.objects.filter(
            brand=brand,
            order_created_at__gte=timezone.now() - timedelta(days=7)
        )
        
        if recent_orders.exists():
            attribution_rate = recent_orders.filter(is_attributed=True).count() / recent_orders.count()
            
            if attribution_rate < 0.6:  # Less than 60% attribution
                notifications.append({
                    'type': 'warning',
                    'title': 'Low Attribution Rate',
                    'message': f'Only {attribution_rate*100:.1f}% of recent orders are attributed to campaigns',
                    'action': 'Review tracking setup',
                    'url': '/shopify/analytics/'
                })
        
        # Check for campaigns needing payment release
        ready_for_release = []
        escrows = EscrowPayment.objects.filter(brand=brand, status='HELD')
        
        for escrow in escrows:
            release_check = escrow.check_release_conditions()
            if release_check['should_release']:
                ready_for_release.append(escrow.campaign.title)
        
        if ready_for_release:
            notifications.append({
                'type': 'success',
                'title': 'Payments Ready for Release',
                'message': f'{len(ready_for_release)} campaigns have met performance targets',
                'action': 'Release payments',
                'url': '/payments/dashboard/'
            })
    
    elif request.user.user_type == 'AGENCY':
        agency = get_object_or_404(Agency, user=request.user)
        
        # Check for new campaign opportunities
        new_campaigns = Campaign.objects.filter(
            status='BIDDING',
            created_at__gte=timezone.now() - timedelta(hours=24),
            bidding_deadline__gt=timezone.now()
        ).exclude(bids__agency=agency).count()
        
        if new_campaigns > 0:
            notifications.append({
                'type': 'info',
                'title': 'New Opportunities',
                'message': f'{new_campaigns} new campaigns available for bidding',
                'action': 'View campaigns',
                'url': '/marketplace/'
            })
        
        # Check Stripe onboarding
        if not hasattr(agency, 'stripe_account_id') or not agency.stripe_account_id:
            notifications.append({
                'type': 'warning',
                'title': 'Payment Setup Required',
                'message': 'Complete Stripe onboarding to receive payments',
                'action': 'Set up payments',
                'url': '/payments/onboarding/'
            })
    
    return JsonResponse({'notifications': notifications})