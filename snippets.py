from stats.models import Tournament
from stats.models import Player
from stats.models import Participant


player_names = ['Krohn', 'West', 'Talevi', 'Piaget']

# pk = Player.objects.get(last_name='Krohn')
# pw = Player.objects.get(last_name='West')
# rp = Player.objects.get(last_name='Piaget')
# jt = Player.objects.get(last_name='Talevi')
#
# p0 = P

# this is tournament with id 2
t = Tournament(
    name='sample tournament',
    season_id=3,
    elimination='single',
)

for player_name in player_names:
    player = Player.objects.get(last_name=player_name)
    participant = Participant(
        type='player',
        tournament=t,
        player=player
    )
    participant.save()

print(t)
# t.participants.add(pk)
# t.participants.add(pw)
# t.participants.add(rp)
# t.participants.add(jt)
#
# t = Tournament.objects.get(id=2)

more_player_names = ['Hudson', 'Reilly', 'Black Golde', 'Rogers']

t2 = Tournament(
    name='8ball qualifier 2',
    season_id=3,
    elimination='double',
)
t2.save()

for player_name in player_names + more_player_names:
    player = Player.objects.get(last_name=player_name)
    participant = Participant(
        type='player',
        tournament=t2,
        player=player
    )
    participant.save()


from stats.models import Tournament
t2 = Tournament.objects.get(id=2)
t2.create_matchups()

####
from stats.models import Tournament, Participant
ch = Tournament(name="individual championship", season_id=3, elimination='double', type='player')
ch.save()

players = Player.objects.filter(id__lt=156).order_by('id')
for player in players:
    participant = Participant(
        type='player',
        tournament=ch,
        player=player
    ).save()

ch.create_brackets()
ch.create_rounds()
for br in ch.bracket_set.all():
    for rd in br.round_set.all():
        rd.create_matchups()
