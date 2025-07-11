# campaigns/admin.py

from django.contrib import admin
from .models import Campaign, CampaignBid, PerformanceMetric

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'brand_user', 'status', 'budget_min', 'budget_max', 'bid_count', 'created_at')
    list_filter = ('status', 'platforms', 'is_featured', 'created_at')
    search_fields = ('title', 'description', 'brand_user__company_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    def bid_count(self, obj):
        return obj.bids.count()
    bid_count.short_description = 'Number of Bids'

@admin.register(CampaignBid)
class CampaignBidAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'agency_user', 'proposed_fee_percentage', 'guaranteed_roas', 'guaranteed_cpa', 'competitiveness_score', 'is_selected', 'created_at')
    list_filter = ('is_selected', 'competitiveness_score', 'created_at')
    search_fields = ('campaign__title', 'agency_user__company_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'platform', 'date', 'impressions', 'clicks', 'conversions', 'spend', 'roas', 'cpa')
    list_filter = ('platform', 'date', 'campaign__brand_user')
    search_fields = ('campaign__title', 'campaign__brand_user__company_name')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)