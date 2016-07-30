from django.shortcuts import render
from django.http import FileResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from backend.models import Dokument
import os
import mimetypes

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
@group_required('Antragstellung')
def datei(request, dokument_id):
	dokument_id = int(dokument_id)
	
	dokument = get_object_or_404(Dokument, pk=dokument_id)
	
	if(dokument.antrag.user.user.id == request.user.id):
		response = FileResponse(open(os.path.join('dokumente', dokument.datei), 'rb'), content_type=mimetypes.guess_type(dokument.datei)[0])
		#response['Content-Disposition'] = 'attachment; filename={0}'.format(os.path.basename(dokument.datei))
		return response
	else:
		raise Http404("Document does not exist")