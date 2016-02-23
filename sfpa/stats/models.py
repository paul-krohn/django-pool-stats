from django.db import models


class Sponsor(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    link = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Season(models.Model):
    name = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date of first week')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Player(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    display_name = models.CharField(max_length=128, null=True, blank=True)

    def __str__(self):
        return self.display_name or "%s %s" % (self.first_name, self.last_name)


class Division(models.Model):
    season = models.ForeignKey(Season)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(Sponsor, null=True)
    division = models.ForeignKey(Division, null=True)
    name = models.CharField(max_length=200)
    players = models.ManyToManyField(Player, blank=True)


class Week(models.Model):
    season = models.ForeignKey(Season)
    date = models.DateField(null=True, blank=True)
    name = models.CharField(max_length=32, null=True)

    def __str__(self):
        return self.name
