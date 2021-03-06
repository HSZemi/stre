from django.db import models
from django.contrib.auth.models import User, Group
from datetime import date

class Person(models.Model):
	user = models.OneToOneField(User, related_name='user', on_delete=models.CASCADE)
	adresse = models.TextField()
	
	NICHT_SOFORT_LOESCHEN = 'nicht_sofort_loeschen'
	SOFORT_LOESCHEN = 'sofort_loeschen'
	
	DATEN_SOFORT_LOESCHEN_CHOICES = (
		(NICHT_SOFORT_LOESCHEN, 'Nachweise werden für zwei Semester nach Antragstellung gespeichert und können in diesem Zeitraum für Folgeanträge genutzt werden. Das Nutzerkonto wird zwei Semester nach der letzten Antragstellung deaktiviert.'),
		(SOFORT_LOESCHEN, 'Nachweise werden gelöscht, sobald sie nicht mehr für die Bearbeitung oder Prüfung benötigt werden. Sie können danach nicht mehr für Folgeanträge genutzt werden. Das Nutzerkonto wird nach vollständiger Bearbeitung aller Anträge deaktiviert.')
	)
	
	daten_sofort_loeschen = models.CharField(
		max_length=25,
		choices=DATEN_SOFORT_LOESCHEN_CHOICES,
		default=SOFORT_LOESCHEN
	)
	
	def __str__(self):
		retval = "{} {}".format(self.user.first_name, self.user.last_name)
		if(retval == " "):
			retval = self.user.username
		return retval
    
class Semester(models.Model):
	WISE = 'WISE'
	SOSE = 'SOSE'
	
	SEMESTER_CHOICES = (
		(WISE, 'Wintersemester'),
		(SOSE, 'Sommersemester'),
	)
	
	semestertyp = models.CharField(
		max_length=4,
		choices=SEMESTER_CHOICES
	)
	
	jahr = models.CharField(max_length=9)
	
	betrag = models.DecimalField(max_digits=10, decimal_places=2)
	
	antragsfrist = models.DateField()
	anzeigefrist = models.DateField()
	erster_tag = models.DateField()
	letzter_tag = models.DateField()
	
	gruppe = models.ForeignKey(Group)
	
	class Meta:
		unique_together = ('semestertyp', 'jahr',)
	
	def antrag_moeglich(self):
		if(self.anzeigefrist >= date.today()):
			return True
		else:
			return False
		
	def frist_abgelaufen(self):
		if(self.antragsfrist < date.today()):
			return True
		else:
			return False
	
	def __str__(self):
		return "{0} {1} ({2} €)".format(self.get_semestertyp_display(), self.jahr, str(self.betrag).replace('.',','))

class Nachweis(models.Model):
	name = models.CharField(max_length=200)
	beschreibung = models.TextField(blank=True)
	datei = models.CharField(max_length=255, default='')
	hochzuladen = models.BooleanField(default=True)
	sort = models.IntegerField()
	
	def __str__(self):
		return self.name

class Antragsgrund(models.Model):
	identifier = models.CharField(max_length=2,unique=True)
	name = models.CharField(max_length=200)
	beschreibung = models.TextField(blank=True)
	nachweise = models.ManyToManyField(Nachweis)
	an_frist_gebunden = models.BooleanField()
	sort = models.IntegerField()
	
	def __str__(self):
		return "[{0}] {1}".format(self.identifier, self.name)

class Status(models.Model):
	name = models.CharField(max_length=200)
	klassen = models.CharField(max_length=200)
	sort = models.IntegerField()
	
	def hochladen_erlaubt(self):
		aktion_hochladen = (GlobalSettings.objects.get()).aktion_hochladen
		if(self.uebergang_from__set.filter(aktion=aktion_hochladen).exists()):
			return True
		else:
			return False
		
	def ueberweisungsbetrag_aendern_erlaubt(self):
		aktion_ueberweisungsbetrag_aendern = (GlobalSettings.objects.get()).aktion_ueberweisungsbetrag_aendern
		if(self.uebergang_from__set.filter(aktion=aktion_ueberweisungsbetrag_aendern).exists()):
			return True
		else:
			return False
		
	def zurueckziehen_erlaubt(self):
		aktion_zurueckziehen = (GlobalSettings.objects.get()).aktion_zurueckziehen
		if(self.uebergang_from__set.filter(aktion=aktion_zurueckziehen).exists()):
			return True
		else:
			return False
	
	def __str__(self):
		return self.name


class Briefvorlage(models.Model):
	name = models.CharField(max_length=200)
	betreff = models.CharField(max_length=200)
	anrede = models.CharField(max_length=200)
	brieftext = models.TextField()
	status = models.ForeignKey(Status)
	hat_nachweise = models.BooleanField()
	hat_begruendung = models.BooleanField()
	hat_freitext = models.BooleanField()
	sort = models.IntegerField()
	
	def __str__(self):
		return self.name

class Aktion(models.Model):
	name = models.CharField(max_length=200)
	user_explizit = models.BooleanField()
	staff_explizit = models.BooleanField()
	setzt_ueberweisungsbetrag = models.BooleanField()
	setzt_ueberweisungsbetrag_explizit = models.BooleanField(default=False)
	setzt_nachfrist1 = models.BooleanField()
	setzt_nachfrist2 = models.BooleanField()
	sort = models.IntegerField()
	briefvorlage = models.ForeignKey(Briefvorlage, null=True, blank=True, default=None)
	
	def __str__(self):
		return self.name

class Uebergang(models.Model):
	aktion = models.ForeignKey(Aktion)
	status_start = models.ForeignKey(Status, related_name='uebergang_from_set')
	status_end = models.ForeignKey(Status, related_name='uebergang_to_set')
	
	class Meta:
		unique_together = ('status_start', 'aktion',)
	
	def __str__(self):
		return "{0} -> ({1}) -> {2}".format(self.status_start.name, self.aktion.name, self.status_end.name)
	
class Antrag(models.Model):
	semester = models.ForeignKey(Semester)
	user = models.ForeignKey(Person)
	
	versandanschrift = models.TextField()
	grund = models.ForeignKey(Antragsgrund)
	
	freitext = models.TextField()
	
	kontoinhaber_in = models.CharField(max_length=400)
	iban = models.CharField(max_length=67) #maximal 34 Stellen + Leerzeichen
	bic = models.CharField(max_length=14) # maximal 11 Stellen, 4 Segmente, Leerzeichen sind unüblich
	
	status = models.ForeignKey(Status)
	nachfrist1 = models.DateField(null=True, default=None)
	nachfrist1_briefdatum = models.DateField(null=True, default=None)
	nachfrist2 = models.DateField(null=True, default=None)
	nachfrist2_briefdatum = models.DateField(null=True, default=None)
	ueberweisungsbetrag = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
	
	antragszeitpunkt = models.DateTimeField(auto_now_add=True)
	letzte_bearbeitung = models.DateTimeField(auto_now=True)
	
	class Meta:
		unique_together = ('semester', 'user',)
	
	def __str__(self):
		return "{0} {1} - {2}".format(self.grund.identifier, self.id, self.user)

class Dokument(models.Model):
	
	GRAU = 'badge-default'
	ROT = 'badge-danger'
	GELB = 'badge-warning'
	GRUEN = 'badge-success'
	BLAU = 'badge-info'
	
	MARKIERUNG_CHOICES = (
		(GRAU, 'Grau'),
		(ROT, 'Rot'),
		(GELB, 'Gelb'),
		(GRUEN, 'Grün'),
		(BLAU, 'Blau'),
	)
	
	markierung = models.CharField(
		max_length=30,
		choices=MARKIERUNG_CHOICES,
		default=GRAU
	)
	
	antrag = models.ForeignKey(Antrag)
	nachweis = models.ForeignKey(Nachweis)
	datei = models.CharField(max_length=1024)
	aktiv = models.BooleanField(default=True)
	timestamp = models.DateTimeField(auto_now_add=True)
	
	def __str__(self):
		return "Dokument #{0}".format(self.id)

	
class Brief(models.Model):
	antrag = models.ForeignKey(Antrag)
	vorlage = models.ForeignKey(Briefvorlage)
	datei = models.CharField(max_length=1024)
	briefdatum = models.DateField()
	timestamp = models.DateTimeField(auto_now_add=True)
	
class History(models.Model):
	timestamp = models.DateTimeField(auto_now_add=True)
	akteur = models.ForeignKey(User)
	antrag = models.ForeignKey(Antrag)
	uebergang = models.ForeignKey(Uebergang)
	ist_undo = models.BooleanField(default=False)
	
class AccountHistory(models.Model):
	timestamp = models.DateTimeField(auto_now_add=True)
	akteur = models.ForeignKey(User, related_name='account_history_akteur')
	account = models.ForeignKey(User, related_name='account_history_account', default=None)
	beschreibung = models.TextField()
	
class Begruendung(models.Model):
	name = models.CharField(max_length=200)
	text = models.TextField()
	sort = models.IntegerField()
	
	def __str__(self):
		return self.name

class GlobalSettings(models.Model):
	status_start = models.ForeignKey(Status)
	aktion_antrag_stellen = models.ForeignKey(Aktion, related_name='aktion_antrag_stellen')
	aktion_hochladen = models.ForeignKey(Aktion, related_name='aktion_hochladen')
	aktion_zurueckziehen = models.ForeignKey(Aktion, related_name='aktion_zurueckziehen')
	aktion_als_ueberwiesen_markieren = models.ForeignKey(Aktion, related_name='aktion_als_ueberwiesen_markieren')
	aktion_antragsdaten_bearbeiten = models.ForeignKey(Aktion, related_name='aktion_antragsdaten_bearbeiten')
	brief_tex = models.TextField()
	liste_tex = models.TextField()
	impressum_html = models.TextField()
	datenschutz_html = models.TextField()
	
	def save(self, *args, **kwargs):
		self.__class__.objects.exclude(id=self.id).delete()
		super(GlobalSettings, self).save(*args, **kwargs)

	@classmethod
	def load(cls):
		try:
			return cls.objects.get()
		except cls.DoesNotExist:
			return cls()
