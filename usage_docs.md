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

* Select the week (only weeks from the current season should be displayed). If you click "save and continue editing", then the list of teams in the drop-down will include only those not yet scheduled for that week.
* select the home and away teams.
* click one of the save buttons

Any match that is scheduled can be entered ahead of time, for example the first few weeks of intra-divisional play.

### Adding players

Ideally, the league will hear about new players before they need to appear on a submitted score sheet, but this is not always possible; in any case, players can be created and added to a team, and a score sheet, after the fact.

* check if the player is already in the system
* create the player  in the Player section of the admin UI
* find the team you need to add them to in the Teams section of the admin UI
* edit the team, adding the player

_Note:_ while editing teams to add players does work in the the mobile UI, it is a bit counter-intuitive and is probably best done in a desktop browser the first few times through.


### Processing score sheets

First, add any new players you have heard about, so that you can fix up any score sheets they should be on.

In the score sheets section of the admin area, filter all the score sheets for the week you are working on.

There are edit and view links for each score sheet (suggestion: open these in a new tab), so you can verify that:

* each game has a home and away player (no '--' in the lineups).
* each game has a marked winner
* substitutions comply with the rules, ie no player has been subbed back in.
* extra or incomplete submissions have been deleted

There are two tasks available (in the Action menu at the top of the list of score sheets) to apply to all the selected score sheets:
* delete (useful for incomplete submissions)
* Make official

Once you are happy with one or more score sheets, select the ones you want (or all of the displayed ones, using the check box at the top of the left-hand column), and select "Make official" from the Action menu; this will trigger a recalculation of the related player and team stats for the season, so it may take a few seconds.
