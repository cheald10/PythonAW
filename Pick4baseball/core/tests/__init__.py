"""
Test suite for Baseball Pick 4 registration and email verification.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class BaseTestCase(TestCase):
    """Base test case with common setup"""
    
    def setUp(self):
        """Set up test client and common data"""
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.verify_url_name = 'verify_email'
        self.resend_url = reverse('resend_verification')
        
        # Test user data
        self.valid_user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
    
    def create_user(self, username='testuser', email='test@example.com', 
                    is_active=False):
        """Helper to create test users"""
        user = User.objects.create_user(
            username=username,
            email=email,
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        user.is_active = is_active
        user.save()
        return user
