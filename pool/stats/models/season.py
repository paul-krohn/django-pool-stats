from django.db import models


class Season(models.Model):
    name = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date of first week')
    is_default = models.BooleanField(default=False)
    minimum_games = models.IntegerField(null=True)

    def __str__(self):
        return self.name
