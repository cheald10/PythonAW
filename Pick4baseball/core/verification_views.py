# core/verification_views.py
"""
Views for email verification functionality.
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .email_utils import verify_email_token, resend_verification_email, get_user_by_email
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def verify_email(request, uidb64, token):
    """
    Verify user's email address using token from email link.
    
    Args:
        request: HTTP request object
        uidb64: Base64 encoded user ID
        token: Verification token
        
    Returns:
        Redirect to login page with success/error message
    """
    # Verify token and get user
    user = verify_email_token(uidb64, token)
    
    if user is not None:
        # Check if already verified
        if user.is_active:
            messages.info(
                request,
                'Your account is already verified. You can log in now.'
            )
            logger.info(f"User {user.email} tried to verify already active account")
        else:
            # Activate user account
            user.is_active = True
            user.save()
            
            messages.success(
                request,
                'Your email has been verified successfully! You can now log in.'
            )
            logger.info(f"Successfully verified email for user {user.email}")
        
        return redirect('login')
    else:
        # Invalid or expired token
        messages.error(
            request,
            'The verification link is invalid or has expired. Please request a new verification email.'
        )
        logger.warning(f"Failed email verification attempt with token: {token[:10]}...")
        return redirect('resend_verification')


@require_http_methods(["GET", "POST"])
def resend_verification(request):
    """
    Display form to resend verification email (GET) or send new email (POST).
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template (GET) or redirect (POST)
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'resend_verification.html')
        
        # Get user by email
        user = get_user_by_email(email)
        
        if user is None:
            # Don't reveal if email exists (security)
            # Still show success message
            messages.success(
                request,
                'If an account with that email exists and is not verified, '
                'we have sent a new verification email.'
            )
            logger.info(f"Verification resend requested for non-existent email: {email}")
            return redirect('login')
        
        # Check if already verified
        if user.is_active:
            messages.info(
                request,
                'This account is already verified. You can log in now.'
            )
            logger.info(f"Resend requested for already active user: {email}")
            return redirect('login')
        
        # Send verification email
        email_sent = resend_verification_email(request, user)
        
        if email_sent:
            messages.success(
                request,
                'A new verification email has been sent. Please check your inbox.'
            )
            logger.info(f"Verification email resent to {email}")
            return redirect('verification_sent')
        else:
            messages.error(
                request,
                'There was an error sending the verification email. Please try again later.'
            )
            logger.error(f"Failed to resend verification email to {email}")
            return render(request, 'resend_verification.html')
    
    # GET request - display form
    return render(request, 'resend_verification.html')


@require_http_methods(["GET"])
def verification_sent(request):
    """
    Display confirmation page after verification email is sent.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered template
    """
    return render(request, 'verification_sent.html')
