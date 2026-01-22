"""
Tests for RegistrationForm validation
"""
from django.test import TestCase
from core.forms import RegistrationForm
from django.contrib.auth.models import User


class RegistrationFormTest(TestCase):
    """Tests for RegistrationForm validation"""
    
    def test_valid_form(self):
        """Test form with valid data"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        form = RegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_email(self):
        """Test form with invalid email format"""
        form_data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_password_mismatch(self):
        """Test form with mismatched passwords"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'DifferentPass123!',
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_duplicate_username(self):
        """Test form with existing username"""
        # Create existing user
        User.objects.create_user(
            username='testuser',
            email='existing@example.com',
            password='TestPass123!'
        )
        
        # Try to register with same username
        form_data = {
            'username': 'testuser',
            'email': 'new@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
    
    def test_duplicate_email(self):
        """Test form with existing email"""
        # Create existing user
        User.objects.create_user(
            username='existinguser',
            email='test@example.com',
            password='TestPass123!'
        )
        
        # Try to register with same email
        form_data = {
            'username': 'newuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_weak_password(self):
        """Test form with weak password"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': '123',
            'password2': '123',
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_missing_required_fields(self):
        """Test form with missing required fields"""
        form_data = {
            'username': 'testuser',
        }
        form = RegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertTrue(len(form.errors) > 0)
