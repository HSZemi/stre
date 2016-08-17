from django.shortcuts import render
from django.conf import settings
from django.http import FileResponse, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from backend.models import Dokument, Brief
import os
import mimetypes

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