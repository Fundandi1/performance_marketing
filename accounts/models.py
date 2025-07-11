# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ('BRAND', 'Brand'),
        ('AGENCY', 'Agency'),
    ]
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    company_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Brand(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    industry = models.CharField(max_length=100)
    company_size = models.CharField(max_length=50)
    annual_ad_spend = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    target_demographics = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"{self.user.company_name} - {self.industry}"

class Agency(models.Model):
    SPECIALIZATION_CHOICES = [
        ('META', 'Meta Ads'),
        ('GOOGLE', 'Google Ads'),
        ('TIKTOK', 'TikTok Ads'),
        ('LINKEDIN', 'LinkedIn Ads'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    specializations = models.JSONField(default=list)
    team_size = models.IntegerField()
    years_experience = models.IntegerField()
    portfolio_url = models.URLField(blank=True)
    certifications = models.JSONField(default=list, blank=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_campaigns = models.IntegerField(default=0)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    competitiveness_score = models.IntegerField(default=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.company_name} - {self.specializations}"

# campaigns/models.py
from django.db import models
from django.utils import timezone
from accounts.models import Brand, Agency

class Campaign(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open for Bidding'),
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
    
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=255)
    description = models.TextField()
    platforms = models.JSONField(default=list)
    budget_min = models.DecimalField(max_digits=12, decimal_places=2)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2)
    target_roas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    target_cpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target_ctr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    campaign_start = models.DateField()
    campaign_end = models.DateField()
    bidding_deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    selected_agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    @property
    def is_bidding_open(self):
        return self.status == 'OPEN' and self.bidding_deadline > timezone.now()

class CampaignBid(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='bids')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='bids')
    proposed_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    guaranteed_roas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    guaranteed_cpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    guaranteed_ctr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    proposal_text = models.TextField()
    estimated_timeline = models.CharField(max_length=255)
    competitiveness_score = models.IntegerField(default=50)
    is_selected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['campaign', 'agency']
    
    def __str__(self):
        return f"{self.agency.user.company_name} - {self.campaign.title}"

class PerformanceMetric(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='metrics')
    date = models.DateField()
    spend = models.DecimalField(max_digits=12, decimal_places=2)
    revenue = models.DecimalField(max_digits=12, decimal_places=2)
    roas = models.DecimalField(max_digits=5, decimal_places=2)
    cpa = models.DecimalField(max_digits=10, decimal_places=2)
    ctr = models.DecimalField(max_digits=5, decimal_places=2)
    impressions = models.IntegerField()
    clicks = models.IntegerField()
    conversions = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['campaign', 'date']
    
    def __str__(self):
        return f"{self.campaign.title} - {self.date}"