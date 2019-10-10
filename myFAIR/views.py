import csv
import hashlib
import json
import os
import re
import subprocess
import rdflib
import time
import uuid
import tempfile
import magic
import random

from urllib.parse import urlparse
from myFAIR import settings
from subprocess import call
from subprocess import check_call
from time import strftime, gmtime
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.client import ConnectionError
from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import render_to_response, render, HttpResponseRedirect, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path
from itertools import groupby
from datetime import datetime, timedelta
from pytz import timezone


@csrf_exempt
def login(request):
    """Login page where Galaxy server, email address, Galaxy password,
    storage location, username and password are stored in a session.

    Arguments:
        request: Login details filled in from the login page.
    """
    if request.method == 'POST':
        err = []
        if request.POST.get('server')[-1] == '/':
            server = request.POST.get('server')
        else:
            server = request.POST.get('server') + '/'
        username = request.POST.get('username')
        password = request.POST.get('password')
        fullname = request.POST.get('fullname')
        galaxypass = request.POST.get("galaxypass")
        galaxyemail = request.POST.get("galaxyemail")
        storagetype = "SEEK"
        noexpire = request.POST.get('no-expire')
        if settings.SEEK_URL != "":
            request.session['storage_type'] = storagetype
            request.session['storage'] = settings.SEEK_URL
        else:
            request.session.flush()
        if galaxypass != "":
            request.session["galaxypass"] = galaxypass
        else:
            err.append("No email address or password")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
        if galaxyemail != "":
            request.session["galaxyemail"] = galaxyemail
        else:
            err.append("No email address or password")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
        if server != "":
            request.session['server'] = server
        else:
            err.append("No server selected")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
        if username != "" and password != "" and fullname != "":
            request.session['fullname'] = fullname
            request.session['username'] = username
            request.session['password'] = password
        else:
            err.append("No valid username or password")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
        if noexpire == "yes":
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(43200)
        return render_to_response('home.html', context={
            'error': err})
    return render(request, 'login.html')


@csrf_exempt
def index(request):
    """Homepage information. The ISA information from the storage location and
    the triple storea re available from the homepage. Data can be searched or
    Galaxy histories can be send to an existing investigation - Study.

    Arguments:
        request: Getting the user details from request.session.

    Raises:
        Exception: Failed to het galaxy user information.
    """
    if (
        request.method == 'POST' and
        request.session.get('username') is None
    ):
        login(request)
    else:
        pass
    if (
        request.session.get('username') is None or
        request.session.get('username') == ""
    ):
        err = ""
        return render_to_response('login.html', context={
            'error': err})
    else:
        if not os.path.isdir(request.session.get('username')):
            call(["mkdir", request.session.get('username')])
        if request.POST.get('inv') is not None:
            investigation = request.POST.get('inv')
        else:
            investigation = ""
        folders = []
        investigations = []
        username = request.session.get('username')
        password = request.session.get('password')
        virtuoso = settings.VIRTUOSO_JS_URL
        server = request.session.get('server')
        try:
            if request.method == "POST":
                gusername, workflows, his, dbkeys = get_galaxy_info(
                    request.POST.get('server'),
                    request.POST.get('galaxyemail'),
                    request.POST.get("galaxypass")
                )
            else:
                gusername, workflows, his, dbkeys = get_galaxy_info(
                    request.session.get('server'),
                    request.session.get('galaxyemail'),
                    request.session.get("galaxypass")
                )
        except Exception:
            request.session.flush()
            return render_to_response('login.html', context={
                'error': 'Credentials incorrect. Please try again'})
        return render(
            request, 'home.html',
            context={'workflows': workflows, 'histories': his,
                     'user': gusername, 'username': username,
                     'password': password, 'server': server,
                     'storage': settings.SEEK_URL,
                     'storagetype': request.session.get('storage_type'),
                     'virtuoso_url': virtuoso,
                     'investigations': investigations,
                     'studies': folders, 'inv': investigation,
                     'dbkeys': dbkeys,
                     'galaxyemail': request.session.get('galaxyemail'),
                     'galaxypass': request.session.get('galaxypass')}
        )


def check_seek_permissions(username, password, userid, studyid):
    """Checks if the user has permissions to add an assay to the 
    selected study. Returns a true if user can create the assay.

    Arguments:
        username: SEEK username.
        password: SEEK password.
        server: The SEEK server URL.
        userid: User ID of the logged in user.
        studyid: Study ID to check for permissions.

    Returns:
        True/False: The user has permissions to add an assay to the study or 
        the user does not have permissions to add an assay to the study.
    """
    peoplequery = ("curl -X GET " + settings.SEEK_URL + "/people/" + str(userid) +
                   " -H \"accept: application/json\"")
    sids = []
    userinfo = subprocess.Popen([peoplequery],
                                stdout=subprocess.PIPE,
                                shell=True).communicate()[0].decode()
    jsonuser = json.loads(userinfo)
    studyids = jsonuser["data"]["relationships"]["studies"]["data"]
    for datanr in range(0, len(studyids)):
        sids.append(jsonuser["data"]["relationships"]
                    ["studies"]["data"][datanr]["id"])
    if studyid in sids:
        return True
    else:
        return False


@csrf_exempt
def seekupload(username, password, title, file, filename,
               content_type, userid, projectid, assayid, description, tags):
    """Uploads data files to an assay.

    Arguments:
        username: SEEK username.
        password: SEEK password.
        title: Title of the uploaded data file.
        file: The file that will be uploaded to the SEEK server.
        filename: Name of the uploaded file.
        content_type: Content type of the uploaded file (e.g. pdf, xml etc.)
        userid: SEEK user ID of the data uploader.
        projectid: SEEK project ID related to the data file.
        assayid: SEEK assay ID related to the data file.
        description: The description of the data.
    """
    tagstring = ""
    if len(tags) > 1:
        for tag in tags[:-1]:
            tagstring += "\\\"" + tag + "\\\", "
        tagstring += "\\\"" + tags[-1] + "\\\""
    else:
        tagstring += "\\\"" + tags[0] + "\\\""
    data_instance_query = (
        "curl -u " + username + ":" + password +
        " -X POST \"" + settings.SEEK_URL + "/data_files\" "
        "-H \"accept: application/json\" "
        "-H \"Content-Type: application/json\" "
        "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"data_files\\\", "
        "\\\"attributes\\\": "
        "{ \\\"title\\\": \\\"" + title + "\\\", "
        "\\\"description\\\": \\\"" + description + "\\\", "
        "\\\"tags\\\": [" + tagstring + " ], "
        "\\\"license\\\": \\\"CC-BY-4.0\\\", "
        "\\\"content_blobs\\\": [ { "
        "\\\"original_filename\\\": \\\"" + filename + "\\\", "
        "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
        "\\\"policy\\\": "
        "{ \\\"access\\\": \\\"download\\\", "
        "\\\"permissions\\\": [ "
        "{ \\\"resource\\\": "
        "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
        "\\\"type\\\": \\\"projects\\\" }, "
        "\\\"access\\\": \\\"edit\\\" } ] } }, "
        "\\\"relationships\\\": "
        "{ \\\"creators\\\": "
        "{ \\\"data\\\": [ "
        "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
        "\\\"type\\\": \\\"people\\\" } ] }, "
        "\\\"projects\\\": "
        "{ \\\"data\\\": [ "
        "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
        "\\\"type\\\": \\\"projects\\\" } ] }, "
        "\\\"assays\\\": "
        "{ \\\"data\\\": [ "
        "{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
        "\\\"type\\\": \\\"assays\\\" } ] } } }} \""
    )
    call([data_instance_query], shell=True)
    seek_data_ids = []
    get_data_files = (
        "curl -X GET \"" +
        settings.SEEK_URL + "/data_files\" "
        "-H \"accept: application/json\""
    )
    all_data_files = subprocess.Popen(
        [get_data_files], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    data_files = json.loads(all_data_files)
    for df in range(0, len(data_files["data"])):
        seek_data_ids.append(int(data_files["data"][df]["id"]))
    get_content_blob = (
        "curl -X GET \"" +
        settings.SEEK_URL + "/data_files/" + str(max(seek_data_ids)) +
        "\" -H \"accept: application/json\""
    )
    json_blob = subprocess.Popen(
        [get_content_blob], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    content_blob = json.loads(json_blob)
    content_blob_url = content_blob["data"]["attributes"]["content_blobs"][0]["link"]
    content_blob_url = content_blob_url.replace("http://localhost:3000", settings.SEEK_URL)
    data_file_query = (
        "curl -u " +
        username + ":" + password +
        " -X PUT \"" + content_blob_url + "\" "
        "-H \"accept: */*\" -H \"Content-Type: application/octet-stream\" -T " +
        file
    )
    call([data_file_query], shell=True)
    call(["rm", "-r", file])
    return HttpResponseRedirect(reverse("index"))


def create_study(username, password, userid, projectid,
                 investigationid, title, description, studyname):
    """Creates a new study in SEEK.

    Arguments:
        username: SEEK Login name
        password: SEEK password
        server: SEEK server URL
        userid: Creator ID in SEEK
        projectid: Selected SEEK project ID.
        investigationid: Selected SEEK investigation ID.
        title: Title entered when creating a new assay.
        description: Description entered when creating a new assay.
        studyname: The name of the new study.
    """
    study_creation_query = (
        "curl -u " + username + ":" + password +
        " -X POST \"" + settings.SEEK_URL + "/studies\" "
        "-H \"accept: application/json\" "
        "-H \"Content-Type: application/json\" "
        "-d \"{ \\\"data\\\": "
        "{ \\\"type\\\": \\\"studies\\\", "
        "\\\"attributes\\\": "
        "{ \\\"title\\\": \\\"" + title + "\\\", "
        "\\\"description\\\": \\\"" + description + "\\\", "
        "\\\"person_responsible_id\\\": \\\"" + str(userid) + "\\\", "
        "\\\"policy\\\": "
        "{ \\\"access\\\": \\\"download\\\", "
        "\\\"permissions\\\": [ { "
        "\\\"resource\\\": "
        "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
        "\\\"type\\\": \\\"projects\\\" }, "
        "\\\"access\\\": \\\"view\\\" } ] } }, "
        "\\\"relationships\\\": "
        "{ \\\"investigation\\\": "
        "{ \\\"data\\\": "
        "{ \\\"id\\\": \\\"" + str(investigationid) + "\\\", "
        "\\\"type\\\": \\\"investigations\\\" } }, "
        "\\\"creators\\\": "
        "{ \\\"data\\\": [ { "
        "\\\"id\\\": \\\"" + str(userid) + "\\\", "
        "\\\"type\\\": \\\"people\\\" } ] } } }}\""
    )
    call([study_creation_query], shell=True)


def create_assay(username, password, userid, projectid, studyid,
                 title, description, assay_type, technology_type, assayname):
    """Creates a new assay in SEEK.

    Arguments:
        username {str} -- SEEK Login name
        password {str} -- SEEK password
        userid {int} -- Creator ID in SEEK
        projectid {int} -- Selected SEEK project ID.
        studyid {int} -- Selected SEEK study ID.
        title {str} -- Title entered when creating a new assay.
        description {str} -- Description entered when creating a new assay.
        assay_type {str} -- The selected assay type when creating a new assay.
        technology_type {str} -- The selected technology type 
        when creating a new assay.
        assayname {str} -- The name of the new assay.
    """
    if check_seek_permissions(username, password, userid, studyid):
        assay_creation_query = (
            "curl -u " + username + ":" + password +
            " -X POST \"" + settings.SEEK_URL + "/assays\" "
            "-H \"accept: application/json\" "
            "-H \"Content-Type: application/json\" "
            "-d \"{ \\\"data\\\": "
            "{ \\\"type\\\": \\\"assays\\\", "
            "\\\"attributes\\\": "
            "{ \\\"title\\\": \\\"" + title + "\\\", "
            "\\\"assay_class\\\": { \\\"key\\\": \\\"EXP\\\" }, "
            "\\\"assay_type\\\": { \\\"uri\\\": \\\"" + assay_type + "\\\" }, "
            "\\\"technology_type\\\": { \\\"uri\\\": \\\"" +
            technology_type + "\\\" }, "
            "\\\"description\\\": \\\"" + description + "\\\", "
            "\\\"policy\\\": "
            "{ \\\"access\\\": \\\"download\\\", "
            "\\\"permissions\\\": [ { "
            "\\\"resource\\\": "
            "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
            "\\\"type\\\": \\\"projects\\\" }, "
            "\\\"access\\\": \\\"view\\\" } ] } }, "
            "\\\"relationships\\\": "
            "{ \\\"study\\\": "
            "{ \\\"data\\\": "
            "{ \\\"id\\\": \\\"" + str(studyid) + "\\\", "
            "\\\"type\\\": \\\"studies\\\" } }, "
            "\\\"creators\\\": "
            "{ \\\"data\\\": [ { "
            "\\\"id\\\": \\\"" + str(userid) + "\\\", "
            "\\\"type\\\": \\\"people\\\" } ] } } }}\""
        )
        call([assay_creation_query], shell=True)
        return True
    else:
        return False


def open_sparql_store():
    """Opening the SEEK SPARQL end-point.

    Returns:
        The SPARQL end-point.
    """
    g = rdflib.ConjunctiveGraph('SPARQLStore')
    g.open(settings.VIRTUOSO_URL)
    return g


def seek_sparql_projects():
    """Run SPARQL query to find all available project on the SEEK server.

    Returns:
        Dictionary with all project in SEEK.
    """
    projects = {}
    g = open_sparql_store()
    p_sparql_query = (
        "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
        "select distinct ?projectid ?projects where {" +
        "?projectid jerm:title ?projects;" +
        "rdf:type jerm:Project" +
        "}"
    )
    for row in g.query(p_sparql_query):
        projects[row[0].split("/")[-1]] = row[1]
    return projects


def seek_sparql_investigations(selected_project_name):
    """Run SPARQL query to find all investigations on the SEEK server
    based on a project name.
    
    Arguments:
        selected_project_name: The name of the selected project 
        in the upload form.

    Returns:
        Dictionary with all investigations belonging to the selected project.
    """
    inv_names = {}
    g = open_sparql_store()
    i_sparql_query = (
        "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
        "select distinct ?investigationid ?investigation where {" +
        "?p jerm:title ?project ." +
        "FILTER regex(?project, \'" + selected_project_name + "\', 'i')" +
        "?p jerm:hasItem ?investigationid." +
        "FILTER regex(?investigationid, 'investigations', 'i')" +
        "?investigationid jerm:title ?investigation" +
        "}"
    )
    for row in g.query(i_sparql_query):
        inv_names[row[0].strip("rdflib.term.URIRef").split(
            "/")[-1]] = row[1]
    return inv_names


def seek_sparql_studies(selected_investigation_name):
    """Run SPARQL query to find all studies on the SEEK server 
    based on an investigation name.
    
    Arguments:
        selected_investigation_name: The name of the selected investigation 
        in the upload form.

    Returns:
        Dictionary with all studies belonging to the selected investigation.
    """
    study_names = {}
    g = open_sparql_store()
    s_sparql_query = (
        "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
        "select distinct ?studyid ?study where {" +
        "?i jerm:title ?investigation ." +
        "FILTER regex(?investigation, \'" + selected_investigation_name + "\', 'i')" +
        "?i jerm:hasPart ?studyid." +
        "FILTER regex(?studyid, 'studies', 'i')" +
        "?studyid jerm:title ?study" +
        "}"
    )
    for row in g.query(s_sparql_query):
        study_names[row[0].strip("rdflib.term.URIRef").split(
            "/")[-1]] = row[1]
    return study_names


def seek_sparql_assays(selected_study_name):
    """Run SPARQL query to find all assays on the SEEK server 
    based on a study name.
    
    Arguments:
        selected_study_name: The name of the selected study 
        in the upload form.
    
    Returns:
        Dictionary with all assays belonging to the selected study.
    """
    assay_names = {}
    g = open_sparql_store()
    s_sparql_query = (
        "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
        "select distinct ?assayid ?assay where {" +
        "?s jerm:title ?study ." +
        "FILTER regex(?study, \'" + selected_study_name + "\', 'i')" +
        "?s jerm:hasPart ?assayid." +
        "FILTER regex(?assayid, 'assays', 'i')" +
        "FILTER (!regex(?assay, '__result__', 'i'))" +
        "?assayid jerm:title ?assay" +
        "}"
    )
    for row in g.query(s_sparql_query):
        assay_names[row[0].strip("rdflib.term.URIRef").split(
            "/")[-1]] = row[1]
    return assay_names


def seek_sparql_samples(selected_assay_name):
    """Run SPARQL query to find all samples on the SEEK server 
    that are linked to an assay.
    
    Arguments:
        selected_assay_name: The name of the selected assay 
        in the upload form.

    Returns:
        Dictionary with all samples linked to the selected assay.
    """
    sample_names = {}
    g = open_sparql_store()
    s_sparql_query = (
        "prefix jerm: <http://jermontology.org/ontology/JERMOntology#>" +
        "select distinct ?sampleid ?sample where {" +
        "?a jerm:title ?assay ." +
        "FILTER regex(?assay, \'" + selected_assay_name + "\', 'i')" +
        "?a jerm:hasPart ?sampleid." +
        "FILTER regex(?sampleid, 'samples', 'i')" +
        "?sampleid jerm:title ?sample" +
        "}"
    )
    for row in g.query(s_sparql_query):
        sample_names[row[0].strip("rdflib.term.URIRef").split(
            "/")[-1]] = row[1]
    return sample_names


@csrf_exempt
def seek(request):
    """Getting the investigations, studies and assays based on the 
    information given by the user in the upload form. The user selects
    the project, investigation, study and assay. After selecting the assay
    the user enter a title and description an can upload a data file to the
    selected assay.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    projects = seek_sparql_projects()
    fullname = request.session.get('fullname')
    selected_project_id = ""
    selected_project_name = ""
    selected_investigation_id = ""
    selected_investigation_name = ""
    selected_study_id = ""
    selected_study_name = ""
    selected_assay_id = ""
    selected_assay_name = ""
    cns = ""
    cna = ""
    eids = {}
    dids = []
    tags = []
    edamterm = ""
    if request.POST.get('stored_disgenet') is not None:
        selected_disgenet_tags = request.POST.get('disgenetresult')
        stored_disgenet = request.POST.get('disgenetresult')
    else:
        stored_disgenet = None
        selected_disgenet_tags = ""
    if request.POST.get('stored_edam') is not None:
        stored_edam = request.POST.get('stored_edam')
    else:
        stored_edam = None
    if request.session.get('storage') is None:
        return HttpResponseRedirect(reverse('index'))
    if request.method == 'POST':
        if request.POST.get('res') is not None:
            datalist = request.POST.get('res').split("\n")
            for edamdata in datalist:
                if "URI" in edamdata:
                    uri = edamdata[4:]
                    stored_edam = uri
                if "Term" in edamdata:
                    edamdata = edamdata.split('\t')
                    edamterm = edamdata[1].strip('\r')
        if request.POST.get('disgenet') is not None and request.POST.get('disgenet') != "":
            selected_disgenet_tags = request.POST.get('disgenetresult')
            dids = disgenet(request.POST.get('disgenet'))
        elif request.POST.get('disgenet') is None and request.POST.get('disgenetresult') is not None:
            dids = request.POST.get('disgenetresult')
        else:
            dids = {}
        if request.POST.get("user") is not None or request.POST.get("user") != "":
            userid = get_seek_userid(
                request.session.get('username'),
                request.session.get('password'),
                fullname
            )
            if userid is None:
                return HttpResponseRedirect(reverse('seek'))
            # Get projects
            if request.POST.get("projects") is not None and request.POST.get("inv") is None:
                selected_project_id = request.POST.get("projects").split(',')[0]
                selected_project_name = request.POST.get("projects").split(',')[1]
                inv_names = seek_sparql_investigations(selected_project_name)
            elif request.POST.get("proj-stored"):
                selected_project_id = request.POST.get("proj-stored").split(',')[0]
                selected_project_name = request.POST.get("proj-stored").split(',')[1]
                inv_names = seek_sparql_investigations(selected_investigation_name)
            # Get investigations
            if request.POST.get("investigations") is not None:
                selected_investigation_id = request.POST.get("investigations").split(',')[0]
                selected_investigation_name = request.POST.get("investigations").split(',')[1]
                study_names = seek_sparql_studies(selected_investigation_name)
            elif request.POST.get("inv-stored"):
                selected_investigation_id = request.POST.get("inv-stored").split(',')[0]
                selected_investigation_name = request.POST.get("inv-stored").split(',')[1]
                study_names = seek_sparql_studies(selected_investigation_name)
            else:
                study_names = {}
            # Get studies
            if request.POST.get("studies") is not None:
                selected_study_id = request.POST.get("studies").split(',')[0]
                selected_study_name = request.POST.get("studies").split(',')[1]
                assay_names = seek_sparql_assays(selected_study_name)
            elif request.POST.get("stu-stored"):
                selected_study_id = request.POST.get("stu-stored").split(',')[0]
                selected_study_name = request.POST.get("stu-stored").split(',')[1]
                assay_names = seek_sparql_assays(selected_study_name)
            else:
                assay_names = {}
            # Get assays
            if request.POST.get("assays") is not None:
                selected_assay_id = request.POST.get("assays").split(',')[0]
                selected_assay_name = request.POST.get("assays").split(',')[1]
            elif request.POST.get("as-stored") is not None:
                selected_assay_id = request.POST.get("as-stored").split(',')[0]
                selected_assay_name = request.POST.get("as-stored").split(',')[1]
            cns = request.POST.get('cns')
            cna = request.POST.get('cna')
            if selected_assay_id != "":
                sample_names = seek_sparql_samples(selected_assay_name)
            else:
                sample_names = {}
            if (
                request.POST.get('newstudy')
            ):
                create_study(
                    request.session.get('username'),
                    request.session.get('password'),
                    # request.session.get('storage'),
                    userid,
                    selected_project_id,
                    selected_investigation_id,
                    request.POST.get('stitle'),
                    request.POST.get('sdescription'),
                    request.POST.get('newstudy')
                )
            if (
                request.POST.get('newassay')
            ):
                seekcheck = create_assay(
                    request.session.get('username'),
                    request.session.get('password'),
                    # request.session.get('storage'),
                    userid,
                    selected_project_id,
                    selected_study_id,
                    request.POST.get('atitle'),
                    request.POST.get('adescription'),
                    request.POST.get('assay_type'),
                    request.POST.get('technology_type'),
                    request.POST.get('newassay')
                )
                if not seekcheck:
                    return HttpResponseRedirect(reverse('seek'))
            if request.FILES.get('uploadfiles'):
                tags.append(stored_disgenet)
                tags.append(stored_edam.strip('\r\n'))
                upload_dir = (
                    "tmp" +
                    hashlib.md5(request.session.get(
                        'username').encode('utf-8')).hexdigest()
                )
                upload_full_path = os.path.join(
                    settings.MEDIA_ROOT, upload_dir)
                content_type = request.FILES['uploadfiles'].content_type
                if not os.path.exists(upload_full_path):
                    os.makedirs(upload_full_path)
                upload = request.FILES["uploadfiles"]
                while os.path.exists(os.path.join(upload_full_path, upload.name)):
                    upload.name = '_' + upload.name
                dest = open(os.path.join(upload_full_path, upload.name), 'wb')
                for chunk in upload.chunks():
                    dest.write(chunk)
                dest.close()
                seekupload(
                    request.session.get('username'),
                    request.session.get('password'),
                    request.POST.get('datatitle'),
                    os.path.join(upload_full_path, upload.name),
                    upload.name,
                    content_type,
                    userid,
                    selected_project_id,
                    selected_assay_id,
                    request.POST.get('description'),
                    tags
                )
                call(["rm", "-r", upload_full_path])
    else:
        inv_names = {}
        study_names = {}
        assay_names = {}
        sample_names = {}
    return render(
        request,
        "seek.html",
        context={'projects': projects,
                 'investigations': inv_names,
                 'studies': study_names,
                 'assays': assay_names,
                 'samples': sample_names,
                 'proj': selected_project_id,
                 'proj_name': selected_project_name,
                 'inv': selected_investigation_id,
                 'inv_name': selected_investigation_name,
                 'stu': selected_study_id,
                 'stu_name': selected_study_name,
                 'as': selected_assay_id,
                 'as_name': selected_assay_name,
                 'cns': cns,
                 'cna': cna,
                 'fullname': fullname,
                 'disgenet': dids,
                 'disgenettags': selected_disgenet_tags,
                 'storeddisgenet': stored_disgenet,
                 'storededam': stored_edam,
                 'edamterm': edamterm,
                 'edam': eids,
                 'storagetype': request.session.get('storage_type'),
                 'storage': request.session.get('storage')})


def get_investigation_folders(storagetype, username, password):
    """Gets the user's investigation folders from the storage URL,
    This will be shown on the homepage for storing existing Galaxy 
    histories.

    Arguments:
        storagetype: The storage type (SEEK or Owncloud)
        username: The username of the ISA structure storage.
        password: The password of the ISA structure storage.

    Returns:
        A list of investigation folder and a list of study folders.
    """
    oc_folders = ""
    if storagetype == "SEEK":
        inv_folders = []
        seek_investigations = seek_sparql_investigations("")
        for dummyii, it in seek_investigations.items():
            inv_folders.append(it)
            seek_sparql_studies(it)
    return inv_folders, oc_folders


def get_study_folders(storagetype, username, password, investigation):
    """Gets the study folders based on the selected investigation from the
    homepage. This is used to store existing Galaxt histories.

    Arguments:
        storagetype: To show if the storage is SEEK or ownCloud.
        username: The username of the ISA structure storage.
        password: The password of the ISA structure storage.
        investigation: SEEK investigation ID.

    Returns:
        A list of investigationa folders and a list of study folders.
    """
    if storagetype == "SEEK":
        seek_inv = seek_sparql_investigations("")
        inv_folders = []
        for dummyii, it in seek_inv.items():
            inv_folders.append(it)
        seek_study = seek_sparql_studies(it)
        oc_folders = []
        for st, dummysi in seek_study.items():
            oc_folders.append(st)
    return oc_folders, inv_folders


def get_galaxy_info(url, email, password):
    """Gets the Galaxy information from the logged in user.

    Arguments:
        url : The Galaxy server URL.
        email: The users email address for the Galaxy server.
        password: The Galaxy server password.

    Returns:
        The Galaxy username of the logged in user. Available Galaxy 
        workflows. A List of Galaxy histories from the user's account and 
        a list of available dbkeys.
    """
    gusername = ""
    gi = GalaxyInstance(
        url=url,
        email=email,
        password=password)
    user = gi.users.get_current_user()
    gusername = user['username']
    workflows = gi.workflows.get_workflows
    history = gi.histories.get_histories()
    hist = json.dumps(history)
    his = json.loads(hist)
    genomes = gi.genomes.get_genomes()
    dbkeys = []
    for gene in genomes:
        for g in gene:
            if "(" not in g:
                dbkeys.append(g)
    return gusername, workflows, his, dbkeys


def get_seek_userid(username, password, fullname):
    """Gets the SEEK user ID based on the full name of the user.

    Arguments:
        username: SEEK username
        password: SEEK password
        fullname: Full name of the user in SEEK.

    Returns:
        The user ID based on the full name of the user or None.
    """
    userquery = ("curl -X GET " + settings.SEEK_URL +
                 "/people -H \"accept: application/json\"")
    getpeople = subprocess.Popen(
        [userquery], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    jsonpeople = json.loads(getpeople)
    userid = None
    for uid in range(0, len(jsonpeople["data"])):
        if jsonpeople["data"][uid]["attributes"]["title"] == fullname:
            userid = str(jsonpeople["data"][uid]["id"])
    return userid


def get_seek_investigations(username, password):
    """Get all SEEK investigations that the logged in user has access to.

    Arguments:
        username: The SEEK username.
        password: The SEEK password.

    Returns:
        A dictionary with SEEK investigations and URLs.
    """
    investigations = {}
    investigation_titles = subprocess.Popen([
        "curl -s -u \'" + username + "\':" + password + " " + settings.SEEK_URL +
        "/investigations.xml | grep -e \'investigation xlink\' | "
        "sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"],
        stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    investigation_titles = investigation_titles.split("\n")
    investigation_titles = list(filter(None, investigation_titles))
    for it in investigation_titles:
        investigation_id = subprocess.Popen([
            "curl -s -u \'" + username + "\':" + password + " " + settings.SEEK_URL +
            "/investigations.xml | grep -e \'" + it +
            "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"],
            stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        investigations[it] = investigation_id.strip("\n")
    return investigations


def get_seek_studies(username, password, investigation):
    """Get all SEEK studies based on an investigation.
    
    Arguments:
        username: The SEEK username.
        password: The SEEK password.
        investigation: Investigation name

    Returns:
        A dictionary with SEEK studies and URLs.
    """
    studies = {}
    investigation_title = investigation.split("/")[-1]
    investigation_command = ("curl -X GET " + settings.SEEK_URL +
                             "/investigations/ -H \"accept: application/json\"")
    investigation_result = subprocess.Popen(
        [investigation_command],
        stdout=subprocess.PIPE, shell=True
    ).communicate()[0].decode()
    json_investigation = json.loads(investigation_result)
    for x in range(0, len(json_investigation["data"])):
        if json_investigation["data"][x]["attributes"]["title"] == investigation_title.strip("\n"):
            investigation_id = json_investigation["data"][x]["id"]
    study_link_command = ("curl -X GET " + settings.SEEK_URL + "/investigations/" +
                          investigation_id + " -H \"accept: application/json\"")
    study_link = subprocess.Popen(
        [study_link_command], stdout=subprocess.PIPE, shell=True
    ).communicate()[0].decode()
    json_study_link = json.loads(study_link)
    study_count = len(
        json_study_link["data"]["relationships"]["studies"]["data"])
    for i in range(study_count):
        study_id = json_study_link["data"]["relationships"]["studies"]["data"][i]["id"]
        study_command = ("curl -X GET " + settings.SEEK_URL + "/studies/" +
                         study_id + " -H \"accept: application/json\"")
        study_results = subprocess.Popen(
            [study_command],
            stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode()
        json_study = json.loads(study_results)
        study_title = json_study["data"]["attributes"]["title"]
        studies[study_title] = study_id
    return studies


def get_seek_assays(username, password, study):
    """Gets the SEEK assays based on a study.

    Arguments:
        username: The SEEK username.
        password: The SEEK password.
        study: Study ID

    Returns:
        A dictionary with SEEK assay IDs and URLs.
    """
    assays = {}
    study_id = study.split("/")[-1]
    assay_titles = subprocess.Popen([
        "curl -s -u \'" + username + "\':" + password + " " + settings.SEEK_URL +
        "/studies/" + study_id + ".xml | grep -e \'study xlink\' | "
                                 "sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
    ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    assay_titles = assay_titles.split("\n")
    assay_titles = list(filter(None, assay_titles))
    for at in assay_titles:
        assay_id = subprocess.Popen([
            "curl -s -u \'" + username + "\':" + password + " " + settings.SEEK_URL +
            "/studies/" + study_id + ".xml | grep -e \'" + at +
            "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        if assay_id is not None or study_id != '':
            assays[at] = assay_id.strip("\n")
        else:
            assays["0"] = "None"
    return assays


@csrf_exempt
def samples(request):
    """Geta all the samples that are selected to be sent to a Galaxy server.

    Arguments:
        request: A string with all selected samples that the user wants
        to send to a Galaxy server.
    """
    samples = request.POST.get('samples')
    sampleselect = []
    if samples is not None or samples != "[]":
        sample = samples.split(',')
        for sam in sample:
            sampleselect.append(
                sam.replace('[', '').replace('"', '').replace(']', '')
            )
        return render(request, 'home.html', context={'samples': sampleselect})
    return render(request, 'home.html', context={'samples': sampleselect})


@csrf_exempt
def triples(request):
    """Select the files that need to be stored in the triple store.

    Arguments:
        request: A request to get the current session.
    """
    if (
        request.session.get('username') == "" or
        request.session.get('username') is None
    ):
        return render(request, "login.html")
    else:
        folders = []
        studies = []
        inv = request.POST.get('inv')
        if request.session.get('storage_type') == "SEEK":
            oc_folders = []
            inv_names = get_seek_investigations(
                request.session.get('username'),
                request.session.get('password'))
            for it, dummyii in inv_names.items():
                oc_folders.append(it)
        if list(filter(None, oc_folders)):
            for oc in oc_folders:
                folders.append(oc)
            folders = list(filter(None, folders))
        if request.method == 'POST':
            datalist = request.POST.get('datalist')
            metalist = request.POST.get('metalist')
            disgenet = request.POST.get('disgenet-tag')
            edam = request.POST.get('edam-tag')
            print(edam)
            if request.POST.get('selected_folder') is not None:
                inv = request.POST.get('selected_folder')
            if inv != "" and inv is not None:
                files = []
                filelist = ''
                if (
                    request.POST.get('study') != "" and
                    request.POST.get('study') is not None
                ):
                    study = request.POST.get('study')
                    filelist = []
                    assays = get_seek_assays(
                        request.session.get('username'),
                        request.session.get('password'),
                        study)
                    for dummyat, ai in assays.items():
                        filelist.append(ai)
                for f in filelist:
                    files.append(f)
                files = list(filter(None, files))
                if not list(filter(None, filelist)):
                    if request.POST.get('selected_study') is not None:
                        study = request.POST.get('selected_study')
            metadata = []
            datafiles = []
            if datalist is not None or metalist is not None:
                if request.POST.get('selected_study') is not None:
                    study = request.POST.get('selected_study')
                datalist = datalist.split(',')
                metalist = metalist.split(',')
                for d in datalist:
                    if 'webdav' not in request.session.get('storage'):
                        datafiles.append(d)
                    else:
                        datafiles.append(
                            request.session.get('storage') + "/" +
                            inv + "/" + study + "/" + d
                        )
                for m in metalist:
                    if 'webdav' not in request.session.get('storage'):
                        metadata.append(m)
                    else:
                        metadata.append(
                            request.session.get('storage') + "/" +
                            inv + "/" + study + "/" + m
                        )
            if metadata or datafiles:
                return render(request, 'store.html', context={
                    'metadata': metadata,
                    'datafiles': datafiles, 'inv': inv,
                    'study': study, 'edam': edam,
                    'disgenet': disgenet})
            return render(request, 'triples.html', context={
                'storagetype': request.session.get('storage_type'),
                'folders': folders, 'files': files,
                'studies': studies, 'inv': inv,
                'sstudy': study})
        return render(request, 'triples.html', context={
            'storagetype': request.session.get('storage_type'),
            'folders': folders, 'studies': studies,
            'investigation': inv})


@csrf_exempt
def investigation(request):
    """Get studies based on the investigation that was selected 
    in the indexing menu.

    Arguments:
        request: A request to get the current session.
    """
    if request.session.get('username') is not None:
        inv_names = get_seek_investigations(
            request.session.get('username'),
            request.session.get('password'))
        oc_folders = inv_names.keys()
        if list(filter(None, oc_folders)):
            folders = []
            studies = []
            oc_studies = ""
            for oc in oc_folders:
                folders.append(oc)
            folders = list(filter(None, folders))
            if (
                request.POST.get('folder') != "" and
                request.POST.get('folder') is not None
            ):
                oc_studies = []
                for it, dummyii in inv_names.items():
                    if it == request.POST.get('folder'):
                        studydict = get_seek_studies(
                            request.session.get('username'),
                            request.session.get('password'), it)
                for st, dummysi in studydict.items():
                    oc_studies.append(st)
            else:
                pass
            if oc_studies != "":
                for s in oc_studies:
                    studies.append(s)
                studies = list(filter(None, studies))
                inv = request.POST.get('folder')
                return render(request, 'triples.html', context={
                    'folders': folders, 'studies': studies, 'inv': inv})
            else:
                return HttpResponseRedirect(reverse('triples'))
    else:
        return HttpResponseRedirect(reverse('index'))


def get_history_id(gi):
    """Get the current Galaxy history ID

    Arguments:
        gi: Galaxy instance.

    Returns:
        The current Galaxy history ID from the logged in user.
    """
    cur_hist = gi.histories.get_current_history()
    current = json.dumps(cur_hist)
    current_hist = json.loads(current)
    history_id = current_hist['id']
    return history_id


def get_input_data(gi):
    """Get input data based on the selected history.
    Find the number of uploaded files and return the id's of the files.

    Arguments:
        gi: Galaxy instance.

    Returns:
        A list of input files from the Galaxy history and 
        the amount of input datasets in the history.
    """
    history_id = get_history_id(gi)
    hist_contents = gi.histories.show_history(history_id, contents=True)
    inputs = {}
    datacount = 0
    datasets = [dataset for dataset in hist_contents if not dataset['deleted']]
    for dataset in datasets:
        inputs[dataset['name']] = dataset['id']
        datacount += 1
    return inputs, datacount


def get_selection(iselect, gselect, select):
    """Get lists of the selected investigations, studies and file names, 
    cleans them and return clean lists.

    Arguments:
        iselect: The Selected investigation names.
        gselect: The Selected study names.
        select: The Selected datafiles.
        mselect: The Selected metadata files.

    Returns:
        Lists of the selected investigations, studies, 
        datafiles and metadata files
    """
    groups = []
    files = []
    investigations = []
    for g in gselect:
        groups.append(g.replace('[', '').replace('"', '').replace(']', ''))
    for s in select:
        if s.replace('[', '').replace('"', '').replace(']', '') not in files:
            files.append(s.replace('[', '').replace('"', '').replace(']', ''))
    for i in iselect:
        if (
            i.replace('[', '').replace('"', '').replace(']', '')
            not in investigations
        ):
            investigations.append(
                i.replace('[', '').replace('"', '').replace(']', ''))
    return files, groups, investigations


def create_new_hist(gi, galaxyemail, galaxypass, server,
                    workflowid, files, new_hist):
    """Create a new history if there are any files selected.

    Arguments:
        gi: The Galaxy Instance.
        galaxyemail: The Galaxy email address.
        galaxypass: The Galaxy password.
        server: The Galaxy server URL.
        workflowid: The Galaxy workflow ID.
        files: A List of files to upload.
        new_hist: The new history name.

    Returns:
        A new Galaxy history ID.
    """
    date = format(datetime.now() + timedelta(hours=2))
    if workflowid != "0":
        if len(list(filter(None, files))) >= 0:
            workflow = gi.workflows.show_workflow(workflowid)
            if new_hist is None or new_hist == "":
                new_hist_name = (workflow['name'] + "_" + date)
            else:
                new_hist_name = new_hist
            gi.histories.create_history(name=new_hist_name)
            history_id = get_history_id(gi)
        else:
            pass
    else:
        if len(list(filter(None, files))) >= 0:
            if new_hist is None or new_hist == "":
                new_hist_name = ("Use_Galaxy_" + date)
            else:
                new_hist_name = new_hist
            gi.histories.create_history(name=new_hist_name)
            history_id = get_history_id(gi)
        else:
            pass
    return history_id


def make_data_files(gi, files, username, password, galaxyemail, galaxypass,
                    control, test, history_id, filetype, dbkey, storagetype):
    """Create datafiles and send them to the Galaxy server.

    Arguments:
        gi: The Galaxy Instance.
        files: A list of files to use within Galaxy
        username: Username used for the storage location.
        password: Password used for the storage location.
        galaxyemail: The Galaxy email address.
        galaxypass: The Galaxy passaword
        control: Samples in control group.
        test: Samples in test group.
        history_id: The Galaxy history ID to send files to.
        filetype: The filetype option when sending data to Galaxy.
        dbkey: The genome db to use in Galaxy.
        storagetype: Checks if storage is in Owncloud or SEEK.

    Raises:
        CalledProcessError: An error occurred when uploading data 
        to the Galaxy server using the FTP address.
    """
    uploaded_files = []
    ftp = gi.config.get_config()["ftp_upload_site"]
    for file in files:
        if storagetype == "SEEK":
            get_file_info = ("curl -X GET \"" + file +
                             "\" -H \"accept: application/json\"")
            file_info = subprocess.Popen(
                [get_file_info], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            json_file_info = json.loads(file_info)
            for v in range(0, len(json_file_info["data"]["attributes"]["versions"])):
                file_url = json_file_info["data"]["attributes"]["versions"][v]["url"]
                filename = json_file_info["data"]["attributes"]["content_blobs"][0]["original_filename"]
            file_url = file_url.replace('?', '/download?')
            call(["curl -L \'" + file_url.replace('http://localhost:3000', settings.SEEK_URL) + "\' -o " +
                  username + "/input_" + filename], shell=True)
            gi.tools.upload_file(
                username + "/input_" + filename,
                history_id, file_type=filetype, dbkey=dbkey
            )
            # gi.tools.upload_from_ftp(
            #     "input_" + filename, history_id,
            #     file_type=filetype, dbkey=dbkey)
            # uploaded_files.append("input_" + filename)
            call(["rm", "-r", username + "/input_" + filename])
    hist = gi.histories.show_history(history_id)
    state = hist['state_ids']
    dump = json.dumps(state)
    status = json.loads(dump)
    # Stop process after workflow is done
    while (
        status['running'] or
        status['queued'] or
        status['new'] or
        status['upload']
    ):
        time.sleep(90)
        hist = gi.histories.show_history(history_id)
        state = hist['state_ids']
        dump = json.dumps(state)
        status = json.loads(dump)
        if (
                not status['running'] and
                not status['queued'] and
                not status['new'] and
                not status['upload']
        ):
            for uf in uploaded_files:
                try:
                    check_call([
                        "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                        " -e \"rm -r " + uf + "; bye\""
                    ], shell=True)
                except subprocess.CalledProcessError:
                    pass


def omicsdi(gi, username, history_id, file_type, dbkey, omics_di_url):
    """Check all available datasets from an entered Omics DI entry.
    
    Arguments:
        gi: Galaxy Instance.
        username: Galaxy username.
        history_id: The current Galaxy history ID.
        file_type: galaxy file type.
        dbkey: Galaxy dbkey
        omics_di_url: The JSON URL of the Omics DI entry.
    """
    searchomicsapi = ("curl https://www.omicsdi.org:443/ws/dataset/search?query=" +
                      omics_di_url + "&start=0&size=20&faceCount=20")
    search = subprocess.Popen([searchomicsapi],
                              stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    searchresults = json.loads(search)
    omics_acc = searchresults["datasets"][0]["id"]
    omics_database = searchresults["datasets"][0]["source"]
    searchfilesapi = ("curl https://www.omicsdi.org:443/ws/dataset/" +
                      omics_database + "/" + omics_acc + "?debug=false")
    r = subprocess.Popen([searchfilesapi],
                         stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    omicsdi_json = json.loads(r)
    filetypes = omicsdi_json["file_versions"][0]["files"]
    for filetype in filetypes:
        filelist = omicsdi_json["file_versions"][0]["files"][filetype]
        for file in filelist:
            call(["wget -O " + username + "/input_" +
                  file.split("/")[-1] + " " + file], shell=True)
            filename = username + "/input_" + file.split("/")[-1]
            gi.tools.upload_file(
                filename, history_id, file_type=file_type, dbkey=dbkey
            )
            call(["rm", "-r", filename])


@csrf_exempt
def upload(request):
    """Call all function needed to send data and metadata files 
    to the Galaxy server and start the workflow if selected.

    Arguments:
        request: A request to receive information needed to upload
        files to the Galaxy server.

    Raises:
        IndexError: An error occurred when searching for the input label name
        from theGalaxy workflow file.
    """
    gi = GalaxyInstance(url=request.session.get('server'),
                        email=request.session.get('galaxyemail'),
                        password=request.session.get("galaxypass"))
    selected = request.POST.get('selected')
    filetype = request.POST.get('filetype')
    dbkey = request.POST.get('dbkey')
    workflowid = request.POST.get('workflowid')
    pid = request.POST.get('data_id')
    control = request.POST.get('samples')
    test = request.POST.get('samplesb')
    new_hist = request.POST.get('historyname')
    param = request.POST.get('param')
    group = request.POST.get('group')
    investigation = request.POST.get('investigation')
    date = format(datetime.now() + timedelta(hours=2))
    select = selected.split(',')
    gselect = group.split(',')
    iselect = investigation.split(',')
    files = get_selection(iselect, gselect, select)[0]
    groups = get_selection(iselect, gselect, select)[1]
    searched_assay = request.POST.get('searched_assay')
    investigations = get_selection(iselect, gselect, select)[2]
    history_id = create_new_hist(gi,
                                 request.session.get('galaxyemail'),
                                 request.session.get("galaxypass"),
                                 request.session.get('server'),
                                 workflowid, files, new_hist)
    inputs = {}
    if len(list(filter(None, files))) <= 0:
        # params = {"mtbls-dwnld": {"study": param}}
        if param != "":
            omicsdi(gi, request.session.get('username'),
                    history_id, filetype, dbkey, param)
            get_assays_cmd = ("curl -X GET \"" + settings.SEEK_URL +
                              "\"/assays -H \"accept: application/json\"")
            all_assays = subprocess.Popen(
                [get_assays_cmd],
                stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            json_assays = json.loads(all_assays)
            for ar in range(0, len(json_assays["data"])):
                if json_assays["data"][ar]["attributes"]["title"] in searched_assay:
                    assayid = json_assays["data"][ar]["id"]
            get_assay_cmd = ("curl -X GET \"" + settings.SEEK_URL + "\"/assays/" +
                             assayid + " -H \"accept: application/json\"")
            selected_assay = subprocess.Popen(
                [get_assay_cmd],
                stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            json_assay = json.loads(selected_assay)
            get_study_cmd = ("curl -X GET \"" + settings.SEEK_URL + "\"/studies/" +
                             json_assay["data"]["relationships"]["study"]["data"]['id'] + " -H \"accept: application/json\"")
            study_info = subprocess.Popen(
                [get_study_cmd],
                stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            json_study = json.loads(study_info)
            groups = [json_study["data"]["attributes"]["title"]]
            tags = [param]
            columns = [3]
    else:
        columns = [1,3]
        tags = [searched_assay]
        make_data_files(gi, files, request.session.get('username'),
                        request.session.get('password'),
                        request.session.get('galaxyemail'),
                        request.session.get('galaxypass'),
                        control, test, history_id, filetype, dbkey,
                        request.session.get('storage_type'))
    if workflowid != "0":
        resultid = uuid.uuid1()
        datamap = dict()
        mydict = {}
        jsonwf = gi.workflows.export_workflow_json(workflowid)
        for i in range(len(jsonwf["steps"])):
            if jsonwf["steps"][str(i)]["name"] == "Input dataset":
                try:
                    label = jsonwf["steps"][str(i)]["inputs"][0]["name"]
                except IndexError:
                    label = jsonwf["steps"][str(i)]["label"]
                mydict[label] = gi.workflows.get_workflow_inputs(
                    workflowid, label=label)[0]
        in_count = 0
        for k, v in mydict.items():
            datasets = get_input_data(gi)[0]
            for dname, did in datasets.items():
                if k in dname:
                    datamap[v] = {'src': "hda", 'id': did}
            in_count += 1
        gi.workflows.run_workflow(
            workflowid, datamap, history_id=history_id)
        gi.workflows.export_workflow_to_local_path(
            workflowid,
            request.session.get('username'),
            True)
        datafiles = get_output(request.session.get('galaxyemail'),
                                request.session.get('galaxypass'),
                                request.session.get('server'))
        store_results(columns, gi, datafiles, request.session.get('server'),
                        request.session.get('username'),
                        request.session.get('password'),
                        workflowid, groups, resultid, investigations, date, 
                        history_id,request.session.get("storage_type"), 
                        tags, request.session.get('fullname'))
        return render_to_response('results.html', context={
            'storagetype': request.session.get('storage_type'),
            'workflowid': workflowid,
            'inputs': inputs, 'pid': pid,
            'tags': tags,
            'server': request.session.get('server')
        })
    else:
        return HttpResponseRedirect(reverse("index"))


def make_collection(data_ids):
    """Create a dataset collection in Galaxy

    Arguments:
        data_ids: A list of Galaxy dataset IDs

    Returns:
        A dictionary of the Galaxy data collection.
    """
    idlist = []
    count = 0
    for c in range(0, len(data_ids)):
        data_id = data_ids[c]
        idlist.append({
            'src': "hda",
            'id': data_id,
            'name': str(count)
        })
        count += 1
    collection = {
        'collection_type': 'list',
        'element_identifiers': idlist,
        'name': 'collection'
    }
    return collection


def store_results(column, gi, datafiles, server, username, password,
                  workflowid, groups, resultid, investigations, date,
                  historyid, storagetype, tags, fullname):
    """Store input and output files that where created or used in a
    Galaxy workflow.
    
    Arguments:
        column: Column number containing 1 or 3. 
        1 for data and 3 for metadata.
        gi: The Galaxy instance.
        datafiles: A List of datafiles
        server: The Galaxy server URL.
        username: Username used for the storage location.
        password: Password used for the storage location.
        workflowid: The Galaxy workflow ID.
        groups: A list of studies.
        resultid: The result ID. 
        investigations: A list of investigations.
        date: The current date and time.
        historyid: The Galaxy history ID.
        storagetype: The type of storage (SEEK or Owncloud)
        tags: Tags to add to the result assay
    """
    assay_id_list = []
    for c in column:
        o = 0
        for name in datafiles[c]:
            cont = subprocess.Popen([
                "curl -s -k " + server + datafiles[c-1][o]
            ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            old_name = name.replace('/', '_').replace(' ', '_')
            with open(username + "/" + old_name, "w") as outputfile:
                outputfile.write(cont)
            new_name = sha1sum(username + "/" + old_name) + "_" + old_name
            os.rename(username + "/" + old_name, username + "/" + new_name)
            o += 1
    if storagetype == "SEEK":
        study_search_query = (
            "curl -X GET \"" + settings.SEEK_URL +
            "/studies\" -H \"accept: application/json\""
        )
        json_studies = subprocess.Popen(
            [study_search_query],
            stdout=subprocess.PIPE,
            shell=True
        ).communicate()[0].decode()
        studies = json.loads(json_studies)
        for s in range(0, len(studies["data"])):
            study_name = studies["data"][s]["attributes"]["title"]
            if study_name in groups:
                studyid = studies["data"][s]["id"]
                project_search_query = (
                    "curl -X GET \"" + settings.SEEK_URL +
                    "/projects\" -H \"accept: application/json\""
                )
                json_projects = subprocess.Popen(
                    [project_search_query],
                    stdout=subprocess.PIPE,
                    shell=True
                ).communicate()[0].decode()
                projects = json.loads(json_projects)
                for p in range(1, len(projects["data"]) + 1):
                    project_id_query = (
                        "curl -X GET \"" + settings.SEEK_URL + "/projects/" +
                        str(p) + "\" -H \"accept: application/json\""
                    )
                    json_project = subprocess.Popen([project_id_query], stdout=subprocess.PIPE,
                                                    shell=True).communicate()[0].decode()
                    project = json.loads(json_project)
                    for ps in range(0, len(project["data"]["relationships"]["studies"]["data"])):
                        if studyid == project["data"]["relationships"]["studies"]["data"][ps]["id"]:
                            projectid = str(p)
                assay_title = (study_name + "__result__" + str(resultid))
                userid = get_seek_userid(username, password, fullname)
                create_assay(
                    username, password, userid, projectid, studyid, assay_title,
                    "Results for ID: " + str(resultid),
                    "http://jermontology.org/ontology/JERMOntology#Experimental_assay_type",
                    "http://jermontology.org/ontology/JERMOntology#Technology_type", assay_title
                )
                assay_search_query = (
                    "curl -X GET \"" + settings.SEEK_URL + "/assays\" -H \"accept: application/json\""
                )
                json_assays = subprocess.Popen(
                    [assay_search_query],
                    stdout=subprocess.PIPE,
                    shell=True
                ).communicate()[0].decode()
                assays = json.loads(json_assays)
                mime = magic.Magic(mime=True)
                content_type = mime.from_file(username + "/" + new_name)
                for ail in range(0, len(assays["data"])):
                    assay_id_list.append(int(assays["data"][ail]["id"]))
                for galaxyfile in os.listdir(username):
                    seekupload(
                        username, password, galaxyfile,
                        username + "/" + galaxyfile,
                        str(galaxyfile), content_type, 1, projectid,
                        str(max(assay_id_list)), workflowid, tags
                    )


def sha1sum(filename, blocksize=65536):
    """Get the sha1 hash based on the file contents.

    Arguments:
        filename: Filename to generate sha1 hash.

    Keyword Arguments:
        blocksize: Used blocksize (default: {65536})

    Returns:
        The sha1 hash generated from the datafile.
    """
    hash = hashlib.sha1()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()


@csrf_exempt
def show_results(request):
    """Show results that are stored in ownCloud or any other 
    supported storage location. This is based on the 
    search results in myFAIR.

    Arguments:
        request: A request to receive the information 
        to show results.

    Raises:
        IndexError: An error occurred when getting the storage location.
    """
    username = request.session.get('username')
    inputs = {}
    out = {}
    workflow = []
    taglinks = []
    if request.method == 'POST':
        request.session['stored_results'] = request.POST
        return render_to_response('results.html', context={'outputs': out})
    else:
        if username is not None:
            old_post = request.session.get('stored_results')
            group = old_post['group']
            group = group.split(',')
            resultid = old_post['resultid']
            if request.session.get('storage_type') == "SEEK":
                resultid = resultid.replace('"', '').strip("[").strip("]")
                if "\\" in resultid:
                    resultid = resultid[:-2]
                results = get_seek_result(resultid)
                for rid, rname in results.items():
                    if "_input_" in rname:
                        inputs[rid] = rname
                    elif ".ga" in rname:
                        seek_workflow = subprocess.Popen(
                            [
                                "curl -X GET " + settings.SEEK_URL + "/data_files/" + rid +
                                " -H 'accept: application/json'"
                            ], stdout=subprocess.PIPE, shell=True
                        ).communicate()[0].decode()
                        tags = json.loads(seek_workflow)['data']['attributes']['tags']
                        if tags:
                            for tag in tags:
                                omicsdi_tag = subprocess.Popen(
                                    [
                                        "curl https://www.omicsdi.org:443/ws/dataset/search?query=" + tag
                                    ], stdout=subprocess.PIPE, shell=True
                                ).communicate()[0].decode()
                                link = (
                                    "https://www.omicsdi.org/dataset/" +
                                    json.loads(omicsdi_tag)['datasets'][0]["source"] +
                                    "/" + json.loads(omicsdi_tag)['datasets'][0]["id"]
                                )
                                taglinks.append(link)
                        call(
                            [
                                "wget -O " + username + "/workflow.ga " +
                                settings.SEEK_URL + "/data_files/" + rid +
                                "/download?version=1"
                            ], shell=True
                        )
                        workflow = read_workflow(username + "/workflow.ga")
                        out[rid] = rname
                        get_file_cmd = (
                            "curl -X GET \"" + settings.SEEK_URL + "/data_files/" + rid + "\" -H \"accept: application/json\"")
                        data_files = subprocess.Popen(
                            [get_file_cmd],
                            stdout=subprocess.PIPE,
                            shell=True
                        ).communicate()[0].decode()
                        json_data_files = json.loads(data_files)
                        if rname == (json_data_files["data"]
                                     ["attributes"]["title"]):
                            wid = (json_data_files["data"]
                                   ["attributes"]["description"])
                    else:
                        out[rid] = rname
                return render(request, 'results.html', context={
                    'storagetype': request.session.get('storage_type'),
                    'inputs': inputs,
                    'outputs': out,
                    'workflow': workflow,
                    'storage': settings.SEEK_URL,
                    'resultid': resultid,
                    'workflowid': wid,
                    'tags': tags,
                    'taglinks': taglinks})
        else:
            return HttpResponseRedirect(reverse('index'))


def get_seek_result(assay):
    """Get the results based on the SEEK assay name.
    Returns data file IDs and titles to show in the result page.

    Arguments:
        assay: Name of the assay where the result is stored.

    Returns:
        A Dictionary with data IDs and titles.
    """
    get_assays_cmd = ("curl -X GET \"" + settings.SEEK_URL +
                      "\"/assays -H \"accept: application/json\"")
    all_assays = subprocess.Popen(
        [get_assays_cmd],
        stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    json_assays = json.loads(all_assays)
    fileidlist = []
    results = {}
    for ar in range(0, len(json_assays["data"])):
        if json_assays["data"][ar]["attributes"]["title"] in assay:
            assayid = json_assays["data"][ar]["id"]
    get_assay_cmd = ("curl -X GET \"" + settings.SEEK_URL + "\"/assays/" +
                     assayid + " -H \"accept: application/json\"")
    selected_assay = subprocess.Popen(
        [get_assay_cmd],
        stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    json_assay = json.loads(selected_assay)
    for df in range(0, len(json_assay["data"]["relationships"]["data_files"]["data"])):
        fileidlist.append(
            json_assay["data"]["relationships"]["data_files"]["data"][df]["id"])
    for fileid in fileidlist:
        get_file_cmd = ("curl -X GET \"" + settings.SEEK_URL + "\"/data_files/" +
                        fileid + " -H \"accept: application/json\"")
        file_info = subprocess.Popen(
            [get_file_cmd],
            stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        json_file = json.loads(file_info)
        results[json_file["data"]["id"]
                ] = json_file["data"]["attributes"]["title"]
    return results


def logout(request):
    """Flush the exisiting session with the users login details.

    Arguments:
        request: Request the session so it can be flushed and the folder
        with the logged in user can be removed.
    """
    if request.session.get('username') is not None:
        call(["rm", "-r", request.session.get('username')])
        request.session.flush()
    return HttpResponseRedirect(reverse('index'))


def get_output(galaxyemail, galaxypass, server):
    """Get all inputs and outputs from the Galaxy workflow.
    This information will be used to store the files in the storage location.

    Arguments:
        galaxyemail: The Galaxy email address.
        galaxypass: The Galaxy password.
        server: The Galaxy server URL.

    Returns:
        Lists with Galaxy inputfile URLs, inputfile names, 
        outputfile URLs and outputfile names.
    """
    if galaxyemail is None:
        return HttpResponseRedirect(reverse("index"))
    else:
        gi = GalaxyInstance(url=server, email=galaxyemail, password=galaxypass)
        historyid = get_history_id(gi)
        inputs = []
        input_ids = []
        outputs = []
        time.sleep(30)
        hist = gi.histories.show_history(historyid)
        state = hist['state_ids']
        dump = json.dumps(state)
        status = json.loads(dump)
        # Stop process after workflow is done
        while (
            status['running'] or
            status['queued'] or
            status['new'] or
            status['upload']
        ):
            time.sleep(90)
            hist = gi.histories.show_history(historyid)
            state = hist['state_ids']
            dump = json.dumps(state)
            status = json.loads(dump)
            if (
                    not status['running'] and
                    not status['queued'] and
                    not status['new'] and
                    not status['upload']
            ):
                break
        files = status['ok']
        for o in files:
            oug = gi.datasets.show_dataset(o, deleted=False, hda_ldda='hda')
            if "input_" in oug['name']:
                inputs.append(oug['id'])
            else:
                outputs.append(oug)
        for i in inputs:
            iug = gi.datasets.show_dataset(i, deleted=False, hda_ldda='hda')
            input_ids.append(iug)
        in_url = []
        in_name = []
        out_url = []
        out_name = []
        for input_id in input_ids:
            in_name.append(input_id["name"])
            in_url.append(input_id["download_url"])
        for out in outputs:
            if out['visible']:
                out_name.append(out["name"])
                out_url.append(out["download_url"])
        return in_url, in_name, out_url, out_name


def read_workflow(filename):
    """Read workflow file to retrieve the steps within the workflow.

    Arguments:
        filename: The name of the Galaxy workflow file.

    Returns:
        A list of all steps used in the Galaxy workflow.
    """
    json_data = open(filename).read()
    data = json.loads(json_data)
    steps = data["steps"]
    steplist = []
    count = 0
    for dummys in steps:
        steplist.append(steps[str(count)])
        count += 1
    call(["rm", filename])
    return steplist


def rerun_seek(gi, resultid, galaxyemail, galaxypass, ftp,
               username, history_id, omicsdi_link):
    """Upload input files from a previous run to the Galaxy server.
    Get the JSON data from the Galaxy workflow file and return this to
    the rerun function to import the workflow.

    Arguments:
        gi: The Galaxy instance.
        resultid: The ID of the result to rerun.
        galaxyemail: Email address used for Galaxy login.
        galaxypass: Password used in Galaxy.
        ftp: The Galaxy server's FTP address.
        username: The username used when logged in to myFAIR.
        history_id: The Galaxy history ID.
        omicsdi_link: Link to the omics DI input files.

    # Returns:
    #     A JSON string of the Galaxy workflow file.

    Raises:
        CalledProcessError: An error occurred when uploading data 
        to the Galaxy server using the FTP address.
    """
    df_id_list = []
    uploaded_files = []
    gacont = None
    get_assays = (
        "curl -X GET \"" +
        settings.SEEK_URL + "/assays\" "
        "-H \"accept: application/json\""
    )
    assays = subprocess.Popen(
        [get_assays], stdout=subprocess.PIPE, shell=True
    ).communicate()[0].decode()
    json_assays = json.loads(assays)
    for x in range(0, len(json_assays["data"])):
        assay_title = str(json_assays["data"][x]["attributes"]["title"])
        if resultid.strip("\n") == assay_title.strip("\n"):
            aid = json_assays["data"][x]["id"]
    get_result_assay = (
        "curl -X GET \"" +
        settings.SEEK_URL + "/assays/" + str(aid) + "\" "
        "-H \"accept: application/json\""
    )
    result_assay = subprocess.Popen(
        [get_result_assay], stdout=subprocess.PIPE, shell=True
    ).communicate()[0].decode()
    json_result_assay = json.loads(result_assay)
    data_files_dict = json_result_assay["data"]["relationships"]["data_files"]
    for dx in range(0, len(data_files_dict["data"])):
        df_id_list.append(data_files_dict["data"][dx]["id"])
    for did in df_id_list:
        get_data_file = (
            "curl -X GET \"" +
            settings.SEEK_URL + "/data_files/" + str(did) + "\" "
            "-H \"accept: application/json\""
        )
        data_file = subprocess.Popen(
            [get_data_file], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode()
        json_result_data = json.loads(data_file)
        if not omicsdi_link:
            if "input_" in json_result_data["data"]["attributes"]["title"]:
                dataid = json_result_data["data"]["id"]
                filename = (json_result_data["data"]["attributes"]
                            ["content_blobs"][0]["original_filename"])
                call(
                    [
                        "wget -O " + username + "/\"" + filename + "\" " +
                        settings.SEEK_URL + "/data_files/" + dataid +
                        "/download?version=1"
                    ], shell=True
                )
                # check_call([
                #     "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                #     " -e \"put " + username + "/" + filename + "; bye\""], shell=True)
                # gi.tools.upload_from_ftp(
                #     filename, history_id, file_type="auto", dbkey="?")
                gi.tools.upload_file(username + "/" + filename,
                                    history_id, file_type="auto", dbkey="?")
                uploaded_files.append(filename)
                call(["rm", username + "/" + filename])
        if ".ga" in json_result_data["data"]["attributes"]["title"]:
            workflowfileid = json_result_data["data"]["id"]
            gacont = subprocess.Popen(
                ["curl -s -k " + settings.SEEK_URL + "/data_files/" +
                    workflowfileid + "/download"],
                stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    if omicsdi_link:
        omicsdi(gi, username, history_id, "auto", "?", omicsdi_link)
    hist = gi.histories.show_history(history_id)
    state = hist['state_ids']
    dump = json.dumps(state)
    status = json.loads(dump)
    # Stop process after workflow is done
    while (
            status['running'] or
            status['queued'] or
            status['new'] or
            status['upload']
    ):
        time.sleep(60)
        hist = gi.histories.show_history(history_id)
        state = hist['state_ids']
        dump = json.dumps(state)
        status = json.loads(dump)
    if workflowfileid != 0:
        rerun_seek_workflow(gi, username, workflowfileid, history_id, gacont)


def rerun_seek_workflow(gi, username, workflowid, history_id, gacont):
    """Start the Galaxy workflow after uploading the data files to the 
    Galaxy server. 

    Arguments:
        gi: Galaxy instance of the logged in user.
        username: SEEK username.
        workflowid: ID of the workflow used in this analysis.
        history_id: ID of the new Galaxy history.
        gacont: JSON content of the workflow used in the analysis.
        omicsdi_link: Link to the omics DI input files.

    Raises:
        IndexError: An error occurred when searching ffor the input name labels
        in the Galaxy workflow file.
    """
    with open(username + "/workflow.ga", 'w') as gafile:
        json_ga = json.loads(gacont)
        for i, dummyj in json_ga.items():
            if i == 'name':
                temp_wf = gi.workflows.get_workflows(name="TEMP_WORKFLOW")
                if temp_wf:
                    for wf in temp_wf:
                        wfid = wf["id"]
                        gi.workflows.delete_workflow(wfid)
                else:
                    json_ga[i] = 'TEMP_WORKFLOW'
        json.dump(json_ga, gafile, indent=2)
    if workflowid != "0":
        gi.workflows.import_workflow_from_local_path(gafile.name)
        workflows = gi.workflows.get_workflows(name="TEMP_WORKFLOW")
        for workflow in workflows:
            newworkflowid = workflow["id"]
        datamap = dict()
        mydict = {}
        jsonwf = gi.workflows.export_workflow_json(newworkflowid)
        for i in range(len(jsonwf["steps"])):
            if jsonwf["steps"][str(i)]["name"] == "Input dataset":
                try:
                    label = jsonwf["steps"][str(i)]["inputs"][0]["name"]
                except IndexError:
                    label = jsonwf["steps"][str(i)]["label"]
                mydict[label] = gi.workflows.get_workflow_inputs(
                    newworkflowid, label=label)[0]
        for k, v in mydict.items():
            datasets = get_input_data(gi)[0]
            for dname, did in datasets.items():
                if k in dname:
                    datamap[v] = {'src': "hda", 'id': did}
        gi.workflows.run_workflow(
            newworkflowid, datamap, history_id=history_id)
        gi.workflows.delete_workflow(newworkflowid)
        call(["rm", gafile.name])


@csrf_exempt
def rerun_analysis(request):
    """Rerun an analysis stored in the triple store.
    Search for a result on the homepage and view the results.
    In the resultspage there is an option to rerun the analysis.

    Arguments:
        request: A request to receive information to rerun previously
        generated results.
    """
    workflowid = request.POST.get('workflowid')
    omicsdi_link = request.POST.get('omicsdi_link')
    workflowid = workflowid.replace('"', '')
    urls = request.POST.get('urls')
    urls = urls.replace('"', '').replace("[", "").replace("]", "")
    urls = urls.split(',')
    urls = sorted(urls)
    gi = GalaxyInstance(
        url=request.session.get('server'),
        email=request.session.get('galaxyemail'),
        password=request.session.get("galaxypass")
    )
    ftp = gi.config.get_config()["ftp_upload_site"]
    gi.histories.create_history(name=request.POST.get('resultid'))
    history_id = get_history_id(gi)
    if request.session.get('storage_type') == "SEEK":
        rerun_seek(
            gi,
            request.POST.get('resultid'),
            request.session.get("galaxyemail"),
            request.session.get("galaxypass"),
            ftp,
            request.session.get('username'),
            history_id,
            omicsdi_link
        )
    return HttpResponseRedirect(reverse("index"))


@csrf_exempt
def disgenet(disgenet):
    """Finds the DisGeNET URI based on the searched disease entered
    when uploading data to the SEEK server.

    Arguments:
        disgenet: Disease entered in the SEEK upload form.

    Returns:
        DisGeNET URIs that are connected to the 
        disease entered in the upload form.
    """
    disgenet_uri = {}
    sparql_query = (
        "PREFIX dcterms: <http://purl.org/dc/terms/>" +
        "SELECT * " +
        "WHERE { SERVICE <http://rdf.disgenet.org/sparql/> { " +
        "?uri dcterms:title ?disease . " +
        "?disease bif:contains \'\"" + disgenet + "\"\' ." +
        "} " +
        "} LIMIT 30"
    )
    g = open_sparql_store()
    for row in g.query(sparql_query):
        disgenet_uri[row[0].strip("rdflib.term.URIRef")] = row[1]
    return disgenet_uri
