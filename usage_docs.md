## Once-a-season tasks

### Creating a new season

Seasons are a top-level object in Django, just go ahead and create one. Unset **is default** on the current default season before setting it on the new one.


### Divisions

Divisions need to be created each season, create new ones with the desired labels and set the season to the one created above.

### Players

Players persist across seasons, so you will only need to add new players at the start of each season, or as they join.

Use the "display name" field to override the default of "First Last".

The email address field is not displayed on the public web site, just in the admin area.

### Teams

Creating teams can be a bit tedious, and many change only slightly from season to season. To help with this, teams can effectively be copied:

1. Open the team you want to copy
1. Change the season to the current season
1. Click "save as new" -- **not** save!
1. Add and remove players
1. Adjust the name, if needed
1. Choose the new team's division for this season

### Weeks

Set up the weeks of play for the entire season, they just need a name, date, and season.

## Weekly tasks

### Create matches

In the Matches section of the admin area, click the "Create Match" button.

Select the week (only weeks from the current season should be displayed), then the home and away teams.

Any match that is scheduled can be entered ahead of time, for exxample the first few weeks of intra-divisional play.

### Processing score sheets

First, add any new players you have heard about, so that you can fix up any score sheets they should be on.

In the score sheets section of the admin area, filter all the score sheets for the week you are working on. 

There are edit and view links for each score sheet, so you can verify that:

* each game has a home and away player, in no '--' in the lineups.
* each game has a marked winner
* substitutions comply with the rules, ie no player has been subbed back in.

Then, click on the "Team A @ Team B" label, and tick the "Official" box, and save the match.

Once you have made all the score sheets official:
* delete any extra submissions.
* from the public view, under the admin menu, click the "Update team stats" and then "Update player stats" links. This will recalculate the rankings for all the teams and players in the current season.