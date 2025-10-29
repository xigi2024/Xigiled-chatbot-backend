import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myassistant.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute('DROP TABLE IF EXISTS "Alexa_chatmessage"')
cursor.execute('DROP TABLE IF EXISTS "Alexa_chatsession"')
cursor.execute('DROP TABLE IF EXISTS "Alexa_product"')
cursor.execute('DROP TABLE IF EXISTS "Alexa_knowledgebase"')
print('Tables dropped successfully')
