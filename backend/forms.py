from django import forms
from backend.models import Antrag, Dokument
from django.forms import ModelForm, ValidationError
import datetime

class LoginForm(forms.Form):
	username = forms.CharField(label='Loginname:')
	password = forms.CharField(label='Passwort:', widget=forms.PasswordInput)

class PasswordChangeForm(forms.Form):
	passwort_alt = forms.CharField(label='Aktuelles Passwort:', widget=forms.PasswordInput)
	passwort_neu1 = forms.CharField(label='Neues Passwort:', widget=forms.PasswordInput)
	passwort_neu2 = forms.CharField(label='Neues Passwort (noch einmal):', widget=forms.PasswordInput)
	
class UeberweisungsbetragForm(forms.Form):
	def __init__(self, max_value, *args, **kwargs):
		super(UeberweisungsbetragForm, self).__init__(*args, **kwargs)
		self.fields['ueberweisungsbetrag'] = forms.DecimalField(min_value=0, max_value=max_value, max_digits=10, decimal_places=2, label='Überweisungsbetrag')
		
class NachfristForm(forms.Form):
	nachfrist = forms.DateField()

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

class BriefBegruendungForm(forms.Form):
	def __init__(self, nachweise, begruendungen, freitext, *args, **kwargs):
		super(BriefBegruendungForm, self).__init__(*args, **kwargs)
		if(nachweise):
			self.fields['fehlende_nachweise'] = forms.ModelMultipleChoiceField(queryset=nachweise, label="Nachweise", help_text="Wähle hier die fehlenden Nachweise aus.", widget=forms.CheckboxSelectMultiple, required=False)
		if(begruendungen):
			self.fields['begruendungen'] = forms.ModelMultipleChoiceField(queryset=begruendungen, label="Nachweise", help_text="hjelp_texst", widget=forms.CheckboxSelectMultiple, required=False)
		if(freitext):
			self.fields['freitext'] = forms.CharField(widget=forms.Textarea, required=False)
		
	step = forms.CharField(widget=forms.HiddenInput(),initial='BriefBegruendungForm')

class BriefErstellenForm(forms.Form):
	step = forms.CharField(widget=forms.HiddenInput(),initial='BriefErstellenForm')
	briefdatum = forms.DateField(initial=datetime.date.today())
	anschrift = forms.CharField(widget=forms.Textarea)
	betreff = forms.CharField()
	anrede = forms.CharField()
	brieftext = forms.CharField(widget=forms.Textarea)

class BulkAlsUeberwiesenMarkierenForm(forms.Form):
	def __init__(self, antraege, *args, **kwargs):
		super(BulkAlsUeberwiesenMarkierenForm, self).__init__(*args, **kwargs)
		self.fields['antraege'] = forms.ModelMultipleChoiceField(queryset=antraege, help_text="", label="Als überwiesen markieren:", widget=forms.CheckboxSelectMultiple)

class AccountForm(forms.Form):
	matrikelnummer = forms.IntegerField(label="Matrikelnummer*", min_value=1000)
	vorname = forms.CharField(label="Vorname(n)*", max_length=30)
	nachname = forms.CharField(label="Nachname(n)*", max_length=30)
	email = forms.EmailField(label="E-Mail-Adresse",required=False, help_text="Ohne Angabe einer gültigen E-Mail-Adresse stehen einige Funktionen nicht zur Verfügung.", max_length=254)
	adresse = forms.CharField(widget=forms.Textarea, label="Anschrift*", help_text="Besteht in der Regel aus Straße, Hausnummer, PLZ und Ort.<br><span style='color:red'><b>Achtung!</b> Eine Änderung dieser Adresse ändert <b>NICHT</b>, an welche Anschrift die Bescheide verschickt werden!</span>")

class PasswortZuruecksetzenForm(forms.Form):
	matrikelnummer = forms.IntegerField(label="Matrikelnummer", min_value=1000)