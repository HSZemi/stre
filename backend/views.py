from django.http import HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from  django.contrib.auth.password_validation import validate_password, ValidationError
from backend.models import Antragsgrund, Semester, Antrag, Person, GlobalSettings, Nachweis, Dokument, Aktion, History, Briefvorlage, Brief
from django.db.models import Count
from .forms import DokumentForm, UeberweisungsbetragForm, BriefErstellenForm
import uuid
import os
import mimetypes
import re
from django.utils.translation import to_locale, get_language
import locale
from django.utils import timezone
import shutil
import subprocess

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

def handle_uploaded_file(f, semester_id, antrag_id):
	if(f.content_type not in ('application/pdf','image/png','image/jpg','image/jpeg')):
		return (False, 'falscher_content_type')
	extension = f.name[-4:].lower()
	if(extension not in ('.pdf','.png','.jpg')):
		return (False, 'falsches_dateiformat')
	
	filename = str(uuid.uuid4())
	filedir = "nachweise/{0}/{1}".format(semester_id, antrag_id)
	filepath = "nachweise/{0}/{1}/{2}{3}".format(semester_id, antrag_id, filename, extension) # extension enthält den Punkt
	
	if(not os.path.isdir(os.path.join('dokumente', filedir))):
		os.makedirs(os.path.join('dokumente', filedir)) #TODO permissions
	
	with open(os.path.join('dokumente', filepath), 'wb+') as destination:
		for chunk in f.chunks():
			destination.write(chunk)
	
	return (True, filepath)

@staff_member_required(login_url='/backend/login')
def antrag(request, antrag_id):
	antrag_id = int(antrag_id)
	message=None
	gmessage=None
	
	if('m' in request.GET):
		gmessage = request.GET['m']
	
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
					uploadaktion = Aktion.objects.filter(status_start=antrag.status).filter(ist_upload=True)[0]
					
					dokument = form.save(commit=False)
					dokument.antrag = antrag
					dokument.datei = pfad[1]
					
					dokument.save()
					antrag.save()
					
					history = History()
					history.akteur = request.user
					history.antrag = antrag
					history.aktion = uploadaktion
					history.save()
					
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
	
	aktionen = Aktion.objects.filter(status_start=antrag.status).filter(staff_explizit=True)
	
	briefe = antrag.brief_set.order_by('-timestamp')
	
	briefvorlagen = antrag.status.briefvorlage_set.all()
	
	context = {'current_page' : 'antrag', 'antrag' : antrag, 'form':form, 'message':message, 'gmessage':gmessage, 'nachweise':nachweise, 'aktionen':aktionen, 'briefe':briefe, 'briefvorlagen':briefvorlagen}
	return render(request, 'backend/antrag.html', context)

@staff_member_required(login_url='/backend/login')
def ueberweisungsbetrag(request, antrag_id):
	antrag_id = int(antrag_id)
	message=None
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	aktion = (GlobalSettings.objects.get()).aktion_ueberweisungsbetrag_aendern
	
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
			
			message = 'betrag_gespeichert'
		else:
			message = 'form_invalid'
	else:
		initialbetrag = antrag.ueberweisungsbetrag
		if(not initialbetrag > 0):
			initialbetrag = antrag.semester.betrag
		form = UeberweisungsbetragForm(initial={'ueberweisungsbetrag': initialbetrag}, max_value=antrag.semester.betrag)
		
		
	context = {'current_page' : 'ueberweisungsbetrag', 'antrag' : antrag, 'form':form, 'message':message}
	return render(request, 'backend/ueberweisungsbetrag.html', context)

def replace_variables(inputstring, replacements):
	pattern = re.compile(r'\b(' + '|'.join(replacements.keys()) + r')\b')
	result = pattern.sub(lambda x: replacements[x.group()], inputstring)
	return result

@staff_member_required(login_url='/backend/login')
def brief(request, antrag_id, briefvorlage_id):
	antrag_id = int(antrag_id)
	briefvorlage_id = int(briefvorlage_id)
	
	brief = None
	
	locale.setlocale(locale.LC_ALL, to_locale(get_language())+'.utf8')
	
	message=None
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	briefvorlage = get_object_or_404(Briefvorlage, pk=briefvorlage_id)
	
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		form = BriefErstellenForm(request.POST)
		# check whether it's valid:
		if form.is_valid():
			replacements = {
				'ANSCHRIFT':form.cleaned_data['anschrift'].replace('\n','\\\\'),
				'BETREFF':form.cleaned_data['betreff'],
				'ANREDE':form.cleaned_data['anrede'],
				'BRIEFTEXT':form.cleaned_data['brieftext'],
				}
			text = replace_variables((GlobalSettings.objects.get()).brief_tex, replacements)
			
			semester_id = antrag.semester.id
			
			filename = str(uuid.uuid4())
			filedir = "briefe/{0}/{1}".format(semester_id, antrag_id)
			filepath = "briefe/{0}/{1}/{2}{3}".format(semester_id, antrag_id, filename, '.tex') # extension enthält den Punkt
			pdffilepath = "briefe/{0}/{1}/{2}{3}".format(semester_id, antrag_id, filename, '.pdf') # extension enthält den Punkt
			
			if(not os.path.isdir(os.path.join('dokumente', filedir))):
				#os.makedirs(os.path.join('dokumente', filedir)) #TODO permissions
				shutil.copytree(os.path.join('dokumente', 'briefe/static'), os.path.join('dokumente', filedir))
			
			with open(os.path.join('dokumente', filepath), 'w') as destination:
				destination.write(text)
			
			if(os.path.isfile(os.path.join('dokumente', filepath))):
				# compile
				retval = subprocess.call(['pdflatex', "-interaction=nonstopmode", "{0}.tex".format(filename)], cwd=os.path.join('dokumente', filedir))
				retval = subprocess.call(['pdflatex', "-interaction=nonstopmode", "{0}.tex".format(filename)], cwd=os.path.join('dokumente', filedir))
				if(os.path.isfile(os.path.join('dokumente', pdffilepath))):
					brief = Brief()
					brief.antrag = antrag
					brief.vorlage = briefvorlage
					brief.datei = pdffilepath
					brief.save()
					
					response = redirect('antragbackend', antrag_id=antrag.id)
					response['Location'] += '?m=brief_wurde_erstellt'
					return response
				else:
					message = 'pdf_datei_nicht_erstellt'
				
			else:
				message = 'tex_datei_nicht_erstellt'
			
			
			return HttpResponse(text)
			message = 'brief_erstellt'
		else:
			message = 'form_invalid'
	else:
		replacements = {
			'VORNAME':antrag.user.user.first_name,
			'NACHNAME':antrag.user.user.last_name,
			'SEMESTER':"{} {}".format(antrag.semester.get_semestertyp_display(), antrag.semester.jahr),
			'FALLNUMMER':'{} {}'.format(antrag.grund.identifier, antrag.id),
			'ANSCHRIFT':"{0} {1}\n{2}".format(antrag.user.user.first_name,antrag.user.user.last_name,antrag.versandanschrift),
			'ANTRAGSDATUM':timezone.localtime(antrag.antragszeitpunkt).strftime("%d. %B %Y %H:%M"), #GAAAAH TIMEZONE FRENZY
			'BEGRUENDUNG':'BLA BLA BLA',
			'ZUSAETZLICHE-BEGRUENDUNG':'even moar BLA',
			'ENDBETRAG':locale.format("%0.2f", antrag.ueberweisungsbetrag, monetary=True),
			'NACHFRIST1':'MUSS MAN AUSRECHNEN',
			'NACHFRIST2':'MUSS MAN AUCH AUSRECHNEN!',
			'LISTE-FEHLENDE-NACHWEISE-UND-DOKUMENTE':'\\begin{itemize}\n\item DIE EINE \n\item DIE andere auch \n\\end{itemize}',
		  }
		
		betreff = replace_variables(briefvorlage.betreff, replacements)
		anrede = replace_variables(briefvorlage.anrede, replacements)
		brieftext = replace_variables(briefvorlage.brieftext, replacements)
		
		form = BriefErstellenForm(initial={'anschrift': replacements['ANSCHRIFT'], 'betreff':betreff, 'anrede':anrede ,'brieftext':brieftext})
		
	context = {'current_page' : 'brief', 'antrag' : antrag, 'briefvorlage':briefvorlage, 'form':form, 'message':message}
	return render(request, 'backend/brief.html', context)

@staff_member_required(login_url='/backend/login')
def antragaktion(request, antrag_id, aktion_id):
	antrag_id = int(antrag_id)
	aktion_id = int(aktion_id)
	message = None
	
	antrag = get_object_or_404(Antrag, pk=antrag_id)
	aktion = get_object_or_404(Aktion, pk=aktion_id)
	
	# Aktion ist zulässig?
	if(Aktion.objects.filter(status_start=antrag.status).filter(staff_explizit=True).filter(pk=aktion.id).exists()):
		
		if(aktion.status_end.name == "Genehmigt"):
			if(antrag.ueberweisungsbetrag > 0 and antrag.ueberweisungsbetrag != antrag.semester.betrag):
				response = redirect('antragbackend', antrag_id=antrag.id)
				response['Location'] += '?m=betrag_ist_modifiziert'
				return response
			else:
				antrag.ueberweisungsbetrag = antrag.semester.betrag
				antrag.save()
		elif(aktion.status_end.name == "teilweise genehmigt"):
			if(antrag.ueberweisungsbetrag == 0 or antrag.ueberweisungsbetrag == antrag.semester.betrag):
				response = redirect('antragbackend', antrag_id=antrag.id)
				response['Location'] += '?m=betrag_ist_nicht_modifiziert'
				return response
				
		antrag.status = aktion.status_end
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
	
@staff_member_required(login_url='/backend/login')
def history(request, antrag_id=None):
	
	if(antrag_id != None):
		antrag_id = int(antrag_id)
		history = History.objects.filter(antrag=antrag_id).order_by('-timestamp')
	else:
		history = History.objects.all().order_by('-timestamp')
	
	context = {'current_page' : 'history', 'history' : history}
	return render(request, 'backend/history.html', context)

@staff_member_required(login_url='/backend/login')
def konfiguration(request):
	return HttpResponse("Hello, world. You're at the konfiguration page.")
