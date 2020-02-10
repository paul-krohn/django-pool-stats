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
