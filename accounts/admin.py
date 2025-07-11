# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Agency, Brand

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'company_name',)
    list_filter = ('user_type', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'company_name')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'company_name', 'phone', 'website', 'bio', 'profile_image',)
        }),
    )

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('user', 'team_size', 'years_experience', 'avg_rating', 'total_campaigns', 'success_rate', 'competitiveness_score')
    list_filter = ('team_size', 'years_experience', 'avg_rating')
    search_fields = ('user__username', 'user__company_name')
    readonly_fields = ('avg_rating', 'total_campaigns', 'success_rate')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('user', 'industry', 'company_size', 'annual_ad_spend')
    list_filter = ('industry', 'company_size')
    search_fields = ('user__username', 'user__company_name', 'industry')