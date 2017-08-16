# stre
Ein Onlinesystem für die Studiticket-Rückerstattung in Entwicklung. Oder auch nicht. Mal sehen.


# Setup
  * pip3 install django
  * pip3 install django-localflavor (für BIC- und IBAN-Felder)
  * pip3 install django-axes (für Login-Kontrolle)
  * sudo apt-get install libmysqlclient-dev (MySQL only)
  * pip3 install mysqlclient (MySQL only)

  * latex installieren (für Brieferstellung)

  * Tabelle mit Kollation 'utf8_bin' erstellen
  * stre/settings.py.template in settings.py umbenennen
  * Datenbankzugriff in stre/settings.py einrichten (im Abschnitt DATABASES = {})
  * dokumente/briefe/static/briefkopf.pdf.template in briefkopf.pdf umbenennen bzw. ersetzen
  * python3 manage.py makemigrations
  * python3 manage.py migrate

  * Im Admin-Interface (/admin/) mit admin:Zeitungsartikel einloggen und eine Gruppe pro Semester anlegen
  * Dann im Admin-Interface die Semester anlegen und die zugehörige Gruppe zuweisen
  * Nutzer müssen in der zugehörigen Gruppe sein um ein Semester bearbeiten/ansehen zu dürfen

# Übersetzungen

django-admin makemessages --locale de --locale en
django-admin compilemessages