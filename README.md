# stre
Ein Onlinesystem für die Studiticket-Rückerstattung in Entwicklung. Oder auch nicht. Mal sehen.


# Setup
  * pip3 install django
  * sudo apt-get install libmysqlclient-dev (MySQL only)
  * pip3 install mysqlclient (MySQL only)

  * Datenbankzugriff in stre/settings.py einrichten (im Abschnitt DATABASES = {})
  * python3 manage.py makemigrations
  * python3 manage.py migrate
