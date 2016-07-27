from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login

from backend.models import Antragsgrund


def index(request):
	context = { }
	return render(request, 'frontend/index.html', context)

def register(request):
	return HttpResponse("Hello, world. You're at the register page.")

def resetpassword(request):
	return HttpResponse("Hello, world. You're at the password reset page. Unfortunately, there is nothing we can do for you.")

def loginpage(request):
	message = 'none'
	
	if('matrikelnummer' in request.POST and 'passwort' in request.POST):
		matrikelnummer = request.POST['matrikelnummer']
		passwort = request.POST['passwort']
		user = authenticate(username=matrikelnummer, password=passwort)
		if user is not None:
			if user.is_active:
				login(request, user)
				# Redirect to a success page.
				message = 'success'
			else:
				# Return a 'disabled account' error message
				message = 'account disabled'
				
		else:
			# Return an 'invalid login' error message.
			message = 'invalid_login'
	
	
	context = { 'message' : message }
	return render(request, 'frontend/login.html', context)

def info(request):
	gruende = Antragsgrund.objects.all()
	context = { 'gruende' : gruende }
	return render(request, 'frontend/info.html', context)

def status(request):
	return HttpResponse("Hello, world. You're at the status page.")