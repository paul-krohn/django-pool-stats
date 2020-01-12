from django.db import models
from django.urls import reverse


class Player(models.Model):
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    display_name = models.CharField(max_length=128, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.display_name or "%s %s" % (self.first_name, self.last_name)

    def as_dict(self):
        return {
            'name': str(self),
            'url': reverse('player', kwargs={'player_id': self.id}),
        }

    class Meta:
        # Players with a display_name that sorts differently from their
        # first name will appear to be out of order in form selects.
        ordering = ['first_name', 'last_name']


class AwayPlayer(Player):
    class Meta:
        proxy = True


class HomePlayer(Player):
    class Meta:
        proxy = True
