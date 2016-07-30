from django.contrib import admin

# Register your models here.
from .models import Semester
from .models import Antragsgrund
from .models import Nachweis
from .models import Status
from .models import Person
from .models import GlobalSettings
from .models import Aktion

admin.site.register(Semester)
admin.site.register(Antragsgrund)
admin.site.register(Nachweis)
admin.site.register(Status)
admin.site.register(Person)
admin.site.register(GlobalSettings)
admin.site.register(Aktion)