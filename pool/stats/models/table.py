from django.db import models

from .sponsor import Sponsor


class Table(models.Model):

    name = models.TextField(blank=True)
    venue = models.ForeignKey(Sponsor, on_delete=models.CASCADE)

    def __str__(self):
        if self.name:
            return ", ".join([self.venue.name, self.name])
        else:
            return self.venue.name
