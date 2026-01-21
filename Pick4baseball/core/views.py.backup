from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import RegistrationForm


def home(request):
    context = {}
    return render(request, 'home.html', context)


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            
            if not user.is_active:
                messages.success(
                    request,
                    f'Account created for {username}! Please check your email to verify your account.'
                )
                return redirect('login')
            else:
                messages.success(
                    request,
                    f'Account created successfully for {username}! You can now log in.'
                )
                return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm()
    
    return render(request, 'register.html', {'form': form})
