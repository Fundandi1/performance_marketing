# performance_marketing/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('accounts/', include('accounts.urls')),
    path('campaigns/', include('campaigns.urls', namespace='campaigns')),
    path('marketplace/', include('marketplace.urls')),
    path('performance/', include('performance.urls')),
    path('payments/', include('payments.urls')),
    path('dashboard/', include('campaigns.urls', namespace='campaigns_dashboard')),  # Dashboard views are in campaigns
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)