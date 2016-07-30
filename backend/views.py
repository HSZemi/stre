from django.http import HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from  django.contrib.auth.password_validation import validate_password, ValidationError
from backend.models import Antragsgrund, Semester, Antrag, Person, GlobalSettings, Nachweis, Dokument
from django.db.models import Count
from .forms import DokumentForm
import uuid
import os
import mimetypes

def group_required(*group_names):
	"""Requires user membership in at least one of the groups passed in."""
	def in_groups(u):
		if u.is_authenticated():
			if bool(u.groups.filter(name__in=group_names)):
				return True
		return False
	return user_passes_test(in_groups)

def loginpage(request):
	message = None
	next_page = 'dashboard'
	if('next' in request.GET and len(request.GET['next']) > 0 and request.GET['next'][0] == '/'):
		next_page = request.GET['next']
		
	if request.user.is_authenticated():
		return redirect(next_page)
	elif request.method == 'POST':
		if('username' in request.POST and 'passwort' in request.POST):
			username = request.POST['username']
			passwort = request.POST['passwort']
			user = authenticate(username=username, password=passwort)
			if user is not None:
				if user.is_active:
					login(request, user)
					if(user.groups.filter(name='Antragstellung').exists()):
						# Redirect to a success page.
						return redirect('index')
					elif(user.is_staff):
						return redirect('dashboard')
					else:
						message = 'falsche_gruppe'
				else:
					# Return a 'disabled account' error message
					message = 'zugang_deaktiviert'
					
			else:
				# Return an 'invalid login' error message.
				message = 'ungueltige_zugangsdaten'
	
	context = { 'message' : message, 'current_page' : 'loginpagebackend'}
	
	return render(request, 'backend/login.html', context)

@staff_member_required(login_url='/backend/login')
def dashboard(request):
	message = None
	
	semester = Semester.objects.order_by('-jahr').annotate(count=Count('antrag'))
	
	context = { 'message' : message, 'current_page' : 'dashboard', 'semester' : semester}
	
	return render(request, 'backend/dashboard.html', context)

@staff_member_required(login_url='/backend/login')
def antraege(request, semester_id):
	semester_id = int(semester_id)
	message = None
	
	semester = get_object_or_404(Semester, pk=semester_id)
	
	context = { 'message' : message, 'current_page' : 'dashboard', 'semester' : semester}
	
	return render(request, 'backend/antraege.html', context)

@staff_member_required(login_url='/backend/login')
def antrag(request, antrag_id):
	antrag_id = int(antrag_id)
	message = None
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = DokumentForm(request.POST, request.FILES)
		# check whether it's valid:
		if form.is_valid():
			
			if(form.cleaned_data['nachweis'] not in antrag.grund.nachweise.all()):
				message = 'nachweis_ungueltig'
			else:
				pfad = handle_uploaded_file(request.FILES['userfile'], antrag.semester.id, antrag.id)
				
				if(pfad[0] == True):
					dokument = form.save(commit=False)
					dokument.antrag = antrag
					dokument.datei = pfad[1]
					
					dokument.save()
					antrag.save()
					
				message = pfad[1]
				
				form = DokumentForm()
		else:
			message = 'form_invalid'
	else:
		form = DokumentForm()
	form.fields["nachweis"].queryset = antrag.grund.nachweise.filter(hochzuladen=True)
		
		
	nachweise_queryset = Nachweis.objects.raw("""SELECT n.id, n.name, n.beschreibung, n.hochzuladen, d.id AS datei_id
		FROM backend_nachweis n LEFT OUTER JOIN (SELECT id, nachweis_id from backend_dokument bd WHERE bd.antrag_id = %s AND bd.aktiv) d ON n.id = d.nachweis_id
		WHERE n.id in (SELECT nachweis_id FROM backend_antragsgrund_nachweise WHERE antragsgrund_id = %s) """, [antrag_id, antrag.grund.id])
	
	nachweise = {}
	for nw in nachweise_queryset:
		if(nw.id not in nachweise):
			nachweise[nw.id] = {}
			nachweise[nw.id]['name'] = nw.name
			nachweise[nw.id]['beschreibung'] = nw.beschreibung
			nachweise[nw.id]['hochzuladen'] = nw.hochzuladen
			nachweise[nw.id]['dokumente'] = []
		if(nw.datei_id != None):
			nachweise[nw.id]['dokumente'].append(nw.datei_id)
	
	context = {'current_page' : 'antrag', 'antrag' : antrag, 'form':form, 'message':message, 'nachweise':nachweise}
	return render(request, 'backend/antrag.html', context)

@staff_member_required(login_url='/backend/login')
def konfiguration(request):
	return HttpResponse("Hello, world. You're at the konfiguration page.")
