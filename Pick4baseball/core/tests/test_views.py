"""
Tests for registration view
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch


class RegistrationViewTest(TestCase):
    """Tests for registration view"""
    
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.valid_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
    
    def test_registration_view_get(self):
        """Test GET request to registration page"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
        self.assertContains(response, 'Register')
    
    @patch('core.views.send_verification_email')
    def test_registration_view_post_success(self, mock_send_email):
        """Test successful registration POST"""
        mock_send_email.return_value = True
        
        response = self.client.post(self.register_url, self.valid_data)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('verification_sent'))
        
        # Check user created
        self.assertTrue(User.objects.filter(username='testuser').exists())
        
        # Check email was called
        mock_send_email.assert_called_once()
    
    def test_registration_view_post_invalid(self):
        """Test registration with invalid data"""
        invalid_data = self.valid_data.copy()
        invalid_data['email'] = 'invalid-email'
        
        response = self.client.post(self.register_url, invalid_data)
        
        # Should stay on registration page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
        
        # User should not be created
        self.assertFalse(User.objects.filter(username='testuser').exists())
    
    @patch('core.views.send_verification_email')
    def test_registration_creates_inactive_user(self, mock_send_email):
        """Test that new users are created as inactive"""
        mock_send_email.return_value = True
        
        self.client.post(self.register_url, self.valid_data)
        
        user = User.objects.get(username='testuser')
        self.assertFalse(user.is_active)
    
    @patch('core.views.send_verification_email')
    def test_registration_sends_email(self, mock_send_email):
        """Test that registration triggers email sending"""
        mock_send_email.return_value = True
        
        self.client.post(self.register_url, self.valid_data)
        
        # Verify send_verification_email was called
        mock_send_email.assert_called_once()
        
        # Check it was called with correct user
        call_args = mock_send_email.call_args
        user = call_args[0][1]  # Second argument is the user
        self.assertEqual(user.username, 'testuser')
