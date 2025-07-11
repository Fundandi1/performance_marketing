# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, TemplateView, UpdateView
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, CustomAuthenticationForm, AgencyProfileForm, BrandProfileForm
from .models import Agency, Brand

class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    
    def get_success_url(self):
        return reverse_lazy('dashboard')

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('dashboard')
    
    def get_initial(self):
        initial = super().get_initial()
        user_type = self.request.GET.get('type')
        if user_type in ['brand', 'agency']:
            initial['user_type'] = user_type.upper()
        return initial
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.save()
        
        # Create profile based on user type
        if user.user_type == 'AGENCY':
            Agency.objects.create(user=user)
        elif user.user_type == 'BRAND':
            Brand.objects.create(user=user)
        
        login(self.request, user)
        messages.success(self.request, 'Account created successfully!')
        return response

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.user_type == 'AGENCY':
            context['profile'] = getattr(user, 'agency', None)
        elif user.user_type == 'BRAND':
            context['profile'] = getattr(user, 'brand', None)
        
        return context

class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.user_type == 'AGENCY':
            context['profile_form'] = AgencyProfileForm(instance=getattr(user, 'agency', None))
        elif user.user_type == 'BRAND':
            context['profile_form'] = BrandProfileForm(instance=getattr(user, 'brand', None))
        
        return context
    
    def post(self, request, *args, **kwargs):
        user = request.user
        
        if user.user_type == 'AGENCY':
            form = AgencyProfileForm(request.POST, instance=getattr(user, 'agency', None))
        elif user.user_type == 'BRAND':
            form = BrandProfileForm(request.POST, instance=getattr(user, 'brand', None))
        else:
            messages.error(request, 'Invalid user type')
            return redirect('accounts:settings')
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
        else:
            messages.error(request, 'Please correct the errors below')
        
        return redirect('accounts:settings')