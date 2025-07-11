# campaigns/management/commands/create_sample_data.py

import os
import django
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import Agency, Brand
from campaigns.models import Campaign, CampaignBid, PerformanceMetric
import random
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for the Performance Marketing Platform'
    
    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create sample brands
        brand_data = [
            {'username': 'luxuryjewelry', 'company': 'Luxury Jewelry Co', 'email': 'brand@luxury.dk', 'industry': 'Jewelry'},
            {'username': 'techgadgets', 'company': 'Tech Gadgets Inc', 'email': 'brand@tech.dk', 'industry': 'Technology'},
            {'username': 'fashionbrand', 'company': 'Fashion Forward', 'email': 'brand@fashion.dk', 'industry': 'Fashion'},
        ]
        
        brands = []
        for data in brand_data:
            if not User.objects.filter(username=data['username']).exists():
                user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password='testpass123',
                    first_name='Brand',
                    last_name='Owner',
                    user_type='BRAND',
                    company_name=data['company']
                )
                brand = Brand.objects.create(
                    user=user,
                    industry=data['industry'],
                    company_size='50-100',
                    annual_ad_spend=500000
                )
                brands.append(brand)
                self.stdout.write(f'Created brand: {data["company"]}')
        
        # Create sample agencies
        agency_data = [
            {'username': 'digitalagency1', 'company': 'Digital Masters Agency', 'email': 'agency@digital.dk'},
            {'username': 'performanceads', 'company': 'Performance Ads Pro', 'email': 'agency@performance.dk'},
            {'username': 'socialexperts', 'company': 'Social Media Experts', 'email': 'agency@social.dk'},
            {'username': 'metaspecialists', 'company': 'Meta Specialists', 'email': 'agency@meta.dk'},
        ]
        
        agencies = []
        for data in agency_data:
            if not User.objects.filter(username=data['username']).exists():
                user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password='testpass123',
                    first_name='Agency',
                    last_name='Owner',
                    user_type='AGENCY',
                    company_name=data['company']
                )
                agency = Agency.objects.create(
                    user=user,
                    specializations=['META', 'GOOGLE', 'TIKTOK'],
                    team_size=random.randint(5, 25),
                    years_experience=random.randint(2, 10),
                    avg_rating=random.uniform(4.0, 5.0),
                    total_campaigns=random.randint(10, 50),
                    success_rate=random.uniform(70, 95),
                    competitiveness_score=random.randint(60, 95)
                )
                agencies.append(agency)
                self.stdout.write(f'Created agency: {data["company"]}')
        
        # Create sample campaigns
        if brands and not Campaign.objects.exists():
            campaign_data = [
                {
                    'title': 'Luxury Jewelry Holiday Campaign',
                    'description': 'Premium holiday campaign targeting affluent customers for luxury jewelry collections. Focus on emotional storytelling and high-quality visuals.',
                    'platforms': ['META', 'GOOGLE'],
                    'budget_min': 75000,
                    'budget_max': 120000,
                    'target_roas': 3.5,
                    'target_cpa': 150,
                    'is_featured': True,
                },
                {
                    'title': 'Tech Gadgets Product Launch',
                    'description': 'Launch campaign for innovative tech gadgets targeting tech enthusiasts and early adopters. Emphasize product features and benefits.',
                    'platforms': ['META', 'TIKTOK', 'GOOGLE'],
                    'budget_min': 50000,
                    'budget_max': 80000,
                    'target_roas': 4.0,
                    'target_cpa': 100,
                    'is_featured': False,
                },
                {
                    'title': 'Fashion Summer Collection',
                    'description': 'Promote new summer fashion collection with vibrant visuals and lifestyle content. Target fashion-conscious millennials and Gen Z.',
                    'platforms': ['META', 'TIKTOK'],
                    'budget_min': 30000,
                    'budget_max': 60000,
                    'target_roas': 3.0,
                    'target_cpa': 80,
                    'is_featured': False,
                },
            ]
            
            campaigns = []
            for i, data in enumerate(campaign_data):
                campaign = Campaign.objects.create(
                    brand=brands[i % len(brands)],
                    title=data['title'],
                    description=data['description'],
                    platforms=data['platforms'],
                    budget_min=data['budget_min'],
                    budget_max=data['budget_max'],
                    target_roas=data['target_roas'],
                    target_cpa=data['target_cpa'],
                    campaign_start=timezone.now().date() + timedelta(days=7),
                    campaign_end=timezone.now().date() + timedelta(days=60),
                    bidding_deadline=timezone.now() + timedelta(days=5),
                    status='OPEN',
                    is_featured=data['is_featured']
                )
                campaigns.append(campaign)
                self.stdout.write(f'Created campaign: {data["title"]}')
            
            # Create sample bids
            if agencies:
                for campaign in campaigns:
                    # Create 2-4 bids per campaign
                    num_bids = random.randint(2, min(4, len(agencies)))
                    selected_agencies = random.sample(agencies, num_bids)
                    
                    for agency in selected_agencies:
                        bid = CampaignBid.objects.create(
                            campaign=campaign,
                            agency=agency,
                            proposed_fee_percentage=random.uniform(8, 18),
                            guaranteed_roas=campaign.target_roas + random.uniform(-0.5, 1.0),
                            guaranteed_cpa=campaign.target_cpa - random.uniform(0, 30),
                            proposal_text=f"We at {agency.user.company_name} have extensive experience with {campaign.brand.industry.lower()} campaigns. Our proven strategies will help you achieve and exceed your performance targets.",
                            estimated_timeline="2-3 weeks for setup and optimization",
                            competitiveness_score=random.randint(60, 95)
                        )
                        self.stdout.write(f'Created bid from {agency.user.company_name} for {campaign.title}')
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('You can now login with:')
        self.stdout.write('Brand accounts: luxuryjewelry / techgadgets / fashionbrand (password: testpass123)')
        self.stdout.write('Agency accounts: digitalagency1 / performanceads / socialexperts / metaspecialists (password: testpass123)')