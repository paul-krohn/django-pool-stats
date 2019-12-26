from django.db import models


class Sponsor(models.Model):
    name = models.CharField(max_length=200)
    sort_name = models.TextField(blank=True, max_length=200)
    address = models.CharField(max_length=200)
    link = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.sort_name = self.name.replace('The ', '')
        super(Sponsor, self).save(*args, **kwargs)

    class Meta:
        ordering = ['sort_name']
