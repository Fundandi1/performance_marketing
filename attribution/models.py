# Advanced attribution features and analytics

# attribution/models.py - Advanced attribution tracking

from django.db import models
from django.utils import timezone
from campaigns.models import Campaign
from accounts.models import Agency
import json

class AttributionWindow(models.Model):
    """Configure attribution windows per campaign"""
    
    ATTRIBUTION_MODEL_CHOICES = [
        ('FIRST_CLICK', 'First Click'),
        ('LAST_CLICK', 'Last Click'),
        ('LINEAR', 'Linear Attribution'),
        ('TIME_DECAY', 'Time Decay'),
        ('POSITION_BASED', 'Position Based (40-20-40)'),
    ]
    
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name='attribution_window')
    
    # Attribution settings
    click_window_days = models.IntegerField(default=7)
    view_window_days = models.IntegerField(default=1)
    attribution_model = models.CharField(max_length=20, choices=ATTRIBUTION_MODEL_CHOICES, default='LAST_CLICK')
    
    # Advanced settings
    cross_device_enabled = models.BooleanField(default=False)
    include_organic_search = models.BooleanField(default=True)
    include_direct_traffic = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attribution window for {self.campaign.title}"

class CustomerJourney(models.Model):
    """Track complete customer journey across touchpoints"""
    
    EVENT_TYPE_CHOICES = [
        ('IMPRESSION', 'Ad Impression'),
        ('CLICK', 'Ad Click'),
        ('VIEW', 'Page View'),
        ('CONVERSION', 'Purchase'),
        ('EMAIL_OPEN', 'Email Open'),
        ('EMAIL_CLICK', 'Email Click'),
    ]
    
    # Customer identification
    session_id = models.CharField(max_length=255)
    customer_email = models.EmailField(null=True, blank=True)
    user_agent_hash = models.CharField(max_length=64)  # For cross-device tracking
    
    # Event details
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, null=True, blank=True)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, null=True, blank=True)
    
    # Attribution data
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)
    utm_term = models.CharField(max_length=100, blank=True)
    
    # Technical details
    page_url = models.URLField()
    referrer_url = models.URLField(blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Value and conversion data
    conversion_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    order_id = models.CharField(max_length=255, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.event_type} - {self.session_id[:8]} - {self.timestamp}"

class MultiTouchAttribution(models.Model):
    """Store multi-touch attribution results"""
    
    order = models.OneToOneField('campaigns.ShopifyOrder', on_delete=models.CASCADE, related_name='multi_touch_attribution')
    
    # Attribution breakdown by touchpoint
    attribution_data = models.JSONField(default=dict)  # Store attribution weights per touchpoint
    
    # Final attribution decision
    primary_agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='primary_attributions')
    attribution_confidence = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Supporting agencies (for shared attribution)
    supporting_agencies = models.JSONField(default=list)  # [{'agency_id': 1, 'weight': 0.3}, ...]
    
    attribution_model_used = models.CharField(max_length=20)
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attribution for order #{self.order.order_number}"

class AttributionRule(models.Model):
    """Custom attribution rules per brand"""
    
    RULE_TYPE_CHOICES = [
        ('PLATFORM_PRIORITY', 'Platform Priority'),
        ('RECENCY_WEIGHT', 'Recency Weighting'),
        ('SPEND_THRESHOLD', 'Minimum Spend Threshold'),
        ('INTERACTION_TYPE', 'Interaction Type Priority'),
    ]
    
    brand = models.ForeignKey('accounts.Brand', on_delete=models.CASCADE, related_name='attribution_rules')
    
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)
    rule_config = models.JSONField(default=dict)  # Flexible rule configuration
    priority = models.IntegerField(default=0)  # Higher priority rules applied first
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f"{self.brand.user.company_name} - {self.rule_type}"

# Advanced attribution processing
from typing import List, Dict, Any
from decimal import Decimal
import hashlib

class AdvancedAttributionProcessor:
    """Process complex attribution scenarios"""
    
    def __init__(self, campaign: Campaign):
        self.campaign = campaign
        self.attribution_window = getattr(campaign, 'attribution_window', None)
    
    def process_order_attribution(self, order_data: dict, journey_events: List[CustomerJourney]) -> Dict[str, Any]:
        """Process advanced attribution for an order"""
        
        if not journey_events:
            return self._fallback_attribution(order_data)
        
        # Apply attribution window
        relevant_events = self._filter_events_by_window(journey_events, order_data['created_at'])
        
        if not relevant_events:
            return self._fallback_attribution(order_data)
        
        # Apply attribution model
        attribution_model = self.attribution_window.attribution_model if self.attribution_window else 'LAST_CLICK'
        
        if attribution_model == 'FIRST_CLICK':
            result = self._first_click_attribution(relevant_events, order_data)
        elif attribution_model == 'LINEAR':
            result = self._linear_attribution(relevant_events, order_data)
        elif attribution_model == 'TIME_DECAY':
            result = self._time_decay_attribution(relevant_events, order_data)
        elif attribution_model == 'POSITION_BASED':
            result = self._position_based_attribution(relevant_events, order_data)
        else:  # LAST_CLICK
            result = self._last_click_attribution(relevant_events, order_data)
        
        return result
    
    def _filter_events_by_window(self, events: List[CustomerJourney], conversion_time: str) -> List[CustomerJourney]:
        """Filter events based on attribution window"""
        
        from datetime import datetime, timedelta
        
        conversion_dt = datetime.fromisoformat(conversion_time.replace('Z', '+00:00'))
        window_days = self.attribution_window.click_window_days if self.attribution_window else 7
        window_start = conversion_dt - timedelta(days=window_days)
        
        return [event for event in events if event.timestamp >= window_start]
    
    def _last_click_attribution(self, events: List[CustomerJourney], order_data: dict) -> Dict[str, Any]:
        """Last click attribution"""
        
        # Find last click event
        click_events = [e for e in events if e.event_type == 'CLICK']
        
        if not click_events:
            return self._fallback_attribution(order_data)
        
        last_click = max(click_events, key=lambda x: x.timestamp)
        
        return {
            'primary_agency': last_click.agency,
            'attribution_confidence': 85.0,
            'attribution_breakdown': {
                str(last_click.agency.id): 1.0 if last_click.agency else 0.0
            },
            'model_used': 'LAST_CLICK',
            'touchpoints': len(events)
        }
    
    def _first_click_attribution(self, events: List[CustomerJourney], order_data: dict) -> Dict[str, Any]:
        """First click attribution"""
        
        click_events = [e for e in events if e.event_type == 'CLICK']
        
        if not click_events:
            return self._fallback_attribution(order_data)
        
        first_click = min(click_events, key=lambda x: x.timestamp)
        
        return {
            'primary_agency': first_click.agency,
            'attribution_confidence': 75.0,
            'attribution_breakdown': {
                str(first_click.agency.id): 1.0 if first_click.agency else 0.0
            },
            'model_used': 'FIRST_CLICK',
            'touchpoints': len(events)
        }
    
    def _linear_attribution(self, events: List[CustomerJourney], order_data: dict) -> Dict[str, Any]:
        """Linear attribution - equal weight to all touchpoints"""
        
        # Get unique agencies from touchpoints
        agencies = {}
        total_touchpoints = 0
        
        for event in events:
            if event.agency and event.event_type in ['CLICK', 'VIEW']:
                agency_id = str(event.agency.id)
                if agency_id not in agencies:
                    agencies[agency_id] = {'agency': event.agency, 'touchpoints': 0}
                agencies[agency_id]['touchpoints'] += 1
                total_touchpoints += 1
        
        if not agencies:
            return self._fallback_attribution(order_data)
        
        # Equal attribution to all agencies
        attribution_breakdown = {}
        for agency_id, data in agencies.items():
            attribution_breakdown[agency_id] = data['touchpoints'] / total_touchpoints
        
        # Primary agency is the one with most touchpoints
        primary_agency_id = max(agencies.keys(), key=lambda x: agencies[x]['touchpoints'])
        primary_agency = agencies[primary_agency_id]['agency']
        
        return {
            'primary_agency': primary_agency,
            'attribution_confidence': 70.0,
            'attribution_breakdown': attribution_breakdown,
            'model_used': 'LINEAR',
            'touchpoints': total_touchpoints
        }
    
    def _time_decay_attribution(self, events: List[CustomerJourney], order_data: dict) -> Dict[str, Any]:
        """Time decay attribution - more recent touchpoints get higher weight"""
        
        from datetime import datetime
        import math
        
        conversion_time = datetime.fromisoformat(order_data['created_at'].replace('Z', '+00:00'))
        agencies = {}
        total_weight = 0
        
        # Calculate weights based on recency (exponential decay)
        for event in events:
            if event.agency and event.event_type in ['CLICK', 'VIEW']:
                agency_id = str(event.agency.id)
                
                # Calculate time difference in hours
                time_diff = (conversion_time - event.timestamp).total_seconds() / 3600
                
                # Exponential decay: weight = e^(-time_diff/24)
                # More recent events get higher weight
                weight = math.exp(-time_diff / 24)
                
                if agency_id not in agencies:
                    agencies[agency_id] = {'agency': event.agency, 'weight': 0}
                
                agencies[agency_id]['weight'] += weight
                total_weight += weight
        
        if not agencies or total_weight == 0:
            return self._fallback_attribution(order_data)
        
        # Normalize weights
        attribution_breakdown = {}
        for agency_id, data in agencies.items():
            attribution_breakdown[agency_id] = data['weight'] / total_weight
        
        # Primary agency is the one with highest weight
        primary_agency_id = max(agencies.keys(), key=lambda x: agencies[x]['weight'])
        primary_agency = agencies[primary_agency_id]['agency']
        
        return {
            'primary_agency': primary_agency,
            'attribution_confidence': 80.0,
            'attribution_breakdown': attribution_breakdown,
            'model_used': 'TIME_DECAY',
            'touchpoints': len(events)
        }
    
    def _position_based_attribution(self, events: List[CustomerJourney], order_data: dict) -> Dict[str, Any]:
        """Position-based attribution (40% first, 20% middle, 40% last)"""
        
        click_events = [e for e in events if e.event_type == 'CLICK' and e.agency]
        
        if not click_events:
            return self._fallback_attribution(order_data)
        
        if len(click_events) == 1:
            # Only one touchpoint gets 100%
            agency = click_events[0].agency
            return {
                'primary_agency': agency,
                'attribution_confidence': 90.0,
                'attribution_breakdown': {str(agency.id): 1.0},
                'model_used': 'POSITION_BASED',
                'touchpoints': 1
            }
        
        agencies = {}
        
        # First touchpoint gets 40%
        first_event = click_events[0]
        first_agency_id = str(first_event.agency.id)
        agencies[first_agency_id] = {'agency': first_event.agency, 'weight': 0.4}
        
        # Last touchpoint gets 40%
        last_event = click_events[-1]
        last_agency_id = str(last_event.agency.id)
        if last_agency_id in agencies:
            agencies[last_agency_id]['weight'] += 0.4
        else:
            agencies[last_agency_id] = {'agency': last_event.agency, 'weight': 0.4}
        
        # Middle touchpoints share 20%
        middle_events = click_events[1:-1] if len(click_events) > 2 else []
        if middle_events:
            middle_weight = 0.2 / len(middle_events)
            for event in middle_events:
                agency_id = str(event.agency.id)
                if agency_id in agencies:
                    agencies[agency_id]['weight'] += middle_weight
                else:
                    agencies[agency_id] = {'agency': event.agency, 'weight': middle_weight}
        
        # Normalize and find primary agency
        attribution_breakdown = {aid: data['weight'] for aid, data in agencies.items()}
        primary_agency_id = max(agencies.keys(), key=lambda x: agencies[x]['weight'])
        primary_agency = agencies[primary_agency_id]['agency']
        
        return {
            'primary_agency': primary_agency,
            'attribution_confidence': 85.0,
            'attribution_breakdown': attribution_breakdown,
            'model_used': 'POSITION_BASED',
            'touchpoints': len(click_events)
        }
    
    def _fallback_attribution(self, order_data: dict) -> Dict[str, Any]:
        """Fallback when no journey data available"""
        
        return {
            'primary_agency': None,
            'attribution_confidence': 0.0,
            'attribution_breakdown': {},
            'model_used': 'FALLBACK',
            'touchpoints': 0
        }

# Enhanced tracking pixel with journey tracking
def generate_advanced_tracking_pixel(campaign):
    """Generate advanced tracking pixel with journey capture"""
    
    pixel_code = f"""
<!-- AgencyMatch Advanced Attribution Pixel -->
<script>
(function() {{
    var AGENCYMATCH_CONFIG = {{
        campaignId: '{campaign.id}',
        utmCampaign: '{campaign.utm_campaign}',
        apiEndpoint: '{settings.SITE_URL}/api/attribution/',
        journeyEndpoint: '{settings.SITE_URL}/api/journey/',
        debug: {str(settings.DEBUG).lower()}
    }};
    
    // Generate session ID
    function generateSessionId() {{
        return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }}
    
    // Get or create session ID
    function getSessionId() {{
        var sessionId = localStorage.getItem('agencymatch_session_id');
        if (!sessionId) {{
            sessionId = generateSessionId();
            localStorage.setItem('agencymatch_session_id', sessionId);
        }}
        return sessionId;
    }}
    
    // Create user agent hash for cross-device tracking
    function getUserAgentHash() {{
        var ua = navigator.userAgent;
        var hash = 0;
        for (var i = 0; i < ua.length; i++) {{
            var char = ua.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }}
        return 'ua_' + Math.abs(hash).toString(36);
    }}
    
    // Track journey event
    function trackJourneyEvent(eventType, additionalData) {{
        var urlParams = new URLSearchParams(window.location.search);
        var utmData = {{}};
        
        ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(function(param) {{
            var value = urlParams.get(param);
            if (value) {{
                utmData[param] = value;
            }}
        }});
        
        var eventData = {{
            session_id: getSessionId(),
            user_agent_hash: getUserAgentHash(),
            event_type: eventType,
            page_url: window.location.href,
            referrer_url: document.referrer,
            utm_data: utmData,
            timestamp: new Date().toISOString(),
            campaign_id: AGENCYMATCH_CONFIG.campaignId
        }};
        
        // Merge additional data
        if (additionalData) {{
            Object.assign(eventData, additionalData);
        }}
        
        // Send to journey tracking endpoint
        fetch(AGENCYMATCH_CONFIG.journeyEndpoint, {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
            }},
            body: JSON.stringify(eventData),
            keepalive: true
        }}).catch(function(error) {{
            if (AGENCYMATCH_CONFIG.debug) {{
                console.error('Journey tracking failed:', error);
            }}
        }});
    }}
    
    // Store attribution data
    function storeAttribution() {{
        var urlParams = new URLSearchParams(window.location.search);
        var utmData = {{}};
        var hasUTM = false;
        
        ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(function(param) {{
            var value = urlParams.get(param);
            if (value) {{
                utmData[param] = value;
                hasUTM = true;
            }}
        }});
        
        if (hasUTM) {{
            var attributionData = {{
                utm: utmData,
                timestamp: Date.now(),
                page: window.location.href,
                referrer: document.referrer,
                sessionId: getSessionId(),
                campaignId: AGENCYMATCH_CONFIG.campaignId
            }};
            
            try {{
                localStorage.setItem('agencymatch_attribution', JSON.stringify(attributionData));
                
                // Track as click event if from ad
                if (document.referrer && (
                    document.referrer.includes('facebook.com') ||
                    document.referrer.includes('google.com') ||
                    document.referrer.includes('tiktok.com')
                )) {{
                    trackJourneyEvent('CLICK', {{
                        utm_source: utmData.utm_source,
                        utm_medium: utmData.utm_medium,
                        utm_campaign: utmData.utm_campaign
                    }});
                }}
                
                if (AGENCYMATCH_CONFIG.debug) {{
                    console.log('AgencyMatch: Attribution stored', attributionData);
                }}
            }} catch(e) {{
                // Handle localStorage errors
            }}
        }}
    }}
    
    // Track page view
    function trackPageView() {{
        trackJourneyEvent('VIEW');
    }}
    
    // Track conversion
    function trackConversion(orderData) {{
        var storedAttribution = null;
        try {{
            var stored = localStorage.getItem('agencymatch_attribution');
            if (stored) {{
                storedAttribution = JSON.parse(stored);
            }}
        }} catch(e) {{
            // Handle errors
        }}
        
        // Track conversion event in journey
        trackJourneyEvent('CONVERSION', {{
            conversion_value: orderData.total || orderData.value,
            order_id: orderData.order_id || orderData.id,
            customer_email: orderData.email
        }});
        
        // Send to attribution endpoint
        var payload = {{
            order: orderData,
            attribution: storedAttribution,
            session_id: getSessionId(),
            timestamp: Date.now()
        }};
        
        fetch(AGENCYMATCH_CONFIG.apiEndpoint, {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
            }},
            body: JSON.stringify(payload),
            keepalive: true
        }}).then(function(response) {{
            if (AGENCYMATCH_CONFIG.debug) {{
                console.log('AgencyMatch: Conversion tracked', response.status);
            }}
        }}).catch(function(error) {{
            if (AGENCYMATCH_CONFIG.debug) {{
                console.error('AgencyMatch: Conversion tracking failed', error);
            }}
        }});
    }}
    
    // Initialize tracking
    storeAttribution();
    trackPageView();
    
    // Make functions globally available
    window.agencyMatchTrackConversion = trackConversion;
    window.agencyMatchTrackEvent = trackJourneyEvent;
    
    // Auto-detect conversions
    if (window.location.pathname.includes('/thank') || 
        window.location.pathname.includes('/success') ||
        window.location.search.includes('order_id')) {{
        
        setTimeout(function() {{
            var orderData = {{
                detected: true,
                url: window.location.href
            }};
            
            // Try to extract order details
            var orderMatch = window.location.search.match(/order_id=([^&]+)/);
            if (orderMatch) {{
                orderData.order_id = orderMatch[1];
            }}
            
            trackConversion(orderData);
        }}, 1000);
    }}
    
    // Track scroll depth for engagement
    var maxScroll = 0;
    window.addEventListener('scroll', function() {{
        var scrollPercent = (window.scrollY + window.innerHeight) / document.body.scrollHeight * 100;
        scrollPercent = Math.min(Math.round(scrollPercent), 100);
        
        if (scrollPercent > maxScroll && scrollPercent >= 25 && scrollPercent % 25 === 0) {{
            maxScroll = scrollPercent;
            trackJourneyEvent('ENGAGEMENT', {{
                engagement_type: 'scroll',
                engagement_value: scrollPercent
            }});
        }}
    }});
    
}})();
</script>
<!-- End AgencyMatch Advanced Attribution Pixel -->
"""
    
    return pixel_code

# API endpoints for advanced attribution
@csrf_exempt
@require_POST
def journey_tracking_api(request):
    """Track customer journey events"""
    
    try:
        data = json.loads(request.body)
        
        # Extract event data
        session_id = data.get('session_id')
        event_type = data.get('event_type')
        campaign_id = data.get('campaign_id')
        
        if not all([session_id, event_type]):
            return JsonResponse({'status': 'missing_data'}, status=400)
        
        # Find campaign and agency
        campaign = None
        agency = None
        
        if campaign_id:
            try:
                campaign = Campaign.objects.get(id=campaign_id, status='ACTIVE')
                agency = campaign.selected_agency
            except Campaign.DoesNotExist:
                pass
        
        # Create journey event
        journey_event = CustomerJourney.objects.create(
            session_id=session_id,
            event_type=event_type,
            campaign=campaign,
            agency=agency,
            utm_source=data.get('utm_data', {}).get('utm_source', ''),
            utm_medium=data.get('utm_data', {}).get('utm_medium', ''),
            utm_campaign=data.get('utm_data', {}).get('utm_campaign', ''),
            utm_content=data.get('utm_data', {}).get('utm_content', ''),
            utm_term=data.get('utm_data', {}).get('utm_term', ''),
            page_url=data.get('page_url', ''),
            referrer_url=data.get('referrer_url', ''),
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            conversion_value=data.get('conversion_value'),
            order_id=data.get('order_id', ''),
            user_agent_hash=data.get('user_agent_hash', '')
        )
        
        return JsonResponse({'status': 'tracked', 'event_id': journey_event.id})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
@require_POST 
def advanced_attribution_api(request):
    """Process advanced attribution with journey data"""
    
    try:
        data = json.loads(request.body)
        order_data = data.get('order', {})
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'status': 'no_session'})
        
        # Get customer journey for this session
        journey_events = CustomerJourney.objects.filter(
            session_id=session_id
        ).order_by('timestamp')
        
        if not journey_events.exists():
            return JsonResponse({'status': 'no_journey'})
        
        # Find the campaign from journey
        campaign_events = journey_events.filter(campaign__isnull=False)
        if not campaign_events.exists():
            return JsonResponse({'status': 'no_campaign'})
        
        # Use the most recent campaign
        campaign = campaign_events.last().campaign
        
        # Process advanced attribution
        processor = AdvancedAttributionProcessor(campaign)
        attribution_result = processor.process_order_attribution(order_data, list(journey_events))
        
        # Store the result (when Shopify webhook comes in, we'll match this)
        # For now, just return the attribution decision
        
        return JsonResponse({
            'status': 'attributed',
            'primary_agency': attribution_result['primary_agency'].user.company_name if attribution_result['primary_agency'] else None,
            'confidence': attribution_result['attribution_confidence'],
            'model': attribution_result['model_used'],
            'touchpoints': attribution_result['touchpoints']
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)