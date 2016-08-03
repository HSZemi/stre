from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from  django.contrib.auth.password_validation import validate_password, ValidationError
from backend.models import Antragsgrund, Semester, Antrag, Person, GlobalSettings, Nachweis, Dokument, Aktion, History, Briefvorlage, Brief, Status, Uebergang, Begruendung
from django.db.models import Count
from .forms import DokumentForm, UeberweisungsbetragForm, BriefErstellenForm, BriefBegruendungForm, NachfristForm
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

def loginpage(request):
	messages = []
	next_page = 'dashboard'
	
	if('next' in request.GET and len(request.GET['next']) > 0 and request.GET['next'][0] == '/'):
		next_page = request.GET['next']
		
	if request.method == 'POST':
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
						messages.append({'klassen':'alert-warning','text':'Huch! Falsche Gruppe'})
				else:
					# Return a 'disabled account' error message
					messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Dein Zugang wurde deaktiviert. Bitte wende dich an den Semesterticketausschuss.'})
					
			else:
				# Return an 'invalid login' error message.
				messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Das hat nicht funktioniert. Hast du Login-Name und Passwort auch wirklich korrekt eingegeben?'})
	
	context = { 'messages' : messages, 'current_page' : 'loginpagebackend'}
	
	return render(request, 'backend/login.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def dashboard(request):
	message = None
	
	semester = Semester.objects.order_by('-jahr').annotate(count=Count('antrag'))
	
	context = { 'message' : message, 'current_page' : 'dashboard', 'semester' : semester}
	
	return render(request, 'backend/dashboard.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def antraege(request, semester_id, status_id=None):
	semester_id = int(semester_id)
	if(status_id != None):
		status_id = int(status_id)
	message = None
	
	semester = get_object_or_404(Semester, pk=semester_id)
	antragsgruende = Antragsgrund.objects.all().order_by('sort')
	statusse = Status.objects.all().order_by('sort')
	
	antraege_sortiert = {}
	
	for grund in antragsgruende:
		if(status_id != None):
			status_select = get_object_or_404(Status, pk=status_id)
			antraege_sortiert[grund] = Antrag.objects.filter(semester__id=semester_id).filter(grund=grund).filter(status=status_select)
		else:
			antraege_sortiert[grund] = Antrag.objects.filter(semester__id=semester_id).filter(grund=grund)
	
	context = { 'message' : message, 'current_page' : 'dashboard', 'semester' : semester, 'antraege_sortiert':antraege_sortiert, 'statusse':statusse, 'status_id':status_id}
	
	return render(request, 'backend/antraege.html', context)

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

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def antrag(request, antrag_id):
	antrag_id = int(antrag_id)
	messages = []
	nachfrist_nr = None
	form = None
	
	if('m' in request.GET):
		if(request.GET['m'] == 'aktion_erfolgreich'):
			messages.append({'klassen':'alert-success', 'text':'<strong>Jawohl!</strong> Die Aktion wurde erfolgreich ausgeführt.'})
		if(request.GET['m'] == 'aktion_nicht_erfolgreich'):
			messages.append({'klassen':'alert-danger', 'text':'<strong>Herrje!</strong> Die Aktion wurde war nicht erfolgreich.'})
		if(request.GET['m'] == 'brief_ungueltig'):
			messages.append({'klassen':'alert-danger', 'text':'<strong>Herrje!</strong> Der erstellte Brief passt nicht zur ausgeführten Aktion. Was ist da denn schiefgelaufen?'})
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	
	uebergaenge = antrag.status.uebergang_from__set
	uebergang_zu = uebergaenge.values('status_end')
	zulaessige_aktionen = Aktion.objects.filter(pk__in=uebergaenge.values('aktion'))
	
	# Dateiupload #
	uploadaktion = (GlobalSettings.objects.get()).aktion_hochladen
	
	if(uploadaktion in zulaessige_aktionen):
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
						
						antrag.status = Uebergang.objects.get(status_start=antrag.status, aktion=uploadaktion).status_end
						antrag.save()
						
						history = History()
						history.akteur = request.user
						history.antrag = antrag
						history.aktion = uploadaktion
						history.save()
						
						messages.append({'klassen':'alert-success','text':'<strong>Das Dokument wurde erfolgreich hochgeladen.</strong> Es sollte jetzt hinter seinem Nachweis aufgeführt sein.'})
					else:
						if(pfad[1] == 'nachweis_ungueltig'):
							messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Das hat nicht funktioniert. Bitte nutze die vorgegebenen Nachweise.'})
						if(pfad[1] == 'falscher_content_type'):
							messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte lade nur PDF-, PNG- oder JPG-Dateien hoch.'})
					
					form = DokumentForm()
			else:
				messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular komplett aus.'})
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
	
	
	aktionen = zulaessige_aktionen.filter(staff_explizit=True).order_by('sort')
	
	briefe = antrag.brief_set.order_by('-timestamp')
	
	
	
	context = {'current_page' : 'antrag', 'antrag' : antrag, 'form':form, 'messages':messages, 'nachweise':nachweise, 'aktionen':aktionen, 'briefe':briefe}
	return render(request, 'backend/antrag.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def ueberweisungsbetrag(request, antrag_id, aktion_id):
	antrag_id = int(antrag_id)
	aktion_id = int(aktion_id)
	messages = []
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	aktion = get_object_or_404(Aktion, pk=aktion_id)
	
	if(not aktion.setzt_ueberweisungsbetrag):
		raise Http404
	
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = UeberweisungsbetragForm(antrag.semester.betrag, request.POST)
		# check whether it's valid:
		if form.is_valid():
			antrag.ueberweisungsbetrag = form.cleaned_data['ueberweisungsbetrag']
			antrag.save()
			
			history = History()
			history.akteur = request.user
			history.antrag = antrag
			history.aktion = aktion
			history.save()
			
			response = redirect('antragaktion', antrag_id=antrag.id, aktion_id=aktion.id)
			response['Location'] += '?m=betrag_gespeichert'
			return response
		else:
			messages.append({'klassen':'alert-warning','text':'<strong>Hoppla!</strong> Bitte fülle das Formular korrekt aus.'})
	else:
		initialbetrag = antrag.ueberweisungsbetragmax_value
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
			
			history = History()
			history.akteur = request.user
			history.antrag = antrag
			history.aktion = aktion
			history.save()
			
			response = redirect('antragaktion', antrag_id=antrag.id, aktion_id=aktion.id)
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
						
						response = redirect('antragaktion', antrag_id=antrag.id, aktion_id=aktion.id, brief_id=brief.id)
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
	
	uebergaenge = antrag.status.uebergang_from__set
	uebergang_zu = uebergaenge.values('status_end')
	zulaessige_aktionen = Aktion.objects.filter(pk__in=uebergaenge.values('aktion'))
	
	# Aktion ist zulässig und explizit aufrufbar?
	if(aktion in zulaessige_aktionen.filter(staff_explizit=True)):
		
		if(aktion.setzt_ueberweisungsbetrag and antrag.ueberweisungsbetrag <= 0):
			return ueberweisungsbetrag(request, antrag.id, aktion.id)
		if(aktion.setzt_nachfrist1 and antrag.nachfrist1 == None):
			return nachfrist(request, antrag.id, aktion.id)
		if(aktion.setzt_nachfrist2 and antrag.nachfrist2 == None):
			return nachfrist(request, antrag.id, aktion.id)
		
		if(aktion.briefvorlage != None):
			if(brief_id == None):
				return brief(request, antrag.id, aktion.briefvorlage.id, aktion.id)
			else:
				brief_id = int(brief_id)
				erstellter_brief = get_object_or_404(Brief, pk=brief_id)
				if(erstellter_brief.vorlage != aktion.briefvorlage):
					response = redirect('antragbackend', antrag_id=antrag.id)
					response['Location'] += '?m=brief_ungueltig'
					return response
				
		antrag.status = Uebergang.objects.get(status_start=antrag.status, aktion=aktion).status_end
		antrag.save()
			
		history = History()
		history.akteur = request.user
		history.antrag = antrag
		history.aktion = aktion
		history.save()
		
		response = redirect('antragbackend', antrag_id=antrag.id)
		response['Location'] += '?m=aktion_erfolgreich'
		return response
	else:
		response = redirect('antragbackend', antrag_id=antrag.id)
		response['Location'] += '?m=aktion_nicht_erfolgreich'
		return response
	
@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def history(request, antrag_id=None):
	antrag = None
	
	if(antrag_id != None):
		antrag_id = int(antrag_id)
		antrag = get_object_or_404(Antrag, pk=antrag_id)
		history = History.objects.filter(antrag=antrag_id).order_by('-timestamp')
	else:
		history = History.objects.all().order_by('-timestamp')
	
	context = {'current_page' : 'history', 'history' : history, 'antrag':antrag}
	return render(request, 'backend/history.html', context)

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
def konfiguration(request):
	return HttpResponse("Hello, world. You're at the konfiguration page.")
