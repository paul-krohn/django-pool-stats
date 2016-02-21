from django.db import models


class Season(models.Model):
    name = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date of first week')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Sponsor(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    link = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(Sponsor, null=True)
    name = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.name
