# campaigns/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Campaign(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('OPEN', 'Open for Bids'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PLATFORM_CHOICES = [
        ('META', 'Meta (Facebook & Instagram)'),
        ('TIKTOK', 'TikTok'),
        ('GOOGLE', 'Google Ads'),
        ('LINKEDIN', 'LinkedIn'),
    ]
    
    # We'll create a simple foreign key to User for now, and fix the relationship later
    brand_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='brand_campaigns')
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    platforms = models.JSONField(default=list)  # List of platforms
    
    # Budget
    budget_min = models.DecimalField(max_digits=12, decimal_places=2)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='DKK')
    
    # Performance targets
    target_roas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    target_cpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target_ctr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Timing
    campaign_start = models.DateField()
    campaign_end = models.DateField()
    bidding_deadline = models.DateTimeField()
    
    # Awards
    selected_agency_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_campaigns')
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.brand_user.company_name}"
    
    @property
    def bid_count(self):
        return self.bids.count()
    
    @property
    def time_remaining(self):
        from django.utils import timezone
        if self.bidding_deadline > timezone.now():
            return self.bidding_deadline - timezone.now()
        return None

class CampaignBid(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='bids')
    agency_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    
    # Bid details
    proposed_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    guaranteed_roas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    guaranteed_cpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    guaranteed_ctr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Proposal
    proposal_text = models.TextField()
    estimated_timeline = models.CharField(max_length=100)
    
    # Performance bonus structure
    bonus_structure = models.JSONField(default=dict)
    
    # Status
    is_selected = models.BooleanField(default=False)
    competitiveness_score = models.PositiveIntegerField(default=0)  # 0-100
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('campaign', 'agency_user')
    
    def __str__(self):
        return f"{self.agency_user.company_name} bid for {self.campaign.title}"

class PerformanceMetric(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='metrics')
    platform = models.CharField(max_length=20, choices=Campaign.PLATFORM_CHOICES)
    date = models.DateField()
    
    # Core metrics
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Calculated metrics
    ctr = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cpa = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cpm = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    roas = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('campaign', 'platform', 'date')
    
    def save(self, *args, **kwargs):
        # Calculate derived metrics
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100
            self.cpm = (self.spend / self.impressions) * 1000
        
        if self.conversions > 0:
            self.cpa = self.spend / self.conversions
        
        if self.spend > 0:
            self.roas = self.revenue / self.spend
        
        super().save(*args, **kwargs)