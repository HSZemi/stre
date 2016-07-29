from django.http import HttpResponse


def login(request):
    return HttpResponse("Hello, world. You're at the backend login.")

def dashboard(request):
    return HttpResponse("Hello, world. You're at the backend dashboard.")

def antraege(request):
    return HttpResponse("Hello, world. You're at the antraege page.")

def antrag(request, antrag_id):
    antrag_id = int(antrag_id)
    return HttpResponse("Hello, world. You're at the antrag {0} page.".format(antrag_id))

def konfiguration(request):
    return HttpResponse("Hello, world. You're at the konfiguration page.")
