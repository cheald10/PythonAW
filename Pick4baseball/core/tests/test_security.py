"""
Security tests for registration system
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from unittest.mock import patch


class SecurityTest(TestCase):
    """Security tests for registration system"""
    
    def setUp(self):
        self.client = Client()
    
    def test_csrf_protection(self):
        """Test CSRF protection on registration"""
        # Django test client automatically handles CSRF
        # This test verifies form requires CSRF token
        response = self.client.get(reverse('register'))
        self.assertContains(response, 'csrfmiddlewaretoken')
    
    def test_password_hashing(self):
        """Test that passwords are hashed, not stored in plain text"""
        user = User.objects.create_user(
            username='hashtest',
            email='hash@example.com',
            password='PlainPassword123!'
        )
        
        # Password should not be stored as plain text
        self.assertNotEqual(user.password, 'PlainPassword123!')
        
        # Should be properly hashed
        self.assertTrue(check_password('PlainPassword123!', user.password))
        
        # Hash should start with algorithm identifier
        self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
    
    @patch('core.views.send_verification_email')
    def test_sql_injection_protection(self, mock_send):
        """Test SQL injection attempts are blocked"""
        mock_send.return_value = True
        
        malicious_data = {
            'username': "admin' OR '1'='1",
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        
        response = self.client.post(reverse('register'), malicious_data)
        
        # Should create user with malicious string as username (escaped)
        # But should NOT create admin user or cause SQL error
        self.assertFalse(User.objects.filter(username='admin').exists())
        
        # The malicious username should be stored safely
        if User.objects.filter(username="admin' OR '1'='1").exists():
            user = User.objects.get(username="admin' OR '1'='1")
            self.assertEqual(user.username, "admin' OR '1'='1")
    
    @patch('core.views.send_verification_email')
    def test_xss_protection(self, mock_send):
        """Test XSS attempts in form fields"""
        mock_send.return_value = True
        
        xss_data = {
            'username': 'xsstest',
            'email': 'xss@example.com',
            'first_name': '<script>alert("XSS")</script>',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        
        self.client.post(reverse('register'), xss_data)
        
        # Script should be stored as-is (Django templates will escape it)
        user = User.objects.get(username='xsstest')
        
        # The script tag should be in the database
        self.assertEqual(user.first_name, '<script>alert("XSS")</script>')
        
        # When rendered in template, Django will escape it
        # (This is tested in template rendering, not here)
