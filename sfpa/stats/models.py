from django.db import models


class Season(models.Model):
    name = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date of first week')

    def __str__(self):
        return self.name


class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.name
