# core/urls.py
"""
Complete URL configuration with email verification and password reset routes.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import verification_views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    path('picks/make/', views.make_picks, name='make_picks'),
    path('picks/view/', views.view_picks, name='view_picks'),

    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('results/', views.weekly_results, name='weekly_results'),
    path('rules/', views.rules, name='rules'),
    path('terms/', views.terms, name='terms'),
    path('settings/', views.account_settings, name='account_settings'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Password Reset - Complete Flow
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='password_reset_form.html',
             email_template_name='password_reset_email.html',
             subject_template_name='password_reset_subject.txt'
         ),
         name='password_reset'),

    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='password_reset_done.html'
         ),
         name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='password_reset_confirm.html'
         ),
         name='password_reset_confirm'),

    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='password_reset_complete.html'
         ),
         name='password_reset_complete'),

    # Email Verification
    path('verify-email/<uidb64>/<token>/', verification_views.verify_email, name='verify_email'),
    path('resend-verification/', verification_views.resend_verification, name='resend_verification'),
    path('verification-sent/', verification_views.verification_sent, name='verification_sent'),
]
