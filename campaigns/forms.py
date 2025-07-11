# campaigns/forms.py

from django import forms
from django.utils import timezone
from .models import Campaign, CampaignBid

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = [
            'title', 'description', 'platforms', 'budget_min', 'budget_max',
            'target_roas', 'target_cpa', 'target_ctr', 'campaign_start', 
            'campaign_end', 'bidding_deadline'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'campaign_start': forms.DateInput(attrs={'type': 'date'}),
            'campaign_end': forms.DateInput(attrs={'type': 'date'}),
            'bidding_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'platforms': forms.CheckboxSelectMultiple(choices=[
                ('META', 'Meta (Facebook & Instagram)'),
                ('TIKTOK', 'TikTok'),
                ('GOOGLE', 'Google Ads'),
                ('LINKEDIN', 'LinkedIn'),
            ]),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'platforms':
                field.widget.attrs.update({
                    'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                })
            else:
                field.widget.attrs.update({
                    'class': 'form-checkbox h-4 w-4 text-blue-600'
                })
    
    def clean(self):
        cleaned_data = super().clean()
        campaign_start = cleaned_data.get('campaign_start')
        campaign_end = cleaned_data.get('campaign_end')
        bidding_deadline = cleaned_data.get('bidding_deadline')
        budget_min = cleaned_data.get('budget_min')
        budget_max = cleaned_data.get('budget_max')
        
        # Validate dates
        if campaign_start and campaign_end:
            if campaign_end <= campaign_start:
                raise forms.ValidationError('Campaign end date must be after start date.')
        
        if bidding_deadline:
            if bidding_deadline <= timezone.now():
                raise forms.ValidationError('Bidding deadline must be in the future.')
        
        # Validate budget
        if budget_min and budget_max:
            if budget_max <= budget_min:
                raise forms.ValidationError('Maximum budget must be greater than minimum budget.')
        
        return cleaned_data

class BidForm(forms.ModelForm):
    class Meta:
        model = CampaignBid
        fields = [
            'proposed_fee_percentage', 'guaranteed_roas', 'guaranteed_cpa', 
            'guaranteed_ctr', 'proposal_text', 'estimated_timeline'
        ]
        widgets = {
            'proposal_text': forms.Textarea(attrs={'rows': 6}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            })
        
        # Add helpful text
        self.fields['proposed_fee_percentage'].help_text = 'Percentage of campaign budget (e.g., 15 for 15%)'
        self.fields['proposal_text'].help_text = 'Describe your approach, experience, and why you\'re the best choice for this campaign'
        self.fields['estimated_timeline'].help_text = 'How long will it take to set up and optimize the campaign?'