from django.contrib import admin

# Register your models here.
from .models import Semester
from .models import Antragsgrund
from .models import Nachweis

admin.site.register(Semester)
admin.site.register(Antragsgrund)
admin.site.register(Nachweis)