# campaigns/models.py
from django.db import models
from django.utils import timezone
from accounts.models import Brand, Agency

class Campaign(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('BIDDING', 'Open for Bidding'),
        ('SELECTED', 'Agency Selected'),
        ('ACTIVE', 'Campaign Running'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PLATFORM_CHOICES = [
        ('META', 'Meta (Facebook & Instagram)'),
        ('GOOGLE', 'Google Ads'),
        ('TIKTOK', 'TikTok'),
        ('LINKEDIN', 'LinkedIn'),
    ]
    
    # Basic campaign info
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=255)
    description = models.TextField()
    platforms = models.JSONField(default=list)
    
    # Budget and targets
    budget_min = models.DecimalField(max_digits=12, decimal_places=2)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2)
    target_roas = models.DecimalField(max_digits=5, decimal_places=2)
    target_cpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Timeline
    campaign_start = models.DateField()
    campaign_end = models.DateField()
    bidding_deadline = models.DateTimeField()
    
    # Agency selection
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    selected_agency = models.ForeignKey('accounts.Agency', on_delete=models.SET_NULL, null=True, blank=True)
    selected_bid = models.OneToOneField('CampaignBid', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Attribution tracking
    utm_campaign = models.CharField(max_length=100, unique=True, blank=True)
    tracking_pixel_installed = models.BooleanField(default=False)
    
    # Escrow and payments
    escrow_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.utm_campaign:
            # Generate unique UTM campaign identifier
            self.utm_campaign = f"agencymatch_{secrets.token_urlsafe(8).lower()}"
        super().save(*args, **kwargs)
    
    def generate_tracking_links(self, agency):
        """Generate UTM tracking links for the selected agency"""
        if not self.brand.shopify_domain:
            return {}
        
        base_url = f"https://{self.brand.shopify_domain.replace('.myshopify.com', '')}.com"
        
        links = {}
        for platform in self.platforms:
            utm_params = {
                'utm_campaign': self.utm_campaign,
                'utm_source': platform.lower(),
                'utm_medium': 'cpc',
                'utm_content': f'agency_{agency.id}',
                'utm_term': f'campaign_{self.id}'
            }
            
            utm_string = '&'.join([f"{k}={v}" for k, v in utm_params.items()])
            tracking_url = f"{base_url}?{utm_string}"
            
            links[platform] = {
                'url': tracking_url,
                'utm_params': utm_params,
                'instructions': self._get_platform_instructions(platform)
            }
        
        return links
    
    def _get_platform_instructions(self, platform):
        instructions = {
            'META': 'Use this URL as your Website URL in Facebook/Instagram ads',
            'GOOGLE': 'Use this URL as your Final URL in Google Ads',
            'TIKTOK': 'Use this URL as your Landing Page URL in TikTok ads',
            'LINKEDIN': 'Use this URL as your Destination URL in LinkedIn ads'
        }
        return instructions.get(platform, 'Use this URL in your ad campaigns')

class CampaignBid(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='bids')
    agency = models.ForeignKey('accounts.Agency', on_delete=models.CASCADE, related_name='bids')
    
    # Performance guarantees
    guaranteed_roas = models.DecimalField(max_digits=5, decimal_places=2)
    guaranteed_cpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Pricing
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Proposal details
    proposal_text = models.TextField()
    estimated_timeline = models.CharField(max_length=255)
    
    # Performance bonus structure
    bonus_threshold_roas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Scoring
    competitiveness_score = models.IntegerField(default=50)
    is_selected = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['campaign', 'agency']

# NEW: Shopify Integration Models
class ShopifyOrder(models.Model):
    """Orders from Shopify with attribution data"""
    
    # Shopify order data
    shopify_order_id = models.BigIntegerField(unique=True)
    order_number = models.CharField(max_length=50)
    
    # Brand and attribution
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='shopify_orders')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, null=True, blank=True, related_name='attributed_orders')
    agency = models.ForeignKey('accounts.Agency', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Order details
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='DKK')
    customer_email = models.EmailField()
    
    # Attribution data
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)
    utm_term = models.CharField(max_length=100, blank=True)
    
    # Attribution quality
    is_attributed = models.BooleanField(default=False)
    attribution_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0-100%
    attribution_method = models.CharField(max_length=50, default='UTM')  # UTM, REFERRER, MANUAL
    
    # Shopify data
    landing_site_ref = models.TextField(blank=True)
    referring_site = models.TextField(blank=True)
    source_name = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    order_created_at = models.DateTimeField()
    processed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order #{self.order_number} - {self.brand.shopify_domain}"

class CampaignPerformance(models.Model):
    """Daily performance metrics per campaign"""
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='daily_performance')
    date = models.DateField()
    
    # Spend data (reported by agency or API)
    total_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    meta_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    google_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tiktok_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Revenue from attributed Shopify orders
    attributed_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    attributed_orders = models.IntegerField(default=0)
    
    # Calculated metrics
    roas = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cpa = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Data source tracking
    spend_data_source = models.CharField(max_length=20, default='MANUAL')  # MANUAL, API, AGENCY_REPORT
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['campaign', 'date']
    
    def calculate_metrics(self):
        """Calculate ROAS and CPA based on current data"""
        if self.total_spend > 0:
            self.roas = self.attributed_revenue / self.total_spend
            self.cpa = self.total_spend / self.attributed_orders if self.attributed_orders > 0 else 0
        else:
            self.roas = 0
            self.cpa = 0
        self.save()

# NEW: Payment and Escrow Models
class EscrowPayment(models.Model):
    """Handle escrow payments between brands and agencies"""
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending Setup'),
        ('HELD', 'Funds in Escrow'),
        ('RELEASED', 'Released to Agency'),
        ('REFUNDED', 'Refunded to Brand'),
        ('DISPUTED', 'Under Dispute'),
    ]
    
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name='escrow')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    agency = models.ForeignKey('accounts.Agency', on_delete=models.CASCADE)
    
    # Payment amounts
    total_budget = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)  # From winning bid
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Performance thresholds
    target_roas = models.DecimalField(max_digits=5, decimal_places=2)
    minimum_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Payment status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    
    # Automatic release conditions
    auto_release_date = models.DateField(null=True, blank=True)  # Auto-release after campaign end
    performance_check_date = models.DateField(null=True, blank=True)  # When to check performance
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def check_release_conditions(self):
        """Check if payment should be released to agency"""
        from django.utils import timezone
        from django.db.models import Sum
        
        # Get campaign performance
        total_performance = self.campaign.daily_performance.aggregate(
            total_spend=Sum('total_spend'),
            total_revenue=Sum('attributed_revenue')
        )
        
        total_spend = total_performance['total_spend'] or 0
        total_revenue = total_performance['total_revenue'] or 0
        actual_roas = total_revenue / total_spend if total_spend > 0 else 0
        
        # Check conditions
        roas_met = actual_roas >= self.target_roas
        spend_met = total_spend >= self.minimum_spend
        time_passed = timezone.now().date() >= (self.auto_release_date or timezone.now().date())
        
        return {
            'should_release': roas_met and spend_met,
            'conditions': {
                'roas_met': roas_met,
                'spend_met': spend_met,
                'time_passed': time_passed,
            },
            'metrics': {
                'actual_roas': actual_roas,
                'target_roas': self.target_roas,
                'total_spend': total_spend,
                'total_revenue': total_revenue,
            }
        }

class PaymentRelease(models.Model):
    """Track individual payment releases"""
    
    RELEASE_TYPE_CHOICES = [
        ('FULL', 'Full Release'),
        ('PARTIAL', 'Partial Release'),
        ('BONUS', 'Performance Bonus'),
        ('SETUP', 'Setup Fee'),
    ]
    
    escrow = models.ForeignKey(EscrowPayment, on_delete=models.CASCADE, related_name='releases')
    release_type = models.CharField(max_length=20, choices=RELEASE_TYPE_CHOICES)
    
    # Amount details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Our 5% fee
    agency_payout = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Performance justification
    period_start = models.DateField()
    period_end = models.DateField()
    achieved_roas = models.DecimalField(max_digits=5, decimal_places=2)
    spend_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Processing
    stripe_transfer_id = models.CharField(max_length=255, blank=True)
    released_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.release_type} - {self.amount} DKK to {self.escrow.agency.user.company_name}"