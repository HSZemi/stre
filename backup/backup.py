#! /usr/bin/env python3

import sys
sys.path.append('../')
import stre.settings
import datetime
import subprocess

host = stre.settings.DATABASES['default']['HOST']
user = stre.settings.DATABASES['default']['USER']
password = stre.settings.DATABASES['default']['PASSWORD']
name = stre.settings.DATABASES['default']['NAME']
gpg_target_id = stre.settings.GPG_TARGET_ID

basename = "{0.year:04d}{0.month:02d}{0.day:02d}_{0.hour:02d}{0.minute:02d}{0.second:02d}".format(datetime.datetime.now())


commands = {}
commands_cleanup= {}

commands['sql'] = "mysqldump --host={host} --user={user} --password={password} --databases {name} --result-file={basename}.sql".format(host=host, user=user, password=password, name=name, basename=basename)

commands['briefe_zip'] = "zip -r {basename}_briefe.zip ../dokumente/briefe/*".format(basename=basename)
commands['export_zip'] = "zip -r {basename}_export.zip ../dokumente/export/*".format(basename=basename)
commands['nachweise_zip'] = "zip -r {basename}_nachweise.zip ../dokumente/nachweise/*".format(basename=basename)

commands['bundle'] = "zip {basename}.zip {basename}.sql {basename}_briefe.zip {basename}_export.zip {basename}_nachweise.zip".format(basename=basename)

commands['encrypt'] = "gpg --output {basename}.zip.gpg --encrypt --recipient {gpg_target_id} {basename}.zip".format(basename=basename, gpg_target_id=gpg_target_id)


commands_cleanup['sql'] = "rm {basename}.sql".format(basename=basename)
commands_cleanup['briefe_zip'] = "rm {basename}_briefe.zip".format(basename=basename)
commands_cleanup['export_zip'] = "rm {basename}_export.zip".format(basename=basename)
commands_cleanup['nachweise_zip'] = "rm {basename}_nachweise.zip".format(basename=basename)
commands_cleanup['zip'] = "rm {basename}.zip".format(basename=basename)



print("Storing backup as {}.gpg".format(basename))
subprocess.run(commands['sql'], shell=True)
subprocess.run(commands['briefe_zip'], shell=True)
subprocess.run(commands['export_zip'], shell=True)
subprocess.run(commands['nachweise_zip'], shell=True)
subprocess.run(commands['bundle'], shell=True)
subprocess.run(commands['encrypt'], shell=True)

print("Removing temporary files")
subprocess.run(commands_cleanup['sql'], shell=True)
subprocess.run(commands_cleanup['briefe_zip'], shell=True)
subprocess.run(commands_cleanup['export_zip'], shell=True)
subprocess.run(commands_cleanup['nachweise_zip'], shell=True)
subprocess.run(commands_cleanup['zip'], shell=True)

print("Backup file created.")
