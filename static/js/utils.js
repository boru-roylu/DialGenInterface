function hide(btn) {
  //let row_id = btn.id.slice(0, 6) + '_row';
  let row_id = btn.id + "_row";
  let p_id = btn.id + "_p";
  var x = document.getElementById(row_id);
  var y = document.getElementById(p_id);
  if (x.style.display === "none") {
    x.style.display = "block";
    y.style.display = "block";
    btn.innerHTML = "Hide";
  } else {
    x.style.display = "none";
    y.style.display = "none";
    btn.innerHTML = "Show";
  }
}

function removeElement(el) {
  el.parentNode.removeChild(el);
}

function jsonEscape(str) {
  return str
    .replace(/\n/g, "\\\\n")
    .replace(/\r/g, "\\\\r")
    .replace(/\t/g, "\\\\t");
}

function createMultiCollapseSection(
  name,
  domains,
  domain_to_table_content,
  createTable,
  domain_to_header_names = undefined,
  domain_to_condition_slots = undefined
) {
  buttons = document.getElementById(name + "Buttons");
  tables = document.getElementById(name + "Tables");

  //let ariaControlsStringForAll = ""
  for (let i = 0; i < domains.length; i++) {
    const domain = domains[i];
    let button = document.createElement("button");
    button.classList.add("btn");
    button.classList.add("btn-primary");
    button.classList.add("multicollapse-button" + "_" + name);
    button.setAttribute("domain", domain);
    button.setAttribute("type", "button");
    button.setAttribute("data-bs-toggle", "collapse");
    button.setAttribute("data-bs-target", "#multiCollapse" + name + domain);
    button.setAttribute("aria-expanded", "false");
    let ariaControlsString = "multiCollapse" + name + domain;
    //ariaControlsStringForAll += ariaControlsString + " "
    button.setAttribute("aria-controls", ariaControlsString);
    button.style.margin = "2px";
    button.style.fontSize = "12px";
    button.id = "btn_" + name + domain;
    button.innerHTML = domain;
    buttons.appendChild(button);

    const div = document.createElement("div");
    div.classList.add("collapse");
    div.setAttribute("data-bs-parent", "#" + name);
    //extractedTupleDiv.classList.add("multi-collapse" + name);
    //extractedTupleDiv.classList.add("multi-collapse" + name);
    div.id = "multiCollapse" + name + domain;

    const card = document.createElement("div");
    card.classList.add("card");
    card.classList.add("card-body");

    let table_content = domain_to_table_content[domain];
    if (domain_to_condition_slots !== undefined) {
      table = createTable(
        name,
        domain,
        table_content,
        domain_to_condition_slots[domain]
      );
    } else if (domain_to_header_names !== undefined) {
      // For queryResult.
      table = createTable(
        name,
        domain,
        table_content,
        domain_to_header_names[domain]
      );
    } else {
      table = createTable(name, domain, table_content);
    }
    card.appendChild(table);
    div.appendChild(card);
    tables.appendChild(div);
  }
}

function createExtractedTupleTable(name, domain, extracted_tuples) {
  const extractedTupleTable = document.createElement("table");
  extractedTupleTable.id = "table_" + name + "_" + domain;
  extractedTupleTable.classList.add("table-bordered");
  extractedTupleTable.classList.add("caption-top");
  const caption = document.createElement("caption");
  caption.textContent = domain;
  caption.style.fontSize = "12px";
  extractedTupleTable.appendChild(caption);
  const header_names = [
    "Turn #",
    "Status",
    "Referent",
    "Domain",
    "Slot",
    "Value",
    "Categorical Value",
  ];
  const header = extractedTupleTable.insertRow(-1);
  for (let i = 0; i < header_names.length; i++) {
    let header_name = header_names[i];
    let header_cell = document.createElement("TH");
    header_cell.innerHTML = header_name;
    header.appendChild(header_cell);
  }

  if (extracted_tuples === undefined) {
    return extractedTupleTable;
  }

  for (let i = 0; i < extracted_tuples.length; i++) {
    let tuple = extracted_tuples[i];
    let row = extractedTupleTable.insertRow(-1);
    let suffix = domain + "_" + i;
    row.id = "whole_row_" + suffix;

    let cell = row.insertCell(-1);
    cell.innerHTML = tuple["turn_idx"] + 1;

    cell = row.insertCell(-1);
    cell.id = "status_" + suffix;
    cell.innerHTML = tuple["state"];

    cell = row.insertCell(-1);
    cell.id = "referent_" + suffix;
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["referent"].strike();
    } else {
      cell.innerHTML = tuple["referent"];
    }

    cell = row.insertCell(-1);
    cell.id = "domain_" + suffix;
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["domain"].strike();
    } else {
      cell.innerHTML = tuple["domain"];
    }

    cell = row.insertCell(-1);
    cell.id = "slot_" + suffix;
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["slot"].strike();
    } else {
      cell.innerHTML = tuple["slot"];
    }

    cell = row.insertCell(-1);
    cell.id = "value_" + suffix;
    cell.innerHTML = tuple["value"];
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["value"].strike();
    } else {
      cell.innerHTML = tuple["value"];
    }

    cell = row.insertCell(-1);
    cell.id = "categorical_value_" + domain + "_" + i;
    cell.innerHTML = tuple["categorical_value"];
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["categorical_value"].strike();
    } else {
      cell.innerHTML = tuple["categorical_value"];
    }
  }
  return extractedTupleTable;
}

function createQueryResultTable(
  name,
  domain,
  selected_candidates,
  header_names
) {
  const table = document.createElement("table");
  table.id = "table_" + name + "_" + domain;
  table.classList.add("table-bordered");
  table.classList.add("caption-top");
  const caption = document.createElement("caption");
  caption.textContent = domain;
  caption.style.fontSize = "12px";
  table.appendChild(caption);

  if (header_names === undefined) {
    return table;
  }

  const header = table.insertRow(-1);
  for (let i = 0; i < header_names.length; i++) {
    let header_name = header_names[i];
    let header_cell = document.createElement("TH");
    header_cell.innerHTML = header_name;
    header.appendChild(header_cell);
  }

  if (selected_candidates === undefined || selected_candidates.length === 0) {
    return table;
  }

  for (let i = 0; i < selected_candidates.length; i++) {
    let cand = selected_candidates[i];
    let row = table.insertRow(-1);
    let suffix = domain + "_" + i;
    row.id = "whole_row_" + suffix;
    for (let j = 0; j < header_names.length; j++) {
      let slot = header_names[j];
      cell = row.insertCell(-1);
      cell.innerHTML = cand[slot];
    }
  }
  return table;
}

function createEditTable(curr_subdialog) {
  const table = document.createElement("table");
  table.id = "edit_table";
  table.classList.add("table-bordered");

  let header_names = [
    "",
    "Turn #",
    "Party",
    "Role",
    "Turn",
    "Your Edit",
    "",
    "",
    "",
  ];

  // Adds the header row.
  const header = table.insertRow(-1);
  for (let i = 0; i < header_names.length; i++) {
    let header_name = header_names[i];
    let header_cell = document.createElement("TH");
    header_cell.innerHTML = header_name;
    header.appendChild(header_cell);
  }

  //Add the data rows.
  for (let i = 0; i < curr_subdialog.length; i++) {
    let turn = curr_subdialog[i];
    let row = table.insertRow(-1);
    suffix = turn["turn_idx"] + 1;
    row.id = "whole_row_" + suffix;

    let cell = row.insertCell(-1);
    let chk = document.createElement("input");
    chk.setAttribute("type", "checkbox");
    chk.setAttribute("value", "no");
    chk.setAttribute("id", "chk_edit_table_" + suffix);
    chk.setAttribute("name", "chk_edit_table");
    chk.setAttribute("row_idx", i);
    cell.appendChild(chk);

    cell = row.insertCell(-1);
    cell.innerHTML = suffix;

    cell = row.insertCell(-1);
    cell.id = "party_turn_" + suffix;
    cell.innerHTML = turn["party"];

    cell = row.insertCell(-1);
    cell.id = "role_turn_" + suffix;
    cell.innerHTML = turn["role"];

    cell = row.insertCell(-1);
    cell.id = "turn_" + suffix;
    cell.innerHTML = turn["text"];
    cell.style.fontSize = "12px";
    cell.width = "45%";
    cell.align = "left";

    cell = row.insertCell(-1);
    cell.width = "45%";
    var textarea = document.createElement("textarea");
    textarea.id = "edit_turn_" + suffix;
    textarea.setAttribute("row_idx", i);
    textarea.type = "text";
    textarea.rows = Math.floor(turn["text"].length / 64 + 3);
    textarea.style.width = "100%";
    textarea.style.height = "100%";
    textarea.style.boarder = "none";
    textarea.style.resize = "none";

    cell.appendChild(textarea);

    button_names = ["copy", "delete", "auto"];
    for (var j = 0; j < button_names.length; j++) {
      button_name = button_names[j];
      cell = row.insertCell(-1);
      button = document.createElement("button");
      button.classList.add(button_name + "_turn");
      button.classList.add("btn");
      button.classList.add("btn-primary");
      button.style.fontSize = "11px";
      button.id = "btn_" + button_name + "_turn_" + suffix;
      button.innerHTML = button_name;
      cell.appendChild(button);
    }
  }

  var table_div = document.getElementById("edit_table_div");
  table_div.innerHTML = "";
  table_div.appendChild(table);
}

function createFinalEditTable(
  history,
  history_text_based_annotations,
  disable_edit = false
) {
  const table = document.createElement("table");
  table.id = "edit_table";
  table.classList.add("table-bordered");

  let header_names = [
    "Turn #",
    "Party",
    "Role",
    "Turn",
    "Your Edit",
    "Labels",
    "Dup.",
    "",
    "",
    "",
  ];
  if (disable_edit == true) {
    header_names = [
      "Turn #",
      "Party",
      "Role",
      "Turn",
      "Your Edit",
      "Labels",
      "Dup.",
      "",
    ];
  }

  // Adds the header row.
  const header = table.insertRow(-1);
  for (let i = 0; i < header_names.length; i++) {
    let header_name = header_names[i];
    let header_cell = document.createElement("TH");
    header_cell.innerHTML = header_name;
    header.appendChild(header_cell);
  }

  //Add the data rows.
  for (let i = 0; i < history.length; i++) {
    let turn = history[i];
    let row = table.insertRow(-1);
    suffix = turn["turn_idx"] + 1;
    row.id = "whole_row_" + suffix;

    let cell = row.insertCell(-1);
    cell.innerHTML = suffix;

    cell = row.insertCell(-1);
    cell.id = "party_turn_" + suffix;
    cell.innerHTML = turn["party"];

    cell = row.insertCell(-1);
    cell.id = "role_turn_" + suffix;
    cell.innerHTML = turn["role"];

    cell = row.insertCell(-1);
    cell.id = "turn_" + suffix;
    if (turn["raw_text"] === null) {
      cell.innerHTML = turn["text"];
    } else {
      cell.innerHTML = turn["raw_text"];
    }
    if (turn["text"] == "[delete this turn]") {
      cell.innerHTML = cell.innerHTML.strike();
    }
    cell.style.fontSize = "12px";
    cell.width = "30%";
    cell.align = "left";

    cell = row.insertCell(-1);
    cell.width = "30%";
    let textarea = document.createElement("textarea");
    textarea.id = "edit_turn_" + suffix;
    textarea.setAttribute("row_idx", i);
    textarea.type = "text";
    textarea.rows = Math.floor(turn["text"].length / 64 + 3);
    textarea.style.width = "100%";
    textarea.style.height = "100%";
    textarea.style.boarder = "none";
    textarea.style.resize = "none";

    if (disable_edit == true) {
      textarea.readOnly = true;
    }

    // We keep [delete this turn] in final review page.
    if (turn["text"] == "[delete this turn]") {
      textarea.readOnly = true;
    }
    textarea.innerHTML = turn["text"];
    textarea.setAttribute("data-text", turn["text"]);
    textarea.addEventListener("focus", () => {
      console.log("Textarea is focused.");
    });
    textarea.addEventListener("blur", () => {
      console.log("Textarea is not focused.");
      let original_text = textarea.getAttribute("data-text");
      if (textarea.value == original_text) {
        return;
      }
      if (
        !confirm(
          "Are you sure you want to edit? Labels will be delete for this turn. You will need to relabel the turn. Click cancel to reset the text to original text."
        )
      ) {
        textarea.value = original_text;
        return;
      }

      turn_idx = i;
      const queryString = window.location.search;
      const url_params = new URLSearchParams(queryString);
      let task_id = url_params.get("task_id");
      let worker_id = url_params.get("worker_id");

      let edit_turns = [];
      for (let i = 0; i < dialog_history.length; i++) {
        let turn = dialog_history[i];
        party_id = "party_turn_" + (turn["turn_idx"] + 1);
        role_id = "role_turn_" + (turn["turn_idx"] + 1);
        textarea_id = "edit_turn_" + (turn["turn_idx"] + 1);
        let textbox = $(`#${textarea_id}`);
        let edit_content = textbox.val().trim();
        let party = $(`#${party_id}`)[0].textContent;
        let role = $(`#${role_id}`)[0].textContent;
        var edit_turn = {
          party: party,
          role: role,
          text: edit_content,
          raw_text: turn["raw_text"],
          deleted: edit_content === "[delete this turn]",
          edit: edit_content !== turn["raw_text"],
          auto_edit: turn["auto_edit"],
          instruction: turn["instruction"],
        };

        if (edit_turn["text"] === "") {
          alert(
            "Turn " +
              (turn["turn_idx"] + 1) +
              " is an empty textbox. Please enter your edit or delete the turn."
          );
          return;
        }
        edit_turns.push(edit_turn);
      }

      let endTime = new Date();
      const timeSpentOnPage = endTime - startTime; // in milliseconds

      let data = {
        task_id: task_id,
        worker_id: worker_id,
        turn_idx: turn_idx,
        turns: edit_turns,
        time_spent_on_page: timeSpentOnPage,
        clean_annotations: true,
      };

      $("#overlay").fadeIn(100);

      $.ajax({
        method: "POST",
        contentType: "application/json",
        url: "/turn_relabeling_submit",
        data: JSON.stringify(data),
        dataType: "json",
      })
        .done(function (msg) {
          $("#overlay").fadeOut(100);
          location.replace(msg);
        }, 500)
        .fail(function () {
          alert("Sorry. Server unavailable. ");
        });
    });
    cell.appendChild(textarea);

    cell = row.insertCell(-1);
    cell.width = "30%";
    cell.id = "labels_turn_" + suffix;
    cell.innerHTML = history_text_based_annotations[i];
    cell.width = "30%";
    cell.align = "left";

    cell = row.insertCell(-1);
    cell.id = "duplicate_tuple_indicator_turn_" + suffix;
    if (turn_idxs_with_duplicate_tuples[i]) {
      cell.innerHTML = "✓";
    }

    let button_names = ["relabel", "copy", "delete"];
    if (disable_edit == true) {
      button_names = ["relabel"];
    }
    for (var j = 0; j < button_names.length; j++) {
      button_name = button_names[j];
      cell = row.insertCell(-1);
      button = document.createElement("button");
      button.classList.add(button_name + "_turn");
      button.classList.add("btn");
      if (button_name == "relabel") {
        button.classList.add("btn-warning");
      } else {
        button.classList.add("btn-primary");
      }
      button.style.fontSize = "11px";
      button.id = "btn_" + button_name + "_turn_" + suffix;
      button.innerHTML = button_name;
      cell.appendChild(button);
    }
  }

  var table_div = document.getElementById("edit_table_div");
  table_div.innerHTML = "";
  table_div.appendChild(table);
}

function createExtractedTupleTableForQuery(
  name,
  domain,
  extracted_tuples,
  condition_slots = undefined
) {
  const extractedTupleTable = document.createElement("table");
  extractedTupleTable.id = "table_" + name + "_" + domain;
  extractedTupleTable.classList.add("table-bordered");
  extractedTupleTable.classList.add("caption-top");
  const caption = document.createElement("caption");
  caption.textContent = domain;
  caption.style.fontSize = "12px";
  extractedTupleTable.appendChild(caption);
  const header_names = [
    "",
    "Turn #",
    "Status",
    "Domain",
    "Slot",
    "Value",
    "Categorical Value",
  ];
  const header = extractedTupleTable.insertRow(-1);
  for (let i = 0; i < header_names.length; i++) {
    let header_name = header_names[i];
    let header_cell = document.createElement("TH");
    header_cell.innerHTML = header_name;
    header.appendChild(header_cell);
  }

  //if (!(domain in domain_to_extracted_tuples)){
  //    return extractedTupleTable
  //}
  if (extracted_tuples === undefined) {
    return extractedTupleTable;
  }

  for (let i = 0; i < extracted_tuples.length; i++) {
    let tuple = extracted_tuples[i];
    let row = extractedTupleTable.insertRow(-1);
    let tuple_string = JSON.stringify(tuple);
    row.setAttribute("data-tuple", tuple_string);
    let suffix = domain + "_" + i;
    row.id = "whole_row_" + suffix;

    let cell = row.insertCell(-1);
    cell.id = "select_" + suffix;
    cell.style.textAlign = "center";
    //cell.width = "25%";

    if (
      condition_slots === undefined ||
      condition_slots.includes(tuple["slot"].toLowerCase())
    ) {
      let chk = document.createElement("input");
      chk.setAttribute("type", "checkbox");
      chk.setAttribute("value", "no");
      chk.setAttribute("id", "chk_" + suffix);
      chk.setAttribute("suffix", suffix);
      chk.setAttribute("name", "chk_" + domain);
      chk.setAttribute("row_idx", i);
      if (tuple["state"] == "delete") {
        chk.disabled = true;
      }
      cell.appendChild(chk);
    }

    cell = row.insertCell(-1);
    cell.innerHTML = tuple["turn_idx"] + 1;

    cell = row.insertCell(-1);
    cell.id = "status_" + suffix;
    cell.innerHTML = tuple["state"];

    cell = row.insertCell(-1);
    cell.id = "domain_" + suffix;
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["domain"].strike();
    } else {
      cell.innerHTML = tuple["domain"];
    }

    cell = row.insertCell(-1);
    cell.id = "slot_" + suffix;
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["slot"].strike();
    } else {
      cell.innerHTML = tuple["slot"];
    }

    cell = row.insertCell(-1);
    cell.id = "value_" + suffix;
    cell.innerHTML = tuple["value"];
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["value"].strike();
    } else {
      cell.innerHTML = tuple["value"];
    }

    cell = row.insertCell(-1);
    cell.id = "categorical_value_" + domain + "_" + i;
    cell.innerHTML = tuple["categorical_value"];
    if (tuple["state"] == "delete") {
      cell.innerHTML = tuple["categorical_value"].strike();
    } else {
      cell.innerHTML = tuple["categorical_value"];
    }
  }
  return extractedTupleTable;
}

function renderQueryResultAsTable(domain, show_slots, candidates) {
  const table = document.createElement("table");
  table.id = "table_" + domain;
  table.classList.add("table-bordered");
  table.classList.add("caption-top");
  const caption = document.createElement("caption");

  if (candidates.length == 0) {
    caption.textContent =
      domain +
      " (No result found based on the current conditions! A prompt will be added to guide the agent to ask the caller to relax the constraints.)";
  } else {
    caption.textContent = domain;
  }
  caption.style.fontSize = "12px";
  table.appendChild(caption);

  let header_names = ["", ""];
  header_names = header_names.concat(show_slots);
  const header = table.insertRow(-1);
  for (let i = 0; i < header_names.length; i++) {
    let header_name = header_names[i];
    let header_cell = document.createElement("TH");
    header_cell.innerHTML = header_name;
    header.appendChild(header_cell);
  }

  for (let i = 0; i < candidates.length; i++) {
    let cand = candidates[i];
    let row = table.insertRow(-1);
    let suffix = domain + "_" + i;
    row.id = "query_result_whole_row_" + suffix;
    row.setAttribute("candidate", JSON.stringify(cand));

    let cell = row.insertCell(-1);
    cell.innerHTML = i + 1;

    cell = row.insertCell(-1);
    let chk = document.createElement("input");
    chk.setAttribute("type", "checkbox");
    chk.setAttribute("value", "no");
    chk.setAttribute("id", "chk_" + suffix);
    chk.setAttribute("domain", domain);
    chk.setAttribute("name", "query_result_chk_" + domain);
    chk.setAttribute("row_idx", i);
    chk.onclick = function () {
      let checked = $(
        "input:checkbox[name=query_result_chk_" + curr_domain + "]:checked"
      ).length;
      if (checked > MAX_NUM_CHECKBOXES) {
        $(this).prop("checked", false);
        alert(
          "You can only select a maximum of " +
            MAX_NUM_CHECKBOXES +
            " checkboxes."
        );
      }
    };
    cell.appendChild(chk);

    for (let i = 0; i < show_slots.length; i++) {
      let slot = show_slots[i];
      cell = row.insertCell(-1);
      cell.id = "slot_" + slot + "_" + suffix;
      cell.innerHTML = cand[slot];
    }
  }
  return table;
}

function addDuplicateTable(
  referent,
  domain,
  slot,
  domain_to_extracted_tuples,
  C,
  raise_alert = true
) {
  let tables = document.getElementById("duplicateTuplesTables");
  //let preview_tables = document.getElementById("duplicateTuplesTablesPreview")

  duplicate_tuples = [];
  if (domain_to_extracted_tuples[domain] != undefined) {
    annotations = domain_to_extracted_tuples[domain];
    for (let i = 0; i < annotations.length; i++) {
      ann = annotations[i];
      if (
        ann["referent"] == referent &&
        ann["domain"] == domain &&
        ann["slot"] == slot
      ) {
        duplicate_tuples.push(ann);
      }
    }
  }

  table_name = referent + "_" + domain + "_" + slot;
  table_name = table_name
    .replaceAll(" ", "")
    .replaceAll("/", "")
    .replaceAll("(", "")
    .replaceAll(")", "");
  let duplicateTupleTable = document.getElementById("table_" + table_name);
  console.log("Duplicate table: ", duplicateTupleTable);
  if (duplicateTupleTable != null) {
    duplicateTupleTable.parentNode.removeChild(duplicateTupleTable);
  }

  preview_table_name = "preview_table" + table_name;
  let previewDuplicateTupleTable = document.getElementById(preview_table_name);
  if (previewDuplicateTupleTable != null) {
    previewDuplicateTupleTable.parentNode.removeChild(
      previewDuplicateTupleTable
    );
  }

  curr_duplicate_tuples = [];
  for (let i = 0; i < C.data.length; i++) {
    let ann = C.data[i];
    if (
      referent != ann.anno_referent ||
      domain != ann.anno_domain ||
      slot != ann.anno_slot
    ) {
      continue;
    }
    let state = ann.state;
    if (state === undefined) {
      state = "keep";
    }
    curr_duplicate_tuples.push({
      referent: ann.anno_referent,
      domain: ann.anno_domain,
      slot: ann.anno_slot,
      value: ann.anno_value,
      categorical_value: ann.anno_categorical_value,
      time_value: ann.anno_time_value,
      turn_idx: ann.turn_idx,
      curr_turn: true,
      state: state,
    });
  }
  console.log("curr_duplicate_tuples", curr_duplicate_tuples);

  if (curr_duplicate_tuples.length == 0) {
    return;
  }

  duplicate_tuples = duplicate_tuples.concat(curr_duplicate_tuples);
  console.log("duplicate_tuples", duplicate_tuples);

  // If no duplicate tuples in the extracted tuples, then no need to add the table.
  if (duplicate_tuples.length < 2) {
    return;
  }

  if (raise_alert) {
    alert(
      "Duplicate values found for (" +
        referent +
        "||" +
        domain +
        "||" +
        slot +
        "). Please resolve the duplicates if necessary."
    );
  }
  window.scrollTo(0, document.body.scrollHeight);

  const row_div = document.createElement("div");
  row_div.classList.add("row");
  tables.appendChild(row_div);

  duplicateTupleTable = document.createElement("table");

  let div = document.getElementById(table_name);
  if (div == null) {
    div = document.createElement("div");
    div.classList.add("col");
    div.id = table_name;
    row_div.appendChild(div);
  }
  div.appendChild(duplicateTupleTable);

  let preview_div_id = table_name + "_preview";
  let preview_div = document.getElementById(preview_div_id);
  if (preview_div == null) {
    preview_div = document.createElement("div");
    preview_div.classList.add("col");
    preview_div.id = preview_div_id;
    row_div.appendChild(preview_div);
  }

  duplicateTupleTable.id = "table_" + table_name;
  duplicateTupleTable.classList.add("table-bordered");
  duplicateTupleTable.classList.add("caption-top");
  const caption = document.createElement("caption");
  console.log("caption", caption);
  caption.textContent = table_name;
  caption.style.fontSize = "12px";
  duplicateTupleTable.appendChild(caption);

  const header_names = [
    "Keep",
    "Concat",
    "Delete",
    "Turn #",
    "Referent",
    "Domain",
    "Slot",
    "Value",
    "Categorical Value",
  ];
  const header = duplicateTupleTable.insertRow(-1);
  for (let i = 0; i < header_names.length; i++) {
    let header_name = header_names[i];
    let header_cell = document.createElement("TH");
    header_cell.innerHTML = header_name;
    header.appendChild(header_cell);
  }

  tuple_strings = [];
  for (let i = 0; i < duplicate_tuples.length; i++) {
    let tuple = duplicate_tuples[i];
    let tuple_string = JSON.stringify(tuple);
    tuple_strings.push(tuple_string);
  }
  for (let i = 0; i < duplicate_tuples.length; i++) {
    let tuple = duplicate_tuples[i];
    console.log("tuple", tuple);
    let row = duplicateTupleTable.insertRow(-1);
    let tuple_string = JSON.stringify(tuple);
    row.setAttribute("data-tuple", tuple_string);
    let suffix = table_name + "_" + i;
    row.id = "whole_row_" + suffix;

    buttons = ["keep", "concat", "delete"];
    for (button of buttons) {
      let cell = row.insertCell(-1);
      cell.id = "select_" + suffix;
      cell.style.textAlign = "center";
      let chk = document.createElement("input");
      chk.classList.add("form-check-input");
      chk.setAttribute("type", "radio");
      //chk.setAttribute('value', 'no');
      chk_name = "chk_" + suffix;
      chk.setAttribute("id", "chk_" + suffix + "_" + button);
      chk.setAttribute("suffix", suffix + "_" + button);
      chk.setAttribute("name", chk_name);
      chk.setAttribute("state", button);
      chk.setAttribute("row_idx", i);

      if (button === "concat" && tuple["categorical_value"].length != 0) {
        chk.disabled = true;
      }

      if (tuple["state"] === button) {
        chk.checked = true;
      }

      cell.appendChild(chk);
    }
    $("input[name=" + chk_name + "]:radio").change(function () {
      console.log("chk_name", chk_name);
      addPreviewDuplicateTable(referent, domain, slot);
    });

    cell = row.insertCell(-1);
    if (tuple["curr_turn"] != null) {
      cell.innerHTML = tuple["turn_idx"] + 1 + " ★";
    } else {
      cell.innerHTML = tuple["turn_idx"] + 1;
    }
    cell = row.insertCell(-1);
    cell.id = "referent_" + suffix;
    cell.innerHTML = tuple["referent"];

    cell = row.insertCell(-1);
    cell.id = "domain_" + suffix;
    cell.innerHTML = tuple["domain"];

    cell = row.insertCell(-1);
    cell.id = "slot_" + suffix;
    cell.innerHTML = tuple["slot"];

    cell = row.insertCell(-1);
    cell.id = "value_" + suffix;
    cell.innerHTML = tuple["value"];

    cell = row.insertCell(-1);
    cell.id = "categorical_value_" + suffix + "_" + i;
    cell.innerHTML = tuple["categorical_value"];
  }
  addPreviewDuplicateTable(referent, domain, slot);
}

function addPreviewDuplicateTable(referent, domain, slot) {
  table_name = referent + "_" + domain + "_" + slot;
  table_name = table_name
    .replaceAll(" ", "")
    .replaceAll("/", "")
    .replaceAll("(", "")
    .replaceAll(")", "");
  let preview_div_id = table_name + "_preview";
  preview_table_name = "preview_table" + table_name;
  let previewDuplicateTupleTable = document.getElementById(preview_table_name);
  if (previewDuplicateTupleTable != null) {
    previewDuplicateTupleTable.parentNode.removeChild(
      previewDuplicateTupleTable
    );
  }
  const preview_div = document.getElementById(preview_div_id);
  previewDuplicateTupleTable = document.createElement("table");

  previewDuplicateTupleTable.id = preview_table_name;
  previewDuplicateTupleTable.classList.add("table-bordered");
  previewDuplicateTupleTable.classList.add("caption-top");
  const caption = document.createElement("caption");
  console.log("caption", caption);
  caption.textContent = "(Preview) " + table_name;
  caption.style.fontSize = "12px";
  previewDuplicateTupleTable.appendChild(caption);

  const header_names = [
    "Turn #",
    "Referent",
    "Domain",
    "Slot",
    "Value",
    "Categorical Value",
  ];
  const header = previewDuplicateTupleTable.insertRow(-1);
  for (let i = 0; i < header_names.length; i++) {
    let header_name = header_names[i];
    let header_cell = document.createElement("TH");
    header_cell.innerHTML = header_name;
    header.appendChild(header_cell);
  }

  let duplicateTupleTable = document.getElementById("table_" + table_name);

  if (duplicateTupleTable == null) {
    return;
  }

  // -1 to skip the header.
  duplicate_tuples = [];
  concat_tuple = undefined;
  first_concat_value_idx = undefined;
  let rows = duplicateTupleTable.rows;
  for (let i = 0; i < rows.length - 1; i++) {
    let suffix = table_name + "_" + i;
    let name = "chk_" + suffix;
    radios = document.getElementsByName(name);
    for (radio of radios) {
      if (radio.checked) {
        let state = radio.getAttribute("state");
        let tuple_string = rows[i + 1].getAttribute("data-tuple");
        let tuple = JSON.parse(tuple_string);

        tuple["turn_idx"] = tuple["turn_idx"] + 1;

        if (state === "delete") {
          break;
        }

        if (state === "concat") {
          if (concat_tuple === undefined) {
            first_concat_value_idx = i;
            concat_tuple = tuple;
          } else {
            concat_tuple["value"] =
              concat_tuple["value"] + " " + tuple["value"];
            concat_tuple["turn_idx"] =
              concat_tuple["turn_idx"] + "," + tuple["turn_idx"];
          }
          break;
        }

        if (state === "keep") {
          tuple["state"] = "keep";
          duplicate_tuples.push(tuple);
          break;
        }
      }
    }
  }

  if (concat_tuple != undefined) {
    concat_tuple["state"] = "concat";
    duplicate_tuples.splice(first_concat_value_idx, 0, concat_tuple);
  }

  for (let i = 0; i < duplicate_tuples.length; i++) {
    let tuple = duplicate_tuples[i];
    let suffix = preview_table_name + "_" + i;
    let row = previewDuplicateTupleTable.insertRow(-1);
    cell = row.insertCell(-1);

    // Aleady added 1 above.
    cell.innerHTML = tuple["turn_idx"];
    cell = row.insertCell(-1);
    cell.id = "referent_" + suffix;
    cell.innerHTML = tuple["referent"];

    cell = row.insertCell(-1);
    cell.id = "domain_" + suffix;
    cell.innerHTML = tuple["domain"];

    cell = row.insertCell(-1);
    cell.id = "slot_" + suffix;
    cell.innerHTML = tuple["slot"];

    cell = row.insertCell(-1);
    cell.id = "value_" + suffix;
    cell.innerHTML = tuple["value"];

    cell = row.insertCell(-1);
    cell.id = "categorical_value_" + suffix + "_" + i;
    cell.innerHTML = tuple["categorical_value"];
  }

  preview_div.appendChild(previewDuplicateTupleTable);
}

function updateTimeSpent() {
  const totalTimeElement = document.getElementById("total_time");
  const pageTimeElement = document.getElementById("page_time");
  const endTime = new Date();
  const diffTime = endTime - startTime;

  const timeSpentOnPage = Math.floor((diffTime + page_time_spent) / 1000); // in seconds
  const minutes = Math.floor(timeSpentOnPage / 60);
  const seconds = timeSpentOnPage % 60;

  const totalTimeSpentOnPage = Math.floor((diffTime + total_time_spent) / 1000); // in seconds
  const total_minutes = Math.floor(totalTimeSpentOnPage / 60);
  const total_seconds = totalTimeSpentOnPage % 60;

  totalTimeElement.textContent = `Total: ${total_minutes} min ${total_seconds} sec`;
  pageTimeElement.textContent = `Page: ${minutes} min ${seconds} sec`;
}

function AddTimeSpentForThankyou(total_time) {
  const totalTimeElement = document.getElementById("total_time");
  const timeSpentOnPage = Math.floor(total_time / 1000); // in seconds
  const minutes = Math.floor(timeSpentOnPage / 60);
  const seconds = timeSpentOnPage % 60;
  totalTimeElement.textContent = `Total: ${minutes} min ${seconds} sec`;
}
