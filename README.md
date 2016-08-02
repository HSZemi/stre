# stre
Ein Onlinesystem für die Studiticket-Rückerstattung in Entwicklung. Oder auch nicht. Mal sehen.


# Setup
  * pip3 install django
  * pip3 install django-localflavor (für BIC- und IBAN-Felder)
  * sudo apt-get install libmysqlclient-dev (MySQL only)
  * pip3 install mysqlclient (MySQL only)

  * Tabelle mit Kollation 'utf8_bin' erstellen
  * Datenbankzugriff in stre/settings.py einrichten (im Abschnitt DATABASES = {})
  * python3 manage.py makemigrations
  * python3 manage.py migrate

  * Im Admin-Interface (/admin/) mit admin:Zeitungsartikel einloggen und ein Semester anlegen