from django import forms
from core.models import User
from django.contrib.auth.forms import UserCreationForm
from core.models import UserProfile, Team, TeamMember, Pick, PickCategory, MLBPlayer, Week


class RegistrationForm(UserCreationForm):
    """User registration form with email, name, and terms acceptance"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    agree_to_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        error_messages={
            'required': 'You must agree to the Terms of Service and Privacy Policy.'
        }
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email

class LoginForm(forms.Form):
    """User login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class ContactForm(forms.Form):
    """Contact form for the contact page"""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Your message...'
        })
    )


class ProfilePictureForm(forms.ModelForm):
    """Form for uploading profile picture"""

    class Meta:
        model = UserProfile
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'profile-picture-input'
            })
        }

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Validate file size (max 5MB)
            if picture.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image file too large (max 5MB)')

            # Validate file type
            if not picture.content_type.startswith('image/'):
                raise forms.ValidationError('File must be an image')

        return picture


class PayoutSettingsForm(forms.ModelForm):
    """Form for managing payout preferences"""

    class Meta:
        model = UserProfile
        fields = [
            'preferred_payout_method',
            'venmo_username',
            'paypal_email',
        ]
        widgets = {
            'preferred_payout_method': forms.Select(attrs={
                'class': 'form-select',
                'id': 'payout-method'
            }),
            'venmo_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@username'
            }),
            'paypal_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
        }
        help_texts = {
            'venmo_username': 'Your Venmo username (include @)',
            'paypal_email': 'Email associated with your PayPal account',
        }


class AccountInfoForm(forms.ModelForm):
    """Form for updating basic account info"""

    # Override timezone to accept any string value from template dropdown
    timezone = forms.CharField(
        max_length=50,
        required=False
    )

    class Meta:
        model = UserProfile
        fields = ['timezone', 'phone_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(555) 123-4567'
            })
        }

class TeamCreationForm(forms.ModelForm):
    """Form for creating a new team"""

    class Meta:
        model = Team
        fields = ['name', 'weekly_fee',]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Team Name'
            }),
            'weekly_fee': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        help_texts = {
            'weekly_fee': 'Amount each member pays per week (e.g., 10.00)',
        }


class JoinTeamForm(forms.Form):
    """Form for joining a team with invite code"""
    join_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter team invite code'
        }),
        help_text='Get this code from your team commissioner'
    )


class PickForm(forms.ModelForm):
    """Form for submitting weekly picks"""

    class Meta:
        model = Pick
        fields = ['category', 'player']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'player': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
