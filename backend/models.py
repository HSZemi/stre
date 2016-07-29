from django.db import models
from django.contrib.auth.models import User
from datetime import date

class Person(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	geburtsort = models.CharField(max_length=200)
	adresse = models.TextField()
	
	def __str__(self):
		return self.user.username
    
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
	
	def antrag_moeglich(self):
		if(self.antragsfrist >= date.today()):
			return True
		else:
			return False
	
	def __str__(self):
		return "{0} {1} ({2} €)".format(self.get_semestertyp_display(), self.jahr, str(self.betrag).replace('.',','))

class Antragsgrund(models.Model):
	identifier = models.CharField(max_length=2)
	name = models.CharField(max_length=200)
	beschreibung = models.TextField()
	
	def __str__(self):
		return "[{0}] {1}".format(self.identifier, self.name)

class Nachweis(models.Model):
	name = models.CharField(max_length=200)
	beschreibung = models.TextField()
	
	def __str__(self):
		return self.name

class Status(models.Model):
	name = models.CharField(max_length=200)
	klassen = models.CharField(max_length=200)
	
	def __str__(self):
		return self.name

class Antrag(models.Model):
	semester = models.ForeignKey(Semester)
	user = models.ForeignKey(Person)
	
	versandanschrift = models.TextField()
	grund = models.ForeignKey(Antragsgrund)
	
	kontoinhaber_in = models.CharField(max_length=400)
	iban = models.CharField(max_length=67) #maximal 34 Stellen + Leerzeichen
	bic = models.CharField(max_length=14) # maximal 11 Stellen, 4 Segmente, Leerzeichen sind unüblich
	
	status = models.ForeignKey(Status)
	
	antragszeitpunkt = models.DateTimeField(auto_now_add=True)
	letzte_bearbeitung = models.DateTimeField(auto_now=True)

class Dokument(models.Model):
	antrag = models.ForeignKey(Antrag)
	nachweis = models.ForeignKey(Nachweis)
	datei = models.CharField(max_length=1024)
	aktiv = models.BooleanField()

class Aktion(models.Model):
	timestamp = models.DateTimeField(auto_now_add=True)
	akteur = models.ForeignKey(User)
	antrag = models.ForeignKey(Antrag)
	aktion = models.CharField(max_length=200)

class GlobalSettings(models.Model):
	status_start = models.ForeignKey(Status)
	
	def save(self, *args, **kwargs):
		self.__class__.objects.exclude(id=self.id).delete()
		super(GlobalSettings, self).save(*args, **kwargs)

	@classmethod
	def load(cls):
		try:
			return cls.objects.get()
		except cls.DoesNotExist:
			return cls()
