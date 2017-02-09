from django.shortcuts import render
from django.conf import settings
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from backend.models import Dokument, Brief, Semester, Antragsgrund, GlobalSettings, Uebergang, Status, Antrag
from backend.views import antraege
import os
import mimetypes
import datetime
import re
import uuid
import shutil
import subprocess
import locale

BASE_DIR = settings.BASE_DIR

# Create your views here.

def group_required(*group_names):
	"""Requires user membership in at least one of the groups passed in."""
	def in_groups(u):
		if u.is_authenticated():
			if bool(u.groups.filter(name__in=group_names)):
				return True
		return False
	return user_passes_test(in_groups)

@login_required
@group_required('Antragstellung','Bearbeitung','Beobachtung')
def datei(request, dokument_id):
	dokument_id = int(dokument_id)
	
	dokument = get_object_or_404(Dokument, pk=dokument_id)
	
	if(dokument.antrag.user.user.id == request.user.id or dokument.antrag.semester.gruppe in request.user.groups.all()):
		response = FileResponse(open(os.path.join(BASE_DIR, dokument.datei), 'rb'), content_type=mimetypes.guess_type(os.path.join(BASE_DIR, dokument.datei))[0])
		#response['Content-Disposition'] = 'attachment; filename={0}'.format(os.path.basename(dokument.datei))
		return response
	else:
		raise Http404("Document does not exist")

@staff_member_required(login_url='/backend/login')
def brief(request, brief_id):
	brief_id = int(brief_id)
	
	brief = get_object_or_404(Brief, pk=brief_id)
	
	# Hat der User Zugriff auf dieses Semester?
	if(brief.antrag.semester.gruppe not in request.user.groups.all()):
		raise Http404
	
	response = FileResponse(open(os.path.join(BASE_DIR, brief.datei), 'rb'), content_type=mimetypes.guess_type(os.path.join(BASE_DIR, brief.datei))[0])
	#response['Content-Disposition'] = 'attachment; filename={0}'.format(os.path.basename(dokument.datei))
	return response

def replace_variables(inputstring, replacements):
	pattern = re.compile(r'\b(' + '|'.join(replacements.keys()) + r')\b')
	result = pattern.sub(lambda x: replacements[x.group()], inputstring)
	return result

@staff_member_required(login_url=settings.BACKEND_LOGIN_URL)
@group_required('Bearbeitung')
def export_ueberweisung(request, semester_id):
	semester_id = int(semester_id)
	messages = []
	locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
	
	semester = get_object_or_404(Semester, pk=semester_id)
	
	# Hat der User Zugriff auf dieses Semester?
	if(semester.gruppe not in request.user.groups.all()):
		raise Http404
	
	titel = "titel"
	zeitstempel = datetime.datetime.now()
	
	tabelle = r"""\begin{{longtable}}{{| p{{1cm}} |p{{4cm}}| p{{4cm}} | p{{4cm}} |p{{2cm}}| p{{5cm}}| p{{4cm}} |}} 
\hline
\textbf{{ID}} & \textbf{{Vorname}} & \textbf{{Nachname}} & \textbf{{Adresse}} & \textbf{{Ü-Betrag}} & \textbf{{IBAN}} \newline \textbf{{BIC}} & \textbf{{Beleg-Nr.}} \endhead \hline 

{inhalt}

\end{{longtable}}"""
	
	zeile = "{id} &	{vorname} &	{nachname} & {adresse} &	\EUR{{{betrag}}} &	{iban} \\newline {bic} & \\\\\\hline\n"
	
	antragsgruende = Antragsgrund.objects.all().order_by('sort')
	
	ueberweisungsaktion = (GlobalSettings.objects.get()).aktion_als_ueberwiesen_markieren
	uebergaenge_ueberweisung = Uebergang.objects.filter(aktion=ueberweisungsaktion)
	statusse = Status.objects.filter(pk__in=uebergaenge_ueberweisung.values_list('status_start', flat=True))
	
	antraege_sortiert = {}
	
	tabellen = ""
	
	for grund in antragsgruende:
		antraege_g = Antrag.objects.filter(semester__id=semester_id, grund=grund, status__id__in=statusse)
		
		inhalt = ""
		
		for antrag in antraege_g:
			
			inhalt += zeile.format(id="{0} {1}".format(antrag.grund.identifier, antrag.id), 
			  vorname=antrag.user.user.first_name, 
			  nachname=antrag.user.user.last_name, 
			  adresse=antrag.versandanschrift.replace("\n","\\newline"), 
			  betrag=locale.format('%.2f', antrag.ueberweisungsbetrag), 
			  iban=antrag.iban, 
			  bic=antrag.bic)
		
		tabellen += "\section*{{{grund}}}\n\n".format(grund=str(grund))
		
		if(len(antraege_g) == 0):
			tabellen += r"\textit{Für diesen Antragsgrund sind aktuell keine Überweisungen auszuführen.}\n\n"
		else:
			tabellen += tabelle.format(inhalt=inhalt)
		
		tabellen += r"\newpage"
		
	replacements = {
		'TITEL':"{} {}".format(semester.get_semestertyp_display(), semester.jahr),
		'ZEITSTEMPEL':zeitstempel.strftime("%d. %B %Y %H:%M"),
		'TABELLEN':tabellen,
		}
	text = replace_variables((GlobalSettings.objects.get()).liste_tex, replacements)
	
	filename = str(uuid.uuid4())
	filedir = "dokumente/export/{0}".format(semester_id)
	filepath = "dokumente/export/{0}/{1}{2}".format(semester_id, filename, '.tex') # extension enthält den Punkt
	pdffilepath = "dokumente/export/{0}/{1}{2}".format(semester_id, filename, '.pdf') # extension enthält den Punkt
	
	if(not os.path.isdir(os.path.join(BASE_DIR, filedir))):
		#os.makedirs(os.path.join('dokumente', filedir)) #TODO permissions
		shutil.copytree(os.path.join(BASE_DIR, "dokumente/export/static"), os.path.join(BASE_DIR, filedir))
	
	with open(os.path.join(BASE_DIR, filepath), 'w') as destination:
		destination.write(text)
	
	if(os.path.isfile(os.path.join(BASE_DIR, filepath))):
		# compile
		retval = subprocess.call(['pdflatex', "-interaction=nonstopmode", "{0}.tex".format(filename)], cwd=os.path.join(BASE_DIR, filedir))
		retval = subprocess.call(['pdflatex', "-interaction=nonstopmode", "{0}.tex".format(filename)], cwd=os.path.join(BASE_DIR, filedir))
		if(os.path.isfile(os.path.join(BASE_DIR, pdffilepath))):
			
			response = FileResponse(open(os.path.join(BASE_DIR, pdffilepath), 'rb'), content_type=mimetypes.guess_type(os.path.join(BASE_DIR, pdffilepath))[0])
			return response
		else:
			messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Die PDF-Datei wurde nicht erstellt. Bestimmt so ein LaTeX-Fehler. Bitte wenden Sie sich an den LaTeX-Guru Ihres Vertrauens.'})
		
	else:
		messages.append({'klassen':'alert-danger','text':'<strong>Herrje!</strong> Der Brief konnte nicht erstellt werden (.tex-Datei nicht erstellt).'})
	
	return antraege(request, semester_id, messages=messages)