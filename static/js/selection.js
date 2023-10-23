/**
 * Map from selection id (e.g., "selection-0") to the Characters
 */
let original_ontologies = ["Technical_Jargon", "Bad_Math", "Encyclopedic", "Commonsense", "Needs_Google", "Grammar_Usage", "Off-prompt", "Redundant", "Self-contradiction", "Incoherent"]
let black_text_errors_types = ["Commonsense", "Grammar_Usage", "Off-prompt"]
var error_types_dict = {
    "Technical_Jargon": "Technical Jargon",
    "Bad_Math" : "Bad Math",
    "Encyclopedic" : "Wrong: Encyclopedic",
    "Commonsense" : "Wrong: Commonsense",
    "Needs_Google" : "Needs Google",
    "Grammar_Usage" : "Grammar / Usage",
    "Off-prompt" : "Off-prompt",
    "Redundant" : "Redundant",
    "Self-contradiction" : "Self-contradiction",
    "Incoherent" : "Incoherent"
};
var situation_text = {};
var old_value = ""

function substitute(input_text) {
    let new_input_text = input_text.replace(/,/g, "_SEP_");
    new_input_text = new_input_text.replace(/"/g, "_QUOTE_");
    new_input_text = new_input_text.replace(/</g, "_LEFT_");
    new_input_text = new_input_text.replace(/>/g, "_RIGHT_");
    new_input_text = new_input_text.replace(/[\r\n]+/g, "_NEWLINE_");
    return new_input_text
}

/**
 * All selected spans
 */
class Characters {
    constructor(situationID, num) {
        this.situationID = situationID;
        this.data = [];
        this.displayID = situationID + '-display';
        this.serializeID = situationID + '-serialize';
    }
    add(newCS) {
        // check for duplicates and add if it's not there.
        for (let oldCS of this.data) {
            if (oldCS == null) {
                continue;
            }
            if (oldCS.equals(newCS)) {
                // animate it to show it exists.
                oldCS.noticeMeSenpai = true;
                return;
            }
        }
        this.data.push(newCS);
    }
    remove(cs) {
        for (let i = this.data.length - 1; i >= 0; i--) {
            if (this.data[i].equals(cs)) {
                //this.data.pop();
                this.data.splice(i, 1);
                //this.data[i] = null
            }
        }
    }
    update() {
        this.render();
        this.serialize();
    }
    render() {
        let display = $('#' + this.displayID).empty();
        for (let i = 0; i < this.data.length; i++) {
            if (this.data[i] == null) {
                continue;
            }
            display.append(this.data[i].render(this.situationID, i));
            display.append('<br>');
        }
    }
    serialize() {
        let strings = [];
        for (let character of this.data) {
            if (character == null) {
                continue;
            }
            console.log('in for loop:', character.serialize());
            strings.push(character.serialize());
        }
        console.log("line 89: [serialize]  ", strings);
        let vals = strings.join(',');
        if ($("#no_badness").is(':not(:checked)')) {
            var situationID = this.situationID
            let serialize = $('#' + situationID + '-serialize');
            serialize.attr('value', '[' + vals + ']');
        } else {
            old_value = '[' + vals + ']';
        }
    }
}
class CharacterSelection {
    constructor(anno_referent,
                error_type,
                anno_slot,
                anno_value,
                anno_categorical_value,
                anno_time_value,
                explanation,
                severity,
                start_end_pairs,
                antecedent_start_end_pairs,
                num,
                color,
                turn_idx,
                state,
                history_turn_idx=-1,
                history_start_end_pairs=[[0, 0]]) {
        this.anno_referent = anno_referent
        this.error_type = error_type
        this.anno_domain = error_type
        this.anno_slot = anno_slot
        this.anno_value = anno_value
        this.anno_categorical_value = anno_categorical_value
        this.anno_time_value = anno_time_value
        this.explanation = explanation
        this.severity = severity
        this.start_end_pairs = start_end_pairs
        this.antecedent_start_end_pairs = antecedent_start_end_pairs
        this.num = num
        this.color = color
        this.noticeMeSenpai = false
        this.turn_idx = turn_idx
        this.state = state
        this.history_turn_idx = history_turn_idx
        this.history_start_end_pairs = history_start_end_pairs
    }
    equals(other) {
        return (this.anno_referent === other.anno_referent
                && this.anno_domain === other.anno_domain
                && this.anno_slot === other.anno_slot 
                && this.anno_value === other.anno_value
                && this.anno_categorical_value === other.anno_categorical_value
                && this.anno_time_value === other.anno_time_value
                && JSON.stringify(this.start_end_pairs) === JSON.stringify(other.start_end_pairs)
                && this.history_turn_idx === other.history_turn_idx
                && JSON.stringify(this.history_start_end_pairs) === JSON.stringify(other.history_start_end_pairs))
    }
    render(situationID, num) {
        let error_type = this.error_type;
        let anno_referent = this.anno_referent;
        let anno_domain = this.error_type;
        let anno_slot = this.anno_slot;
        let anno_value = this.anno_value;
        let anno_categorical_value = this.anno_categorical_value
        let anno_time_value = this.anno_time_value
        let explanation = this.explanation;
        let severity = this.severity;
        let start_end_pairs = this.start_end_pairs;
        let antecedent_start_end_pairs = this.antecedent_start_end_pairs; // so they go in the closure
        let color = this.color;
        let turn_idx = this.turn_idx;
        let state = this.state;
        let history_turn_idx = this.history_turn_idx;
        let history_start_end_pairs = this.history_start_end_pairs;

        let categorical_value = anno_categorical_value
        if (anno_categorical_value === '' && anno_time_value === '') {
            categorical_value = '(non-categorical)' 
        }
        if (anno_categorical_value === '' && anno_time_value !== '') {
            categorical_value = anno_time_value
        }

        // NOTE: no referent in MWOZ.
        let txt = `${anno_referent} || ${anno_domain} || ${anno_slot} || ${anno_value} || ${categorical_value}`
        //let txt = `${anno_domain} || ${anno_slot} || ${anno_value} || ${categorical_value}`
        if (this.history_turn_idx !== -1) {
            //txt = `(turn # = ${this.history_turn_idx}) ${anno_domain} || ${anno_slot} || ${anno_value} || ${categorical_value}`
            txt = `(turn # = ${this.history_turn_idx + 1}) ${anno_referent} || ${anno_domain} || ${anno_slot} || ${anno_value} || ${categorical_value}`
        }
        let text_color = "black"
        let opposite_color = "white"

        let removeButton = $('<button></button>')
            .addClass('bg-transparent ' + text_color +' bn hover-' + opposite_color + ' hover-bg-' + text_color + ' br-pill mr1 pointer')
            .append('✘')
            .on('click', function () {
                document.getElementById(situationID).innerHTML = situation_text[situationID]
                C.remove(new CharacterSelection(
                    anno_referent,
                    anno_domain,
                    anno_slot,
                    anno_value,
                    anno_categorical_value,
                    anno_time_value,
                    explanation,
                    severity,
                    start_end_pairs,
                    antecedent_start_end_pairs,
                    num,
                    color,
                    turn_idx,
                    state,
                    history_turn_idx,
                    history_start_end_pairs));
                annotate(C, situation_text["situation-0"])
                C.update();
                addDuplicateTable(anno_referent, anno_domain, anno_slot, domain_to_extracted_tuples, C);
            });

        // class dib is for animation purposes.
        //.addClass('b grow ' + text_color +' pa2 ma1 br-pill dib quality-span')
        let span = $('<span></span>')
            .addClass('b grow ' + text_color +' pa1 ma1 br-pill quality-span')
            .append(removeButton)
            .append(txt);
        //console.log('[span]', span);
        span.css({'background-color': this.color})
        span.css({'line-height': 2.5})
        span.attr('id', 'quality-span-'+num)
        // span.addClass('quality-span-'+num)

        span.attr('data-referent', anno_referent)
        // error-type is used as domain
        span.attr('data-error-type', error_type)
        span.attr('data-slot', anno_slot)
        span.attr('data-value', anno_value)
        span.attr('data-categorical-value', anno_categorical_value)
        span.attr('data-time-value', anno_time_value)
        span.attr('data-color', this.color)
        span.attr('data-situation-id', situationID)
        span.attr('data-severity', severity)
        span.attr('data-explanation', explanation)
        span.attr('data-start-end-pairs', start_end_pairs)
        span.attr('data-antecedent-start-end-pairs', antecedent_start_end_pairs)
        //span.attr('data-color', color)
        span.attr('data-num', num)
        // span.attr('data-num', characters_num)
        // if the character needs to be noticed, abide.
        if (this.noticeMeSenpai) {
            this.noticeMeSenpai = false;
            span.addClass("animated bounce faster");
            setTimeout(function () {
                span.removeClass('animated bounce faster');
            }, 1000);
        }
        return span;
    }
    serialize() {
        var filtered = this.antecedent_start_end_pairs.filter(function (el) {
            return el != null;
          });
        let string = ('[' 
                 + substitute(this.anno_referent)
                 + ',' + substitute(this.anno_domain) 
                 + ',' + substitute(this.anno_slot)
                 + ',' + substitute(this.anno_value)
                 + ',' + substitute(this.anno_categorical_value)
                 + ',' + substitute(this.anno_time_value)
                 + ',' + this.start_end_pairs[0][0]
                 + ',' + this.start_end_pairs[0][1] 
                 + ',[' + filtered + ']]');
        console.log('line 240: [string]:', string);
        return string
    }
}

// globals
let C = new Characters("situation-0", 0);
// provided externally to the script!
// let start;
// let end;
let start_end_pairs = []
let antecedent_start_end_pairs = []
let n_situations = 1;
let situationID;

// NOTE: no referent in MWOZ. Uses dummy.
let curr_referent = undefined;
//let curr_referent = 'dummy'
let curr_domain = undefined;
let curr_slot = undefined;
//let curr_value = undefined;
//let curr_categorical_value = undefined;
let curr_value = '';
let curr_categorical_value = '';
let curr_time_value = '';
let curr_color = undefined;

function comparespan(span_a, span_b) {
    let index_a = span_a[1]
    let index_b = span_b[1]
    if(index_a == index_b) {
        return span_a[3] - span_b[3]
    }
    return index_a - index_b;
}

function annotate(character, text) {
    let character_selections = character.data
    let span_list = []
    for(selection of character_selections) {
        if (selection == null) {
            continue;
        }
        let num = selection.num
        let p_span_id = "p-span-" + num
        let start_end_pair = selection.start_end_pairs[0]
        //span_list.push([p_span_id, start_end_pair[0], true, num, selection.error_type, selection.color]);
        //span_list.push([p_span_id, start_end_pair[1], false, num, selection.error_type, selection.color]);
        span_list.push([p_span_id, start_end_pair[0], true, num, selection.error_type, selection.color]);
        span_list.push([p_span_id, start_end_pair[1], false, num, selection.error_type, selection.color]);
        let antecedent_start_end_pairs = selection.antecedent_start_end_pairs
        if (antecedent_start_end_pairs.length > 0) {
            for(antecedent of antecedent_start_end_pairs) {
                if (antecedent != null) {
                    span_list.push([p_span_id + "_antecedent", antecedent[0], true, num, selection.error_type + "_antecedent"]);
                    span_list.push([p_span_id + "_antecedent", antecedent[1], false, num, selection.error_type + "_antecedent"]);
                }
            }
        }
    }

    span_list.sort(comparespan)
    console.log('span_list');
    console.log(span_list);
    let new_text = ""
    for(i in span_list) {
        span = span_list[i]
        var before_pair_end;
        if(i == 0) {
            before_pair_end = 0
        } else{
            console.log('before_pair_end', before_pair_end)
            before_pair_end = span_list[i - 1][1]
        }
        //console.log('color span', span[5]);
        start_temp = span[1]
        subtxt = text.substring(before_pair_end, start_temp)
        var span_to_add;
        var color_class = span[4]
        //var span_color = span[5]
        var span_color = span[5] 

        if(span[2]) {
            // span_to_add = "<span id=\"p-span-" + span[3]+ "\"class=\"annotation border-" + color_class + "\">"
            //span_to_add = "<span class=\"annotation border-" + color_class + " " + span[0]+ "\">"
            span_to_add = "<span class=\"annotation " + span[0] + "\" style=\"border-bottom:thick solid " + span_color + "\">"
        } else {
            span_to_add = "</span>"
            // multiple spans cross together (intersect)
            for (j = i; j >0; j--) {
                if (span_list[j - 1][2] && span_list[j-1][3] != span[3]) {
                    var previous_color_class = span_list[j-1][4]
                    span_to_add += "</span>"
                } else {
                    break
                }
            }
            for (j = i; j >0; j--) {
                if (span_list[j - 1][2] && span_list[j-1][3] != span[3]) {
                    var previous_color_class = span_list[j-1][4]
                    span_to_add += "<span class=\"annotation border-" + previous_color_class + " p-span-" + span_list[j-1][3]+ "\">"
                } else {
                    break
                }
            }
        }
        new_text += subtxt + span_to_add
    }
    if (span_list.length == 0) {
        new_text += text
    } else {
        new_text += text.substring(span_list[span_list.length - 1][1])
    }
    console.log("new_text", new_text);
    console.log($("#situation-0"));
    document.getElementById("situation-0").innerHTML = new_text
};

function annotate_select_span(character, text, select_span, select_antecedents) {
    let character_selections = character.data
    let span_list = []
    for(selection of character_selections) {
        if (selection == null) {
            continue;
        }
        let num = selection.num
        let p_span_id = "p-span-" + num
        let start_end_pair = selection.start_end_pairs[0]
        span_list.push([p_span_id, start_end_pair[0], true, num, selection.error_type]);
        span_list.push([p_span_id, start_end_pair[1], false, num, selection.error_type]);
    }
    for(l in select_antecedents) {
        if (select_antecedents[l] != null) {
            span_list.push(["select-antecedent--" + (l+1), select_antecedents[l][0], true, -1, "select-antecedent"]);
            span_list.push(["select-antecedent--" + (l+1), select_antecedents[l][1], false, -1, "select-antecedent"]);
        }
    }
    if (select_span !== undefined) {
        span_list.push(["select-span--1", select_span[0], true, -1, "select-span"]);
        span_list.push(["select-span--1", select_span[1], false, -1, "select-span"]);
    }
    // console.log(span_list)
    span_list.sort(comparespan)
    // console.log(span_list)
    let new_text = ""
    for(i in span_list) {
        span = span_list[i]
        var before_pair_end;
        if(i == 0) {
            before_pair_end = 0
        } else{
            before_pair_end = span_list[i - 1][1]
        }
        start_temp = span[1]
        subtxt = text.substring(before_pair_end, start_temp)
        var span_to_add;
        var color_class = span[4]
        var span_color = span[5]
        if(span[2]) {
            // span_to_add = "<span id=\"p-span-" + span[3]+ "\"class=\"annotation border-" + color_class + "\">"
            //span_to_add = "<span class=\"annotation border-" + color_class + " " + span[0]+ "\">"
            span_to_add = "<span class=\"annotation " + span[0] + "\" style=\"border-bottom:thick solid " + span_color + "\">"
            if (span[4] == "select-span") {
                span_to_add = "<span class=\"annotation bg-yellow " + span[0]+ "\">"
            }
            if (span[4] == "select-antecedent") {
                span_to_add = "<span class=\"annotation bg-light-yellow " + span[0]+ "\">"
            }
        } else {
            span_to_add = "</span>"
            // multiple spans cross together (intersect)
            for (j = i; j >0; j--) {
                if (span_list[j - 1][2] && span_list[j-1][3] != span[3]) {
                    var previous_color_class = span_list[j-1][4]
                    span_to_add += "</span>"
                } else {
                    break
                }
            }
            for (j = i; j >0; j--) {
                if (span_list[j - 1][2] && span_list[j-1][3] != span[3]) {
                    var previous_color_class = span_list[j-1][4]
                    if (span_list[j - 1][4] == "select-span") {
                        span_to_add += "<span class=\"annotation bg-yellow " + span_list[j-1][0] + "\">"
                    }
                    if (span_list[j - 1][4] == "select-antecedent") {
                        span_to_add += "<span class=\"annotation bg-light-yellow " + span_list[j-1][0] + "\">"
                    }
                    else {
                        span_to_add += "<span class=\"annotation border-" + previous_color_class + " " + span_list[j-1][0]+ "\">"
                    }
                } else {
                    break
                }
            }
        }
        new_text += subtxt + span_to_add
    }
    if (span_list.length == 0) {
        new_text += text
    } else {
        new_text += text.substring(span_list[span_list.length - 1][1])
    }
    document.getElementById("situation-0").innerHTML = new_text
};

function list_antecedents() {
    let display = $('#selection_antecedent').text("Selected antecedents: ");
    // console.log(antecedent_start_end_pairs)
    for (a in antecedent_start_end_pairs) {
        pair = antecedent_start_end_pairs[a]
        if (pair != null) {
            start = pair[0]
            end = pair[1]
            let txt = situation_text["situation-0"].substring(start, end)
            let removeButton = $('<button></button>')
                .addClass('bg-transparent black bn hover-white hover-bg-black br-pill mr1')
                .attr('antecedent-num', a)
                .append('✘')
                .on('click', function () {
                    antecedent_start_end_pairs[$(this).attr('antecedent-num')] = null
                    list_antecedents();
                    //C.remove(new CharacterSelection(error_type, explanation, severity, start_end_pairs));
                    annotate_select_span(C, situation_text["situation-0"], start_end_pairs[0], antecedent_start_end_pairs)
                    //C.update();
                });
            let span = $('<span></span>')
                .addClass('bg-light-yellow black pa1 ma1 dib quality-span')
                .append(removeButton)
                .append(txt);
            display.append(span);
            display.append('<br>');
        }
    }
}

function disable_everything() {
    // $('#confirm_button').prop('disabled', true);
    $("input[name='error_type']").removeClass("selected")
    //$("input:radio[name='severity']").prop('checked', false);
    $("input:radio[name='error_type']").prop('checked', false);
    //$('#explanation').val('');
    $("#button_div").addClass("disable");
    $("#severity_div").addClass("disable");
    $("#explanation_div").addClass("disable");
    $("#antecedent_selection").slideUp("fast");
    document.getElementById("time").value = "";
    //$(".slot-input").hide();
    //$(".value-input").hide();
    //antecedent_start_end_pairs = []
    //annotate_select_span(C, situation_text["situation-0"], start_end_pairs[0], antecedent_start_end_pairs)
}

// script
$(document).ready(function () {
    // build up elements we're working with
    situation_text['situation-0'] = $('#' + 'situation-0').text()
    // initialize our data structures NOTE: later we'll have to add data that's loaded
    // into the page (the machine's default guesses). or... maybe we won't?
    var pageX;
    var pageY;
    // $(document).on('mousedown', function(e){
    //     var selector = $("#quality-selection");
    //     if (!selector.is(e.target) &&
    //         !selector.has(e.target).length) {
    //             selector.fadeOut(1);
    //     }
    // });

    $('#close-icon').on("click", function(e) {
        $("input:radio[name='severity']").prop('checked', false);
        $('#error_type').val('');
        $('#explanation').val('');
        $("#quality-selection").fadeOut(0.2);
        start_end_pairs = []
        antecedent_start_end_pairs = []
        annotate(C, situation_text["situation-0"])
        disable_everything();
    });
    $("#situation-0").on("mousedown", function(e){
        pageX = e.pageX;
        pageY = e.pageY;
        document.getElementById("situation-0").innerHTML = situation_text["situation-0"]
    });

    function display_value_options(slot){
        if (slot.categorical_value) {
            $("#categorical-value").show();
        }
        if (slot.extractive_value) {
            $("#extractive-value").show();
            $("#extractive-value-box-btn").show();
            $("#extractive-value-textarea")[0].value = $('.selection_a').text();
            return
        }
        if (slot.abstractive_value) {
            $("#abstractive-value").show();
            $("#abstractive-value-box-btn").show();
            $("#abstractive-value-textarea")[0].value = $('.selection_a').text();
            return
        }
        if (slot.time_value) {
            $("#time-value").show();
            $("#time-value-box-btn").show();
            //$("#time-value-textarea").value = $('.selection_a').text();
            return
        }
    }

    function hide_all_value_options(){
        $("#categorical-value").hide()
        $("#extractive-value").hide()
        $("#extractive-value-box-btn").hide()
        $("#abstractive-value").hide()
        $("#abstractive-value-box-btn").hide()
        $("#time-value").hide()
        $("#time-value-box-btn").hide()
    }

    function create_buttons(items, level, parent, color){
        for (let idx = 0; idx < items.length; idx++) {
            let ele = items[idx];
            //console.log(`[${level} idx] ${idx} [${level} val] ${ele.val} [${level} id] ${ele.id}`);
            //console.log(`level = ${level} parent = ${parent}`);

            let button = `${level}-${ele.id}`
            jQuery('<div>', {
                id: button,
                class: `column ${level}` + (parent === '' ? '' : ` ${parent}`),
            }).appendTo(`#${level}-row`)

            jQuery('<input>', {
                class: 'checkbox-tools antecedent_no_able ' + level + '-input',
                type: 'radio',
                //name: button,
                name: level,
                id: `${button}-input`,
                value: ele.val,
            }).appendTo(`#${button}`)

            jQuery('<label>', {
                class: 'b for-checkbox-tools',
                for: button,
                id: `'${button}-label`,
                text: ele.val,
            }).appendTo(`#${button}`)

            if (level === 'referent') {
                $(`#${button}`).on('click', function() {
                    color = ele.color
                    // NOTE: no referent in MWOZ. Uses dummy.
                    curr_referent = ele.val
                    //curr_referent = 'dummy'
                    $(`.${level} label`).css('background-color', '#ecedf3')
                    $(`.${level} label`).css('opacity', 1)
                    $(`.${ele.id} label`).css('background-color', '#ecedf3')
                    $(`#${button} label`).css('background-color', color)
                    $(`#${button} label`).css('opacity', 0.7)
                })
                continue;
            }

            if (level != 'domain') {
                $(`#${button}`).hide()
            }
            $(`#${button}`).on('click', function() {
                if (level == 'domain') {
                    color = ele.color
                }
                //console.log(`[click] level = ${level} parent = ${parent} self = ${ele.id}`);
                // Resets the color of the same row and the color of its children. 
                $(`.${level} label`).css('background-color', '#ecedf3')
                $(`.${level} label`).css('opacity', 1)
                $(`.${ele.id} label`).css('background-color', '#ecedf3')
                $(`#${button} label`).css('background-color', color)
                $(`#${button} label`).css('opacity', 0.7)

                if (level == 'domain') {
                    $(`.slot`).hide()
                    $(`.value`).hide()
                    //$("#textarea-value").hide()
                    //$("#freeform-value-row").hide()
                    hide_all_value_options()
                    $(`.${ele.id}`).show()
                    curr_domain = ele.val
                    curr_color = color
                    curr_slot = undefined
                    //curr_value = undefined
                    //curr_categorical_value = undefined
                    curr_value = ''
                    curr_categorical_value = ''
                    curr_time_value = ''
                    return
                } 
                
                let domain_idx = ele.id.split("-")[0];
                let slot_idx = ele.id.split("-")[1];
                if (level == 'slot') {
                    $(`.value label`).css('background-color', '#ecedf3')
                    $(`.value label`).css('opacity', 1)
                    $(`.value`).hide()
                    //$("#textarea-value").hide()
                    //$("#freeform-value-row").hide()
                    hide_all_value_options()
                    $(`.${ele.id}`).show()
                    curr_slot = ele.val
                    curr_color = color
                    curr_value = ''
                    curr_categorical_value = ''
                    curr_time_value = ''
                    display_value_options(ele)
                    $("#button_div").addClass("disable");

                    if (!is_categorical_value_only(domain_idx, slot_idx)) {
                        $("#button-extractive-value").removeClass("disable");
                        $("#button-abstractive-value").removeClass("disable");
                        $("#button-time-value").removeClass("disable");
                    }

                    // If now values, show textarea.
                    // TODO: handle the value from text box
                    //if (ele.values.length == 0) {
                    //if (ele.free_from_value) {
                    //    //$("#textarea-value").show()
                    //    //$('#textarea-value')[0].value = $('.selection_a').text();
                    //    $("#freeform-value-row").show()
                    //    $("#textarea-value")[0].value = $('.selection_a').text();
                    //}
                }

                // Shows all the other buttons of the selected level
                // (only slot or value level).
                $(`.${parent}`).show()

                // Allows to click on the confirm button.
                if (level == 'value') {
                    if (is_categorical_value_only(domain_idx, slot_idx)) {
                        $("#button_div").removeClass("disable");
                    } else {
                        $("#button-extractive-value").removeClass("disable");
                        $("#button-abstractive-value").removeClass("disable");
                        $("#button-time-value").removeClass("disable");
                    }
                    curr_value = $('.selection_a').text()
                    curr_categorical_value = ele.val
                    curr_color = color
                }
            })
        }
    }
    function is_categorical_value_only(domain_idx, slot_idx) {
        return (is_categorical_value(domain_idx, slot_idx)
                && (!is_extractive_value(domain_idx, slot_idx))
                && (!is_abstractive_value(domain_idx, slot_idx))
                && (!is_time_value(domain_idx, slot_idx)))
    }
    function is_categorical_value(domain_idx, slot_idx) {
        let slot = schema[domain_idx].slots[slot_idx];
        return slot.categorical_value
    }
    function is_extractive_value(domain_idx, slot_idx) {
        let slot = schema[domain_idx].slots[slot_idx];
        return slot.extractive_value
    }
    function is_time_value(domain_idx, slot_idx) {
        let slot = schema[domain_idx].slots[slot_idx];
        return slot.time_value
    }
    function is_abstractive_value(domain_idx, slot_idx) {
        let slot = schema[domain_idx].slots[slot_idx];
        //console.log('[is abstractive value] ' + slot.abstractive_value);
        return slot.abstractive_value
    }

    create_buttons(referent_schema, 'referent', '')
    create_buttons(schema, 'domain', '')
    for (let idx = 0; idx < schema.length; idx++) {
        let domain = schema[idx]
        create_buttons(domain.slots, 'slot', `${domain.id}`, domain.color)
        for (let jdx = 0; jdx < domain.slots.length; jdx++) {
            let slot = domain.slots[jdx]
            create_buttons(slot.values, 'value', `${slot.id}`, domain.color)
        }
    }

    $("#confirm-extractive-value-btn").on('click', function() {
        curr_value = $("#extractive-value-textarea")[0].value
        if (curr_value.length === 0){
            alert("Empty value entered!")
            $("#extractive-value-textarea")[0].value = $('.selection_a').text();
            return
        }
        $("#button_div").removeClass("disable");
    })

    $("#confirm-abstractive-value-btn").on('click', function() {
        curr_value = $("#abstractive-value-textarea")[0].value
        if (curr_value.length === 0) {
            alert("Empty value entered!")
            $("#abstractive-value-textarea")[0].value = $('.selection_a').text();
            return
        }
        //if (curr_value === $('.selection_a').text()) {
        //    alert("Abstract value! You can modify the value to make it more complete. Please check!")
        //}
        $("#button_div").removeClass("disable");
    })

    $("#confirm-time-value-btn").on('click', function() {
        curr_value = $("#time").val();
        curr_time_value = $("#time").val();
        if (curr_time_value.length === 0){
            alert("Empty value entered!")
            return
        }
        $("#button_div").removeClass("disable");
    })


    function hide_buttons(items, level){
        for (let idx = 0; idx < items.length; idx++) {
            let ele = items[idx];
            let button = `${level}-${ele.id}`
            $(`#${button}`).hide()
        }
        $(`.${level} label`).css('background-color', '#ecedf3')
        $(`.${level} label`).css('opacity', 1)
    }

    function reset_buttons(){
        $(`.referent label`).css('background-color', '#ecedf3')
        $(`.domain label`).css('background-color', '#ecedf3')
        $(`.referent label`).css('opacity', 1)
        $(`.domain label`).css('opacity', 1)
        hide_all_value_options()
        // hide all slots.
        for (let idx = 0; idx < schema.length; idx++) {
            let domain = schema[idx]
            hide_buttons(domain.slots, 'slot')
            // hide all values.
            for (let jdx = 0; jdx < domain.slots.length; jdx++) {
                let slot = domain.slots[jdx]
                hide_buttons(slot.values, 'value')
            }
        }
        $("#button-extractive-value").addClass("disable");
        $("#button-abstractive-value").addClass("disable");
        $("#button-time-value").addClass("disable");
        // NOTE: no referent in MWOZ. Uses dummy.
        curr_referent = undefined
        //curr_referent = 'dummy'
        curr_domain = undefined
        curr_slot = undefined
        curr_value = ''
        curr_categorical_value = ''
        curr_time_value = ''
        curr_color = undefined
    }

    $("#situation-0").on('mouseup', function (e) {
        reset_buttons();
        situationID = e.target.id;
        let selection = window.getSelection();
        if (selection.anchorNode != selection.focusNode || selection.anchorNode == null) {
            // highlight across spans
            return;
        }
        // $('#quality-selection').fadeOut(1);
        let range = selection.getRangeAt(0);
        let [start, end] = [range.startOffset, range.endOffset];
        if (start == end) {
            // disable on single clicks
            annotate(C, situation_text["situation-0"])
            return;
        }
        // manipulate start and end to try to respect word boundaries and remove
        // whitespace.
        end -= 1; // move to inclusive model for these computations.
        let txt = $('#' + situationID).text();
        while (txt.charAt(start) == ' ') {
            start += 1; // remove whitespace
        }
        while (start - 1 >= 0 && txt.charAt(start - 1) != ' ') {
            start -= 1; // find word boundary
        }
        while (txt.charAt(end) == ' ') {
            end -= 1; // remove whitespace
        }
        while (end + 1 <= txt.length - 1 && txt.charAt(end + 1) != ' ') {
            end += 1; // find word boundary
        }
        // move end back to exclusive model
        end += 1;
        // stop if empty or invalid range after movement
        if (start >= end) {
            return;
        }
        //console.log('start', start, 'end', end);
        if ($("#antecedent_selection").first().is(":hidden")) {
            start_end_pairs = []
            antecedent_start_end_pairs = []
            start_end_pairs.push([start, end])
            let selection_text = "<b>Selected span:</b> <a class=\"selection_a\">";
            start = start_end_pairs[0][0]
            end = start_end_pairs[0][1]
            let select_text = $('#' + situationID).text().substring(start, end)
            selection_text += select_text + "</a>"
            document.getElementById("selection_text").innerHTML = selection_text


            //create_domain_buttons()
            $('#quality-selection').css({
                'display': "inline-block",
                'left': pageX - 150,
                'top' : pageY - 350,
            }).fadeIn(200, function() {
                disable_everything()
            });
            annotate_select_span(C, situation_text["situation-0"], [start, end], antecedent_start_end_pairs)
        } else {  
            $("#explanation_div").removeClass("disable");
            antecedent_start_end_pairs.push([start, end])
            list_antecedents()
            annotate_select_span(C, situation_text["situation-0"], start_end_pairs[0], antecedent_start_end_pairs)
        }
    });
    $('#confirm_button').on("click", function(e) {
        var explanation = "123"; //$("textarea#explanation").val();
        var severity = "123" //$('input[name="severity"]:checked').val();
        if (curr_referent === undefined) {
            alert(`Referent is ${curr_referent}. You must select a referent.`)
            return false
        }
        if (curr_domain === undefined) {
            alert(`Domain is ${curr_domain}. You must select a domain.`)
            return false
        }
        if (curr_slot === undefined) {
            alert(`Slot is ${curr_slot}. You must select a slot.`)
            return false
        }
        if (curr_value === '' && curr_categorical_value === '' && curr_time_value === '') {
            alert(`Value is ${curr_value}. You must select a value.`)
            return false
        }

        let display = $('#' + situationID + "-display")
        display.attr('id', situationID + '-display')
        display.attr('data-situation-id', situationID)
        let turn_idx = turn_to_be_annotated2['turn_idx']
        let state = turn_to_be_annotated2['state']
        C.add(new CharacterSelection(
            curr_referent,
            curr_domain,
            curr_slot,
            curr_value,
            curr_categorical_value,
            curr_time_value,
            explanation,
            severity,
            start_end_pairs,
            antecedent_start_end_pairs,
            C.data.length,
            curr_color,
            turn_idx,
            state));
        C.update();
        $('#quality-selection').fadeOut(1, function() {
           disable_everything()
        });
        start_end_pairs = []
        antecedent_start_end_pairs = []
        annotate(C, situation_text["situation-0"])
        addDuplicateTable(curr_referent, curr_domain, curr_slot, domain_to_extracted_tuples, C);
    });


    $(document).on('mouseover','.quality-span',function(e){
        var color_class = $(this).attr("data-color")
        var quality_id = e.target.id
        var situation_id = $(this).attr("data-situation-id")
        var span_num = $(this).attr("data-num")
        var p_span_id = ".p-span-" + span_num
        $(p_span_id).css("backgroundColor", color_class);
        $(p_span_id).css("opacity", "");
        var antecedent_color_class= color_class+"_antecedent"
        var antecedent_p_span_id = ".p-span-" + span_num + "_antecedent"
        $(antecedent_p_span_id).addClass("bg-"+antecedent_color_class);
        if (black_text_errors_types.includes(color_class)) {
            $(p_span_id).addClass("black");
            $(antecedent_p_span_id).addClass("black")
        } else {
            $(p_span_id).addClass("black");
            $(antecedent_p_span_id).addClass("black")
        }
    });
    $(document).on('mouseout','.quality-span',function(e){
        // $(this).css("color","white")
        var color_class = $(this).attr("data-error-type")
        // $(this).addClass(color_class)
        var quality_id = e.target.id
        var situation_id = $(this).attr("data-situation-id")
        var span_num = $(this).attr("data-num")
        var p_span_id = ".p-span-" + span_num
        //$(p_span_id).removeClass("bg-"+color_class);
        //$(p_span_id).removeClass(this.color);
        $(p_span_id).css("backgroundColor", "");
        $(p_span_id).css("opacity", "1");
        var antecedent_color_class= color_class+"_antecedent"
        var antecedent_p_span_id = ".p-span-" + span_num + "_antecedent"
        $(antecedent_p_span_id).removeClass("bg-"+antecedent_color_class);
        if (black_text_errors_types.includes(color_class)) {
            $(p_span_id).removeClass("black");
            $(antecedent_p_span_id).removeClass("black")
        } else {
            $(p_span_id).removeClass("black");
            $(antecedent_p_span_id).removeClass("black")
            //$(p_span_id).removeClass("white");
            //$(antecedent_p_span_id).removeClass("white")
        }

        // document.getElementById(situation_id).innerHTML = situation_text[situation_id]
    });
   
    // clear button in the quality select box
    $("#clear_button").on("click", function(){
        $("input:radio[name='error_type']").prop('checked', false);
        $("input:radio[name='severity']").prop('checked', false);
        $('#error_type').val('');
        $('#explanation').val('');
    });

    $(".antecedent_able").on('click',function(e){
        if (!$(this).hasClass("selected")) {
            $("input[name='error_type']").removeClass("selected")
            //$("input[name='domain']").removeClass("selected")
            $(this).addClass("selected")
            $("#antecedent_selection").slideDown("fast");
            antecedent_start_end_pairs = []
            annotate_select_span(C, situation_text["situation-0"], start_end_pairs[0], antecedent_start_end_pairs)
            var id = $(this).attr("id")
            $('#explanation').val('');
            $("#button_div").addClass("disable");
            $("#severity_div").addClass("disable");
            $("#explanation_div").addClass("disable");
        }
    });

    $(".antecedent_no_able").on('click',function(e){
        $("input[name='error_type_1']").removeClass("selected")
        $("input[name='error_type_2']").removeClass("selected")
        $("input[name='error_type_3']").removeClass("selected")

        $("#antecedent_selection").slideUp("fast");
        antecedent_start_end_pairs = []
        annotate_select_span(C, situation_text["situation-0"], start_end_pairs[0], antecedent_start_end_pairs)
        document.getElementById("selection_antecedent").innerHTML = "Selected antecedents: "
        $("#button_div").addClass("disable");
    });

    $("#explanation").on('change keyup paste', function() {
        $("#severity_div").removeClass("disable");
    });

    $(document).on('click','.checkbox-tools-severity',function(e){
        $("#button_div").removeClass("disable");
    });


    $(document).on("keypress", function(e){
          if (e.key === "Enter") {
            e.preventDefault();
          }
    });

    $( function() {
        $( "#quality-selection" ).draggable();
      } );

    for (var i = 0; i < turn_to_be_annotated2.annotations.length; i++) {
        let explanation = "123"; 
        let severity = "123";
        let ann = turn_to_be_annotated2.annotations[i];
        C.add(new CharacterSelection(
            ann.referent,
            ann.domain,
            ann.slot,
            ann.value,
            ann.categorical_value,
            ann.time_value,
            explanation,
            severity,
            [[ann.start, ann.end]],
            [],
            C.data.length,
            ann.color,
            turn_to_be_annotated2['turn_idx'],
            ann.state,
            ann.history_turn_idx,
            ann.history_start_end_pairs));
        C.update();
        addDuplicateTable(ann.referent, ann.domain, ann.slot, domain_to_extracted_tuples, C, raise_alert=false);
    }
    annotate(C, situation_text["situation-0"])
});
