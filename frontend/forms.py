from django import forms
from backend.models import Antrag, Dokument
from django.forms import ModelForm

class PasswordChangeForm(forms.Form):
	passwort_alt = forms.CharField(label='Aktuelles Passwort:', widget=forms.PasswordInput)
	passwort_neu1 = forms.CharField(label='Neues Passwort:', widget=forms.PasswordInput)
	passwort_neu2 = forms.CharField(label='Neues Passwort (noch einmal):', widget=forms.PasswordInput)

class AntragForm(ModelForm):
	class Meta:
		model = Antrag
		fields = ['versandanschrift', 'grund', 'kontoinhaber_in', 'iban', 'bic']
		
		labels = {
			'grund': 'Antragsgrund',
			'kontoinhaber_in': 'Kontoinhaber/in',
			'iban': 'IBAN',
			'bic': 'BIC',
		}
		
		help_texts = {
			'versandanschrift': 'An diese Adresse werden die Bescheide versandt.',
			'grund': 'Bitte wähle aus, weshalb du den Antrag auf Rückerstattung stellst.<br>Im nächsten Schritt kannst du dann die benötigten Nachweise hochladen.',
		}

class DokumentForm(ModelForm):
	class Meta:
		model = Dokument
		fields = ['nachweis']
		
		labels = {
			'nachweis': 'Nachweis-Art',
		}
		
		help_texts = {
			'nachweis': 'Zu welchem Nachweis gehört diese Datei?',
		}
	userfile = forms.FileField(help_text="Erlaubte Dateitypen: PDF, JPG, PNG", label="Datei:")