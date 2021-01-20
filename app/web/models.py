from django.db.models import *

class ChefForm(Model):
    fullname = CharField(max_length=200, blank=True)
    contactInfo = CharField(max_length=200, blank=True)
    city = CharField(max_length=200, blank=True)
    commune = CharField(max_length=200, blank=True)
    message = CharField(max_length=2000, blank=True)

    def __str__(self):
        return self.fullname
