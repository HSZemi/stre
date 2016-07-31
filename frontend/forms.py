from django import forms
from backend.models import Antrag, Dokument, Semester
from django.forms import ModelForm, ValidationError
from datetime import date


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

class RegistrierungForm(forms.Form):
	semester = forms.ModelChoiceField(queryset=Semester.objects.filter(antragsfrist__gte=date.today()).order_by('-jahr'), label="Semester*", help_text="Für welches Semester soll der Antrag gestellt werden?")
	matrikelnummer = forms.IntegerField(label="Matrikelnummer*", min_value=1000)
	passwort = forms.CharField(label="Passwort wählen*", widget=forms.PasswordInput(), help_text="Dieses Passwort benötigst du, um deinen Antragsstatus einzusehen, Nachweise hochzuladen und weitere Anträge zu stellen. Wer deine Matrikelnummer und dein Passwort errät, hat Zugriff auf all deine Daten und Dokumente. Wähle deshalb ein sicheres Passwort!")
	vorname = forms.CharField(label="Vorname(n)*")
	nachname = forms.CharField(label="Nachname(n)*")
	email = forms.EmailField(label="E-Mail-Adresse",required=False, help_text="Ohne Angabe einer gültigen E-Mail-Adresse stehen einige Funktionen nicht zur Verfügung.")
	adresse = forms.CharField(widget=forms.Textarea, label="Anschrift*", help_text="Besteht in der Regel aus Straße, Hausnummer, PLZ und Ort.")