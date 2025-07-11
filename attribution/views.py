# shopify_integration/views.py - Webhook handling and attribution

import json
import hmac
import hashlib
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from accounts.models import Brand, Agency
from campaigns.models import Campaign, CampaignPerformance
from .models import ShopifyOrder

@csrf_exempt
@require_POST
def shopify_order_webhook(request):
    """Handle Shopify order/create webhook for attribution"""
    
    # Verify webhook authenticity
    if not verify_shopify_webhook(request):
        return HttpResponse('Unauthorized', status=401)
    
    try:
        order_data = json.loads(request.body)
        shop_domain = request.META.get('HTTP_X_SHOPIFY_SHOP_DOMAIN')
        
        # Find the brand
        brand = Brand.objects.get(shopify_domain=shop_domain)
        
        # Process attribution
        shopify_order = process_order_attribution(order_data, brand)
        
        # Update campaign performance if attributed
        if shopify_order.is_attributed and shopify_order.campaign:
            update_campaign_performance(shopify_order.campaign, shopify_order)
        
        return HttpResponse('OK')
        
    except Brand.DoesNotExist:
        # Log this but don't fail - store might not be connected yet
        return HttpResponse('Store not connected', status=404)
    except Exception as e:
        # Log error but return OK to prevent Shopify from retrying
        print(f"Webhook processing error: {e}")
        return HttpResponse('Processing error', status=500)

def verify_shopify_webhook(request):
    """Verify the webhook came from Shopify"""
    signature = request.META.get('HTTP_X_SHOPIFY_HMAC_SHA256')
    if not signature:
        return False
    
    webhook_secret = settings.SHOPIFY_WEBHOOK_SECRET
    computed_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        request.body,
        hashlib.sha256
    ).digest()
    
    return hmac.compare_digest(signature.encode('utf-8'), computed_signature)

def process_order_attribution(order_data, brand):
    """Main attribution logic for Shopify orders"""
    
    # Extract attribution data from multiple sources
    attribution_data = extract_attribution_data(order_data)
    
    # Find matching campaign
    campaign, agency = find_matching_campaign(attribution_data, brand)
    
    # Calculate attribution confidence
    confidence = calculate_attribution_confidence(attribution_data, campaign)
    
    # Create order record
    shopify_order = ShopifyOrder.objects.create(
        shopify_order_id=order_data['id'],
        order_number=order_data.get('order_number', str(order_data['id'])),
        brand=brand,
        campaign=campaign,
        agency=agency,
        
        # Order details
        total_price=float(order_data['total_price']),
        currency=order_data.get('currency', 'DKK'),
        customer_email=order_data.get('email', ''),
        
        # Attribution data
        utm_source=attribution_data.get('utm_source', ''),
        utm_medium=attribution_data.get('utm_medium', ''),
        utm_campaign=attribution_data.get('utm_campaign', ''),
        utm_content=attribution_data.get('utm_content', ''),
        utm_term=attribution_data.get('utm_term', ''),
        
        # Attribution quality
        is_attributed=bool(campaign),
        attribution_confidence=confidence,
        attribution_method=attribution_data.get('method', 'UTM'),
        
        # Shopify data
        landing_site_ref=order_data.get('landing_site_ref', ''),
        referring_site=order_data.get('referring_site', ''),
        source_name=order_data.get('source_name', ''),
        
        order_created_at=datetime.fromisoformat(order_data['created_at'].replace('Z', '+00:00'))
    )
    
    return shopify_order

def extract_attribution_data(order_data):
    """Extract UTM and attribution data from Shopify order"""
    attribution_data = {'method': 'UNKNOWN'}
    
    # Source 1: Landing site URL (most reliable)
    landing_site = order_data.get('landing_site_ref', '')
    if landing_site:
        utm_params = parse_utm_from_url(landing_site)
        if utm_params:
            attribution_data.update(utm_params)
            attribution_data['method'] = 'UTM'
            attribution_data['confidence_boost'] = 30
    
    # Source 2: Referring site analysis
    referring_site = order_data.get('referring_site', '')
    if referring_site and not attribution_data.get('utm_source'):
        source_guess = infer_source_from_referrer(referring_site)
        if source_guess:
            attribution_data['utm_source'] = source_guess
            attribution_data['method'] = 'REFERRER'
            attribution_data['confidence_boost'] = 15
    
    # Source 3: Shopify's source_name field
    source_name = order_data.get('source_name')
    if source_name and not attribution_data.get('utm_source'):
        attribution_data['utm_source'] = source_name.lower()
        attribution_data['method'] = 'SHOPIFY_SOURCE'
        attribution_data['confidence_boost'] = 10
    
    return attribution_data

def parse_utm_from_url(url):
    """Extract UTM parameters from URL"""
    if not url:
        return {}
    
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        utm_data = {}
        utm_keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
        
        for key in utm_keys:
            if key in params and params[key]:
                utm_data[key] = params[key][0]  # Take first value
        
        return utm_data
    except Exception:
        return {}

def infer_source_from_referrer(referrer):
    """Guess traffic source from referrer URL"""
    if not referrer:
        return None
    
    referrer = referrer.lower()
    
    source_mapping = {
        'facebook.com': 'facebook',
        'instagram.com': 'facebook',
        'google.com': 'google',
        'tiktok.com': 'tiktok',
        'linkedin.com': 'linkedin',
        't.co': 'twitter',
        'youtube.com': 'youtube',
    }
    
    for domain, source in source_mapping.items():
        if domain in referrer:
            return source
    
    return 'organic'

def find_matching_campaign(attribution_data, brand):
    """Find which campaign and agency should get credit"""
    
    utm_campaign = attribution_data.get('utm_campaign')
    if not utm_campaign:
        return None, None
    
    try:
        # Find active campaign with matching UTM
        campaign = Campaign.objects.get(
            utm_campaign=utm_campaign,
            brand=brand,
            status='ACTIVE'
        )
        return campaign, campaign.selected_agency
    except Campaign.DoesNotExist:
        return None, None

def calculate_attribution_confidence(attribution_data, campaign):
    """Calculate confidence score for attribution (0-100%)"""
    
    if not campaign:
        return 0
    
    confidence = 20  # Base confidence for any match
    
    # UTM campaign exact match (highest confidence)
    if attribution_data.get('utm_campaign') == campaign.utm_campaign:
        confidence += 40
    
    # Source matches campaign platforms
    utm_source = attribution_data.get('utm_source', '').lower()
    platform_mapping = {
        'facebook': 'META',
        'instagram': 'META', 
        'google': 'GOOGLE',
        'tiktok': 'TIKTOK',
        'linkedin': 'LINKEDIN'
    }
    
    mapped_platform = platform_mapping.get(utm_source)
    if mapped_platform and mapped_platform in campaign.platforms:
        confidence += 20
    
    # Medium indicates paid advertising
    utm_medium = attribution_data.get('utm_medium', '').lower()
    if utm_medium in ['cpc', 'paid', 'social', 'display']:
        confidence += 15
    
    # Bonus for clean UTM data
    utm_keys = ['utm_source', 'utm_medium', 'utm_campaign']
    complete_utm = all(attribution_data.get(key) for key in utm_keys)
    if complete_utm:
        confidence += 5
    
    # Apply method-specific confidence boost
    confidence += attribution_data.get('confidence_boost', 0)
    
    return min(100, max(0, confidence))

def update_campaign_performance(campaign, order):
    """Update campaign performance with new attributed order"""
    
    today = timezone.now().date()
    
    # Get or create today's performance record
    performance, created = CampaignPerformance.objects.get_or_create(
        campaign=campaign,
        date=today,
        defaults={
            'total_spend': 0,
            'attributed_revenue': 0,
            'attributed_orders': 0
        }
    )
    
    # Add this order's revenue
    performance.attributed_revenue += order.total_price
    performance.attributed_orders += 1
    
    # Recalculate metrics
    performance.calculate_metrics()
    
    return performance

# Enhanced Shopify OAuth and connection flow
def connect_shopify_store(request):
    """Initiate Shopify OAuth for store connection"""
    
    if request.method == 'POST':
        shop_domain = request.POST.get('shop_domain', '').strip()
        
        # Validate and normalize domain
        if not shop_domain:
            return JsonResponse({'error': 'Shop domain is required'}, status=400)
        
        # Add .myshopify.com if not present
        if not shop_domain.endswith('.myshopify.com'):
            shop_domain = f"{shop_domain}.myshopify.com"
        
        # Check if already connected
        brand = get_object_or_404(Brand, user=request.user)
        if brand.shopify_connected and brand.shopify_domain:
            return JsonResponse({'error': 'Store already connected'}, status=400)
        
        # Generate OAuth URL
        oauth_url = generate_shopify_oauth_url(shop_domain, request.user.id)
        
        return JsonResponse({'oauth_url': oauth_url})
    
    return render(request, 'shopify_integration/connect.html')

def generate_shopify_oauth_url(shop_domain, user_id):
    """Generate Shopify OAuth URL with proper scopes"""
    
    scopes = 'read_orders,read_products,write_script_tags'
    redirect_uri = f"{settings.SITE_URL}/shopify/callback/"
    
    oauth_url = (
        f"https://{shop_domain}/admin/oauth/authorize?"
        f"client_id={settings.SHOPIFY_API_KEY}&"
        f"scope={scopes}&"
        f"redirect_uri={redirect_uri}&"
        f"state={user_id}"
    )
    
    return oauth_url

@csrf_exempt
def shopify_oauth_callback(request):
    """Handle Shopify OAuth callback and setup webhooks"""
    
    code = request.GET.get('code')
    shop = request.GET.get('shop')
    state = request.GET.get('state')
    
    if not all([code, shop, state]):
        return HttpResponse('Invalid callback parameters', status=400)
    
    try:
        # Exchange code for access token
        access_token = exchange_oauth_code(shop, code)
        
        # Update brand with Shopify connection
        user = get_object_or_404(CustomUser, id=state)
        brand = get_object_or_404(Brand, user=user)
        
        brand.shopify_domain = shop
        brand.shopify_access_token = access_token
        brand.shopify_connected = True
        brand.save()
        
        # Set up webhooks
        setup_shopify_webhooks(brand)
        
        # Redirect to success page
        return redirect('campaigns:dashboard')
        
    except Exception as e:
        return HttpResponse(f'Connection failed: {e}', status=500)

def exchange_oauth_code(shop, code):
    """Exchange OAuth code for access token"""
    import requests
    
    url = f"https://{shop}/admin/oauth/access_token"
    data = {
        'client_id': settings.SHOPIFY_API_KEY,
        'client_secret': settings.SHOPIFY_API_SECRET,
        'code': code,
    }
    
    response = requests.post(url, data=data)
    response.raise_for_status()
    
    return response.json()['access_token']

def setup_shopify_webhooks(brand):
    """Set up order webhooks for attribution tracking"""
    import requests
    
    headers = {
        'X-Shopify-Access-Token': brand.shopify_access_token,
        'Content-Type': 'application/json'
    }
    
    webhook_url = f"{settings.SITE_URL}/webhooks/shopify/orders/"
    
    # Order creation webhook
    webhook_data = {
        'webhook': {
            'topic': 'orders/create',
            'address': webhook_url,
            'format': 'json'
        }
    }
    
    url = f"https://{brand.shopify_domain}/admin/api/2023-10/webhooks.json"
    response = requests.post(url, headers=headers, json=webhook_data)
    
    if response.status_code == 201:
        print(f"Webhook created for {brand.shopify_domain}")
    else:
        print(f"Webhook creation failed: {response.text}")

# Attribution debug and analytics