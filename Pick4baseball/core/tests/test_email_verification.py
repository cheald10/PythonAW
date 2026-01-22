"""
Tests for email verification functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from unittest.mock import patch


class EmailVerificationTest(TestCase):
    """Tests for email verification functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_active=False
        )
    
    def get_verification_url(self, user):
        """Helper to generate verification URL"""
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    
    def test_valid_verification_token(self):
        """Test verification with valid token"""
        url = self.get_verification_url(self.user)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
    
    def test_invalid_verification_token(self):
        """Test verification with invalid token"""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse('verify_email', kwargs={
            'uidb64': uid,
            'token': 'invalid-token-123'
        })
        
        response = self.client.get(url)
        
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
    
    def test_expired_verification_token(self):
        """Test verification with expired token"""
        url = self.get_verification_url(self.user)
        
        self.user.set_password('NewPassword123!')
        self.user.save()
        
        response = self.client.get(url)
        
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
    
    def test_verification_activates_user(self):
        """Test that verification changes is_active to True"""
        self.assertFalse(self.user.is_active)
        
        url = self.get_verification_url(self.user)
        self.client.get(url)
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
    
    @patch('core.email_utils.send_verification_email')
    def test_resend_verification_email(self, mock_send):
        """Test resending verification email"""
        mock_send.return_value = True
        
        response = self.client.post(
            reverse('resend_verification'),
            {'email': 'test@example.com'}
        )
        
        mock_send.assert_called_once()
        self.assertEqual(response.status_code, 302)
    
    @patch('core.email_utils.send_verification_email')
    def test_already_verified_user(self, mock_send):
        """Test resending for already verified user"""
        self.user.is_active = True
        self.user.save()
        
        response = self.client.post(
            reverse('resend_verification'),
            {'email': 'test@example.com'}
        )
        
        mock_send.assert_not_called()
        self.assertEqual(response.status_code, 302)
