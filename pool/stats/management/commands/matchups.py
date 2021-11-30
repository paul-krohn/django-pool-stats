from django.core.management.base import BaseCommand

from ...models import Match, PlayerSeasonSummary, ScoreSheet, Season


def get_previous_season(season_id):
    this_season = Season.objects.get(id=season_id)
    # now get the seasons before this one (ie excluding this one), ordered by date
    seasons = Season.objects.filter(pub_date__lt=this_season.pub_date).order_by('-pub_date')
    return seasons[0] or None


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('the_id', type=int)
        parser.add_argument('-s', dest='scoresheet', default=False, action='store_true')
        parser.add_argument('-k', dest='skip_players', nargs='+', type=int)

    @staticmethod
    def get_matchups(options):
        print('the players to skip are: {}'.format(options['skip_players']))
        matchups = []
        if options['scoresheet']:
            scoresheet = ScoreSheet.objects.get(id=options['the_id'])
            for game in scoresheet.games.all():
                ap_summary = PlayerSeasonSummary.objects.get(season=scoresheet.match.season, player=game.away_player)
                hp_summary = PlayerSeasonSummary.objects.get(season=scoresheet.match.season, player=game.home_player)
                matchups.append({'away': ap_summary, 'home': hp_summary})
        else:
            match = Match.objects.get(id=options['the_id'])
            for ap in match.away_team.players.all():
                if ap.id in options['skip_players']:
                    continue
                for hp in match.home_team.players.all():
                    if hp.id in options['skip_players']:
                        continue
                    matchups.append({
                        'away': PlayerSeasonSummary.objects.get(
                            season=match.season, player=ap
                        ),
                        'home': PlayerSeasonSummary.objects.get(
                            season=match.season, player=hp
                        )
                    })
        return matchups

    def handle(self, *args, **options):
        e = Elo(beta=80)
        matchups = self.get_matchups(options)
        away_win_cumul = 0.0
        for matchup in matchups:
            away_win_p = e.expect(matchup['away'].elo, matchup['home'].elo)
            away_win_cumul += away_win_p
            print("{ap} vs {hp}: {p:.1f}%".format(
                ap=matchup['away'].player, hp=matchup['home'].player, p=away_win_p * 100)
            )
        # print("expected wins for {}: {:.2f}".format(match.away_team, away_win_cumul))
        print("expected wins for away: {:.2f}".format(away_win_cumul / ( len(matchups) / 16.0)))