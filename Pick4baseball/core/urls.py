# core/urls.py
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views, views_leaderboard
from . import verification_views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('team/<int:team_id>/', views.team_detail, name='team_detail'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path("test-email/", views.test_email, name="test_email"),
    path('verify/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('verification-sent/', verification_views.verification_sent, name='verification_sent'),
    path('create-team/', views.create_team, name='create_team'),
    path('join-team/', views.join_team, name='join_team'),
    path('how-to-play/', views.how_to_play, name='how_to_play'),

    # Picks

    path('picks/make/', views.make_picks, name='make_picks'),
    path('picks/view/', views.view_picks, name='view_picks'),
    # In the Teams section
    path('teams/', views.my_teams, name='my_teams'),

    # Leaderboard - FIXED: All use views_leaderboard
    path('leaderboard/', views_leaderboard.leaderboard, name='leaderboard'),
    path('leaderboard/teams/', views_leaderboard.team_leaderboard, name='team_leaderboard'),
    path('results/', views_leaderboard.weekly_results, name='weekly_results'),
    path('results/<int:week_number>/', views_leaderboard.weekly_results, name='weekly_results_specific'),
    path('profile/', views_leaderboard.user_profile, name='user_profile'),
    path('profile/<str:username>/', views_leaderboard.user_profile, name='user_profile_view'),

    # Password Reset

    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Info pages
    path('rules/', views.rules, name='rules'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('settings/', views.account_settings, name='account_settings'),
    path('how-to-play/', views.how_to_play, name='how_to_play'),

    # Payments
    path('payments/', views.payment_portal, name='payment_portal'),
    path('payments/history/', views.payment_history, name='payment_history'),
    path('payments/confirmation/<int:payment_id>/', views.payment_confirmation, name='payment_confirmation'),
    path('api/payments/create-intent/<int:team_id>/', views.create_payment_intent, name='create_payment_intent'),
    path('webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),

    path('payments/pay-with-balance/', views.pay_with_balance, name='pay_with_balance'),
    path('payments/withdraw/', views.request_withdrawal, name='request_withdrawal'),
    path('payments/transactions/', views.transaction_history, name='transaction_history'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
