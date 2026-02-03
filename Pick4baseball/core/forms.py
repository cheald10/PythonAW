# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError
from .models import Team


class RegistrationForm(UserCreationForm):
    """
    Custom registration form extending Django's UserCreationForm.
    Includes additional fields: email, first_name, last_name
    """

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'John',
            'class': 'form-control'
        }),
        help_text='Required.'
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Smith',
            'class': 'form-control'
        }),
        help_text='Required.'
    )

    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'your.email@example.com',
            'class': 'form-control'
        }),
        help_text='Required. Enter a valid email address.'
    )

    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'baseballfan2025',
            'class': 'form-control'
        }),
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
    )

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Create a strong password',
            'class': 'form-control',
            'minlength': '8'
        }),
        help_text='Your password must contain at least 8 characters.'
    )

    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Re-enter your password',
            'class': 'form-control',
            'minlength': '8'
        }),
        help_text='Enter the same password as before, for verification.'
    )

    agree_to_terms = forms.BooleanField(
        required=True,
        label="I agree to the Terms of Service and Privacy Policy"
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'agree_to_terms')

    def clean_email(self):
        """
        Validate that the email is unique in the system.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def clean_username(self):
        """
        Validate that the username is unique (case-insensitive).
        """
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('This username is already taken.')
        return username

    def clean_password2(self):
        """
        Validate that the two password entries match.
        """
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError('The two password fields must match.')

        return password2

    def save(self, commit=True):
        """
        Save the user instance with additional fields.
        Set user as inactive until email is verified (if email verification is enabled).
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        # Set user as inactive until email verification
        # Change this to True if you want to skip email verification
        user.is_active = False  # Will be set to True after email verification

        if commit:
            user.save()

        return user


class TeamCreationForm(forms.ModelForm):
    """
    Form for creating a new team.

    Fields:
    - name: Team name (required)
    - description: Team description (optional)
    - weekly_fee: Weekly fee amount (required) - $5 or $10

    Note: All teams are private by default.
    Users can only join via join code.
    """

    # Explicitly define weekly_fee as ChoiceField to ensure dropdown works
    weekly_fee = forms.ChoiceField(
        label='Weekly Fee',
        required=True,
        choices=[
            ('', '-- Select Weekly Fee --'),
            ('5', '$5.00 per week'),
            ('10', '$10.00 per week'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True,
        }),
        help_text='Amount each member pays per week to play'
    )

    class Meta:
        model = Team
        fields = ['name', 'description', 'weekly_fee']

        labels = {
            'name': 'Team Name',
            'description': 'Team Description',
        }

        help_texts = {
            'name': 'Choose a unique name for your team',
            'description': 'Tell potential members what your team is about (optional)',
        }

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter team name (e.g., "The Baseball Bandits")',
                'maxlength': 100,
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe your team (optional)',
            }),
        }

    def clean_name(self):
        """Validate team name is unique and appropriate"""
        name = self.cleaned_data.get('name')

        if name:
            # Check if name already exists (case-insensitive)
            if Team.objects.filter(name__iexact=name).exists():
                raise forms.ValidationError(
                    'A team with this name already exists. Please choose a different name.'
                )

            # Check minimum length
            if len(name.strip()) < 3:
                raise forms.ValidationError(
                    'Team name must be at least 3 characters long.'
                )

        return name

    def clean_description(self):
        """Clean and validate description"""
        description = self.cleaned_data.get('description')

        if description:
            # Trim whitespace
            description = description.strip()

            # Check max length
            if len(description) > 500:
                raise forms.ValidationError(
                    'Description must be 500 characters or less.'
                )

        return description

    def clean_weekly_fee(self):
        """
        Convert string choice to appropriate format for database.
        This handles conversion whether the model field is DecimalField,
        CharField, IntegerField, etc.
        """
        fee = self.cleaned_data.get('weekly_fee')

        if fee:
            try:
                # Convert string to float/decimal
                # Django will handle converting to the correct type for the model
                return float(fee)
            except (ValueError, TypeError):
                raise forms.ValidationError('Invalid fee selected.')

        return fee


class JoinTeamForm(forms.Form):
    """
    Form for joining an existing team using a join code
    """
    join_code = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-uppercase',
            'placeholder': 'Enter 8-character join code',
            'maxlength': 8,
            'style': 'letter-spacing: 0.2em; font-weight: bold;',
            'autocomplete': 'off',
        }),
        label='Join Code',
        help_text='Enter the 8-character code provided by your team captain'
    )

    def clean_join_code(self):
        """Validate join code exists and format it"""
        code = self.cleaned_data.get('join_code', '').strip().upper()

        if not code:
            raise forms.ValidationError('Please enter a join code.')

        # Check if team exists with this code
        try:
            team = Team.objects.get(join_code=code)
        except Team.DoesNotExist:
            raise forms.ValidationError('Invalid join code. Please check and try again.')

        # Store the team for later use
        self.cleaned_data['team'] = team

        return code

# Global priority choices for the contact form
PRIORITY_CHOICES = [
    ("Low", "Low"),
    ("Medium", "Medium"),
    ("High", "High"),
    ("Urgent", "Urgent"),
]

class ContactForm(forms.Form):
    subject = forms.CharField(max_length=200)
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES)
    message = forms.CharField(widget=forms.Textarea)