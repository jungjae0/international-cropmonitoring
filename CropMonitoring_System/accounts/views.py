from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.shortcuts import render, redirect

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # 로그인 처리
            return redirect('/maps')  # 로그인 후 이동할 페이지
    else:
        form = UserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})
