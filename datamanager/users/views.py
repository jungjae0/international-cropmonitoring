from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def redirect_after_login(request):
    if request.user.is_authenticated:
        return redirect('tile_list')  # 로그인 된 경우 → jobs 목록
    else:
        return redirect('login')     # 로그인 안 된 경우 → 로그인 페이지