from django.db import models
from django.contrib.auth.models import User

class Person(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	matrikelnummer = models.IntegerField()
	anschrift = models.TextField()
    
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
	
	def __str__(self):
		return "{0} {1} ({2} €)".format(self.semestertyp, self.jahr, self.betrag)

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
	
class Antrag(models.Model):
	semester = models.ForeignKey(Semester)
	user = models.ForeignKey(Person)
	
	versandanschrift = models.TextField()
	grund = models.ForeignKey(Antragsgrund)
	
	letzte_bearbeitung = models.DateTimeField(auto_now=True)

class Aktion(models.Model):
	timestamp = models.DateTimeField(auto_now_add=True)
	akteur = models.ForeignKey(User)
	antrag = models.ForeignKey(Antrag)
	aktion = models.CharField(max_length=200)


