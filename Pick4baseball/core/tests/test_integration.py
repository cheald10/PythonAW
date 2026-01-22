"""
Integration tests for complete registration flow
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from unittest.mock import patch


class RegistrationIntegrationTest(TestCase):
    """Integration tests for complete registration flow"""
    
    def setUp(self):
        self.client = Client()
    
    @patch('core.views.send_verification_email')
    def test_complete_registration_flow(self, mock_send_email):
        """Test complete flow: register → verify → login"""
        mock_send_email.return_value = True
        
        # Step 1: Register
        register_data = {
            'username': 'integrationtest',
            'email': 'integration@example.com',
            'first_name': 'Integration',
            'last_name': 'Test',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        
        response = self.client.post(reverse('register'), register_data)
        self.assertEqual(response.status_code, 302)
        
        # Step 2: Verify user created and inactive
        user = User.objects.get(username='integrationtest')
        self.assertFalse(user.is_active)
        
        # Step 3: Attempt login before verification (should fail)
        login_success = self.client.login(
            username='integrationtest',
            password='TestPass123!'
        )
        self.assertFalse(login_success)
        
        # Step 4: Verify email
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        verify_url = reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
        
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 302)
        
        # Step 5: Check user is now active
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        
        # Step 6: Login after verification (should succeed)
        login_success = self.client.login(
            username='integrationtest',
            password='TestPass123!'
        )
        self.assertTrue(login_success)
    
    @patch('core.views.send_verification_email')
    @patch('core.email_utils.send_verification_email')
    def test_register_with_resend(self, mock_resend, mock_send):
        """Test flow: register → resend → verify"""
        mock_send.return_value = True
        mock_resend.return_value = True
        
        # Register
        register_data = {
            'username': 'resendtest',
            'email': 'resend@example.com',
            'first_name': 'Resend',
            'last_name': 'Test',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        
        self.client.post(reverse('register'), register_data)
        user = User.objects.get(username='resendtest')
        
        # Resend verification
        response = self.client.post(
            reverse('resend_verification'),
            {'email': 'resend@example.com'}
        )
        
        self.assertEqual(response.status_code, 302)
        mock_resend.assert_called_once()
        
        # Verify
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        verify_url = reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
        
        self.client.get(verify_url)
        
        user.refresh_from_db()
        self.assertTrue(user.is_active)
