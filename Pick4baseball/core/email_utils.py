# core/email_utils.py
"""
Email verification utilities for Baseball Pick 4 app.
Handles token generation, email verification, and email sending.
"""

from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import get_user_model
from django.conf import settings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def send_verification_email(request, user):
    """
    Send verification email to user with token link.

    Args:
        request: HTTP request object (needed for domain)
        user: User object to send verification email to

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Get current site
        current_site = get_current_site(request)

        # Determine protocol (http or https)
        protocol = 'https' if request.is_secure() else 'http'

        # Email context
        context = {
            'user': user,
            'domain': current_site.domain,
            'protocol': protocol,
            'uid': uid,
            'token': token,
            'current_year': 2026,
        }

        # Render email template
        html_content = render_to_string('email_verification.html', context)

        # Create email
        subject = 'Verify Your Email - Baseball Pick 4'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        # Create email message with HTML
        email = EmailMultiAlternatives(
            subject=subject,
            body='Please verify your email address to activate your account.',  # Plain text fallback
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")

        # Send email
        email.send()

        logger.info(f"Verification email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Error sending verification email to {user.email}: {str(e)}")
        return False


def verify_email_token(uidb64, token):
    """
    Verify email token and return user if valid.

    Args:
        uidb64: Base64 encoded user ID
        token: Token string

    Returns:
        User: User object if token is valid, None otherwise
    """
    try:
        # Decode user ID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

        # Check token validity
        if default_token_generator.check_token(user, token):
            return user
        else:
            logger.warning(f"Invalid token for user {user.email}")
            return None

    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        logger.warning(f"Email verification failed: {str(e)}")
        return None


def resend_verification_email(request, user):
    """
    Resend verification email to user.

    Args:
        request: HTTP request object
        user: User object

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check if user is already verified
    if user.is_active:
        logger.info(f"User {user.email} already verified, not sending email")
        return True

    # Send new verification email
    return send_verification_email(request, user)


def get_user_by_email(email):
    """
    Get user by email address.

    Args:
        email: Email address string

    Returns:
        User: User object if found, None otherwise
    """
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None
