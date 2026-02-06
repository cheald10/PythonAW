from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from core.models import UserProfile, Team, TeamMember, Pick, PickCategory, MLBPlayer, Week


class RegistrationForm(UserCreationForm):
    """User registration form with email"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
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
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        }),
        help_text='Contact support to change your email'
    )
    
    class Meta:
        model = UserProfile
        fields = ['timezone', 'phone_number']
        widgets = {
            'timezone': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(555) 123-4567'
            })
        }


class TeamCreationForm(forms.ModelForm):
    """Form for creating a new team"""
    
    class Meta:
        model = Team
        fields = ['name', 'weekly_fee', 'season_year']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Team Name'
            }),
            'weekly_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '10.00',
                'step': '0.01'
            }),
            'season_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2026'
            }),
        }
        help_texts = {
            'weekly_fee': 'Amount each member pays per week (e.g., 10.00)',
            'season_year': 'MLB season year for this team',
        }


class JoinTeamForm(forms.Form):
    """Form for joining a team with invite code"""
    invite_code = forms.CharField(
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
