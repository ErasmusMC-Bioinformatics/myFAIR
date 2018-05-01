/*
** Creating the interface to make queries and show the data.
** It also sends some important data to views.py to be able to 
** upload data to Galaxy.
*/
var count = 0;
var SPARQL_ENDPOINT = 'http://localhost:3030/ds/query?query='
var USER = document.getElementById('user').innerHTML.replace('@', '');
// Show or hide divs and tables on page load
// Create a var with all searchable items
$(document).ready(function () {
    $("#samples").addClass('hidden');
    $("#search-panel").removeClass('hidden');
    $("#search-result-panel").removeClass('hidden');
    $("#results").addClass('hidden');
    $("#errorPanel").addClass('hidden');
    $("#infoPanel").addClass('hidden');
    var sampleid = "SELECT DISTINCT ?value FROM " +
        "<http://127.0.0.1:3030/ds/data/" + USER + "> WHERE " +
        "{ ?sample <http://127.0.0.1:3030/ds/data?graph=" + USER +
        "#sample_id> ?value }" + "ORDER BY(?value)"
    var study = "SELECT DISTINCT ?value FROM " +
        "<http://127.0.0.1:3030/ds/data/" + USER + "> WHERE " +
        "{ ?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
        "#group_id> ?value }" + "ORDER BY (?value)"
    var disease = "SELECT DISTINCT ?value FROM " +
        "<http://127.0.0.1:3030/ds/data/" + USER + "> WHERE " +
        "{ ?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
        "#disease> ?value }" + "ORDER BY (?value)"
    var investigation = "SELECT DISTINCT ?value FROM " +
        "<http://127.0.0.1:3030/ds/data/" + USER + "> WHERE " +
        "{ ?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
        "#investigation_id> ?value }" + "ORDER BY (?value)"
    fillList = [study, investigation, sampleid, disease]
    resultList = [study, investigation]
    for (fl in fillList) {
        var service = encodeURI(
            SPARQL_ENDPOINT + fillList[fl] + '&format=json').replace(
                /#/g, '%23').replace('+', '%2B');
        $.ajax({
            url: service, dataType: 'jsonp', success: function (result) {
                var inputOption = document.getElementById('search');
                var dataList = document.getElementById('searchDataList');
                $(inputOption).empty();
                $(inputOption).val('');
                result.results.bindings.forEach(function (v) {
                    var option = document.createElement('option');
                    option.setAttribute('width', '70%');
                    if (v.url !== undefined) {
                        option.value = v.value.value;
                        option.setAttribute('data-input-value', v.url.value);
                    }
                    else {
                        option.value = v.value.value;
                        option.setAttribute('data-input-value', v.value.value);
                    }
                    if (dataList !== null) {
                        dataList.appendChild(option);
                    }
                });
            }
        });
    }
    for (rl in resultList) {
        var service = encodeURI(
            SPARQL_ENDPOINT + resultList[rl] + '&format=json').replace(
                /#/g, '%23').replace('+', '%2B');
        $.ajax({
            url: service, dataType: 'jsonp', success: function (result) {
                var inputOption = document.getElementById('search-result');
                var resultDataList = document.getElementById('resultDataList');
                $(inputOption).empty();
                $(inputOption).val('');
                result.results.bindings.forEach(function (v) {
                    var option = document.createElement('option');
                    option.setAttribute('width', '70%');
                    if (v.url !== undefined) {
                        option.value = v.value.value;
                        option.setAttribute('data-input-value', v.url.value);
                    }
                    else {
                        option.value = v.value.value;
                        option.setAttribute('data-input-value', v.value.value);
                    }
                    if (resultDataList !== null) {
                        resultDataList.appendChild(option);
                    }
                });
            }
        });
    }
});
// Query the datafiles based on sample name, investigation name, 
// study name or disease
// Query the results based on investigation or study name
function sparqlQuery() {
    $("#errorPanel").addClass('hidden');
    $("#infoPanel").addClass('hidden');
    $("#results").addClass('hidden');
    $("#noResultPanel").addClass('hidden');
    var SEARCH = document.getElementById('search').value;
    var RSEARCH = document.getElementById('search-result').value;
    if (SEARCH != '') {
        var query = "SELECT DISTINCT ?pid ?meta ?investigation ?study ?sex " +
            "?disease ?disease_iri ?method_iri ?sample FROM " +
            "<http://127.0.0.1:3030/ds/data/" + USER + ">" +
            "WHERE {" +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#pid> ?pid ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#meta> ?meta ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#investigation_id> ?investigation ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#group_id> ?study ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#sex> ?sex ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#sample_id> ?sample ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#disease> ?disease ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#disgenet_iri> ?disease_iri ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#edam_iri> ?method_iri ." +
            "FILTER (CONTAINS(?sample, '" + SEARCH +
            "') || regex(?disease, '" + SEARCH +
            "', 'i') || regex(?study, '" + SEARCH +
            "', 'i') || regex(?investigation, '" + SEARCH +
            "', 'i'))} ORDER BY (?sample)";
    }
    if (RSEARCH != '') {
        var query = "SELECT DISTINCT (?s as ?id) ?resultid ?investigation " +
            "?study ?date ?workflow ?historyid FROM " +
            "<http://127.0.0.1:3030/ds/data/" + USER + ">" +
            "WHERE {" +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#results_id> ?resultid ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#group_id> ?study ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#investigation_id> ?investigation ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#workflow> ?workflow ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#historyid> ?historyid ." +
            "?s <http://127.0.0.1:3030/ds/data?graph=" + USER +
            "#date> ?date ." + "FILTER (regex(?study, '" + RSEARCH +
            "', 'i') || regex(?investigation, '" + RSEARCH +
            "', 'i'))} ORDER BY DESC(?date)";
    }
    var isValueMissing = false;
    if (SEARCH === '' && RSEARCH === '') {
        var errorMessage = ("<strong>Input error : " +
            "</strong>Please enter a value ")
        isValueMissing = true;
        $("#errorPanel").html(errorMessage);
        $("#errorPanel").removeClass('hidden');
        return false;
    }
    if (!isValueMissing) {
        $('#process').buttonLoader('start');
        console.log("SPARQL query \n" + query);
        var service = encodeURI(SPARQL_ENDPOINT + query + '&format=json').
            replace(/#/g, '%23').replace('+', '%2B');
        $("#infoPanel").html(
            '<strong>Info :</strong> Some queries take more time to process,' +
            'thanks for being patient');
        $.ajax({
            url: service, dataType: 'jsonp', success: function (result) {
                document.getElementById('search').value = '';
                document.getElementById('search-result').value = '';
                console.log(result);
                fillTable(result);
            },
            error: function (xhr) {
                alert("An error occured: " + xhr.status + " " +
                    xhr.statusText);
            }
        });
    }
}
// Fill table with search results
function fillTable(result) {
    $("#infoPanel").addClass('hidden');
    $("#noResultPanel").addClass('hidden');
    $('#process').buttonLoader('stop');
    $("#results").removeClass('hidden');
    $("#results_table").removeClass('hidden');
    var hasResult = false;
    var table = '<thead><tr>'
    table += '<th>select file</th>'
    result.head.vars.forEach(function (entry) {
        if (entry.indexOf("URI") === -1) {
            table += '<th><a>' + entry + '</a></th>'
        }
    });
    //    table += '<th>groups</th>'
    table += '</tr></thead><tbody>'
    var rownr = 1;
    result.results.bindings.forEach(function (value) {
        table += '<tr>'
        if (hasCol) {
            table += '<td><button id="index_buttons" onclick="getoutput()">' +
                'Show results</button></td>';
        }
        table += '<td><input type="checkbox" name="select" id="' + rownr +
            '" value="' + rownr + '"><label for="' + rownr + '"></label></td>';
        rownr = rownr + 1;
        result.head.vars.forEach(function (head) {
            if (head.indexOf("URI") === -1 && value[head] !== undefined) {
                var resource = value[head + "URI"];
                var displayName = value[head].value;
                hasResult = true;
                if (resource !== undefined) {
                    var resourceURI = resource.value;
                    var sampleTypeURI = value["sampleTypeURI"];
                    if (head === "group" && sampleTypeURI !== undefined) {
                        var sampleid = value["sampleid"];
                        var family = value["family"];
                        var group = value["group"];
                        var sex = value["sex"];
                        var galaxy = "galaxy";
                        table += '</span></span></div></td>';
                    }
                    else {
                        table += '<td><a target="_blank" href="' + resourceURI
                            + '" resource="' + resourceURI +
                            '"> <span property="rdfs:label">'
                            + displayName + '</span></a></td>';
                    }
                }
                else {
                    if (
                        displayName.indexOf("http://") >= 0 ||
                        displayName.indexOf("https://") >= 0
                    ) {
                        table += '<td><span><a target="_blank" href="' +
                            displayName + '">' + displayName +
                            '</a></span></td>';
                    } else {
                        table += '<td><span>' + displayName + '</span></td>';
                    }
                }
                if (head === "sample" && rownr >= 2) {
                    table += '<td>' +
                        '<input type="checkbox" name="samplea" id="' +
                        rownr + 'A" value="' + displayName + '">' +
                        '<label for="' + rownr + 'A">&nbsp;A</label>' +
                        '</td>' +
                        '<td>' +
                        '<input type="checkbox" name="sampleb" id="' +
                        rownr + 'B" value="' + displayName + '">' +
                        '<label for="' + rownr + 'B">&nbsp;B</label>' +
                        '</td>';
                }
            }
        });
        table += '</tr>';
    });
    table += '</tr></tbody>'
    $("#pagingContainer").empty();
    $('#results_table').html(table);
    $('#results_table').simplePagination({
        perPage: 30,
        previousButtonText: 'Prev',
        nextButtonText: 'Next',
        previousButtonClass: "btn btn-primary btn-xs",
        nextButtonClass: "btn btn-primary btn-xs"
    });
    // Check if column exists
    function hasColumn(tblSel, content) {
        var ths = document.querySelectorAll(tblSel + ' th');
        return Array.prototype.some.call(ths, function (el) {
            return el.textContent === content;
        });
    };
    var hasCol = hasColumn("#results_table thead", "workflow");
    if (hasCol) {
        document.getElementById('show_results').style.display = "block";
        $('#galaxy').html(
            '<p>Select a result and press the Show results button</p>'
        );
    } else {
        $('#galaxy').html(
            '<select name="filetype" id="filetype" class="select-option">' +
            '<optgroup label="File Type:" style="color: #21317F;">' +
            '<option value="vcf">vcf</option>' +
            '<option value="tabular">tabular</option>' +
            '<option value="fasta">fasta</option>' +
            '<option value="fastq">fastq</option>' +
            '<option value="auto">auto</option>' +
            '</optgroup>' +
            '</select>' +
            '&nbsp' +
            '<select name="dbkey" id="dbkey" class="select-option">' +
            '<optgroup label="Database" style="color: #21317F;">' +
            '<option value="hg19">HG19</option>' +
            '<option value="hg18">HG18</option>' +
            '<option value="?">?</option>' +
            '</optgroup>' +
            '</select>' +
            '&nbsp' +
            '<input type="text" id="historyname" name="historyname" ' +
            'style="width:25%;" placeholder="Enter new history name."/>' +
            '&nbsp' +
            '<button id="index_buttons" onclick="postdata(\'group\')">' +
            '<span class="glyphicon glyphicon-forward" aria-hidden="true">' +
            '</span> send to galaxy ' +
            '<span class="glyphicon glyphicon-backward" aria-hidden="true">' +
            '</span></button>'
        );
    }
    // Sort table when clicking on the header
    $('th').click(function () {
        var table = $(this).parents('table').eq(0)
        var rows = table.find(
            'tr:gt(0)').toArray().sort(comparer($(this).index()))
        this.desc = !this.desc
        if (!this.desc) { rows = rows.reverse() }
        for (var i = 0; i < rows.length; i++) { table.append(rows[i]) }
    })
    function comparer(index) {
        return function (a, b) {
            var valA = getCellValue(a, index), valB = getCellValue(b, index)
            return ($.isNumeric(valA) &&
                $.isNumeric(valB) ? valA - valB : valA.localeCompare(valB))
        }
    }
    function getCellValue(row, index) {
        return $(row).children('td').eq(index).html()
    }
    if (!hasResult) {
        $("#noResultPanel").removeClass('hidden');
        $("#results_table").addClass('hidden');
    }
}
// Get selected data by checking the checkboxes
function postdata(g) {
    document.getElementById('loading').style.display = "block";
    var workflowid = document.getElementById('workflow').value;
    var selected = new Array;
    var selectout = new Array;
    var onlydata = "";
    var col = "";
    if (document.getElementById('onlydata').checked) {
        var onlydata = document.getElementById('onlydata').value;
    }
    if (document.getElementById('col').checked) {
        var col = document.getElementById('col').value;
    }
    var dat = [];
    var meta = [];
    var group = [];
    var investigation = [];
    var samples = new Array;
    var samplesb = new Array;
    // Add sample to list if checkbox is checked
    $("input:checkbox[name=samplea]:checked").each(function () {
        samples.push($(this).val());
    });
    $("input:checkbox[name=sampleb]:checked").each(function () {
        samplesb.push($(this).val());
    });
    // Add row to list if checkbox is checked
    $("input:checkbox[name=select]:checked").each(function () {
        selected.push($(this).val());
    });
    for (s = 0; s < selected.length; s++) {
        dat.push(getrow(selected[s])[0]);
        meta.push(getrow(selected[s])[1]);
        group.push(getrow(selected[s])[2]);
        investigation.push(getrow(selected[s])[3]);
    }
    var jsonSamples = JSON.stringify(samples);
    var jsonSamplesb = JSON.stringify(samplesb);
    var jsonSelected = JSON.stringify(dat);
    var jsonMeta = JSON.stringify(meta);
    var jsonGroup = JSON.stringify(group);
    var jsonInvestigation = JSON.stringify(investigation);
    var data_id = checkData(g);
    var meta_id = checkMeta(g);
    var token = "ygcLQAJkWH2qSfawc39DI9tGxisceVSTgw9h2Diuh0z03QRx9Lgl91gneTok";
    var filetype = document.getElementById('filetype').value;
    var dbkey = document.getElementById('dbkey').value;
    var historyname = document.getElementById('historyname').value;
    $.ajax({
        type: 'POST',
        url: "upload/",
        data: {
            'data_id': data_id, 'token': token, 'workflowid': workflowid,
            'filetype': filetype, 'dbkey': dbkey, 'meta_id': meta_id,
            'selected': jsonSelected, 'meta': jsonMeta, 'onlydata': onlydata,
            'col': col, 'samples': jsonSamples, 'samplesb': jsonSamplesb,
            'historyname': historyname, 'group': jsonGroup,
            'investigation': jsonInvestigation
        },
        success: function (data) {
            if (dat.length <= 0) {
                document.getElementById('errormessage').innerHTML =
                    "No file selected, please try again."
                document.getElementById('error').style.display = "block";
                document.getElementById('finished').style.display = "none";
                document.getElementById('loading').style.display = "none";
            } else {
                document.getElementById('loading').style.display = "none";
                document.getElementById('error').style.display = "none";
                document.getElementById('finished').style.display = "block";
            }
            setTimeout(refresh, 5000);
        },
        error: function (data) {
            document.getElementById('loading').style.display = "none";
            document.getElementById('finished').style.display = "none";
            document.getElementById('error').style.display = "block";
            setTimeout(refresh, 5000);
        }
    });
}
// Get selected output information
function getoutput() {
    var selected = new Array;
    var group = [];
    var investigations = [];
    var resultid = new Array;
    $("input:checkbox[name=select]:checked").each(function () {
        selected.push($(this).val());
    });
    for (s = 0; s < selected.length; s++) {
        resultid.push(getrow(selected[s])[1]);
        group.push(getrow(selected[s])[2]);
        investigations.push(getrow(selected[s])[3]);
    }
    var jsonGroup = JSON.stringify(group);
    var jsonInvestigation = JSON.stringify(investigations);
    var jsonResultid = JSON.stringify(resultid);
    $.ajax({
        type: 'POST',
        url: "results",
        data: {
            'group': jsonGroup, 'resultid': jsonResultid,
            'investigations': jsonInvestigation
        },
        success: function (data) {
            window.location.href = "results";
        },
        error: function (data) {
            window.location.reload();
        }
    });
}
// Refresh the page
function refresh() {
    // window.location.reload();
    // window.parent.window.location.reload();
    window.location.href = "";
}
// Loop through the results_table and get the pid (first column)
function checkData(g) {
    var n1 = document.getElementById('results_table').rows.length;
    var i = 0, j = 0;
    var str = "";
    for (i = 0; i < n1; i++) {
        var groups = document.getElementById(
            'results_table').rows[i].cells.item(3).innerText;
        if (groups == g) {
            var n = i;
            var n2 = document.getElementById('results_table').rows[i].length;
            for (i = 1; i < n1; i++) {
                var x = document.getElementById(
                    'results_table').rows[n].cells.item(j + 1).innerText;
            }
        }
        else {
            x = "";
        }
        str = str + x;
    }
    return str;
}
// Go through the results table and get the metadata
function checkMeta(g) {
    var n1 = document.getElementById('results_table').rows.length;
    var i = 0, j = 0;
    var str = "";
    for (i = 0; i < n1; i++) {
        var groups = document.getElementById(
            'results_table').rows[i].cells.item(3).innerText;
        if (groups == g) {
            var n = i;
            var n2 = document.getElementById('results_table').rows[i].length;
            for (i = 1; i < n1; i++) {
                var x = document.getElementById(
                    'results_table').rows[n].cells.item(j + 2).innerText;
            }
        }
        else {
            x = "";
        }
        str = str + x;
    }
    return str;
}
// Get the selected row and return all columns
function getrow(r) {
    var str = "";
    var str2 = "";
    var str3 = "";
    var str4 = "";
    var x = document.getElementById(
        'results_table').rows[r].cells.item(1).innerText;
    var y = document.getElementById(
        'results_table').rows[r].cells.item(2).innerText;
    var z = document.getElementById(
        'results_table').rows[r].cells.item(4).innerText;
    var i = document.getElementById(
        'results_table').rows[r].cells.item(3).innerText;
    str = str + x;
    str2 = str2 + y;
    str3 = str3 + z;
    str4 = str4 + i;
    return [str, str2, str3, str4];
}
// Rerun the analysis with information from the results
function rerun_analysis() {
    wid = document.getElementById("workflowid").innerText;
    inputs = document.getElementById("input-list").innerText;
    inputs = inputs.split(',');
    resultid = document.getElementById("title").innerText;
    var urls = new Array;
    for (i = 0; i <= (inputs.length - 1); i++) {
        urls.push(
            resultid.replace(" ", "") + "/" +
            inputs[i].replace(" ", "").replace("\n", "").replace(
                "'", "").replace("[", "").replace("]", "").replace("'", "")
        )
    }
    var jsonURLS = JSON.stringify(urls);
    document.getElementById('running').style.display = "block";
    $.ajax({
        type: 'POST',
        url: "rerun",
        data: {
            'workflowid': wid, 'inputs': inputs, 'urls': jsonURLS,
            'resultid': resultid
        },
        success: function (data) {
            document.getElementById('running').style.display = "none";
            document.getElementById('finished').style.display = "block";
            setTimeout(refresh, 5000);
        },
        error: function (data) {
            document.getElementById('error').style.display = "block";
            setTimeout(refresh, 5000);
        },
    });
}