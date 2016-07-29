from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from  django.contrib.auth.password_validation import validate_password, ValidationError
from backend.models import Antragsgrund, Semester, Antrag, Person, GlobalSettings
from .forms import PasswordChangeForm, AntragForm


def group_required(*group_names):
	"""Requires user membership in at least one of the groups passed in."""
	def in_groups(u):
		if u.is_authenticated():
			if bool(u.groups.filter(name__in=group_names)):
				return True
		return False
	return user_passes_test(in_groups)


@login_required
@group_required('Antragstellung')
def statuspage(request):
	message = None
	validation_errors = []
	
	# # # # # # # # # # #
	# PASSWORTÄNDERUNG  #
	# # # # # # # # # # #
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = PasswordChangeForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			# passwort_neu1 == passwort_neu2 ?
			if(form.cleaned_data['passwort_neu1'] != form.cleaned_data['passwort_neu2']):
				message = 'neue_passwoerter_stimmen_nicht_ueberein'
			
			# passwort_alt korrekt?
			elif(not request.user.check_password(form.cleaned_data['passwort_alt'])):
				message = 'altes_passwort_nicht_korrekt'
			
			# Änderung erfolgreich?
			else:
				# Validatoren
				try:
					validate_password(form.cleaned_data['passwort_neu1'], user=request.user)
					request.user.set_password(form.cleaned_data['passwort_neu1'])
					request.user.save()
					
					message = 'passwort_erfolgreich_geaendert'
					# login user again
					return redirect('loginpage', message=message)
					
				except ValidationError as e:
					message = 'validation_error'
					validation_errors = e

	# if a GET (or any other method) we'll create a blank form
	else:
		form = PasswordChangeForm()
	
	# # # # # # # # # # #
	# PERSÖNLICHE DATEN #
	# # # # # # # # # # # 
	
	person = Person.objects.get(user=request.user.id)
	
	# # # # # # # # # # #
	# ANTRAGSÜBERSICHT  #
	# # # # # # # # # # # 
	
	semester = Semester.objects.raw("""SELECT s.id, s.semestertyp, s.betrag, s.jahr, s.antragsfrist, a.id AS antrag, a.status AS status, a.klassen AS klassen
					FROM backend_semester s LEFT OUTER JOIN (SELECT ba.id AS id, ba.semester_id AS semester_id, bs.name AS status, bs.klassen AS klassen FROM backend_antrag ba JOIN backend_status bs ON ba.status_id = bs.id WHERE user_id = %s) a ON s.id = a.semester_id 
					ORDER BY s.jahr""", [person.id])
	
	context = {'person':request.user, 'current_page' : 'index', 'semester' : semester, 'form' : form, 'message':message, 'validation_errors' : validation_errors, 'person':person}
	return render(request, 'frontend/status.html', context)

def index(request):
	if(request.user.is_authenticated() and bool(request.user.groups.filter(name__in=['Antragstellung']))):
		return statuspage(request)
	else:
		context = { 'current_page' : 'index' }
		return render(request, 'frontend/index.html', context)
		

def logoutpage(request):
	logout(request)
	return redirect('index')

def register(request):
	return HttpResponse("Hello, world. You're at the register page.")

def resetpassword(request):
	return HttpResponse("Hello, world. You're at the password reset page. Unfortunately, there is nothing we can do for you.")

def loginpage(request, message=None):
	
	if('matrikelnummer' in request.POST and 'passwort' in request.POST):
		matrikelnummer = request.POST['matrikelnummer']
		passwort = request.POST['passwort']
		user = authenticate(username=matrikelnummer, password=passwort)
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
	
	
	context = { 'message' : message, 'current_page' : 'loginpage' }
	return render(request, 'frontend/login.html', context)

def info(request):
	gruende = Antragsgrund.objects.all()
	context = { 'gruende' : gruende, 'current_page' : 'info' }
	return render(request, 'frontend/info.html', context)

def impressum(request):
	context = {'current_page' : 'impressum' }
	return render(request, 'frontend/impressum.html', context)

@login_required
@group_required('Antragstellung')
def antragstellung(request, semester_id):
	semester_id = int(semester_id)
	
	semester = Semester.objects.get(id=semester_id)
	person = Person.objects.get(user__id=request.user.id)
	form = None
	
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = AntragForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			
			antrag = form.save(commit=False)
			antrag.semester = semester
			antrag.user = person
			antrag.status = (GlobalSettings.objects.get()).status_start
			
			antrag.save()
	else:
		initial_form_values = {'kontoinhaber_in': '{0} {1}'.format(person.user.first_name, person.user.last_name),
				'versandanschrift':person.adresse}
		form = AntragForm(initial=initial_form_values)
	
	context = {'current_page' : 'antragstellung', 'semester' : semester, 'form' : form }
	return render(request, 'frontend/antragstellung.html', context)

@login_required
@group_required('Antragstellung')
def antrag(request, antrag_id):
	antrag_id = int(antrag_id)
	
	antrag = Antrag.objects.get(id=antrag_id)
	person = Person.objects.get(user__id=request.user.id)
	
	context = {'current_page' : 'antrag', 'antrag' : antrag}
	return render(request, 'frontend/antrag.html', context)



