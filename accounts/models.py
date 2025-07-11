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
    
    # Shopify Integration
    shopify_domain = models.CharField(max_length=255, unique=True, null=True, blank=True)
    shopify_access_token = models.TextField(blank=True)
    shopify_connected = models.BooleanField(default=False)
    
    # Platform fees and payments
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.company_name} - {self.shopify_domain or 'No Shopify'}"

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
    stripe_account_id = models.CharField(max_length=255, blank=True)
    stripe_onboarding_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.company_name} - {self.specializations}"
