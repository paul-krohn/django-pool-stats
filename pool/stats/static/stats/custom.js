/*
  Sets the function called on keyup on a filter_box_selector (ie text input). Filters
  visibility of table body rows that match the table_body_selector.
*/
function filterer(filter_box_selector, table_body_selector){
    $(filter_box_selector).keyup(function () {
        var rex = new RegExp($(filter_box_selector).val(), 'i');
        $(table_body_selector + ' tr').hide();
        $(table_body_selector + ' tr').filter(function () {
            return rex.test($(this).text());
        }).show();
    });
}

function reset_last_game(){
    // Find the last checked radio button and uncheck it
    var set_radio_buttons = $('input[type=radio]').filter(function () {
        return this.checked === true;
    });
    if (set_radio_buttons.length) {
        set_radio_buttons[set_radio_buttons.length - 1].checked = false;
        return $(set_radio_buttons[set_radio_buttons.length - 1]).data('game-order');
    }
}


function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function ScoreSheet(args) {
    let app = new Vue({
        el: '#scoresheet',
        data: {
            games: [],
            teams: {
                // this pre-population suppresses a warning that team.(home|away) is undefined
                "home": {
                    "url": null
                },
                "away": {
                    "url": null
                }
            },
            editable: false,
            owner: false,
            editing: false,
            gameFormUrl: args.gameUpdateUrl,
            dataUrl: args.dataUrl,
            gameGroupSize: args.gameGroupSize,
            csrfToken: args.csrfToken,
        },

        watch: {
            // IDK if _both_ the `editable` and `owner` callbacks are needed.
            editable: function () {
                this.editing = this.editable && this.owner;
            },
            owner: function () {
                this.editing = this.editable && this.owner;
            },
        },
        methods: {
            updateData: function () {
                return new Promise((resolve, reject) => {
                    let self = this;
                    $.ajax({
                        url: this.dataUrl,
                        dataType: 'json',
                        success: function (data) {
                            self.teams = data.teams;
                            self.games = data.games;
                            self.editable = data.editable;
                            self.owner = data.owner;
                            resolve();
                        },
                        headers: {
                            Accept: "application/json",
                        }
                    });
                });
            },
            displayDate: function (dateString) {
                let timestamp = new Date(dateString);
                return timestamp.toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'});
            },
            editMode: function (amIEditing) {
                if (this.editing !== amIEditing) {
                    this.editing = amIEditing;
                    $('#is-editing-buttons').find('.btn').toggleClass('btn-primary').toggleClass('btn-default');
                }
                if (this.editing) {
                    $('#lineup-controls-wrapper').removeClass('hidden');
                } else {
                    $('#lineup-controls-wrapper').addClass('hidden');
                }
            },
            isOdd: function (number) {
                return number % 2;
            },
            gameWrapperClasses: function (number) {
                let base_classes = [];
                if (this.isOdd(number)) {
                    base_classes.push('scoresheet-odd');
                }
                return base_classes.join(' ');
            },
            matchupButtonId: function (matchup, participant) {
                return ("matchup_button_" + matchup.id + '_' + participant.id);
            },
            confirmResetLastGame: function () {
                $.confirm({
                    text: 'Reset last game?',
                    confirm: this.resetLastGame,
                });
            },
            resetLastGame: function () {
                let validWinners = ['away', 'home'];
                let scoredGames = this.games.filter(b => validWinners.includes(b.winner));
                if (scoredGames.length) {
                    let game = scoredGames[scoredGames.length - 1];
                    game.winner = '';
                    this.submitGame(game);
                }
            },
            getMarkGameText: function (game, ha) {
                if (game.winner === '') {
                    return ha.charAt(0).toUpperCase();
                } else if (game.winner === ha) {
                    return '&#10003;';
                } else {
                    return '&ndash;';
                }
            },
            getGameMarkClasses: function (game, ha) {
                let commonClasses = ['btn', 'btn-sm', 'mark-winner'];
                let winnerClass = 'btn-primary';
                let loserClass = 'btn-default';
                if (game.winner === ha) {
                    commonClasses.push(winnerClass)
                } else {
                    commonClasses.push(loserClass)
                }
                return commonClasses;
            },
            markGame: function (game, ha) {
                if (this.editing) {
                    game.winner = ha;
                    this.submitGame(game);
                }
            },
            submitGame: function (game) {
                let self = this;
                $.ajaxSetup({
                    beforeSend: function (xhr, settings) {
                        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                            xhr.setRequestHeader("X-CSRFToken", self.csrfToken);
                        }
                    },
                    dataType: 'application/json',
                });
                $.ajax({
                    type: "POST",
                    url: self.gameFormUrl,
                    dataType: "json",
                    data: {
                        "game_id": game.id,
                        "winner": game.winner,
                        "table_run": game.table_run,
                        "forfeit": game.forfeit,
                    },
                    success: function (response) {
                        self.updateData();
                    },
                });
            },
            toggleGameDetails: function () {
                $(".game_attributes").each(function (i, aDiv) {
                    if ($(aDiv).css('display') === 'none') {
                        $(aDiv).css('display', 'block');
                    } else {
                        $(aDiv).css('display', 'none');
                    }
                });
            },
        },
        mounted: function () {
            this.updateData();
        },
    });
}