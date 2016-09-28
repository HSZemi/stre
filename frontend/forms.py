from django import forms
from backend.models import Antrag, Dokument, Semester
from django.forms import ModelForm, ValidationError
from localflavor.generic.forms import BICFormField, IBANFormField
from datetime import date

class LoginForm(forms.Form):
	username = forms.IntegerField(label='Loginname:')
	password = forms.CharField(label='Passwort:', widget=forms.PasswordInput)

class PasswordChangeForm(forms.Form):
	passwort_alt = forms.CharField(label='Aktuelles Passwort:', widget=forms.PasswordInput)
	passwort_neu1 = forms.CharField(label='Neues Passwort:', widget=forms.PasswordInput)
	passwort_neu2 = forms.CharField(label='Neues Passwort (noch einmal):', widget=forms.PasswordInput)

class AccountForm(forms.Form):
	email = forms.EmailField(label="E-Mail-Adresse",required=False, help_text="Ohne Angabe einer gültigen E-Mail-Adresse stehen einige Funktionen nicht zur Verfügung.")
	adresse = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Anschrift", help_text="<span style='color:red'><b>Achtung!</b> Eine Änderung dieser Adresse ändert <b>NICHT</b>, an welche Anschrift die Bescheide verschickt werden!</span><br>Die Adresse für den Versand der Bescheide kannst du nur persönlich in der Sprechstunde des Ausschusses ändern lassen.")

class AntragForm(ModelForm):
	class Meta:
		model = Antrag
		fields = [ 'grund', 'freitext', 'versandanschrift','kontoinhaber_in']
		
		labels = {
			'grund': 'Antragsgrund',
			'freitext' : 'Hinweise zum Antrag',
			'kontoinhaber_in': 'Kontoinhaber/in',
			'iban': 'IBAN',
			'bic': 'BIC',
		}
		
		help_texts = {
			'versandanschrift': 'An diese Adresse werden die Bescheide versandt.',
			'grund': 'Bitte wähle aus, weshalb du den Antrag auf Rückerstattung stellst.<br>Im nächsten Schritt kannst du dann die benötigten Nachweise hochladen.',
			'freitext': 'Weitere Hinweise zum Antrag wie z. B. der Verweis auf einen früheren (auf Papier gestellten) Antrag, aus dem Nachweise übernommen werden sollen, oder die Erläuterung eines sonstigen Grundes.',
		}
	
	def __init__(self, gruende, *args, **kwargs):
		super(AntragForm, self).__init__(*args, **kwargs)
		self.fields['grund'] = forms.ModelChoiceField(queryset=gruende, label="Antragsgrund", help_text="Bitte wähle aus, weshalb du den Antrag auf Rückerstattung stellst.<br>Im nächsten Schritt kannst du dann die benötigten Nachweise hochladen.", widget=forms.Select)	
		self.fields['freitext'] = forms.CharField(widget=forms.Textarea, label='Hinweise zum Antrag', help_text='Weitere Hinweise zum Antrag wie z. B. der Verweis auf einen früheren (auf Papier gestellten) Antrag, aus dem Nachweise übernommen werden sollen, oder die Erläuterung eines sonstigen Grundes.', required=False)	
		
	iban = IBANFormField(label="IBAN", help_text="Auf dieses Konto wird der Rückerstattungsbetrag überwiesen, falls dein Antrag erfolg hat.")
	bic = BICFormField(label="BIC")
	
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
	formname = forms.CharField(widget=forms.HiddenInput(),initial='DokumentForm')
	
class DokumentUebertragenForm(ModelForm):
	class Meta:
		model = Dokument
		fields = ['nachweis']
		
		labels = {
			'nachweis': 'Nachweis-Art',
		}
		
		help_texts = {
			'nachweis': 'Zu welchem Nachweis gehört diese Datei?',
		}
	formname = forms.CharField(widget=forms.HiddenInput(),initial='DokumentUebertragenForm')
	
	def __init__(self, dokumente, *args, **kwargs):
		super(DokumentUebertragenForm, self).__init__(*args, **kwargs)
		self.fields['userfile'] = forms.ModelChoiceField(queryset=dokumente, help_text="Du kannst die Dateien im alten Antrag aufrufen.", label="Datei:")
	

class RegistrierungForm(forms.Form):
	semester = forms.ModelChoiceField(queryset=Semester.objects.filter(anzeigefrist__gte=date.today()).order_by('-jahr'), label="Semester*", help_text="Für welches Semester soll der Antrag gestellt werden?")
	matrikelnummer = forms.IntegerField(label="Matrikelnummer*", min_value=1000)
	passwort = forms.CharField(label="Passwort wählen*", widget=forms.PasswordInput(), help_text="Dieses Passwort benötigst du, um deinen Antragsstatus einzusehen, Nachweise hochzuladen und weitere Anträge zu stellen. Wer deine Matrikelnummer und dein Passwort errät, hat Zugriff auf all deine Daten und Dokumente. Wähle deshalb ein sicheres Passwort!")
	vorname = forms.CharField(label="Vorname(n)*", max_length=30)
	nachname = forms.CharField(label="Nachname(n)*", max_length=30)
	email = forms.EmailField(label="E-Mail-Adresse",required=False, help_text="Ohne Angabe einer gültigen E-Mail-Adresse stehen einige Funktionen nicht zur Verfügung.", max_length=254)
	adresse = forms.CharField(widget=forms.Textarea, label="Anschrift*", help_text="Besteht in der Regel aus Straße, Hausnummer, PLZ und Ort.")

class PasswortResetForm(forms.Form):
	matrikelnummer = forms.IntegerField(label="Matrikelnummer", min_value=1000)