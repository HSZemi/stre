from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from  django.contrib.auth.password_validation import validate_password, ValidationError
from backend.models import Antragsgrund, Semester, Antrag, Person, GlobalSettings, Nachweis, Dokument, Aktion, History, Briefvorlage, Brief, Status, Uebergang, Begruendung
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist
from .forms import DokumentForm, DokumentUebertragenForm, UeberweisungsbetragForm, BriefErstellenForm, BriefBegruendungForm, NachfristForm, LoginForm, BulkAlsUeberwiesenMarkierenForm, AccountForm, PasswortZuruecksetzenForm
from axes.decorators import watch_login
import uuid
import os
import mimetypes
import re
from django.utils.translation import to_locale, get_language
import locale
from django.utils import timezone
import shutil
import subprocess
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

@watch_login
def loginpage(request):
	messages = []
	next_page = 'backend:dashboard'
	form = LoginForm()
	
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
						return redirect('backend:index')
					elif(user.is_staff):
						return redirect('backend:dashboard')
					else:
						messages.append({'klassen':'alert-warning','text':'Huch! Falsche Gruppe'})
				else:
					# Return a 'disabled account' error message
					messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Dein Zugang wurde deaktiviert. Bitte wende dich an den Semesterticketausschuss.'})
					
			else:
				# Return an 'invalid login' error message.
				messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Das hat nicht funktioniert. Hast du Login-Name und Passwort auch wirklich korrekt eingegeben?'})
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
	
	context = { 'messages' : messages, 'current_page' : 'loginpagebackend', 'form':form}
	
	return render(request, 'backend/login.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def dashboard(request):
	message = None
	
	semester = Semester.objects.order_by('-jahr').annotate(count=Count('antrag')).filter(gruppe__in=request.user.groups.values_list('id',flat=True))
	
	context = { 'message' : message, 'current_page' : 'dashboard', 'semester' : semester}
	
	return render(request, 'backend/dashboard.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def suche(request, suchbegriff=None):
	try: # teste auf Antrag-ID
		antrag_id = int(suchbegriff)
		
		antrag = Antrag.objects.get(pk=antrag_id)
		
		return redirect('backend:antrag', antrag_id=antrag_id)
	
	except (ValueError, ObjectDoesNotExist): # suche nach Name
		
		result = Antrag.objects.filter(user__user__first_name__icontains=suchbegriff) | Antrag.objects.filter(user__user__last_name__icontains=suchbegriff)
		
		result = result.filter(semester__gruppe__in=request.user.groups.values_list('id',flat=True))
		
		result = result.order_by('-semester', '-id')
		
		context = {'antraege':result, 'suchbegriff':suchbegriff}
		
		return render(request, 'backend/suche.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def antraege(request, semester_id, status_id=None, messages=None):
	semester_id = int(semester_id)
	if(status_id != None):
		status_id = int(status_id)
	message = None
	
	semester = get_object_or_404(Semester, pk=semester_id)
	
	# Hat der User Zugriff auf dieses Semester?
	if(semester.gruppe not in request.user.groups.all()):
		raise Http404
	
	antragsgruende = Antragsgrund.objects.all().order_by('sort')
	statusse = Status.objects.all().order_by('sort')
	
	antraege_sortiert = {}
	
	for grund in antragsgruende:
		if(status_id != None):
			status_select = get_object_or_404(Status, pk=status_id)
			antraege_sortiert[grund] = Antrag.objects.filter(semester__id=semester_id).filter(grund=grund).filter(status=status_select)
		else:
			antraege_sortiert[grund] = Antrag.objects.filter(semester__id=semester_id).filter(grund=grund)
	
	context = { 'message' : message, 'current_page' : 'antraege', 'semester' : semester, 'antraege_sortiert':antraege_sortiert, 'statusse':statusse, 'status_id':status_id, 'messages':messages}
	
	return render(request, 'backend/antraege.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def account(request, person_id):
	person_id = int(person_id)
	
	person = get_object_or_404(Person, pk=person_id)
	
	antraege_count = Antrag.objects.filter(user=person, semester__in=Semester.objects.filter(gruppe__in=request.user.groups.all())).count()
	if(antraege_count == 0):
		raise Http404
	
	semester = Semester.objects.raw("""SELECT s.id, s.semestertyp, s.betrag, s.jahr, s.antragsfrist, s.anzeigefrist, a.id AS antrag, a.status AS status, a.klassen AS klassen
					FROM backend_semester s LEFT OUTER JOIN (SELECT ba.id AS id, ba.semester_id AS semester_id, bs.name AS status, bs.klassen AS klassen FROM backend_antrag ba JOIN backend_status bs ON ba.status_id = bs.id WHERE user_id = %s) a ON s.id = a.semester_id WHERE s.gruppe_id in (SELECT group_id FROM auth_user_groups WHERE user_id=%s) 
					ORDER BY s.jahr""", [person.id, request.user.id])
	
	context = {'current_page' : 'account', 'semester' : semester, 'person':person}
	
	return render(request, 'backend/account.html', context)

def handle_uploaded_file(f, semester_id, antrag_id):
	if(f.content_type not in ('application/pdf','image/png','image/jpg','image/jpeg')):
		return (False, 'falscher_content_type')
	extension = f.name[-4:].lower()
	if(extension not in ('.pdf','.png','.jpg')):
		return (False, 'falsches_dateiformat')
	
	filename = str(uuid.uuid4())
	filedir = "dokumente/nachweise/{0}/{1}".format(semester_id, antrag_id)
	filepath = "dokumente/nachweise/{0}/{1}/{2}{3}".format(semester_id, antrag_id, filename, extension) # extension enthält den Punkt
	
	if(not os.path.isdir(filedir)):
		os.makedirs(os.path.join(BASE_DIR, filedir)) #TODO permissions
	
	with open(os.path.join(BASE_DIR, filepath), 'wb+') as destination:
		for chunk in f.chunks():
			destination.write(chunk)
	
	return (True, filepath)

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

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def antrag(request, antrag_id):
	antrag_id = int(antrag_id)
	messages = []
	nachfrist_nr = None
	form = None
	form_uebertragen = None
	
	if('m' in request.GET):
		if(request.GET['m'] == 'aktion_erfolgreich'):
			messages.append({'klassen':'alert-success', 'text':'<strong>Jawohl!</strong> Die Aktion wurde erfolgreich ausgeführt.'})
		if(request.GET['m'] == 'aktion_nicht_erfolgreich'):
			messages.append({'klassen':'alert-danger', 'text':'<strong>Herrje!</strong> Die Aktion wurde war nicht erfolgreich.'})
		if(request.GET['m'] == 'brief_ungueltig'):
			messages.append({'klassen':'alert-danger', 'text':'<strong>Herrje!</strong> Der erstellte Brief passt nicht zur ausgeführten Aktion. Was ist da denn schiefgelaufen?'})
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	
	# Hat der User Zugriff auf das Semester des Antrags?
	if(antrag.semester.gruppe not in request.user.groups.all()):
            raise Http404
	
	uebergaenge = antrag.status.uebergang_from__set
	uebergang_zu = uebergaenge.values('status_end')
	zulaessige_aktionen = Aktion.objects.filter(pk__in=uebergaenge.values('aktion'))
	
	form = DokumentForm()
	form.fields["nachweis"].queryset = antrag.grund.nachweise.filter(hochzuladen=True)
		
	dokumente = Dokument.objects.filter(antrag__user=antrag.user, antrag__semester__gruppe__in=request.user.groups.all()).exclude(antrag=antrag).order_by('-timestamp')
	
	if dokumente:
		form_uebertragen = DokumentUebertragenForm(dokumente)
		form_uebertragen.fields["nachweis"].queryset = antrag.grund.nachweise.filter(hochzuladen=True)
	
	# Dateiupload #
	uploadaktion = (GlobalSettings.objects.get()).aktion_hochladen
	
	if(uploadaktion in zulaessige_aktionen):
		if request.method == 'POST' and 'formname' in request.POST:
			if request.POST['formname'] == 'DokumentForm':
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
							
							uebergang = Uebergang.objects.get(status_start=antrag.status, aktion=uploadaktion)
							antrag.status = uebergang.status_end
							antrag.save()
							
							history = History()
							history.akteur = request.user
							history.antrag = antrag
							history.uebergang = uebergang
							history.save()
							
							messages.append({'klassen':'alert-success','text':'<strong>Das Dokument wurde erfolgreich hochgeladen.</strong> Es sollte jetzt hinter seinem Nachweis aufgeführt sein.'})
						else:
							if(pfad[1] == 'nachweis_ungueltig'):
								messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Das hat nicht funktioniert. Bitte nutze die vorgegebenen Nachweise.'})
							if(pfad[1] == 'falscher_content_type'):
								messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte lade nur PDF-, PNG- oder JPG-Dateien hoch.'})
						
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
		
		
		
	nachweise_queryset = Nachweis.objects.raw("""SELECT n.id, n.name, n.beschreibung, n.hochzuladen, d.id AS datei_id, d.timestamp AS datei_timestamp, d.markierung AS datei_markierung
		FROM backend_nachweis n LEFT OUTER JOIN (SELECT id, timestamp, markierung, nachweis_id from backend_dokument bd WHERE bd.antrag_id = %s AND bd.aktiv) d ON n.id = d.nachweis_id
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
			nachweise[nw.id]['dokumente'].append({'id':nw.datei_id, 'timestamp':nw.datei_timestamp, 'markierung':nw.datei_markierung})
	
	
	aktionen = zulaessige_aktionen.filter(staff_explizit=True).order_by('sort')
	
	briefe = antrag.brief_set.order_by('-timestamp')
	
	markierungen = Dokument._meta.get_field('markierung').choices
	
	context = {'current_page' : 'antrag', 'antrag' : antrag, 'form':form, 'form_uebertragen':form_uebertragen, 'messages':messages, 'nachweise':nachweise, 'aktionen':aktionen, 'briefe':briefe, 'markierungen':markierungen}
	return render(request, 'backend/antrag.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def ueberweisungsbetrag(request, antrag_id, aktion_id):
	antrag_id = int(antrag_id)
	aktion_id = int(aktion_id)
	messages = []
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	aktion = get_object_or_404(Aktion, pk=aktion_id)
	uebergang = get_object_or_404(Uebergang, status_start=antrag.status, aktion=aktion)
	
	# Hat der User Zugriff auf das Semester des Antrags?
	if(antrag.semester.gruppe not in request.user.groups.all()):
            raise Http404
	
	if(not aktion.setzt_ueberweisungsbetrag):
		raise Http404
	
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = UeberweisungsbetragForm(antrag.semester.betrag, request.POST)
		# check whether it's valid:
		if form.is_valid():
			antrag.ueberweisungsbetrag = form.cleaned_data['ueberweisungsbetrag']
			antrag.save()
			
			# Hier wird kein Übergang vollzogen
			#history = History()
			#history.akteur = request.user
			#history.antrag = antrag
			#history.uebergang = uebergang
			#history.save()
			
			response = redirect('backend:antragaktion', antrag_id=antrag.id, aktion_id=aktion.id)
			response['Location'] += '?m=betrag_gespeichert'
			return response
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
	else:
		initialbetrag = antrag.ueberweisungsbetrag
		if(not initialbetrag > 0):
			initialbetrag = antrag.semester.betrag
		form = UeberweisungsbetragForm(initial={'ueberweisungsbetrag': initialbetrag}, max_value=antrag.semester.betrag)
		
		
	context = {'current_page' : 'ueberweisungsbetrag', 'antrag' : antrag, 'form':form, 'messages':messages}
	return render(request, 'backend/ueberweisungsbetrag.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def nachfrist(request, antrag_id, aktion_id):
	antrag_id = int(antrag_id)
	aktion_id = int(aktion_id)
	
	message=None
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	aktion = get_object_or_404(Aktion, pk=aktion_id)
	uebergang = get_object_or_404(Uebergang, status_start=antrag.status, aktion=aktion)
	
	# Hat der User Zugriff auf das Semester des Antrags?
	if(antrag.semester.gruppe not in request.user.groups.all()):
            raise Http404
	
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = NachfristForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			if(aktion.setzt_nachfrist1):
				antrag.nachfrist1 = form.cleaned_data['nachfrist']
			if(aktion.setzt_nachfrist2):
				antrag.nachfrist2 = form.cleaned_data['nachfrist']
			
			antrag.save()
			
			# Nachfrist setzen ist kein eigener History-Eintrag
			#history = History()
			#history.akteur = request.user
			#history.antrag = antrag
			#history.uebergang = uebergang
			#history.save()
			
			response = redirect('backend:antragaktion', antrag_id=antrag.id, aktion_id=aktion.id)
			response['Location'] += '?m=nachfrist_gesetzt'
			return response
		else:
			message = 'form_invalid'
	else:
		initialfrist = datetime.date.today()
		if aktion.setzt_nachfrist1:
			initialfrist += datetime.timedelta(days=30)
		if aktion.setzt_nachfrist2:
			initialfrist += datetime.timedelta(days=10)
		form = NachfristForm(initial={'nachfrist': initialfrist})
		
		
	context = {'current_page' : 'nachfrist', 'antrag' : antrag, 'form':form, 'message':message}
	return render(request, 'backend/nachfrist.html', context)

def replace_variables(inputstring, replacements):
	pattern = re.compile(r'\b(' + '|'.join(replacements.keys()) + r')\b')
	result = pattern.sub(lambda x: replacements[x.group()], inputstring)
	return result

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def brief(request, antrag_id, briefvorlage_id, aktion_id):
	antrag_id = int(antrag_id)
	briefvorlage_id = int(briefvorlage_id)
	aktion_id = int(aktion_id)
	
	brief = None
	form = None
	
	locale.setlocale(locale.LC_ALL, to_locale(get_language())+'.utf8')
	
	messages=[]
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	briefvorlage = get_object_or_404(Briefvorlage, pk=briefvorlage_id)
	aktion = get_object_or_404(Aktion, pk=aktion_id)
	
	# Hat der User Zugriff auf das Semester des Antrags?
	if(antrag.semester.gruppe not in request.user.groups.all()):
            raise Http404
	
	nachweise = None
	begruendungen = None
	if(briefvorlage.hat_nachweise):
		nachweise = antrag.grund.nachweise
	if(briefvorlage.hat_begruendung):
		begruendungen = Begruendung.objects.order_by('sort')
	
	if request.method == 'POST':
		
		if('step' in request.POST and request.POST['step'] == 'BriefErstellenForm'):
			# create a form instance and populate it with data from the request:
			form = BriefErstellenForm(request.POST)
			# check whether it's valid:
			if form.is_valid():
				replacements = {
					'BRIEFDATUM':form.cleaned_data['briefdatum'].strftime("%d. %B %Y"),
					'ANSCHRIFT':form.cleaned_data['anschrift'].replace('\n','\\\\'),
					'BETREFF':form.cleaned_data['betreff'],
					'ANREDE':form.cleaned_data['anrede'],
					'BRIEFTEXT':form.cleaned_data['brieftext'],
					}
				text = replace_variables((GlobalSettings.objects.get()).brief_tex, replacements)
				
				if(aktion.setzt_nachfrist1):
					antrag.nachfrist1_briefdatum = form.cleaned_data['briefdatum']
					antrag.save()
				if(aktion.setzt_nachfrist2):
					antrag.nachfrist2_briefdatum = form.cleaned_data['briefdatum']
					antrag.save()
				
				semester_id = antrag.semester.id
				
				filename = str(uuid.uuid4())
				filedir = "dokumente/briefe/{0}/{1}".format(semester_id, antrag_id)
				filepath = "dokumente/briefe/{0}/{1}/{2}{3}".format(semester_id, antrag_id, filename, '.tex') # extension enthält den Punkt
				pdffilepath = "dokumente/briefe/{0}/{1}/{2}{3}".format(semester_id, antrag_id, filename, '.pdf') # extension enthält den Punkt
				
				if(not os.path.isdir(os.path.join(BASE_DIR, filedir))):
					#os.makedirs(os.path.join('dokumente', filedir)) #TODO permissions
					shutil.copytree(os.path.join(BASE_DIR, "dokumente/briefe/static"), os.path.join(BASE_DIR, filedir))
				
				with open(os.path.join(BASE_DIR, filepath), 'w') as destination:
					destination.write(text)
				
				if(os.path.isfile(os.path.join(BASE_DIR, filepath))):
					# compile
					retval = subprocess.call(['pdflatex', "-interaction=nonstopmode", "{0}.tex".format(filename)], cwd=os.path.join(BASE_DIR, filedir))
					retval = subprocess.call(['pdflatex', "-interaction=nonstopmode", "{0}.tex".format(filename)], cwd=os.path.join(BASE_DIR, filedir))
					if(os.path.isfile(os.path.join(BASE_DIR, pdffilepath))):
						brief = Brief()
						brief.antrag = antrag
						brief.vorlage = briefvorlage
						brief.briefdatum = form.cleaned_data['briefdatum']
						brief.datei = pdffilepath
						brief.save()
						
						response = redirect('backend:antragaktion', antrag_id=antrag.id, aktion_id=aktion.id, brief_id=brief.id)
						response['Location'] += '?m=brief_wurde_erstellt'
						return response
					else:
						messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Die PDF-Datei wurde nicht erstellt. Bestimmt so ein LaTeX-Fehler. Bitte wenden Sie sich an den LaTeX-Guru Ihres Vertrauens.'})
					
				else:
					messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Der Brief konnte nicht erstellt werden (.tex-Datei nicht erstellt).'})
				
			else:
				messages.append({'klassen':'alert-danger','text':'<strong>Hoppla!</strong> Das Formular wurde nicht anständig ausgefüllt.'})
				
		elif('step' in request.POST and request.POST['step'] == 'BriefBegruendungForm'):
			# create a form instance and populate it with data from the request:
			form = BriefBegruendungForm(nachweise, begruendungen, briefvorlage.hat_freitext, request.POST)
			# check whether it's valid:
			if form.is_valid():
				
				nachfrist1 = None
				nachfrist1_briefdatum = None
				nachfrist2 = None
				nachfrist2_briefdatum = None
				
				if(antrag.nachfrist1 != None):
					nachfrist1 = antrag.nachfrist1.strftime("%d. %B %Y")
				if(antrag.nachfrist1_briefdatum != None):
					nachfrist1_briefdatum = antrag.nachfrist1_briefdatum.strftime("%d. %B %Y")
				if(antrag.nachfrist2 != None):
					nachfrist2 = antrag.nachfrist2.strftime("%d. %B %Y")
				if(antrag.nachfrist2_briefdatum != None):
					nachfrist2_briefdatum = antrag.nachfrist2_briefdatum.strftime("%d. %B %Y")
				
				fehlende_nachweise = ''
				if 'fehlende_nachweise' in form.cleaned_data and form.cleaned_data['fehlende_nachweise']:
					fehlende_nachweise = "\\begin{itemize}\n"
					for n in form.cleaned_data['fehlende_nachweise']:
						fehlende_nachweise += "\\item {0}\n".format(n.name)
					fehlende_nachweise += "\\end{itemize}"
				ausgewaehlte_begruendungen = ''
				if 'begruendungen' in form.cleaned_data:
					for n in form.cleaned_data['begruendungen']:
						ausgewaehlte_begruendungen += "\n{0}\n".format(n.text)
				freitext = ''
				if 'freitext' in form.cleaned_data:
					freitext = form.cleaned_data['freitext']
				
				replacements = {
					'VORNAME':antrag.user.user.first_name,
					'NACHNAME':antrag.user.user.last_name,
					'SEMESTER':"{} {}".format(antrag.semester.get_semestertyp_display(), antrag.semester.jahr),
					'FALLNUMMER':'{} {}'.format(antrag.grund.identifier, antrag.id),
					'ANSCHRIFT':"{0} {1}\n{2}".format(antrag.user.user.first_name,antrag.user.user.last_name,antrag.versandanschrift),
					'ANTRAGSDATUM':timezone.localtime(antrag.antragszeitpunkt).strftime("%d. %B %Y %H:%M"), #GAAAAH TIMEZONE FRENZY
					'ENDBETRAG':locale.format("%0.2f", antrag.ueberweisungsbetrag, monetary=True),
					'NACHFRIST1-DATUM':nachfrist1,
					'NACHFRIST1-BRIEFDATUM':nachfrist1_briefdatum,
					'NACHFRIST2-DATUM':nachfrist2,
					'NACHFRIST2-BRIEFDATUM':nachfrist2_briefdatum,
					'LISTE-FEHLENDE-NACHWEISE-UND-DOKUMENTE':fehlende_nachweise,
				}
				
				ausgewaehlte_begruendungen = replace_variables(ausgewaehlte_begruendungen, replacements)
				freitext = replace_variables(freitext, replacements)
				
				replacements['BEGRUENDUNG'] = ausgewaehlte_begruendungen
				replacements['FREITEXT'] = freitext
				
				betreff = replace_variables(briefvorlage.betreff, replacements)
				anrede = replace_variables(briefvorlage.anrede, replacements)
				brieftext = replace_variables(briefvorlage.brieftext, replacements)
				
				form = BriefErstellenForm(initial={'anschrift': replacements['ANSCHRIFT'], 'betreff':betreff, 'anrede':anrede ,'brieftext':brieftext})
			else:
				messages.append({'klassen':'alert-danger','text':'<strong>Hoppla!</strong> Das Formular wurde nicht anständig ausgefüllt.'})
		else:
			messages.append({'klassen':'alert-danger','text':'<strong>Hä?</strong> Was ist das für 1 POST-Request.'})
	else:
		
		
		
		form = BriefBegruendungForm(nachweise, begruendungen, briefvorlage.hat_freitext)
		
	context = {'current_page' : 'brief', 'antrag' : antrag, 'briefvorlage':briefvorlage, 'form':form, 'messages':messages}
	return render(request, 'backend/brief.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def antragaktion(request, antrag_id, aktion_id, brief_id=None):
	antrag_id = int(antrag_id)
	aktion_id = int(aktion_id)
	messages = []
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	aktion = get_object_or_404(Aktion, pk=aktion_id)
	uebergang = get_object_or_404(Uebergang, status_start=antrag.status, aktion=aktion)
	
	# Hat der User Zugriff auf das Semester des Antrags?
	if(antrag.semester.gruppe not in request.user.groups.all()):
		raise Http404
	
	uebergaenge = antrag.status.uebergang_from__set
	uebergang_zu = uebergaenge.values('status_end')
	zulaessige_aktionen = Aktion.objects.filter(pk__in=uebergaenge.values('aktion'))
	
	# Aktion ist zulässig und explizit aufrufbar?
	if(aktion in zulaessige_aktionen.filter(staff_explizit=True)):
		
		if(aktion.setzt_ueberweisungsbetrag and antrag.ueberweisungsbetrag <= 0):
			return ueberweisungsbetrag(request, antrag.id, aktion.id)
		if(aktion.setzt_nachfrist1 and (antrag.nachfrist1 == None or not (('m' in request.GET and request.GET['m'] == 'nachfrist_gesetzt') or (brief_id != None)))):
			return nachfrist(request, antrag.id, aktion.id)
		if(aktion.setzt_nachfrist2 and (antrag.nachfrist2 == None or not (('m' in request.GET and request.GET['m'] == 'nachfrist_gesetzt') or (brief_id != None)))):
			return nachfrist(request, antrag.id, aktion.id)
		
		if(aktion.briefvorlage != None):
			if(brief_id == None):
				return brief(request, antrag.id, aktion.briefvorlage.id, aktion.id)
			else:
				brief_id = int(brief_id)
				erstellter_brief = get_object_or_404(Brief, pk=brief_id)
				if(erstellter_brief.vorlage != aktion.briefvorlage):
					response = redirect('backend:antrag', antrag_id=antrag.id)
					response['Location'] += '?m=brief_ungueltig'
					return response
				
		antrag.status = uebergang.status_end
		antrag.save()
			
		history = History()
		history.akteur = request.user
		history.antrag = antrag
		history.uebergang = uebergang
		history.save()
		
		response = redirect('backend:antrag', antrag_id=antrag.id)
		response['Location'] += '?m=aktion_erfolgreich'
		return response
	else:
		response = redirect('backend:antrag', antrag_id=antrag.id)
		response['Location'] += '?m=aktion_nicht_erfolgreich'
		return response
	
@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def history(request, antrag_id=None):
	antrag = None
	messages = []
	
	if(antrag_id != None):
		antrag_id = int(antrag_id)
		antrag = get_object_or_404(Antrag, pk=antrag_id)
		
		if('m' in request.GET):
			if(request.GET['m'] == 'aktion_nicht_zulaessig'):
				messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Diese Aktion ist nicht zulässig.'})
			if(request.GET['m'] == 'aktion_erfolgreich'):
				messages.append({'klassen':'alert-success','text':'<strong>Aktion erfolgreich!</strong> Die Aktion wurde erfolgreich rückgängig gemacht.'})
		
		# Hat der User Zugriff auf das Semester des Antrags?
		if(antrag.semester.gruppe not in request.user.groups.all()):
			raise Http404
		
		history = History.objects.filter(antrag=antrag_id).order_by('-timestamp')
	else:
		history = History.objects.filter(antrag__semester__gruppe__in=request.user.groups.values_list('id',flat=True)).order_by('-timestamp')
	
	context = {'current_page' : 'history', 'history' : history, 'antrag':antrag, 'messages':messages}
	return render(request, 'backend/history.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def markieren(request, dokument_id, markierung):
	dokument_id = int(dokument_id)
	dokument = None
	messages = []
	
	markierungen = Dokument._meta.get_field('markierung').choices
	markierungen_ids = [m[0] for m in markierungen]
	
	if markierung not in markierungen_ids:
		raise Http404
	
	dokument = get_object_or_404(Dokument, pk=dokument_id)
	
	# Hat der User Zugriff auf das Semester des Antrags?
	if(dokument.antrag.semester.gruppe not in request.user.groups.all()):
		raise Http404
	
	dokument.markierung = markierung
	dokument.save()
	
	return redirect('backend:antrag', antrag_id=dokument.antrag.id)



@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def undo(request, history_id):
	history = get_object_or_404(History, pk=history_id)
	
	# darf User den Antrag sehen?
	if(history.antrag.semester.gruppe not in request.user.groups.all()):
		raise Http404
	
	if(history.ist_undo):
		response = redirect('backend:history', antrag_id=history.antrag.id)
		response['Location'] += '?m=aktion_nicht_zulaessig'
		return response
	
	# ist Antrag im Endstatus?
	if(history.antrag.status == history.uebergang.status_end):
		
		# Aktion umgekehrt ausführen
		if(history.uebergang.aktion.setzt_ueberweisungsbetrag):
			history.antrag.ueberweisungsbetrag = 0.0
		if(history.uebergang.aktion.setzt_nachfrist1):
			history.antrag.nachfrist1 = None
		if(history.uebergang.aktion.setzt_nachfrist2):
			history.antrag.nachfrist2 = None
		
		history.antrag.status = history.uebergang.status_start
		history.antrag.save()
		
		new_history = History()
		new_history.akteur = request.user
		new_history.antrag = history.antrag
		new_history.uebergang = history.uebergang
		new_history.ist_undo = True
		new_history.save()
		
		response = redirect('backend:history', antrag_id=history.antrag.id)
		response['Location'] += '?m=aktion_erfolgreich'
		return response
		
	else:
		# Aktion kann nicht rückgängig gemacht werden
		response = redirect('backend:history', antrag_id=history.antrag.id)
		response['Location'] += '?m=aktion_nicht_zulaessig'
		return response

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def bulk_als_ueberwiesen_markieren(request, semester_id):
	semester_id=int(semester_id)
	messages = []
	temp = ''
	
	semester = get_object_or_404(Semester, pk=semester_id)
	
	# Hat der User Zugriff auf dieses Semester?
	if(semester.gruppe not in request.user.groups.all()):
		raise Http404
	
	antragsgruende = Antragsgrund.objects.all().order_by('sort')
	
	ueberweisungsaktion = (GlobalSettings.objects.get()).aktion_als_ueberwiesen_markieren
	uebergaenge_ueberweisung = Uebergang.objects.filter(aktion=ueberweisungsaktion)
	statusse = Status.objects.filter(pk__in=uebergaenge_ueberweisung.values_list('status_start', flat=True))
	
	antraege = Antrag.objects.filter(semester__id=semester_id, status__id__in=statusse).order_by('grund__sort', 'id')

	form = BulkAlsUeberwiesenMarkierenForm(antraege)
	
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = BulkAlsUeberwiesenMarkierenForm(antraege, request.POST)
		# check whether it's valid:
		if form.is_valid():
			modifiziert_counter = 0
			for antrag in form.cleaned_data['antraege']:
				try:
					uebergang = Uebergang.objects.get(status_start=antrag.status, aktion=ueberweisungsaktion)
					antrag.status = uebergang.status_end
					antrag.save()
					
					history = History()
					history.akteur = request.user
					history.antrag = antrag
					history.uebergang = uebergang
					history.save()
					
					modifiziert_counter += 1
					
				except Uebergang.DoesNotExist:
					messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Antrag {0} konnte nicht als überwiesen markiert werden, da der Status-Übergang nicht zulässig war.'.format(str(antrag))})
			
			if(modifiziert_counter > 0):
				messages.append({'klassen':'alert-success','text':'<strong>Erfolg!</strong> {0} Anträge wurden als überwiesen markiert.'.format(modifiziert_counter)})
			else:
				messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Kein Antrag wurde als überwiesen markiert.'})
			
			form = BulkAlsUeberwiesenMarkierenForm(antraege)
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
	else:
		form = BulkAlsUeberwiesenMarkierenForm(antraege)
		
	context = {'current_page' : 'bulk_als_ueberwiesen_markieren', 'messages':messages, 'form':form, 'semester':semester, 'temp':temp}
	return render(request, 'backend/bulk_als_ueberwiesen_markieren.html', context)
	

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def konfiguration(request):
	return HttpResponse("Hello, world. You're at the konfiguration page.")

def resetpassword(request):
	return HttpResponse("Bitte kontaktieren Sie das IT-Referat Ihres Vertrauens.")

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def account_bearbeiten(request, person_id):
	person_id = int(person_id)
	messages = []
	person = get_object_or_404(Person, pk=person_id)
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = AccountForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			person.user.email = form.cleaned_data['email']
			person.user.save()
			person.adresse = form.cleaned_data['adresse']
			person.save()
			messages.append({'klassen':'alert-success','text':'<strong>Hurra!</strong> Die Daten dieser Person wurden geändert.'})
			
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
	else:
		form = AccountForm(initial={'matrikelnummer':person.user.username, 'vorname':person.user.first_name, 'nachname':person.user.last_name, 'email':person.user.email, 'adresse':person.adresse})
		
	
	context = {'current_page' : 'account', 'form':form, 'messages':messages, 'person':person}
	return render(request, 'backend/account_bearbeiten.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def tools(request):
	messages = []
	passwort_neu = None
	matrikelnummer = None
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = PasswortZuruecksetzenForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			matrikelnummer = form.cleaned_data['matrikelnummer']
			
			try:
				user = User.objects.get(username=matrikelnummer)
				passwort_neu = User.objects.make_random_password()
				user.set_password(passwort_neu)
				user.save()
				messages.append({'klassen':'alert-success','text':'<p><strong>Hurra!</strong> Das Passwort wurde auf ein zufällig generiertes Passwort geändert.</p><p style="font-size:200%;">Neues Passwort für Matrikelnummer {matrikelnummer}: <b>{passwort_neu}</b></p>'.format(matrikelnummer=matrikelnummer, passwort_neu=passwort_neu)})
			except User.DoesNotExist:
				messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Es existiert keine Person mit dieser Matrikelnummer im System.'})
			
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
	else:
		form = PasswortZuruecksetzenForm()
		
	
	context = {'current_page' : 'tools', 'form':form, 'messages':messages, 'matrikelnummer':matrikelnummer, 'passwort_neu':passwort_neu}
	return render(request, 'backend/tools.html', context)
