/**
 * Handling all the JavaScript for the myFAIR webpage. Generates the
 * SPARQL queries to get the investigations, studies, assays and results 
 * available in SEEK. Passes all needed variables to rerun an analysis to
 * the Python code.
 * 
 * @summary Creating the myFAIR interface and connect with the Python code.
 *
 * @link   https://github.com/ErasmusMC-Bioinformatics/myFAIR
 * @file   This files defines the myFAIR JavaScript functionality.
 * @author Rick Jansen <rick.jansen1984@gmail.com>
 */
var USER = document.getElementById('user').innerHTML.replace('@', '');
var SERVER = document.getElementById('storagename').innerHTML
var STORAGETYPE = document.getElementById('storage-type').innerHTML
var VIRTUOSO_URL = document.getElementById('virtuoso-url').innerHTML
var SPARQL_ENDPOINT = VIRTUOSO_URL + '?default-graph-uri=&query='
var SEARCH_ASSAY = ''
if(STORAGETYPE === "SEEK") {
    document.getElementById("ssearch").style.display = "block";
    document.getElementById("asearch").style.display = "block";
} else {
    var SPARQL_ENDPOINT = 'http://localhost:3030/ds/query?query='
}


/**
 * Show or hide divs and tables on page load.
 * Run SPARQL queries to retrieve metadata from
 * the virtuoso triple store.
 */
$(document).ready(function () {
    $("#samples").addClass('hidden');
    $("#search-panel").removeClass('hidden');
    $("#search-result-panel").removeClass('hidden');
    $("#process").removeClass('hidden');
    $("#results").addClass('hidden');
    $("#errorPanel").addClass('hidden');
    $("#infoPanel").addClass('hidden');
    var investigations = "PREFIX dcterms: <http://purl.org/dc/terms/>" + 
        "SELECT DISTINCT ?value WHERE {?s dcterms:title ?value . " +
        "FILTER regex(?s, 'investigations', 'i')}"
    var studies = "PREFIX dcterms: <http://purl.org/dc/terms/> " +
        "SELECT DISTINCT ?value WHERE {" +
        "?s dcterms:title ?value " +
        "FILTER regex(?s, 'studies', 'i')}"
    var assays = "PREFIX dcterms: <http://purl.org/dc/terms/> " +
        "SELECT DISTINCT ?value WHERE {" +
        "?s dcterms:title ?value " +
        "FILTER (!regex(?value, '__result__', 'i')) . " +
        "FILTER regex(?s, 'assays', 'i')}"
    var iservice = encodeURI(
        SPARQL_ENDPOINT + investigations + '&format=json').replace(
            /#/g, '%23').replace('+', '%2B');
    $.ajax({
        url: iservice, dataType: 'jsonp', success: function (result) {
            var iinputOption = document.getElementById('isearch');
            var idataList = document.getElementById('isearchDataList');
            $(iinputOption).empty();
            $(iinputOption).val('');
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
                if (idataList !== null) {
                    idataList.appendChild(option);
                }
            });
        }
    });
    var sservice = encodeURI(
        SPARQL_ENDPOINT + studies + '&format=json').replace(
            /#/g, '%23').replace('+', '%2B');
    $.ajax({
        url: sservice, dataType: 'jsonp', success: function (result) {
            var sinputOption = document.getElementById('ssearch');
            var sdataList = document.getElementById('ssearchDataList');
            $(sinputOption).empty();
            $(sinputOption).val('');
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
                if (sdataList !== null) {
                    sdataList.appendChild(option);
                }
            });
        }
    });
    var aservice = encodeURI(
        SPARQL_ENDPOINT + assays + '&format=json').replace(
            /#/g, '%23').replace('+', '%2B');
    $.ajax({
        url: aservice, dataType: 'jsonp', success: function (result) {
            var ainputOption = document.getElementById('asearch');
            var adataList = document.getElementById('asearchDataList');
            $(ainputOption).empty();
            $(ainputOption).val('');
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
                if (adataList !== null) {
                    adataList.appendChild(option);
                }
            });
        }
    });
    resultList = [studies]
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


/**
 * Generate SPARQL queries to get metadata related to
 * the data files on the SEEK server.
 */
function sparqlQuery() {
    $("#errorPanel").addClass('hidden');
    $("#infoPanel").addClass('hidden');
    $("#results").addClass('hidden');
    $("#noResultPanel").addClass('hidden');
    var ISEARCH = document.getElementById('isearch').value;
    var SSEARCH = document.getElementById('ssearch').value;
    var ASEARCH = document.getElementById('asearch').value;
    var RSEARCH = document.getElementById('search-result').value;
    if (ISEARCH != '' || SSEARCH != '' || ASEARCH != '') {
        if(STORAGETYPE === "SEEK"){
            var query = 
                "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> " +
                "PREFIX dcterms: <http://purl.org/dc/terms/> " +
                "PREFIX jerm: <http://jermontology.org/ontology/JERMOntology#> " +
                "SELECT DISTINCT (COALESCE(?fileurl, \"NA\") as ?fileurl) (COALESCE(?filetitle, \"NA\") as ?filetitle) ?investigation ?study ?assay WHERE {" +
                "?i dcterms:title ?investigation ; " +
                "rdf:type jerm:Investigation ." +
                "?i jerm:itemProducedBy ?projectid . " +
                "?projectid dcterms:title ?project . " +
                "?i jerm:hasPart ?studyid . " +
                "?studyid dcterms:title ?study . " +
                "?studyid jerm:hasPart ?assayid . " +
                "?assayid dcterms:title ?assay . " +
                "OPTIONAL {" +
                "?fileurl jerm:isPartOf ?assayid . " + 
                "?fileurl dcterms:title ?filetitle ." +
                "}" +
                "FILTER regex(?investigation, '" + ISEARCH + "', 'i') . " +
                "FILTER regex(?study, '" + SSEARCH + "', 'i') . " +
                "FILTER regex(?assay, '" + ASEARCH + "', 'i') . " +
                "FILTER (!regex(?assay, '__result__', 'i')) . " +
                "FILTER (!regex(?fileurl, 'samples', 'i')) . " +
                "}";
        } 
    }
    if (RSEARCH != '') {
        var query = 
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> " +
        "PREFIX dcterms: <http://purl.org/dc/terms/> " +
        "PREFIX jerm: <http://jermontology.org/ontology/JERMOntology#> " +
        "SELECT DISTINCT ?assayid (?assay AS ?result_assay) ?investigation ?study ?date  WHERE {" +
            "?i dcterms:title ?investigation ; " +
            "rdf:type jerm:Investigation ." +
            "?i jerm:itemProducedBy ?projectid . " +
            "?projectid dcterms:title ?project . " +
            "?i jerm:hasPart ?studyid . " +
            "?studyid dcterms:title ?study . " +
            "?studyid jerm:hasPart ?assayid . " +
            "?assayid dcterms:title ?assay . " +
            "?assayid dcterms:created ?date . " +
            "?file jerm:isPartOf ?assayid . " + 
            "?file dcterms:title ?filetitle . " +
            "FILTER regex(?study, '" + RSEARCH + "', 'i') ." +
            "FILTER regex(?assay, '__result__', 'i')} ORDER BY DESC(?date)";
    }
    var isValueMissing = false;
    if (ISEARCH === '' && SSEARCH === '' && ASEARCH === '' && RSEARCH === '') {
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
                document.getElementById('isearch').value = '';
                document.getElementById('ssearch').value = '';
                document.getElementById('asearch').value = '';
                document.getElementById('search-result').value = '';                
                if (ASEARCH != '') {
                    SEARCH_ASSAY = ASEARCH;
                } else {
                    try {
                        result.results.bindings.forEach(function (value) {
                            SEARCH_ASSAY = value.assay.value;
                        });
                    } catch (error) {
                        console.log('No value');
                        SEARCH_ASSAY = '';
                    }
                }
                fillTable(result);
            },
            error: function (xhr) {
                alert("An error occured: " + xhr.status + " " +
                    xhr.statusText);
            }
        });
    }
}


/**
 * Generates a table with the results from the SPARQL queries.
 * 
 * @param {Object} result SPARQL query results
 */
function fillTable(result) {
    $("#search-panel").addClass('hidden');
    $("#search-result-panel").addClass('hidden');
    $("#process").addClass('hidden');
    $("#infoPanel").addClass('hidden');
    $("#noResultPanel").addClass('hidden');
    $('#process').buttonLoader('stop');
    $("#results").removeClass('hidden');
    $("#results_table").removeClass('hidden');
    var hasResult = false;
    var table = '<thead><tr>'
    table += '<th>select file(s)</th>'
    result.head.vars.forEach(function (entry) {
        if (entry.indexOf("URI") === -1) {
            table += '<th><a>' + entry + '</a></th>'
        } else {
            table += '<th><a></a></th>'
        }
    });
    table += '</tr></thead><tbody>'
    var rownr = 1;
    result.results.bindings.forEach(function (value) {
        table += '<tr>'
        if (hasCol) {
            table += '<td><button id="index_buttons" onclick="getoutput()">' +
                'Show results</button></td>';
        }
        try {
            if (value.fileurl.value === "NA") {
                table += '<td>&nbsp;</td>';
            } else {
                table += '<td><input type="checkbox" name="select" id="' + rownr +
                '" value="' + rownr + '"><label for="' + rownr + '"></label></td>';
            }
        } catch (error) {
            table += '<td><input type="checkbox" name="select" id="' + rownr +
                '" value="' + rownr + '"><label for="' + rownr + '"></label></td>';
        }
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
                        displayName = (
                            SERVER + '/' +
                            displayName.split('/')[3] + '/' +
                            displayName.split('/')[4]
                        )
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


    /**
     * Check if a column exists and has the specified header.
     * 
     * @param {string} tblSel Selected table header.
     * @param {string} content Content of the table header.
     */
    function hasColumn(tblSel, content) {
        var ths = document.querySelectorAll(tblSel + ' th');
        return Array.prototype.some.call(ths, function (el) {
            return el.textContent === content;
        });
    };

    if(STORAGETYPE === "SEEK"){
        var hasCol = hasColumn("#results_table thead", "result_assay");
    } else {
        var hasCol = hasColumn("#results_table thead", "workflow");
    }
    if (hasCol) {
        document.getElementById('workflow_select').style.display = "none";
        document.getElementById('show_results').style.display = "block";
        $('#galaxy').html(
            '<p>Select a result and press the Show results button</p>'
        );
    } else {
        document.getElementById('workflow_select').style.display = "block";
        document.getElementById('show_results').style.display = "none";
        $('#galaxy').html(
            '<div id="omicsdiArea" style="display:block;">' +
                '<span><b><i>Omics DI entry:</i></b></span>' +
                '<input type="text" id="param" name="param" ' +
                'style="width:99%;" placeholder="Enter Omics DI accession number (required)"/>' +
                '<br>' +
                '<br>' +
            '</div>' +
            '<div id="checkArea" style="display:block;">' +
                '<b><i>Select which tags to add</i></b>' +
                '<br>' +
                '<input type="checkbox" id="discheck" name="discheck" onchange="checkTagging()"/>' +
                '<label for="discheck">&nbsp;DisGeNET</label>' +
                '&emsp;&emsp;' +
                '<input type="checkbox" id="olscheck" name="olscheck" onchange="checkTagging()"/>' +
                '<label for="olscheck">&nbsp;OLS</label>' +
                '<br>' +
            '</div>' +
            '<div id="disgenetArea" style="display:none;">' +
                '<hr>' +
                '<span><b><i>DisGeNET entry:</i></b></span>' +
                '<input type="text" id="omicsdi-disgenet" name="omicsdi-disgenet" ' +
                'style="width:99%; placeholder="Enter DisGeNET entry i.e. (optional)"/>' +
                '<div id="disgenetResults" style="display:none;">' +
                    '<b><i>Please select a DisGeNET tag from the dropdown menu.</i></b>' +
                    '<select id="disgenetList" name="disgenetList" style="width:100.3%;">' +
                    '</select>' +
                '</div>' +
                '<br>' +
                '<div id="loadingDisgenet" style="text-align:center;display:none;float: none;">' +
                    '<img id="loadingimg" src="../static/img/wait.gif" width="10%" height="10%">' +
                '</div>' +
                '<button id="index_buttons" style="width:100.5%;" onclick="searchDisgenet()">' +
                    'Search DisGeNET' +
                '</button>' +
                '<br>' +
                '<br>' +
            '</div>' +
            '<div id="olsArea" style="display:none;">' +
                '<hr>' +
                '<span><b><i>OLS entry:</i></b></span>' +
                '<input type="text" id="omicsdi-ols" name="omicsdi-ols" ' +
                'style="width:99%; placeholder="Enter OLS search term i.e. bioinformatics (optional)"/>' +
                '<div id="olsResults" style="display:none;">' +
                    '<b><i>Please select an OLS tag from the dropdown menu.</i></b>' +
                    '<select id="olsList" name="olsList" style="width:100.3%;">' +
                    '</select>' +
                '</div>' +
                '<br>' +
                '<div id="loadingOLS" style="text-align:center;display:none;float: none;">' +
                    '<img id="loadingimg" src="../static/img/wait.gif" width="10%" height="10%">' +
                '</div>' +
                '<button id="index_buttons" style="width:100.5%;" onclick="searchOLS()">Search OLS</button>' +
                '<br>' +
                '<br>' +
                '<hr>' +
            '</div>' +
            '<div id="galaxyArea" style="display:block;">' +
                '<select name="filetype" id="filetype" class="select-option">' +
                    '<optgroup label="File Type:" style="color: #21317F;">' +
                        '<option value="auto">auto</option>' +
                        '<option value="vcf">vcf</option>' +
                        '<option value="tabular">tabular</option>' +
                        '<option value="fasta">fasta</option>' +
                        '<option value="fastq">fastq</option>' +
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
                'style="max-width:98%;" placeholder="Enter new history name (optional)"/>' +
            '</div>' +
            '<button id="index_buttons" style="width: 24%;" onclick="refresh()">' +
            '<span class="glyphicon glyphicon-backward" aria-hidden="true"></span> Search again</button>' +
            '&nbsp' +
            '<button id="index_buttons" style="width: 75%;" onclick="postdata(\'group\')">' +
            'Send to Galaxy</button>'
        );
    }


    /**
     * Clicking on the table header.
     */
    $('th').click(function () {
        var table = $(this).parents('table').eq(0)
        var rows = table.find(
            'tr:gt(0)').toArray().sort(comparer($(this).index()))
        this.desc = !this.desc
        if (!this.desc) { rows = rows.reverse() }
        for (var i = 0; i < rows.length; i++) { table.append(rows[i]) }
    })


    /**
     * Sort on the header when clicked on.
     * 
     * @param {number} index Row number.
     */
    function comparer(index) {
        return function (a, b) {
            var valA = getCellValue(a, index), valB = getCellValue(b, index)
            return ($.isNumeric(valA) &&
                $.isNumeric(valB) ? valA - valB : valA.localeCompare(valB))
        }
    }


    /**
     * Gets the value of a cell after sorting.
     * 
     * @param {object} row HTML object to get the row.
     * @param {number} index Row number.
     */
    function getCellValue(row, index) {
        return $(row).children('td').eq(index).html()
    }
    if (!hasResult) {
        $("#noResultPanel").removeClass('hidden');
        $("#results_table").addClass('hidden');
    } else {
        var elementExists = document.getElementsByName("select");
        if (elementExists.length > 0) {
            document.getElementById('checkArea').style.display = "none";
            document.getElementById('omicsdiArea').style.display = "none";
        } else {
            document.getElementById('checkArea').style.display = "block";
            document.getElementById('omicsdiArea').style.display = "block";
        }
    }
}


/**
 * Check if the DisGeNET and/or OLS checkboxes are checked.
 * When the checkbox is checked the specified area will be displayed.
 */
function checkTagging() {
    var x = document.getElementById('discheck').checked;
    var y = document.getElementById('olscheck').checked;
    if(x) {
        document.getElementById('disgenetArea').style.display = "block";
    } else {
        document.getElementById('disgenetArea').style.display = "none";
    }
    if(y) {
        document.getElementById('olsArea').style.display = "block";
    } else {
        document.getElementById('olsArea').style.display = "none";
    }
}


/**
 * Search query to get DisGeNET results to add as a tag 
 * to the Omics DI results.
 */
function searchDisgenet() {
    document.getElementById('loadingDisgenet').style.display = "block";
    disgenet_term = document.getElementById('omicsdi-disgenet').value;
    var query = 
    "PREFIX dcterms: <http://purl.org/dc/terms/>" +
    "SELECT * " +
    "WHERE { SERVICE <http://rdf.disgenet.org/sparql/> { " +
    "?uri dcterms:title ?disease . " +
    "FILTER(contains(?disease, \"" + disgenet_term + "\"))" +
    "} " +
    "} LIMIT 10";
    var service = encodeURI(SPARQL_ENDPOINT + query + '&format=json').
        replace(/#/g, '%23').replace('+', '%2B');
    $.ajax({
        url: service, dataType: 'jsonp', success: function (result) {
            document.getElementById('omicsdi-disgenet').value = '';
            var disgetnetList = document.getElementById('disgenetList');
            document.getElementById('disgenetResults').style.display = "block";
            document.getElementById('loadingDisgenet').style.display = "none";
            $(disgetnetList).empty();
            $(disgetnetList).val('');
            result.results.bindings.forEach(function (v) {
                var option = document.createElement('option');
                option.setAttribute('width', '70%');
                option.text = v.disease.value;
                option.value = v.uri.value;
                option.setAttribute('data-input-value', v.uri.value);
                if (disgetnetList !== null) {
                    disgetnetList.appendChild(option);
                }
            });
        },
        error: function (xhr) {
            alert("An error occured: " + xhr.status + " " +
                xhr.statusText);
        }
    });
}


/**
 * 
 */
function searchOLS() {
    document.getElementById('loadingOLS').style.display = "block";
    ols_term = document.getElementById('omicsdi-ols').value;
    var query = "https://www.ebi.ac.uk/ols/api/search?q=" + ols_term;
    var service = encodeURI(query + '&format=json').
        replace(/#/g, '%23').replace('+', '%2B');
    $.ajax({
        url: service, success: function (result) {
            var olsList = document.getElementById('olsList');
            olsList.style.display = "block";
            document.getElementById('omicsdi-ols').value = '';
            document.getElementById('olsResults').style.display = "block";
            document.getElementById('loadingOLS').style.display = "none";
            $(olsList).empty();
            $(olsList).val('');
            result.response.docs.forEach(function (v) {
                var option = document.createElement('option');
                option.setAttribute('width', '70%');
                option.text = v.label + " (" + v.ontology_name + ") ";
                option.value = v.iri;
                if (olsList !== null) {
                    olsList.appendChild(option);
                }
            });
        },
        error: function (xhr) {
            alert("An error occured: " + xhr.status + " " +
                xhr.statusText);
        }
    });
}


/**
 * Send all selected data to the python code 
 * so it can be send to a Galaxy server.
 * 
 * @param {string} groupname Group name.
 */
function postdata(groupname) {
    document.getElementById('loading').style.display = "block";
    var workflowid = document.getElementById('workflow').value;
    var selected = new Array;
    var selectout = new Array;
    var dat = [];
    var group = [];
    var investigation = [];
    var samples = new Array;
    var samplesb = new Array;
    var searched_assay = SEARCH_ASSAY;
    console.log(searched_assay);
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
        // meta.push(getrow(selected[s])[1]);
        group.push(getrow(selected[s])[2]);
        investigation.push(getrow(selected[s])[3]);
        var searched_assay = getrow(selected[s])[4];
    }
    var jsonSamples = JSON.stringify(samples);
    var jsonSamplesb = JSON.stringify(samplesb);
    var jsonSelected = JSON.stringify(dat);
    var jsonGroup = JSON.stringify(group);
    var jsonInvestigation = JSON.stringify(investigation);
    var data_id = checkData(groupname);
    var token = "ygcLQAJkWH2qSfawc39DI9tGxisceVSTgw9h2Diuh0z03QRx9Lgl91gneTok";
    var filetype = document.getElementById('filetype').value;
    var dbkey = document.getElementById('dbkey').value;
    var historyname = document.getElementById('historyname').value;
    var param = document.getElementById('param').value;
    var eDisgenet = document.getElementById("disgenetList");
    var eOLS = document.getElementById("olsList");
    try {
        var omicsdi_disgenet = eDisgenet.options[eDisgenet.selectedIndex].value;
    } catch (error) {
        var omicsdi_disgenet = "";
    }
    try {
        var omicsdi_ols = eOLS.options[eOLS.selectedIndex].value;
    } catch (error) {
        var omicsdi_ols = "";
    }
    $.ajax({
        type: 'POST',
        url: "upload/",
        data: {
            'data_id': data_id, 'token': token, 'workflowid': workflowid,
            'filetype': filetype, 'dbkey': dbkey, 'selected': jsonSelected,
            'samples': jsonSamples, 'samplesb': jsonSamplesb,
            'historyname': historyname, 'group': jsonGroup, 'param': param,
            'investigation': jsonInvestigation, 'searched_assay': searched_assay,
            'omicsdi_disgenet': omicsdi_disgenet, 'omicsdi_ols': omicsdi_ols
        },
        success: function (data) {
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


/**
 * Get selected output information
 */
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


/**
 * Refresh the page.
 */
function refresh() {
    window.location.href = "";
}


/**
 * Get data from the results table.
 * 
 * @param {string} groupname Group name.
 */
function checkData(groupname) {
    var n1 = document.getElementById('results_table').rows.length;
    var i = 0, j = 0;
    var str = "";
    for (i = 0; i < n1; i++) {
        var groups = document.getElementById(
            'results_table').rows[i].cells.item(3).innerText;
        if (groups == groupname) {
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

/**
 * Get the selected rows.
 * 
 * @param {string} row Row number needed to get text from specific row.
 */
function getrow(row) {
    var str = "";
    var str2 = "";
    var str3 = "";
    var str4 = "";
    var str5 = "";
    var x = document.getElementById(
        'results_table').rows[row].cells.item(1).innerText;
    var y = document.getElementById(
        'results_table').rows[row].cells.item(2).innerText;
    var z = document.getElementById(
        'results_table').rows[row].cells.item(4).innerText;
    var i = document.getElementById(
        'results_table').rows[row].cells.item(3).innerText;
    var a = document.getElementById(
        'results_table').rows[row].cells.item(5).innerText;
    str = str + x;
    str2 = str2 + y;
    str3 = str3 + z;
    str4 = str4 + i;
    str5 = str5 + a;
    return [str, str2, str3, str4, str5];
}


/**
 * Get all information needed to rerun an analysis.
 */
function rerun_analysis() {
    document.getElementById('input-list').style.display = "block";
    wid = document.getElementById("workflowid").innerText;
    inputs = document.getElementById("input-list").innerText;
    inputs = inputs.split('\n');
    if ($('#omicsdi_link').length > 0) {
        var omicsdi_link = document.getElementById("omicsdi_link").innerText;
      } else {
        var omicsdi_link;
      }
    resultid = document.getElementById("title").innerText;
    var urls = [];
    for (i = 0; i <= (inputs.length - 1); i++) {
        if (inputs[i] !== "") {
            urls.push(
                (resultid.replace(" ", "").replace("\n", "") + "/" +
                    inputs[i].replace(" ", "").replace("\n", "").replace(
                        "'", "").replace("[", "").replace("]", "").replace("'", ""))
            )
        }
    }
    var jsonURLS = JSON.stringify(urls)
    document.getElementById('running').style.display = "block";
    document.getElementById('wrapper').style.display = "none";
    document.getElementById('showresults').style.display = "none";
    $.ajax({
        type: 'POST',
        url: "rerun",
        data: {
            'workflowid': wid, 'inputs': inputs, 'urls': jsonURLS,
            'omicsdi_link':omicsdi_link ,'resultid': resultid
        },
        success: function (data) {
            document.getElementById('running').style.display = "none";
            document.getElementById('finished').style.display = "block";
            setTimeout(refresh, 5000);
        },
        error: function (data) {
            document.getElementById('running').style.display = "none";
            document.getElementById('error').style.display = "block";
            setTimeout(refresh, 5000);
        },
    });
}
