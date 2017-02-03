from django.http import HttpResponse, FileResponse, Http404, HttpResponseForbidden, HttpRequest
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.urlresolvers import reverse
from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from django.contrib.auth.password_validation import validate_password, ValidationError
from backend.models import Antragsgrund, Semester, Antrag, Person, GlobalSettings, Nachweis, Dokument, Aktion, History, Uebergang
from django.db import IntegrityError
from .forms import PasswordChangeForm, AntragForm, DokumentForm, DokumentUebertragenForm, RegistrierungForm, AccountForm, LoginForm, PasswortResetForm
from axes.decorators import watch_login
import uuid
import os
import shutil
import mimetypes
import datetime

BASE_DIR = settings.BASE_DIR

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
	messages = []
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
				messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Der Inhalt der beiden Felder für das neue Passwort stimmt nicht überein.'})
			
			# passwort_alt korrekt?
			elif(not request.user.check_password(form.cleaned_data['passwort_alt'])):
				messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Das alte Passwort ist leider nicht korrekt.'})
			
			
			# Änderung erfolgreich?
			else:
				# Validatoren
				try:
					validate_password(form.cleaned_data['passwort_neu1'], user=request.user)
					request.user.set_password(form.cleaned_data['passwort_neu1'])
					request.user.save()
					
					# passwort erfolgreich geändert
					# login user again
					response = redirect('frontend:loginpage')
					response['Location'] += '?m=passwort_erfolgreich_geaendert'
					return response
					
				except ValidationError as e:
					validation_errors = e
					for validation_error in validation_errors:
						messages.append({'klassen':'alert-warning','text':validation_error})

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
	
	semester = Semester.objects.raw("""SELECT s.id, s.semestertyp, s.betrag, s.jahr, s.antragsfrist, s.anzeigefrist, a.id AS antrag, a.status AS status, a.klassen AS klassen
					FROM backend_semester s LEFT OUTER JOIN (SELECT ba.id AS id, ba.semester_id AS semester_id, bs.name AS status, bs.klassen AS klassen FROM backend_antrag ba JOIN backend_status bs ON ba.status_id = bs.id WHERE user_id = %s) a ON s.id = a.semester_id 
					ORDER BY s.jahr""", [person.id])
	
	initialstatus = (GlobalSettings.objects.get()).status_start
	neue_antraege = person.antrag_set.filter(status=initialstatus).values_list('id', flat=True)
	
	context = {'person':request.user, 'current_page' : 'index', 'semester' : semester, 'form' : form, 'messages':messages, 'person':person, 'neue_antraege':neue_antraege}
	return render(request, 'frontend/status.html', context)

def index(request):
	if(request.user.is_authenticated() and bool(request.user.groups.filter(name__in=['Antragstellung']))):
		return statuspage(request)
	else:
		context = { 'current_page' : 'index' }
		return render(request, 'frontend/index.html', context)
		

def logoutpage(request):
	logout(request)
	return redirect('frontend:index')

def registrierung(request):
	user = None
	messages = []
	form = None
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = RegistrierungForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			
			# Nutzeraccount erstellen
			
			semester = form.cleaned_data['semester']
			matrikelnummer = form.cleaned_data['matrikelnummer']
			email = form.cleaned_data['email']
			passwort = form.cleaned_data['passwort']
			vorname = form.cleaned_data['vorname']
			nachname = form.cleaned_data['nachname']
			adresse = form.cleaned_data['adresse']
			daten_sofort_loeschen = form.cleaned_data['daten_sofort_loeschen']
			daten_sofort_loeschen_bool = True if daten_sofort_loeschen == 'sofort_loeschen' else False
			
			try:
				validate_password(form.cleaned_data['passwort'])
					
				# User erstellen und in Gruppe 'Antragstellung' aufnehmen
				user = User.objects.create_user(matrikelnummer, email, passwort, first_name=vorname, last_name=nachname)
				group = Group.objects.get(name='Antragstellung') 
				group.user_set.add(user)
				
				# Person um User bauen
				person = Person()
				person.user = user
				person.adresse = adresse
				person.daten_sofort_loeschen = daten_sofort_loeschen_bool
				person.save()
				
				# User einloggen und Seite 2 aufrufen
				user = authenticate(username=matrikelnummer, password=passwort)
				if user is not None:
					if user.is_active:
						login(request, user)
						if(user.groups.filter(name='Antragstellung').exists()):
							# Willkommens-E-Mail senden
							
							if(user.email):
								send_mail(
									'[STRE] Willkommen im Semesterticketrückerstattungssystem!',
									'Hallo {vorname} {nachname}!\n\nDu hast dich gerade erfolgreich im Semesterticketrückerstattungssystem registriert.\nMit deiner Matrikelnummer ({matrikelnummer}) und dem von dir gewählten Passwort kannst du dich im System anmelden, Nachweise hochladen und deinen Antragsstatus verfolgen.\n\n{timestamp}\n\n------------------\n~>Signatur<~'.format(vorname=user.first_name, nachname=user.last_name, matrikelnummer=user.username, timestamp=datetime.datetime.now()),
									'STRE-Bot<sz-bot@asta.uni-bonn.de>',
									[user.email],
									fail_silently=False,
								)
							
							# Redirect auf Seite 2
							response = redirect('frontend:antragstellung', semester_id=semester.id)
							response['Location'] += '?m=initialantrag'
							return response
						else:
							messages.append({'klassen':'alert-danger','text':'falsche_gruppe'})
					else:
						# Return a 'disabled account' error message
						messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Dein Zugang wurde deaktiviert. Bitte wende dich an den Semesterticketausschuss.'})
						
				else:
					# Return an 'invalid login' error message.
					messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Das hat nicht funktioniert. Hast du Matrikelnummer und Passwort auch wirklich korrekt eingegeben?'})
				
			except IntegrityError as ie:
				# user existiert bereits
				login_url = reverse('frontend:loginpage')
				messages.append({'klassen':'alert-info','text':'<strong>Hoppla!</strong> Für diese Matrikelnummer existiert bereist ein Konto. <a href="{0}?u={1}">Melde dich bitte an</a> und stelle dann den Antrag.'.format(login_url, form.cleaned_data['matrikelnummer'])})
			except ValidationError as e:
				validation_errors = e
				for validation_error in validation_errors:
					messages.append({'klassen':'alert-warning','text':validation_error})
			
			
		else:
			# form invalid
			pass
	else:
		form = RegistrierungForm()
	context = { 'current_page' : 'registrierung', 'form':form, 'user':user, 'messages':messages }
	return render(request, 'frontend/registrierung.html', context)

@watch_login
def resetpassword(request):
	user = None
	messages = []
	form = None
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = PasswortResetForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			
			matrikelnummer = form.cleaned_data['matrikelnummer']
			
			try:
				user = User.objects.get(username=matrikelnummer)
				
				if(user.email):
					
					uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
					token = default_token_generator.make_token(user)
					
					reseturl = request.build_absolute_uri(reverse('frontend:resetpasswordconfirm', kwargs={'uidb64':uidb64, 'token':token}))
					
					send_mail(
						'[STRE] Passwort zurücksetzen',
						'Hallo {vorname} {nachname}!\n\nDu möchtest offenbar dein Passwort für das Semesterticketrückerstattungssystem zurücksetzen.\nKlicke hierzu auf den folgenden Link:\n\n{reseturl}\n\n{timestamp}\n\n------------------\n~>Signatur<~'.format(vorname=user.first_name, nachname=user.last_name, reseturl=reseturl, timestamp=datetime.datetime.now()),
						'STRE-Bot<sz-bot@asta.uni-bonn.de>',
						[user.email],
						fail_silently=False,
					)
			
			except User.DoesNotExist:
				pass
			messages.append({'klassen':'alert-success','text':'<h3>E-Mail versendet.</h3><p>An deine hinterlegte E-Mail-Adresse wurde ein Link gesendet, mit dem du dein Passwort zurücksetzen kannst.</p><p>Falls du keine E-Mail erhalten hast, hast du entweder eine falsche Matrikelnummer eingegeben oder keine E-Mail-Adresse hinterlegt.</p>'})
				
			
			
		else:
			# form invalid
			pass
	else:
		form = PasswortResetForm()
	context = { 'current_page' : 'reset', 'form':form, 'messages':messages }
	return render(request, 'frontend/reset.html', context)

@watch_login
def resetpasswordconfirm(request, uidb64, token):
	user = None
	messages = []
	
	try:
		uid = urlsafe_base64_decode(uidb64)
		user = User.objects.get(pk=uid)
	except (TypeError, ValueError, OverflowError, User.DoesNotExist):
		user = None
		messages.append({'klassen':'alert-danger','text':'<strong>Hoppla!</strong> Das hat leider nicht funktioniert. Falls der Fehler nicht verschwindet, kontaktiere bitte den Ausschuss für das Semesterticket.'})
		
	if user is not None and default_token_generator.check_token(user, token):
		if(user.email):
			passwort_neu = User.objects.make_random_password()
			user.set_password(passwort_neu)
			user.save()
			send_mail(
			'[STRE] Dein Passwort wurde zurückgesetzt',
			'Hallo {vorname} {nachname}!\n\nDein neues Passwort lautet:\n{passwort}\n\n{timestamp}\n\n------------------\n~>Signatur<~'.format(vorname=user.first_name, nachname=user.last_name, matrikelnummer=user.username, passwort=passwort_neu, timestamp=datetime.datetime.now()),
			'STRE-Bot<sz-bot@asta.uni-bonn.de>',
			[user.email],
			fail_silently=False,
		)
		messages.append({'klassen':'alert-success','text':'<strong>Formidabel!</strong> Dein neues Passwort wurde dir per E-Mail zugeschickt.'})
	else:
		messages.append({'klassen':'alert-danger','text':'<strong>Hoppla!</strong> Das hat leider nicht funktioniert. Falls der Fehler nicht verschwindet, kontaktiere bitte den Ausschuss für das Semesterticket.'})
	
	context = { 'current_page' : 'resetconfirm', 'messages':messages }
	return render(request, 'frontend/resetconfirm.html', context)

@watch_login
def loginpage(request):
	messages=[]
	matnr=None
	form = LoginForm()
	
	if('m' in request.GET):
		message = request.GET['m']
		if(message == "passwort_erfolgreich_geaendert"):
			messages.append({'klassen':'alert-success','text':'<strong>Dein Passwort wurde erfolgreich geändert.</strong> Bitte melde dich mit deinem neuen Passwort an.'})
	if('u' in request.GET):
		try:
			matnr = str(int(request.GET['u'])) # nur Zahlen erlaubt!
		except ValueError:
			pass
	
	next_page = 'frontend:index'
	if('next' in request.GET and len(request.GET['next']) > 0 and request.GET['next'][0] == '/'):
		next_page = request.GET['next']
	
	if request.method == 'POST':
		form = LoginForm(request.POST)
		if form.is_valid():
			username = form.cleaned_data['username']
			passwort = form.cleaned_data['password']
			user = authenticate(username=username, password=passwort)
			if user is not None:
				if user.is_active:
					login(request, user)
					if(user.groups.filter(name='Antragstellung').exists()):
						# Redirect to a success page.
						return redirect(next_page)
					elif(user.is_staff):
						return redirect('backend:dashboard')
					else:
						# falsche_gruppe
						messages.append({'klassen':'alert-danger','text':'falsche_gruppe'})
						
				else:
					# Return a 'disabled account' error message
					messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Dein Zugang wurde deaktiviert. Bitte wende dich an den Semesterticketausschuss.'})
					
			else:
				# Return an 'invalid login' error message.
				messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Das hat nicht funktioniert. Hast du Matrikelnummer und Passwort auch wirklich korrekt eingegeben?'})
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
	
	context = { 'messages' : messages, 'current_page' : 'loginpage', 'matrikelnummer':matnr, 'form':form}
	return render(request, 'frontend/login.html', context)

def info(request):
	gruende = Antragsgrund.objects.all().order_by('sort')
	context = { 'gruende' : gruende, 'current_page' : 'info' }
	return render(request, 'frontend/info.html', context)

def rechner(request):
	semester = Semester.objects.all().order_by('jahr')
	context = { 'semester' : semester, 'current_page' : 'rechner' }
	return render(request, 'frontend/rechner.html', context)

def impressum(request):
	context = {'current_page' : 'impressum' }
	return render(request, 'frontend/impressum.html', context)

@login_required
@group_required('Antragstellung')
def antragstellung(request, semester_id):
	semester_id = int(semester_id)
	messages = []
	initialantrag = False
	form = None
	
	semester = get_object_or_404(Semester, pk=semester_id)
	
	person = Person.objects.get(user__id=request.user.id)
	
	# Check ob Antrag bereits existiert
	if(Antrag.objects.filter(semester=semester, user=person).exists()):
		return antrag(request, Antrag.objects.get(semester=semester, user=person).id)
	
	if('m' in request.GET):
		message = request.GET['m']
		if(message == 'initialantrag'):
			initialantrag = True
	
	gruende = Antragsgrund.objects.all().order_by('sort')
	if(semester.frist_abgelaufen()):
		gruende = Antragsgrund.objects.filter(an_frist_gebunden=False)
	
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = AntragForm(gruende, request.POST)
		
		habe_gelesen = ('habe_gelesen' in request.POST and request.POST['habe_gelesen'] == 'on')
		if habe_gelesen:
			# check whether it's valid:
			if form.is_valid():
				
				neu_antrag = form.save(commit=False)
				neu_antrag.semester = semester
				neu_antrag.user = person
				neu_antrag.iban = form.cleaned_data['iban']
				neu_antrag.bic = form.cleaned_data['bic']
				neu_antrag.status = (GlobalSettings.objects.get()).status_start
				
				neu_antrag.save()
				
				
				aktion = (GlobalSettings.objects.get()).aktion_antrag_stellen
				uebergang = get_object_or_404(Uebergang, status_start=neu_antrag.status, aktion=aktion)
				
				history = History()
				history.akteur = request.user
				history.antrag = neu_antrag
				history.uebergang = uebergang
				history.save()
				
				if(person.user.email):
					send_mail(
						'[STRE] Dein Antrag wurde gestellt',
						'Hallo {vorname} {nachname}!\n\nDu hast gerade im Semesterticketrückerstattungssystem einen Antrag für das {semester} gestellt.\nVergiss nicht, die notwendigen Nachweise hochzuladen!\n\n{timestamp}\n\n------------------\n~>Signatur<~'.format(vorname=person.user.first_name, nachname=person.user.last_name, semester=semester, timestamp=datetime.datetime.now()),
						'STRE-Bot<sz-bot@asta.uni-bonn.de>',
						[person.user.email],
						fail_silently=False,
					)
				
				response = redirect('frontend:antrag', antrag_id=neu_antrag.id)
				response['Location'] += '?m=antrag_erstellt'
				return response
			else:
				#form invalid 
				pass #TODO
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Du solltest wirklich die Hinweise lesen. Und dann den Haken unten setzen.'})
	else:
		initial_form_values = {'kontoinhaber_in': '{0} {1}'.format(person.user.first_name, person.user.last_name),
				'versandanschrift':person.adresse}
		form = AntragForm(gruende, initial=initial_form_values)
	
	context = {'current_page' : 'antragstellung', 'semester' : semester, 'form' : form, 'initialantrag':initialantrag, 'messages':messages }
	return render(request, 'frontend/antragstellung.html', context)

def handle_uploaded_file(f, semester_id, antrag_id):
	messages = []
	filepath = None
	
	if(f.content_type not in ('application/pdf','image/png','image/jpg','image/jpeg')):
		messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte lade nur PDF-, PNG- oder JPG-Dateien hoch.'})
		return (filepath, messages)
	
	extension = f.name[-4:].lower()
	if(extension not in ('.pdf','.png','.jpg')):
		messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte lade nur PDF-, PNG- oder JPG-Dateien hoch.'})
		return (filepath, messages)
	
	filename = str(uuid.uuid4())
	filedir = "dokumente/nachweise/{0}/{1}".format(semester_id, antrag_id)
	filepath = "dokumente/nachweise/{0}/{1}/{2}{3}".format(semester_id, antrag_id, filename, extension) # extension enthält den Punkt
	
	if(not os.path.isdir(os.path.join(BASE_DIR, filedir))):
		os.makedirs(os.path.join(BASE_DIR, filedir)) #TODO permissions
	
	with open(os.path.join(BASE_DIR, filepath), 'wb+') as destination:
		for chunk in f.chunks():
			destination.write(chunk)
	
	messages.append({'klassen':'alert-success','text':'<strong>Das Dokument wurde erfolgreich hochgeladen.</strong> Er sollte jetzt hinter seinem Nachweis aufgeführt sein.'})
	return (filepath, messages)

def copy_old_file(dokument, semester_id, antrag_id):
	messages = []
	filepath = None
	
	extension = dokument.datei[-4:].lower()
	
	filename = str(uuid.uuid4())
	filedir = "dokumente/nachweise/{0}/{1}".format(semester_id, antrag_id)
	filepath = "dokumente/nachweise/{0}/{1}/{2}{3}".format(semester_id, antrag_id, filename, extension) # extension enthält den Punkt
	
	if(not os.path.isdir(os.path.join(BASE_DIR, filedir))):
		os.makedirs(os.path.join(BASE_DIR, filedir)) #TODO permissions
	
	# Dokument kopieren
	shutil.copy(os.path.join(BASE_DIR, dokument.datei), os.path.join(BASE_DIR, filepath))
	
	messages.append({'klassen':'alert-success','text':'<strong>Das Dokument wurde erfolgreich kopiert.</strong> Er sollte jetzt hinter seinem Nachweis aufgeführt sein.'})
	return (filepath, messages)

@login_required
@group_required('Antragstellung')
def antrag(request, antrag_id):
	antrag_id = int(antrag_id)
	messages = []
	form = None
	form_uebertragen = None
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	if(antrag.user.user != request.user):
		return HttpResponseForbidden()
	
	
	if('m' in request.GET):
		message = request.GET['m']
		if(message == 'antrag_erstellt'):
			messages.append({'klassen':'alert-info','text':'<strong>Glückwunsch!</strong> Dein Antrag auf Semesterticketrückerstattung wurde erstellt. Lade nun die benötigten Nachweise hoch!<br>Das Formular hierzu findest du auf dieser Seite etwas weiter unten.'})
			
	
	form = DokumentForm()
	form.fields["nachweis"].queryset = antrag.grund.nachweise.filter(hochzuladen=True)
		
	dokumente = Dokument.objects.filter(antrag__user__user=request.user).exclude(antrag=antrag).order_by('-timestamp')
	
	if dokumente:
		form_uebertragen = DokumentUebertragenForm(dokumente)
		form_uebertragen.fields["nachweis"].queryset = antrag.grund.nachweise.filter(hochzuladen=True)
	
	if request.method == 'POST' and 'formname' in request.POST:
		if request.POST['formname'] == 'DokumentForm':
			# create a form instance and populate it with data from the request:
			form = DokumentForm(request.POST, request.FILES)
			# check whether it's valid:
			if form.is_valid():
				
				if(form.cleaned_data['nachweis'] not in antrag.grund.nachweise.all()):
					messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Das hat nicht funktioniert. Bitte nutze die vorgegebenen Nachweise.'})
				else:
					filepath, huf_messages = handle_uploaded_file(request.FILES['userfile'], antrag.semester.id, antrag.id)
					
					messages.extend(huf_messages)
					
					if(filepath != None):
						uploadaktion = (GlobalSettings.objects.get()).aktion_hochladen
						uebergang = get_object_or_404(Uebergang, status_start=antrag.status, aktion=uploadaktion)
						
						dokument = form.save(commit=False)
						dokument.antrag = antrag
						dokument.datei = filepath
						
						dokument.save()
						
						antrag.status = uebergang.status_end
						antrag.save()
						
						history = History()
						history.akteur = request.user
						history.antrag = antrag
						history.uebergang = uebergang
						history.save()
					
					form = DokumentForm()
					form.fields["nachweis"].queryset = antrag.grund.nachweise.filter(hochzuladen=True)
			else:
				messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
		elif request.POST['formname'] == 'DokumentUebertragenForm':
			# create a form instance and populate it with data from the request:
			form_uebertragen = DokumentUebertragenForm(dokumente, request.POST)
			# check whether it's valid:
			if form_uebertragen.is_valid():
				
				if(form_uebertragen.cleaned_data['nachweis'] not in antrag.grund.nachweise.all()):
					messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Das hat nicht funktioniert. Bitte nutze die vorgegebenen Nachweise.'})
				else:
					# Datei kopieren
					dokument_src = form_uebertragen.cleaned_data['userfile']
					
					filepath, huf_messages = copy_old_file(dokument_src, antrag.semester.id, antrag.id)
					
					messages.extend(huf_messages)
					
					if(filepath != None):
						uploadaktion = (GlobalSettings.objects.get()).aktion_hochladen
						uebergang = get_object_or_404(Uebergang, status_start=antrag.status, aktion=uploadaktion)
						
						dokument = form_uebertragen.save(commit=False)
						dokument.antrag = antrag
						dokument.datei = filepath
						
						dokument.save()
						
						antrag.status = uebergang.status_end
						antrag.save()
						
						history = History()
						history.akteur = request.user
						history.antrag = antrag
						history.uebergang = uebergang
						history.save()
					
					form_uebertragen = DokumentUebertragenForm(dokumente)
					form_uebertragen.fields["nachweis"].queryset = antrag.grund.nachweise.filter(hochzuladen=True)
			else:
				messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
		else:
			pass # was ist das für ein Formular!?
		
		
	nachweise_queryset = Nachweis.objects.raw("""SELECT n.id, n.name, n.beschreibung, n.hochzuladen, n.sort, d.id AS datei_id, d.timestamp AS datei_timestamp
		FROM backend_nachweis n LEFT OUTER JOIN (SELECT id, timestamp, nachweis_id from backend_dokument bd WHERE bd.antrag_id = %s AND bd.aktiv) d ON n.id = d.nachweis_id
		WHERE n.id in (SELECT nachweis_id FROM backend_antragsgrund_nachweise WHERE antragsgrund_id = %s) ORDER BY n.sort ASC """, [antrag_id, antrag.grund.id])
	
	nachweise = {}
	for nw in nachweise_queryset:
		if(nw.id not in nachweise):
			nachweise[nw.id] = {}
			nachweise[nw.id]['name'] = nw.name
			nachweise[nw.id]['beschreibung'] = nw.beschreibung
			nachweise[nw.id]['hochzuladen'] = nw.hochzuladen
			nachweise[nw.id]['dokumente'] = []
		if(nw.datei_id != None):
			nachweise[nw.id]['dokumente'].append({'id':nw.datei_id, 'timestamp':nw.datei_timestamp})
	
	context = {'current_page' : 'antrag', 'antrag' : antrag, 'form':form, 'form_uebertragen':form_uebertragen, 'messages':messages, 'nachweise':nachweise}
	return render(request, 'frontend/antrag.html', context)
	
@login_required
@group_required('Antragstellung')
def account(request):
	messages = []
	person = get_object_or_404(Person, user=request.user.id)
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = AccountForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			person.user.email = form.cleaned_data['email']
			person.user.save()
			person.adresse = form.cleaned_data['adresse']
			person.save()
			messages.append({'klassen':'alert-success','text':'<strong>Hurra!</strong> Deine Daten wurden geändert.'})
			
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
	else:
		form = AccountForm(initial={'email':person.user.email, 'adresse':person.adresse})
		
	
	context = {'current_page' : 'account', 'form':form, 'messages':messages, 'person':person}
	return render(request, 'frontend/account.html', context)
	
@login_required
@group_required('Antragstellung')
def antragzurueckziehen(request, antrag_id):
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	if(antrag.user.user != request.user):
		return HttpResponseForbidden()
	return HttpResponse("Dies ist aktuell nicht implementiert. Bitte wenden Sie sich an den Semesterticketausschuss Ihres Vertrauens.")