from django.http import HttpResponse
from django.shortcuts import render

from backend.models import Antragsgrund


def index(request):
	gruende = Antragsgrund.objects.all()
	context = { 'gruende' : gruende }
	return render(request, 'frontend/index.html', context)

def register(request):
	return HttpResponse("Hello, world. You're at the register page.")

def info(request):
	return HttpResponse("Hello, world. You're at the info page.")

def status(request):
	return HttpResponse("Hello, world. You're at the status page.")