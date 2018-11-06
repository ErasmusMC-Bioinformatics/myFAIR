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
import plotly
import plotly.graph_objs as go

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
        if request.POST.get('storage')[-1] == '/':
            storage = request.POST.get('storage')[:-1]
        else:
            storage = request.POST.get('storage')
        username = request.POST.get('username')
        password = request.POST.get('password')
        galaxypass = request.POST.get("galaxypass")
        galaxyemail = request.POST.get("galaxyemail")
        noexpire = request.POST.get('no-expire')
        if storage != "":
            request.session['storage'] = storage
            storage_command = ("curl -s " + storage)
            storage_call = subprocess.Popen(
                [storage_command], stdout=subprocess.PIPE, shell=True
            ).communicate()[0].decode()
            if "seek4science" in storage_call or "fair-dom" in storage_call:
                request.session['storage_type'] = "SEEK"
            else:
                request.session['storage_type'] = "nextcloud"
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
        if username != "" and password != "":
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
    if (request.method == 'POST' and
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
        storage = request.session.get('storage')
        server = request.session.get('server')
        if investigation is not None and investigation != "":
            oc_folders, inv_folders = get_study_folders(
                storage,
                request.session.get('storage_type'),
                username,
                password,
                investigation
            )
        else:
            inv_folders, oc_folders = get_investigation_folders(
                storage,
                request.session.get('storage_type'),
                username,
                password
            )
        for inv in inv_folders:
            if "/owncloud/" in request.session.get('storage'):
                investigation_name = inv.replace(
                    '/owncloud/remote.php/webdav/', '').replace('/', '')
                if "." not in investigation_name:
                    new = investigation_name
                    investigations.append(new)
            elif request.session.get('storage_type') == "SEEK":
                investigations = get_seek_investigations(
                    username, password, storage)
            else:
                investigation_name = inv.replace(
                    '/remote.php/webdav/', '').replace('/', '')
                if "." not in investigation_name:
                    new = investigation_name
                    investigations.append(new)
        for oc in oc_folders:
            if "/owncloud/" in request.session.get('storage'):
                study = oc.replace(
                    '/owncloud/remote.php/webdav/', '')
                study = study.replace('/', '').replace(investigation, '')
                if "." not in study:
                    new = study
                    folders.append(new)
            elif request.session.get('storage_type') == "SEEK":
                folders.append(oc)
            else:
                study = oc.replace(
                    '/remote.php/webdav/', '')
                study = study.replace('/', '').replace(investigation, '')
                if "." not in study:
                    new = study
                    folders.append(new)
        folders = list(filter(None, folders))
        investigations = list(filter(None, investigations))
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
                     'storage': storage,
                     'storagetype': request.session.get('storage_type'),
                     'investigations': investigations,
                     'studies': folders, 'inv': investigation,
                     'dbkeys': dbkeys,
                     'galaxyemail': request.session.get('galaxyemail'),
                     'galaxypass': request.session.get('galaxypass')}
        )


def check_seek_permissions(username, password, server, userid, studyid):
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
    peoplequery = ("curl -X GET " + server + "/people/" + userid + 
    " -H \"accept: application/json\"")
    sids = []
    userinfo = subprocess.Popen([peoplequery],
                                stdout=subprocess.PIPE,
                                shell=True).communicate()[0].decode()
    jsonuser = json.loads(userinfo)
    studyids = jsonuser["data"]["relationships"]["studies"]["data"]
    for datanr in range(0,len(studyids)):
        sids.append(jsonuser["data"]["relationships"]
                    ["studies"]["data"][datanr]["id"])
    if studyid in sids:
        return True
    else:
        return False


@csrf_exempt
def seekupload(username, password, storage, title, file, filename,
               content_type, userid, projectid, assayid, description):
    """Uploads data files to an assay.
    
    Arguments:
        username: SEEK username.
        password: SEEK password.
        storage: [description]
        title: Title of the uploaded data file.
        file: The file that will be uploaded to the SEEK server.
        filename: Name of the uploaded file.
        content_type: Content type of the uploaded file (e.g. pdf, xml etc.)
        userid: SEEK user ID of the data uploader.
        projectid: SEEK project ID related to the data file.
        assayid: SEEK assay ID related to the data file.
        description: The description of the data.
    
    """
    data_instance_query = (
        "curl -u " + username + ":" + password +
        " -X POST \"" + storage + "/data_files\" "
        "-H \"accept: application/json\" "
        "-H \"Content-Type: application/json\" "
        "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"data_files\\\", "
        "\\\"attributes\\\": "
        "{ \\\"title\\\": \\\"" + title + "\\\", "
        "\\\"description\\\": \\\"" + description + "\\\", "
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
    seek_data_ids = []  # List with data_file ids
    get_data_files = (
        "curl -X GET \"" +
        storage + "/data_files\" "
        "-H \"accept: application/json\""
    )
    all_data_files = subprocess.Popen(
        [get_data_files], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    data_files = json.loads(all_data_files)
    for df in range(0, len(data_files["data"])):
        seek_data_ids.append(int(data_files["data"][df]["id"]))
    get_content_blob = (
        "curl -X GET \"" +
        storage + "/data_files/" + str(max(seek_data_ids)) +
        "\" -H \"accept: application/json\""
    )
    json_blob = subprocess.Popen(
        [get_content_blob], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    content_blob = json.loads(json_blob)
    content_blob_url = content_blob["data"]["attributes"]["content_blobs"][0]["link"]
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


def create_study(username, password, server, userid, projectid,
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
        " -X POST \"" + server + "/studies\" "
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


def create_assay(username, password, server, userid, projectid, studyid,
                 title, description, assay_type, technology_type, assayname):
    """Creates a new assay in SEEK.

    TODO: Check if user has permission to add an assay
    to the study.

    Arguments:
        username {str} -- SEEK Login name
        password {str} -- SEEK password
        server {str} -- SEEK server URL
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
    if check_seek_permissions(username, password, server, userid, studyid):
        assay_creation_query = (
            "curl -u " + username + ":" + password +
            " -X POST \"" + server + "/assays\" "
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
    projects = {}
    selected_project = ""
    selected_project_name = ""
    selected_investigation = ""
    selected_investigation_name = ""
    selected_study = ""
    selected_study_name = ""
    selected_assay = ""
    selected_assay_name = ""
    inv_names = {}
    study_names = {}
    assay_names = {}
    searches = {}
    cns = ""
    cna = ""
    err = ""
    eids = {}
    dids = []
    fullname = ""
    user_dict = {}
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
    get_projects = "curl -s -X GET \"" + \
        request.session.get("storage") + \
        "/projects\" -H \"accept: application/json\""
    json_projects = subprocess.Popen([get_projects],
                                        stdout=subprocess.PIPE,
                                        shell=True).communicate()[0].decode()
    test_projects = json.loads(json_projects)
    for x in range(0, len(test_projects["data"])):
        projects[test_projects["data"][x]["id"]
                    ] = test_projects["data"][x]["attributes"]["title"]
    if request.method == 'POST':
        if request.POST.get('res') is not None:
            datalist = request.POST.get('res').split("\n")
            for edamdata in datalist:
                if "URI" in edamdata:
                    uri = edamdata[4:]
                    stored_edam = uri
        if request.POST.get('disgenet') is not None and request.POST.get('disgenet') != "":
            selected_disgenet_tags = request.POST.get('disgenetresult')
            dids = disgenet(request.POST.get('disgenet'))
        elif request.POST.get('disgenet') is None and request.POST.get('disgenetresult') is not None:
            dids = request.POST.get('disgenetresult')
        else:
            dids = {}
        if request.POST.get("user") is not None or request.POST.get("user") != "":
            if fullname == "":
                fullname = request.POST.get("user")
            userid = get_seek_userid(request.session.get('storage'),
                                request.session.get('username'),
                                request.session.get('password'),
                                fullname)
            if userid is None:
                return HttpResponseRedirect(reverse('seek'))
            if request.POST.get("projects") is not None and request.POST.get('user') is not None:
                selected_project = request.POST.get("projects").split(',')[0]
                selected_project_name = request.POST.get("projects").split(',')[1]
            elif request.POST.get("proj"):
                selected_project = request.POST.get("proj").split(',')[0]
                selected_project_name = request.POST.get("proj").split(',')[1]
            if request.POST.get("investigations") is not None:
                selected_investigation = request.POST.get(
                    "investigations").split(',')[0]
                selected_investigation_name = request.POST.get(
                    "investigations").split(',')[1]
            elif request.POST.get("inv") and request.POST.get("proj") is not None:
                selected_investigation = request.POST.get("inv").split(',')[0]
                selected_investigation_name = request.POST.get("inv").split(',')[1]
            if request.POST.get("studies") is not None:
                selected_study = request.POST.get("studies").split(',')[0]
                selected_study_name = request.POST.get("studies").split(',')[1]
            elif request.POST.get("stu") is not None and request.POST.get("as") is not None:
                selected_study = request.POST.get("stu").split(',')[0]
                selected_study_name = request.POST.get("stu").split(',')[1]
            if request.POST.get("assays") is not None:
                selected_assay = request.POST.get("assays").split(',')[0]
                selected_assay_name = request.POST.get("assays").split(',')[1]
            elif request.POST.get("as") is not None:
                selected_assay = request.POST.get("as").split(',')[0]
                selected_assay_name = request.POST.get("as").split(',')[1]
            if projects and not inv_names:
                inv_search = []
                search_project = ("curl -s -X GET \"" + request.session.get(
                    "storage") + "/projects/" + selected_project +
                    "\" -H \"accept: application/json\"")
                project_search_results = subprocess.Popen(
                    [search_project],
                    stdout=subprocess.PIPE,
                    shell=True).communicate()[0].decode()
                test_search = json.loads(project_search_results)
                for inv in range(0, len(test_search["data"]["relationships"]["investigations"]["data"])):
                    inv_search.append(
                        test_search["data"]["relationships"]["investigations"]["data"][inv]["id"])
                for inv_id in inv_search:
                    inv_search_query = "curl -s -X GET \"" + request.session.get(
                        "storage") + "/investigations/" + inv_id + "\" -H \"accept: application/json\""
                    res_investogations = subprocess.Popen([inv_search_query], stdout=subprocess.PIPE,
                                                        shell=True).communicate()[0].decode()
                    found_investigations = json.loads(res_investogations)
                    inv_names[inv_id] = found_investigations["data"]["attributes"]["title"]
            if inv_names and projects and not study_names and selected_investigation != "":
                study_search = []
                search_investigation = "curl -s -X GET \"" + request.session.get(
                    "storage") + "/investigations/" + selected_investigation + "\" -H \"accept: application/json\""
                investigation_search_results = subprocess.Popen([search_investigation],
                                                                stdout=subprocess.PIPE,
                                                                shell=True).communicate()[0].decode()
                test_search = json.loads(investigation_search_results)
                for study in range(0, len(test_search["data"]["relationships"]["studies"]["data"])):
                    study_search.append(
                        test_search["data"]["relationships"]["studies"]["data"][study]["id"])
                for study_id in study_search:
                    study_search_query = "curl -s -X GET \"" + request.session.get(
                        "storage") + "/studies/" + study_id + "\" -H \"accept: application/json\""
                    res_studies = subprocess.Popen([study_search_query], stdout=subprocess.PIPE,
                                                shell=True).communicate()[0].decode()
                    found_studies = json.loads(res_studies)
                    study_names[study_id] = found_studies["data"]["attributes"]["title"]
            if study_names and not assay_names and selected_study != "":
                assay_search = []
                search_assay = "curl -s -X GET \"" + request.session.get(
                    "storage") + "/studies/" + selected_study + "\" -H \"accept: application/json\""
                assay_search_results = subprocess.Popen([search_assay],
                                                        stdout=subprocess.PIPE,
                                                        shell=True).communicate()[0].decode()
                test_search = json.loads(assay_search_results)
                for assay in range(0, len(test_search["data"]["relationships"]["assays"]["data"])):
                    assay_search.append(
                        test_search["data"]["relationships"]["assays"]["data"][assay]["id"])
                for assay_id in assay_search:
                    assay_search_query = "curl -s -X GET \"" + request.session.get(
                        "storage") + "/assays/" + assay_id + "\" -H \"accept: application/json\""
                    res_assays = subprocess.Popen(
                        [assay_search_query], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
                    found_assays = json.loads(res_assays)
                    assay_names[assay_id] = found_assays["data"]["attributes"]["title"]
            cns = request.POST.get('cns')
            cna = request.POST.get('cna')
            if (
                request.POST.get('newstudy')
            ):
                # create study function
                create_study(
                    request.session.get('username'),
                    request.session.get('password'),
                    request.session.get('storage'),
                    userid,
                    request.POST.get("proj").split(',')[0],
                    request.POST.get("inv").split(',')[0],
                    request.POST.get('stitle'),
                    request.POST.get('sdescription'),
                    request.POST.get('newstudy')
                )
            if (
                request.POST.get('newassay')
            ):
                # create assay function
                seekcheck = create_assay(
                    request.session.get('username'),
                    request.session.get('password'),
                    request.session.get('storage'),
                    userid,
                    request.POST.get("proj").split(',')[0],
                    request.POST.get("stu").split(',')[0],
                    request.POST.get('atitle'),
                    request.POST.get('adescription'),
                    request.POST.get('assay_type'),
                    request.POST.get('technology_type'),
                    request.POST.get('newassay')
                )
                if not seekcheck:
                    return HttpResponseRedirect(reverse('seek'))
            if request.FILES.get('uploadfiles'):
                upload_dir = (
                    "tmp" +
                    hashlib.md5(request.session.get(
                        'username').encode('utf-8')).hexdigest()
                )
                upload_full_path = os.path.join(settings.MEDIA_ROOT, upload_dir)
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
                    request.session.get('storage'),
                    request.POST.get('title'),
                    os.path.join(upload_full_path, upload.name),
                    upload.name,
                    content_type,
                    userid,
                    request.POST.get("proj").split(',')[0],
                    request.POST.get("as").split(',')[0],
                    request.POST.get('description')
                )
                call(["rm", "-r", upload_full_path])
    return render(
        request,
        "seek.html",
        context={'projects': projects,
                 'investigations': inv_names,
                 'studies': study_names,
                 'assays': assay_names,
                 'userids': user_dict,
                 'proj': selected_project,
                 'proj_name': selected_project_name,
                 'inv': selected_investigation,
                 'inv_name': selected_investigation_name,
                 'stu': selected_study,
                 'stu_name': selected_study_name,
                 'as': selected_assay,
                 'as_name': selected_assay_name,
                 'cns': cns,
                 'cna': cna,
                 'searches': searches,
                 'fullname': fullname,
                 'disgenet': dids,
                 'disgenettags': selected_disgenet_tags,
                 'storeddisgenet': stored_disgenet,
                 'storededam': stored_edam,
                 'edam': eids,
                 'err': err})


def get_investigation_folders(storage, storagetype, username, password):
    """Gets the user's investigation folders from the storage URL,
    This will be shown on the homepage for storing existing Galaxy 
    histories.

    Arguments:
        storage: The URL of the ISA structure storage.
        storagetype: The storage type (SEEK or Owncloud)
        username: The username of the ISA structure storage.
        password: The password of the ISA structure storage.

    Returns:
        A list of investigation folder and a list of study folders.
    """
    oc_folders = ""
    if storagetype != "SEEK":
        inv_folders = subprocess.Popen([
            "curl -s -X PROPFIND -u" + username + ":" + password +
            " '" + storage + "/' | grep -oPm250 '(?<=<d:href>)[^<]+'"
        ], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    else:
        inv_folders = []
        seek_investigations = get_seek_investigations(
            username, password, storage)
        for it, dummyii in seek_investigations.items():
            inv_folders.append(it)
            get_seek_studies(username, password, storage, it)
    return inv_folders, oc_folders


def get_study_folders(storage, storagetype, username, password, investigation):
    """Gets the study folders based on the selected investigation from the
    homepage. This is used to store existing Galaxt histories.

    Arguments:
        storage: The URL of the ISA structure storage.
        storagetype: To show if the storage is SEEK or ownCloud.
        username: The username of the ISA structure storage.
        password: The password of the ISA structure storage.
        investigation: SEEK investigation ID.

    Returns:
        A list of investigationa folders and a list of study folders.
    """
    if storagetype != "SEEK":
        oc_folders = subprocess.Popen([
            "curl -s -X PROPFIND -u " + username + ":" + password +
            " '" + storage + "/" + investigation +
            "' | grep -oPm250 '(?<=<d:href>)[^<]+'"],
            stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
        inv_folders = subprocess.Popen([
            "curl -s -X PROPFIND -u " + username + ":" + password +
            " '" + storage +
            "/' | grep -oPm250 '(?<=<d:href>)[^<]+'"],
            stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    else:
        seek_inv = get_seek_investigations(
            username, password, storage)
        inv_folders = []
        for it, dummyii in seek_inv.items():
            inv_folders.append(it)
        seek_study = get_seek_studies(
            username, password, storage, it)
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
    ftp = gi.config.get_config()["ftp_upload_site"]
    if "bioinf-galaxian" in ftp:
        ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
    for gene in genomes:
        for g in gene:
            if "(" not in g:
                dbkeys.append(g)
    return gusername, workflows, his, dbkeys


def get_seek_userid(server, username, password, fullname):
    """Gets the SEEK user ID based on the full name of the user.
    
    Arguments:
        server: SEEK server address.
        username: SEEK username
        password: SEEK password
        fullname: Full name of the user in SEEK.
    
    Returns:
        The user ID based on the full name of the user or None.
    """
    userquery = ("curl -X GET " + server + "/people -H \"accept: application/json\"")
    getpeople = subprocess.Popen(
        [userquery], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    jsonpeople = json.loads(getpeople)
    userid = None
    for uid in range(0, len(jsonpeople["data"])):
        print(jsonpeople["data"][uid]["attributes"]["title"])
        if jsonpeople["data"][uid]["attributes"]["title"] == fullname:
            userid = str(jsonpeople["data"][uid]["id"])
    return userid


def get_seek_investigations(username, password, storage):
    """Get all SEEK investigations that the logged in user has access to.

    Arguments:
        username: The SEEK username.
        password: The SEEK password.
        storage: The SEEK URL.

    Returns:
        A dictionary with SEEK investigations and URLs.
    """
    investigations = {}
    investigation_titles = subprocess.Popen([
        "curl -s -u \'" + username + "\':" + password + " " + storage +
        "/investigations.xml | grep -e \'investigation xlink\' | "
        "sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"],
        stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    investigation_titles = investigation_titles.split("\n")
    investigation_titles = list(filter(None, investigation_titles))
    for it in investigation_titles:
        investigation_id = subprocess.Popen([
            "curl -s -u \'" + username + "\':" + password + " " + storage +
            "/investigations.xml | grep -e \'" + it +
            "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"],
            stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        investigations[it] = investigation_id.strip("\n")
    return investigations


def get_seek_studies(username, password, storage, investigation):
    """Get all SEEK studies based on an investigation.

    Arguments:
        username: The SEEK username.
        password: The SEEK password.
        storage: The SEEK URL.
        investigation: Investigation name

    Returns:
        A dictionary with SEEK studies and URLs.
    """
    studies = {}
    investigation_title = investigation.split("/")[-1]
    investigation_command = ("curl -X GET " + storage +
                            "/investigations/ -H \"accept: application/json\"")
    investigation_result = subprocess.Popen(
        [investigation_command],
        stdout=subprocess.PIPE, shell=True
    ).communicate()[0].decode()
    json_investigation = json.loads(investigation_result)
    for x in range(0, len(json_investigation["data"])):
        if json_investigation["data"][x]["attributes"]["title"] == investigation_title.strip("\n"):
            investigation_id = json_investigation["data"][x]["id"]
    study_link_command = ("curl -X GET " + storage + "/investigations/" +
                    investigation_id + " -H \"accept: application/json\"")
    study_link = subprocess.Popen(
        [study_link_command], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode()
    json_study_link = json.loads(study_link)
    study_count = len(
        json_study_link["data"]["relationships"]["studies"]["data"])
    for i in range(study_count):
        study_id = json_study_link["data"]["relationships"]["studies"]["data"][i]["id"]
        study_command = ("curl -X GET " + storage + "/studies/" +
                    study_id + " -H \"accept: application/json\"")
        study_results=subprocess.Popen(
            [study_command],
            stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode()
        json_study = json.loads(study_results)
        study_title = json_study["data"]["attributes"]["title"]
        studies[study_title] = study_id
    return studies


def get_seek_assays(username, password, storage, study):
    """Gets the SEEK assays based on a study.

    Arguments:
        username: The SEEK username.
        password: The SEEK password.
        storage: The SEEK URL.
        study: Study ID

    Returns:
        A dictionary with SEEK assay IDs and URLs.
    """
    assays = {}
    study_id = study.split("/")[-1]
    assay_titles = subprocess.Popen([
        "curl -s -u \'" + username + "\':" + password + " " + storage +
        "/studies/" + study_id + ".xml | grep -e \'study xlink\' | "
                                 "sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
    ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    assay_titles = assay_titles.split("\n")
    assay_titles = list(filter(None, assay_titles))
    for at in assay_titles:
        assay_id = subprocess.Popen([
            "curl -s -u \'" + username + "\':" + password + " " + storage +
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
def modify(request):
    """Delete triples from the triple store.
    This can be done based on an investigation or study name.

    Arguments:
        request: A request to get the current session.
    """
    if request.session.get('username') is not None:
        if request.POST.get('ok') == 'ok':
            if request.POST.get('dstudy') != "":
                call([
                    "bash ~/myFAIR/static/bash/triples.sh -u " +
                    request.session.get('username').replace('@', '') +
                    " -t5 -s " + request.POST.get('dstudy')
                ], shell=True)
            elif request.POST.get('dinvestigation') != "":
                call([
                    "bash ~/myFAIR/static/bash/triples.sh -u " +
                    request.session.get('username').replace('@', '') +
                    " -t6 -s " + request.POST.get('dinvestigation')
                ], shell=True)
        else:
            err = "Please check accept to delete study or investigation"
            return render(request, "modify.html", context={'error': err})
        return HttpResponseRedirect(reverse('index'))
    else:
        return HttpResponseRedirect(reverse('index'))


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
                request.session.get('password'),
                request.session.get('storage'))
            for it, dummyii in inv_names.items():
                oc_folders.append(it)
        else:
            oc_folders = subprocess.Popen([
                "curl -s -X PROPFIND -u" +
                request.session.get('username') + ":" +
                request.session.get('password') +
                " '" + request.session.get('storage') +
                "/' | grep -oPm250 '(?<=<d:href>)[^<]+'"
            ], stdout=subprocess.PIPE, shell=True
            ).communicate()[0].decode().split("\n")
        if list(filter(None, oc_folders)):
            for oc in oc_folders:
                if "/owncloud/" in request.session.get('storage'):
                    new = oc.replace(
                        '/owncloud/remote.php/webdav/', '').replace('/', '')
                    folders.append(new)
                elif request.session.get('storage_type') == "SEEK":
                    folders.append(oc)
                else:
                    new = oc.replace(
                        '/remote.php/webdav/', '').replace('/', '')
                    folders.append(new)
            folders = list(filter(None, folders))
        if request.method == 'POST':
            datalist = request.POST.get('datalist')
            metalist = request.POST.get('metalist')
            disgenet = request.POST.get('disgenet-tag')
            edam = request.POST.get('edam-tag')
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
                    if request.session.get('storage_type') != "SEEK":
                        filelist = subprocess.Popen([
                            "curl -s -X PROPFIND -u " +
                            request.session.get('username') + ":" +
                            request.session.get('password') + " '" +
                            request.session.get('storage') +
                            "/" + inv + "/" + study +
                            "' | grep -oPm100 '(?<=<d:href>)[^<]+'"
                        ], stdout=subprocess.PIPE, shell=True
                        ).communicate()[0].decode().split("\n")
                    else:
                        filelist = []
                        assays = get_seek_assays(
                            request.session.get('username'),
                            request.session.get('password'),
                            request.session.get('storage'), study)
                        for dummyat, ai in assays.items():
                            filelist.append(ai)
                for f in filelist:
                    if "/owncloud/" in request.session.get('storage'):
                        new = f.replace(
                            '/owncloud/remote.php/webdav/' +
                            inv + "/" + study, '').replace('/', '')
                        files.append(new)
                    elif request.session.get('storage_type') == "SEEK":
                        files.append(f)
                    else:
                        new = f.replace(
                            '/remote.php/webdav/' + inv + "/" +
                            study, '').replace('/', '')
                        files.append(new)
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
                'folders': folders, 'files': files,
                'studies': studies, 'inv': inv,
                'sstudy': study})
        return render(request, 'triples.html', context={
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
        if "webdav" in request.session.get('storage'):
            oc_folders = subprocess.Popen([
                "curl -s -X PROPFIND -u " +
                request.session.get('username') + ":" +
                request.session.get('password') +
                " '" + request.session.get('storage') +
                "/' | grep -oPm250 '(?<=<d:href>)[^<]+'"
            ], stdout=subprocess.PIPE, shell=True
            ).communicate()[0].decode().split("\n")
        else:
            inv_names = get_seek_investigations(
                request.session.get('username'),
                request.session.get('password'),
                request.session.get('storage'))
            oc_folders = inv_names.keys()
        if list(filter(None, oc_folders)):
            folders = []
            studies = []
            oc_studies = ""
            for oc in oc_folders:
                if "b2drop" in request.session.get('storage'):
                    new = oc.replace(
                        '/remote.php/webdav/', '').replace('/', '')
                    if "." not in new:
                        folders.append(new)
                elif "/owncloud/" in request.session.get('storage'):
                    new = oc.replace(
                        '/owncloud/remote.php/webdav/', '').replace('/', '')
                    if "." not in new:
                        folders.append(new)
                elif request.session.get('storage_type') == "SEEK":
                    folders.append(oc)
                else:
                    new = oc.replace(
                        '/remote.php/webdav/', '').replace('/', '')
                    if "." not in new:
                        folders.append(new)
            folders = list(filter(None, folders))
            if (
                request.POST.get('folder') != "" and
                request.POST.get('folder') is not None
            ):
                if "webdav" in request.session.get('storage'):
                    oc_studies = subprocess.Popen([
                        "curl -s -X PROPFIND -u " +
                        request.session.get('username') + ":" +
                        request.session.get('password') + " '" +
                        request.session.get('storage') + "/" +
                        request.POST.get('folder') +
                        "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
                    ], stdout=subprocess.PIPE, shell=True
                    ).communicate()[0].decode().split("\n")
                else:
                    oc_studies = []
                    for it, dummyii in inv_names.items():
                        if it == request.POST.get('folder'):
                            studydict = get_seek_studies(
                                request.session.get('username'),
                                request.session.get('password'),
                                request.session.get('storage'), it)
                    for st, dummysi in studydict.items():
                        oc_studies.append(st)
            else:
                if request.POST.get('selected_folder') is not None:
                    oc_studies = subprocess.Popen([
                        "curl -s -X PROPFIND -u " +
                        request.session.get('username') + ":" +
                        request.session.get('password') + " '" +
                        request.session.get('storage') + "/" +
                        request.POST.get('selected_folder') +
                        "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
                    ], stdout=subprocess.PIPE, shell=True
                    ).communicate()[0].decode().split("\n")
            if oc_studies != "":
                for s in oc_studies:
                    if (
                        request.POST.get('folder') != "" and
                        request.POST.get('folder') is not None
                    ):
                        oc_studies = list(filter(None, oc_studies))
                        if "/owncloud/" in request.session.get('storage'):
                            new = s.replace(
                                '/owncloud/remote.php/webdav/' +
                                request.POST.get('folder') + "/", '').replace(
                                    '/', '')
                            studies.append(new)
                        elif request.session.get('storage_type') == "SEEK":
                            studies.append(s)
                        else:
                            new = s.replace(
                                '/remote.php/webdav/' +
                                request.POST.get('folder') + "/", '').replace(
                                    '/', '')
                            studies.append(new)
                    elif (
                        request.POST.get('selected_folder') != "" and
                        request.POST.get('selected_folder') is not None
                    ):
                        if "/owncloud/" in request.session.get('storage'):
                            new = s.replace(
                                '/owncloud/remote.php/webdav/' +
                                request.POST.get('selected_folder') +
                                "/", '').replace('/', '')
                            studies.append(new)
                        else:
                            new = s.replace(
                                '/remote.php/webdav/' +
                                request.POST.get('selected_folder') +
                                "/", '').replace('/', '')
                            studies.append(new)
                studies = list(filter(None, studies))
                inv = request.POST.get('folder')
                return render(request, 'triples.html', context={
                    'folders': folders, 'studies': studies, 'inv': inv})
            else:
                return HttpResponseRedirect(reverse('triples'))
    else:
        return HttpResponseRedirect(reverse('index'))


@csrf_exempt
def store(request):
    """Read the metadata file and store all information in the triple store.

    Arguments:
        request: A request to receive all the information that needs
        to be stored in the triple store.
    """
    if request.method == 'POST':
        username = request.session.get('username')
        password = request.session.get('password')
        storage = request.session.get('storage')
        inv = request.POST.get('inv')
        study = request.POST.get('study')
        metadata = request.POST.get('metadata')
        datafile = request.POST.get('datafile')
        disgenet = onto(request.POST.get('disgenet'),
                        request.POST.get('edam'))[0]
        edam = onto(request.POST.get('disgenet'), request.POST.get('edam'))[1]
        if username == "" or username is None:
            login(request)
        else:
            pid = datafile
            metadata = metadata.split(',')
            if metadata is not None:
                for m in metadata:
                    mfile = m.replace('[', '').replace(']', '').replace(
                        '"', '').replace(' ', '')
                    metafile = subprocess.Popen([
                        "curl -s -k -u " +
                        username + ":" + password + " " + mfile
                    ], stdout=subprocess.PIPE, shell=True
                    ).communicate()[0].decode()
                    metaf = open(username + '/metafile.csv', 'w')
                    metaf.write(metafile)
                    metaf.close()
                    filemeta = "metafile.csv"
                    if "This is the WebDAV interface." in metafile:
                        createMetadata(request, datafile)
                        filemeta = "meta.txt"
                        call([
                            "curl -s -k -u " + username + ":" + password +
                            " -T " + '\'' + "meta.txt" + '\'' + " " +
                            storage + "/" + inv + "/" + study + "/meta.txt"
                        ], shell=True)
            with open(username + "/" + filemeta, 'rt') as csvfile:
                count = 0
                reader = csv.DictReader(csvfile)
                cnt = 0
                for row in reader:
                    for p in pid.split(','):
                        data = p.replace('[', '').replace(']', '').replace(
                            "'", "").replace('"', '').replace(' ', '')
                        call([
                            "bash ~/myFAIR/static/bash/triples.sh -u " +
                            username.replace('@', '') +
                            " -t0 -r " + str(cnt) + " -i " +
                            inv + " -s " + study + " -p " + data
                        ], shell=True, stdout=subprocess.PIPE)
                    if filemeta == "meta.txt":
                        metatriple = (storage + "/" + inv + "/" +
                                      study + "/meta.txt")
                        call([
                            "bash ~/myFAIR/static/bash/triples.sh -u " +
                            username.replace('@', '') +
                            " -t1 -r " + str(cnt) + " -s " +
                            study + " -m " + metatriple
                        ], shell=True, stdout=subprocess.PIPE)
                    else:
                        for m in metadata:
                            m = m.replace('[', '').replace(']', '')
                            mfile = m.replace('"', '').replace(
                                "'", "").replace(' ', '')
                            metatriple = mfile
                            call([
                                "bash ~/myFAIR/static/bash/triples.sh -u " +
                                username.replace('@', '') + " -t1 -r " +
                                str(cnt) + " -s " + study + " -m " + metatriple
                            ], shell=True, stdout=subprocess.PIPE)
                    disease = request.POST.get('disgenet').replace(" ", "%20")
                    call([
                        "bash ~/myFAIR/static/bash/triples.sh -u " +
                        username.replace('@', '') +
                        " -t2 -r " + str(cnt) + " -i " + inv +
                        " -s " + study + " -d " + disgenet + " -e " + edam +
                        " -v " + disease
                    ], shell=True, stdout=subprocess.PIPE)
                    headers = []
                    for (k, v) in row.items():
                        for h in range(0, len(k.split('\t'))):
                            if k.split('\t')[h] != "":
                                value = v.split('\t')[h]
                                header = k.split('\t')[h]
                                headers.append(header.replace('"', ''))
                                if "#" in header:
                                    header = header.replace('#', '')
                                call([
                                    "bash ~/myFAIR/static/bash/triples.sh "
                                    "-u " + username.replace('@', '') +
                                    " -t3 -r " + str(cnt) + " -i " + inv +
                                    " -s " + study + " -a " +
                                    header.replace('"', '') + " -b " +
                                    value.replace('"', '').replace('+', '%2B')
                                ], shell=True, stdout=subprocess.PIPE)
                    if "sex" not in headers:
                        call([
                            "bash ~/myFAIR/static/bash/triples.sh -u " +
                            username.replace('@', '') +
                            " -t4 -r " + str(cnt) + " -i " +
                            inv + " -s " + study + " -b Unknown"
                        ], shell=True, stdout=subprocess.PIPE)
                    count += 1
                    cnt += 1
            call(["rm", username + "/metafile.csv"])
            call(["rm", username + "/meta.txt"])
        return HttpResponseRedirect(reverse("index"))


def get_history_id(galaxyemail, galaxypass, server):
    """Get the current Galaxy history ID

    Arguments:
        galaxyemail: The Galaxy email address.
        galaxypass: The Galaxy password.
        server: The Galaxy server URL.

    Returns:
        The current Galaxy history ID from the logged in user.
    """
    gi = GalaxyInstance(url=server, email=galaxyemail, password=galaxypass)
    cur_hist = gi.histories.get_current_history()
    current = json.dumps(cur_hist)
    current_hist = json.loads(current)
    history_id = current_hist['id']
    return history_id


def get_input_data(galaxyemail, galaxypass, server):
    """Get input data based on the selected history.
    Find the number of uploaded files and return the id's of the files.

    Arguments:
        galaxyemail: The Galaxy email address.
        galaxypass: The Galaxy password.
        server: The Galaxy server URL.

    Returns:
        A list of input files from the Galaxy history and 
        the amount of input datasets in the history.
    """
    gi = GalaxyInstance(url=server, email=galaxyemail, password=galaxypass)
    history_id = get_history_id(galaxyemail, galaxypass, server)
    hist_contents = gi.histories.show_history(history_id, contents=True)
    inputs = {}
    datacount = 0
    datasets = [dataset for dataset in hist_contents if not dataset['deleted']]
    for dataset in datasets:
        inputs[dataset['name']] = dataset['id']
        datacount += 1
    return inputs, datacount


def createMetadata(request, datafile):
    """Create a metadata file when there is none available.
    Only for GEO data matrices.

    Arguments:
        request: A request to get the current session.
        datafile: The GEO data matrix.

    Returns:
        A metadata file created from the GEO data matrix.
    """
    samples = []
    datafile = datafile.split(',')
    for f in datafile:
        filename = f.replace('[', '').replace(']', '').replace(
            '"', '').replace(' ', '')
        cont = subprocess.Popen([
            "curl -u " + request.session.get('username') + ":" +
            request.session.get('password') +
            " -k -s " + filename[1:]
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    with open(request.session.get('username') + "/data.txt", "w") as datafile:
        datafile.write(cont)
    with open(datafile.name, "r") as tfile:
        for line in tfile:
            if "!Sample_geo_accession" in line:
                line = line.split('\t')
                for x in range(0, len(line)):
                    samples.append(line[x].replace('\n', ''))
        samples = list(filter(None, samples))
        tfile.seek(0)
        with open(request.session.get('username') + "/meta.txt", "w") as meta:
            for i in range(0, len(samples)):
                for line in tfile:
                    if "!Sample" in line:
                        line = line.split('\t')
                        line[i] = line[i].replace("!Sample_", "").replace(
                            "\n", "").replace("'", "").replace(",", "")
                        line[i] = line[i].replace("\"", "")
                        if line[i] == "geo_accession":
                            line[i] = "sample_id"
                        elif line[1] == "\"female\"" or line[1] == "\"male\"":
                            line[0] = "sex"
                        if "title" not in line[0]:
                            meta.write(
                                re.sub(r'[^\x00-\x7F]+', ' ', line[i]) + '\t')
                meta.write('\n')
                tfile.seek(0)
        meta.close()
    datafile.close()
    call(["rm", request.session.get('username') + "/data.txt"])
    return meta


def get_selection(iselect, gselect, select, mselect):
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
    mfiles = []
    investigations = []
    for g in gselect:
        groups.append(g.replace('[', '').replace('"', '').replace(']', ''))
    for s in select:
        if s.replace('[', '').replace('"', '').replace(']', '') not in files:
            files.append(s.replace('[', '').replace('"', '').replace(']', ''))
    for m in mselect:
        if m.replace('[', '').replace('"', '').replace(']', '') not in mfiles:
            mfiles.append(m.replace('[', '').replace('"', '').replace(']', ''))
    for i in iselect:
        if (
            i.replace('[', '').replace('"', '').replace(']', '')
            not in investigations
        ):
            investigations.append(
                i.replace('[', '').replace('"', '').replace(']', ''))
    return files, mfiles, groups, investigations


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
        if len(list(filter(None, files))) > 0:
            workflow = gi.workflows.show_workflow(workflowid)
            if new_hist is None or new_hist == "":
                new_hist_name = (workflow['name'] + "_" + date)
            else:
                new_hist_name = new_hist
            gi.histories.create_history(name=new_hist_name)
            history_id = get_history_id(galaxyemail, galaxypass, server)
        else:
            pass
    else:
        if len(list(filter(None, files))) > 0:
            if new_hist is None or new_hist == "":
                new_hist_name = ("Use_Galaxy_" + date)
            else:
                new_hist_name = new_hist
            gi.histories.create_history(name=new_hist_name)
            history_id = get_history_id(galaxyemail, galaxypass, server)
        else:
            pass
    return history_id


def split_data_files(username, filename, control, test):
    """Create datafiles and send them to the Galaxy server.

    Arguments:
        username: Username used for the storage location.
        filename: Name of the file that needs to be split.
        control: Samples in control group.
        test: Samples in test group.

    Returns:
        Lists of samples in group A and group B.
        Files with samples from group A and group B.
        The complete datafile.
    """
    samples_a = []
    samples_b = []
    linenr = 0
    matrix = False
    noheader = False
    with open(username + "/input_" + filename, "r") as tfile:
        with open(username + "/input_A_" + filename, "w") as ndfilea:
            with open(username + "/input_B_" + filename, "w") as ndfileb:
                for line in tfile:
                    if linenr == 0:
                        samples_a.append(0)
                        samples_b.append(0)
                        if "!" not in line:
                            noheader = True
                    if not noheader:
                        if "!Sample_geo_accession" in line:
                            line = line.split('\t')
                            for x in range(0, len(line)):
                                if line[x].replace('\n', '') in control:
                                    samples_a.append(x)
                                if line[x].replace('\n', '') in test:
                                    samples_b.append(x)
                        else:
                            if "!series_matrix_table_begin" in line:
                                matrix = True
                                samples_a.append(0)
                            if matrix:
                                line = line.split('\t')
                                for p in (p for p, x in enumerate(line)
                                          if p in samples_a):
                                    if (
                                        "!series_matrix_table_begin"
                                        not in line[p] and
                                        "!series_matrix_table_end"
                                        not in line[p]
                                    ):
                                        ndfilea.write(
                                            line[p].replace('\"',
                                                            '').replace('\n',
                                                                        '') +
                                            '\t'
                                        )
                                for pb in (
                                    pb for pb, x in enumerate(line)
                                    if pb in samples_b
                                ):
                                    if (
                                        "!series_matrix_table_begin"
                                        not in line[pb] and
                                        "!series_matrix_table_end"
                                        not in line[pb]
                                    ):
                                        ndfilea.write(
                                            line[pb].replace('\"',
                                                             '').replace('\n',
                                                                         '') +
                                            '\t'
                                        )
                                ndfilea.write('\n')
                            else:
                                line.strip()
                    else:
                        line = line.split('\t')
                        if linenr == 0:
                            column = 0
                            control = control.split(',')
                            test = test.split(',')
                            for l in line:
                                for c in control:
                                    if (
                                        str(c.replace('[', '').replace(
                                            ']', '').replace(
                                            '"', '')) == l.replace('\n', '')
                                    ):
                                        samples_a.append(column)
                                for t in test:
                                    if (
                                        str(t.replace('[', '').replace(
                                            ']', '').replace(
                                            '"', '')) == l.replace('\n', '')
                                    ):
                                        samples_b.append(column)
                                column += 1
                        column = 0
                        for l in line:
                            if column in samples_a:
                                ndfilea.write(
                                    line[column].replace(
                                        '\"', '').replace('\n', '') + '\t'
                                )
                            if column in samples_b:
                                ndfileb.write(
                                    line[column].replace(
                                        '\"', '').replace('\n', '') + '\t'
                                )
                            column += 1
                        ndfilea.write('\n')
                        ndfileb.write('\n')
                    linenr += 1
        return samples_a, samples_b, ndfilea, ndfileb, tfile


def make_data_files(gi, files, username, password, galaxyemail, galaxypass,
                    control, test, history_id, filetype, dbkey, storagetype):
    """Create datafiles and send them to the Galaxy server.

    TODO: Check if user has the correct permissions to the study.
    TODO: Give a message to the user when there is no edit permission.

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
    if "bioinf-galaxian" in ftp:
        ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
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
            call(["curl -L " + file_url + " -o " +
                  username + "/input_" + filename], shell=True)
        else:
            nfile = str(file).split('/')
            filename = nfile[len(nfile)-1]
            with open(username + "/input_" + filename, "w") as dfile:
                cont = subprocess.Popen([
                    "curl -u " + username + ":" + password + " -k -s " + file
                ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
                dfile.write(cont)
            dfile.close()
        if control != "[]" or test != "[]":
            samples_a, samples_b, ndfilea, ndfileb, tfile = split_data_files(
                username, filename, control, test)
            if len(samples_a) > 1:
                check_call([
                    "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                    " -e \"put " + ndfilea.name + "; bye\""
                ], shell=True)
                gi.tools.upload_from_ftp(
                    ndfilea.name.split("/")[-1], history_id,
                    file_type=filetype, dbkey=dbkey)
                uploaded_files.append(ndfilea.name.split("/")[-1])
            if len(samples_b) > 1:
                check_call([
                    "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                    " -e \"put " + ndfileb.name + "; bye\""
                ], shell=True)
                gi.tools.upload_from_ftp(
                    ndfileb.name.split("/")[-1], history_id,
                    file_type=filetype, dbkey=dbkey)
                uploaded_files.append(ndfileb.name.split("/")[-1])
            ndfilea.close()
            ndfileb.close()
            call(["rm", ndfilea.name])
            call(["rm", ndfileb.name])
        else:
            if storagetype == "SEEK":
                check_call([
                    "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                    " -e \"put " + username + "/input_" + filename + "; bye\""
                ], shell=True)
                gi.tools.upload_from_ftp(
                    "input_" + filename, history_id,
                    file_type=filetype, dbkey=dbkey)
                uploaded_files.append("input_" + filename)
                call(["rm", "-r", username + "/input_" + filename])
            else:
                with open(username + "/input_" + filename, "r") as tfile:
                    check_call([
                        "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                        " -e \"put " + tfile.name + "; bye\""
                    ], shell=True)
                gi.tools.upload_from_ftp(
                    tfile.name.split("/")[-1], history_id,
                    file_type=filetype, dbkey=dbkey)
                uploaded_files.append(tfile.name.split("/")[-1])
                call(["rm", dfile.name])
                call(["rm", tfile.name])
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


def split_meta_files(username, metadatafile, control, test):
    """Creates new metadata file when data is split into classes.

    Arguments:
        username: Username used for the storage location.
        metadatafile: Metadata file that will be edited.
        control: Samples in control group
        test: Samples in test group

    Returns:
        A new metadata file
    """
    linenr = 0
    with open(username + "/input_classmeta.txt", "w") as nmeta:
        for l in metadatafile:
            columns = l.split('\t')
            if len(columns) > 0:
                if linenr > 0:
                    if len(columns) > 0:
                        for c in control:
                            selected_control = str(
                                c.replace('[', '').replace(
                                    ']', '').replace('"', '')
                            )
                            file_control = columns[0].replace('[', '').replace(
                                ']', '').replace('"', '').replace('\n', '')
                            if selected_control == file_control:
                                l = l.replace(
                                    '\n', '').replace('\r', '')
                                nmeta.write(l + "\tA")
                                nmeta.write("\n")
                        for t in test:
                            selected_test = str(
                                t.replace('[', '').replace(
                                    ']', '').replace('"', '')
                            )
                            file_test = columns[0].replace('[', '').replace(
                                ']', '').replace('"', '').replace('\n', '')
                            if selected_test == file_test:
                                l = l.replace(
                                    '\n', '').replace('\r', '')
                                nmeta.write(l + "\tB")
                                nmeta.write("\n")
                else:
                    l = l.replace('\n', '').replace('\r', '')
                    nmeta.write(l + "\tclass_id" + "\n")
            linenr += 1
    return nmeta


def make_meta_files(gi, mfiles, username, password, galaxyemail,
                    galaxypass, control, test, history_id):
    """Create metadata files and send them to the Galaxy server.

    Arguments:
        gi: The Galaxy Instance.
        mfiles: A list of metadata files.
        username: Username used for the storage location.
        password: Password used for the storage location.
        galaxyemail: The Galaxy email address.
        galaxypass: The Galaxy passaword
        control: Samples in control group.
        test: Samples in test group.
        history_id: The Galaxy history ID to send files to.

    Raises:
        CalledProcessError: An error occurred when uploading data 
        to the Galaxy server using the FTP address.
    """
    uploaded_files = []
    ftp = gi.config.get_config()["ftp_upload_site"]
    if "bioinf-galaxian" in ftp:
        ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
    control = control.split(',')
    test = test.split(',')
    for meta in mfiles:
        mfile = str(meta).split('/')
        mfilename = mfile[len(mfile)-1]
        if meta == "No metadata":
            pass
        else:
            mcont = subprocess.Popen([
                "curl -u " + username + ":" + password + " -k -s " + meta
            ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            with open(username + "/input_" + mfilename, "w") as metfile:
                metfile.write(mcont)
            metfile.close()
            # linenr = 0
            with open(username + "/input_" + mfilename, "r") as metadatafile:
                if control[0] != "[]" or test[0] != "[]":
                    nmeta = split_meta_files(
                        username, metadatafile, control, test)
                    call([
                        "lftp -u " + galaxyemail + ":" + galaxypass + " " +
                        ftp + " -e \"put " + nmeta.name + "; bye\""
                    ], shell=True)
                    gi.tools.upload_from_ftp(
                        nmeta.name.split("/")[-1], history_id,
                        file_type="auto", dbkey="?")
                    uploaded_files.append(nmeta.name.split("/")[-1])
                    call(["rm", nmeta.name])
                    call(["rm", metadatafile.name])
                else:
                    call([
                        "lftp -u " + galaxyemail + ":" + galaxypass + " " +
                        ftp + " -e \"put " + metadatafile.name + "; bye\""
                    ], shell=True)
                    gi.tools.upload_from_ftp(
                        metadatafile.name.split("/")[-1], history_id,
                        file_type="auto", dbkey="?")
                    uploaded_files.append(metadatafile.name.split("/")[-1])
                    call(["rm", metadatafile.name])
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
    selectedmeta = request.POST.get('meta')
    filetype = request.POST.get('filetype')
    dbkey = request.POST.get('dbkey')
    workflowid = request.POST.get('workflowid')
    pid = request.POST.get('data_id')
    sendmeta = request.POST.get('sendmeta')
    # makecol = request.POST.get('col')
    # data_ids = []
    control = request.POST.get('samples')
    test = request.POST.get('samplesb')
    new_hist = request.POST.get('historyname')
    group = request.POST.get('group')
    investigation = request.POST.get('investigation')
    date = format(datetime.now() + timedelta(hours=2))
    select = selected.split(',')
    mselect = selectedmeta.split(',')
    gselect = group.split(',')
    iselect = investigation.split(',')
    files = get_selection(iselect, gselect, select, mselect)[0]
    mfiles = get_selection(iselect, gselect, select, mselect)[1]
    groups = get_selection(iselect, gselect, select, mselect)[2]
    investigations = get_selection(iselect, gselect, select, mselect)[3]
    history_id = create_new_hist(gi,
                                 request.session.get('galaxyemail'),
                                 request.session.get("galaxypass"),
                                 request.session.get('server'),
                                 workflowid, files, new_hist)
    inputs = {}
    if len(list(filter(None, files))) <= 0:
        return HttpResponseRedirect(reverse("index"))
    else:
        if sendmeta != "true":
            make_data_files(gi, files, request.session.get('username'),
                            request.session.get('password'),
                            request.session.get('galaxyemail'),
                            request.session.get('galaxypass'),
                            control, test, history_id, filetype, dbkey,
                            request.session.get('storage_type'))
        else:
            make_data_files(gi, files, request.session.get('username'),
                            request.session.get('password'),
                            request.session.get('galaxyemail'),
                            request.session.get('galaxypass'),
                            control, test, history_id, filetype, dbkey,
                            request.session.get('storage_type'))
            make_meta_files(gi, mfiles, request.session.get('username'),
                            request.session.get('password'),
                            request.session.get('galaxyemail'),
                            request.session.get('galaxypass'),
                            control, test, history_id)
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
                datasets = get_input_data(
                    request.session.get('galaxyemail'),
                    request.session.get('galaxypass'),
                    request.session.get('server'))[0]
                for dname, did in datasets.items():
                    if k in dname:
                        datamap[v] = {'src': "hda", 'id': did}
                in_count += 1
            # if makecol == "true":
            #     gi.histories.create_dataset_collection(
            #         history_id, make_collection(data_ids))
            gi.workflows.run_workflow(
                workflowid, datamap, history_id=history_id)
            gi.workflows.export_workflow_to_local_path(
                workflowid,
                request.session.get('username'),
                True)
            datafiles = get_output(request.session.get('galaxyemail'),
                                   request.session.get('galaxypass'),
                                   request.session.get('server'))
            store_results(1, gi, datafiles, request.session.get('server'),
                          request.session.get('username'),
                          request.session.get('password'),
                          request.session.get('storage'), workflowid,
                          groups, resultid, investigations, date, history_id,
                          request.session.get("storage_type"))
            store_results(3, gi, datafiles, request.session.get('server'),
                          request.session.get('username'),
                          request.session.get('password'),
                          request.session.get('storage'), workflowid,
                          groups, resultid, investigations, date, history_id,
                          request.session.get("storage_type"))
            if request.session.get("storage_type") != "SEEK":
                ga_store_results(request.session.get('username'),
                                 request.session.get('password'), workflowid,
                                 request.session.get('storage'),
                                 resultid, groups, investigations)
                call(["rm", request.session.get('username') + "/input_test"])
            return render_to_response('results.html', context={
                'workflowid': workflowid,
                'inputs': inputs, 'pid': pid,
                'server': request.session.get(
                    'server'
                )})
        else:
            # if makecol == "true":
            #     history_data = gi.histories.show_history(
            #         history_id, contents=True)
            #     for c in range(0, len(history_data)):
            #         data_ids.append(history_data[c]['id'])
            #     gi.histories.create_dataset_collection(
            #         history_id, make_collection(data_ids))
            ug_store_results(
                gi,
                request.session.get('galaxyemail'),
                request.session.get('galaxypass'),
                request.session.get('server'),
                workflowid,
                request.session.get('username'),
                request.session.get('password'),
                request.session.get('storage'),
                groups, investigations, date, history_id)
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


def store_results(column, gi, datafiles, server, username, password, storage,
                  workflowid, groups, resultid, investigations, date,
                  historyid, storagetype):
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
        storage: The URL for the storage location.
        workflowid: The Galaxy workflow ID.
        groups: A list of studies.
        resultid: The result ID. 
        investigations: A list of investigations.
        date: The current date and time.
        historyid: The Galaxy history ID.
        storagetype: The type of storage (SEEK or Owncloud)
    """
    assay_id_list = []
    o = 0
    for name in datafiles[column]:
        cont = subprocess.Popen([
            "curl -s -k " + server + datafiles[column-1][o]
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        old_name = date + "_" + name.replace('/', '_').replace(' ', '_')
        with open(username + "/" + old_name, "w") as outputfile:
            outputfile.write(cont)
        new_name = sha1sum(username + "/" + old_name) + "_" + old_name
        os.rename(username + "/" + old_name, username + "/" + new_name)
        # export = gi.histories.export_history(
        #             historyid,
        #             include_deleted=False,
        #             include_hidden=True)
        # home = str(Path.home())+ "/"
        # call(["touch", home + username + "/" + historyid + ".tar"])
        # f = open(home + username + "/" + historyid + ".tar", 'rb+')
        # gi.histories.download_history(
        #     historyid,
        #     export,
        #     f)
        # shaname = sha1sum(f.name) + "_" + f.name.split('/')[-1]
        # os.rename(f.name, home + username + "/" +
        #         strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname)
        # history_tar = strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname
        # url.append(strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname)
        if storagetype != "SEEK":
            for i in investigations:
                for g in groups:
                    call([
                        "curl -s -k -u " + username + ":" + password +
                        " -X MKCOL " + storage + "/" + i.replace('"', '') +
                        "/" + g.replace('"', '') + "/results_" + str(resultid)
                    ], shell=True)
                    call([
                        "curl -s -k -u " + username + ":" + password +
                        " -T " + '\'' + username + "/" + new_name + '\'' +
                        " " + storage + "/" + i.replace('"', '') + "/" +
                        g.replace('"', '') + "/results_" + str(resultid) +
                        "/" + new_name
                    ], shell=True)
                    # call([
                    #     "curl -s -k -u " + username + ":" + password +
                    #     " -T " + '\'' + username + "/" + new_name + '\'' +
                    #     " " + storage + "/" + i.replace('"', '') + "/" +
                    #     g.replace('"', '') + "/results_" + str(resultid) +
                    #     "/" + history_tar
                    # ], shell=True)
                    call([
                        "curl http://127.0.0.1:3030/ds/update -X POST --data "
                        "'update=INSERT DATA { "
                        "GRAPH <http://127.0.0.1:3030/ds/data/" +
                        username.replace('@', '') +
                        "> { <http://127.0.0.1:3030/" + str(resultid) +
                        "> <http://127.0.0.1:3030/ds/data?graph=" +
                        username.replace('@', '') + "#pid> \"" + storage + "/" +
                        i.replace('"', '') + "/" + g.replace('"', '') +
                        "/results_" + str(resultid) + "/" + new_name +
                        "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                    ], shell=True)
                    call([
                        "curl http://127.0.0.1:3030/ds/update -X POST --data "
                        "'update=INSERT DATA { "
                        "GRAPH <http://127.0.0.1:3030/ds/data/" +
                        username.replace('@', '') +
                        "> { <http://127.0.0.1:3030/" + str(resultid) +
                        "> <http://127.0.0.1:3030/ds/data?graph=" +
                        username.replace('@', '') + "#results_id> \"" +
                        str(resultid) + "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                    ], shell=True)
                    call([
                        "curl http://127.0.0.1:3030/ds/update -X POST --data "
                        "'update=INSERT DATA { "
                        "GRAPH <http://127.0.0.1:3030/ds/data/" +
                        username.replace('@', '') +
                        "> { <http://127.0.0.1:3030/" + str(resultid) +
                        "> <http://127.0.0.1:3030/ds/data?graph=" +
                        username.replace('@', '') + "#historyid> \"" +
                        str(historyid) + "\" } }'"
                        " -H 'Accept: text/plain,*/*;q=0.9'"
                    ], shell=True)
                    call([
                        "curl http://127.0.0.1:3030/ds/update -X POST --data "
                        "'update=INSERT DATA { "
                        "GRAPH <http://127.0.0.1:3030/ds/data/" +
                        username.replace('@', '') +
                        "> { <http://127.0.0.1:3030/" + str(resultid) +
                        "> <http://127.0.0.1:3030/ds/data?graph=" +
                        username.replace('@', '') + "#group_id> \"" +
                        g.replace('"', '') +
                        "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                    ], shell=True)
                    call([
                        "curl http://127.0.0.1:3030/ds/update -X POST --data "
                        "'update=INSERT DATA { "
                        "GRAPH <http://127.0.0.1:3030/ds/data/" +
                        username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                        str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                        username.replace('@', '') + "#investigation_id> \"" +
                        i.replace('"', '') +
                        "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                    ], shell=True)
                    call([
                        "curl http://127.0.0.1:3030/ds/update -X POST --data "
                        "'update=INSERT DATA { "
                        "GRAPH <http://127.0.0.1:3030/ds/data/" +
                        username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                        str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                        username.replace('@', '') + "#date> \"" + date +
                        "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                    ], shell=True)
        o += 1
    if storagetype == "SEEK":
        study_search_query = (
            "curl -X GET \"" + storage +
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
                study_title = study_name
                project_search_query = (
                    "curl -X GET \"" + storage +
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
                        "curl -X GET \"" + storage + "/projects/" +
                        str(p) + "\" -H \"accept: application/json\""
                    )
                    json_project = subprocess.Popen([project_id_query], stdout=subprocess.PIPE,
                                                    shell=True).communicate()[0].decode()
                    project = json.loads(json_project)
                    for ps in range(0, len(project["data"]["relationships"]["studies"]["data"])):
                        if studyid == project["data"]["relationships"]["studies"]["data"][ps]["id"]:
                            projectid = str(p)
                if column == 1:
                    assay_title = (study_title + "__result__" + str(resultid))
                    create_assay(
                        username, password, storage, 1, projectid, studyid, assay_title,
                        "Results for ID: " + str(resultid),
                        "http://jermontology.org/ontology/JERMOntology#Experimental_assay_type",
                        "http://jermontology.org/ontology/JERMOntology#Technology_type", assay_title
                    )
                assay_search_query = (
                    "curl -X GET \"" + storage + "/assays\" -H \"accept: application/json\""
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
                        username, password, storage, galaxyfile,
                        username + "/" + galaxyfile,
                        str(galaxyfile), content_type, 1, projectid,
                        str(max(assay_id_list)), workflowid
                    )


def ga_store_results(username, password, workflowid, storage,
                     resultid, groups, investigations):
    """Store information about the used Galaxy workflow.

    Arguments:
        username: Username used for the storage location.
        password: Password used for the storage location.
        workflowid: The ID of the workflow used for analysis.
        storage: The URL for the storage location
        resultid: The result ID.
        groups: A list of studies.
        investigations: A list of investigations.
    """
    for filename in os.listdir(username + "/"):
        if ".ga" in filename:
            new_name = sha1sum(username + "/" + filename) + "_" + filename
            os.rename(username + "/" + filename, username + "/" + new_name)
            for i in investigations:
                for g in groups:
                    call([
                        "curl -s -k -u " + username + ":" + password + " -T " +
                        username + "/" + new_name + " " + storage + "/" +
                        i.replace('"', '') + "/" + g.replace('"', '') +
                        "/results_" + str(resultid) + "/" + new_name
                    ], shell=True)
                    call([
                        "curl http://127.0.0.1:3030/ds/update -X POST --data "
                        "'update=INSERT DATA { "
                        "GRAPH <http://127.0.0.1:3030/ds/data/" +
                        username.replace('@', '') +
                        "> { <http://127.0.0.1:3030/" + str(resultid) +
                        "> <http://127.0.0.1:3030/ds/data?graph=" +
                        username.replace('@', '') + "#workflow> \"" +
                        username + "/" + new_name +
                        "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                    ], shell=True)
                    call([
                        "curl http://127.0.0.1:3030/ds/update -X POST --data "
                        "'update=INSERT DATA { "
                        "GRAPH <http://127.0.0.1:3030/ds/data/" +
                        username.replace('@', '') +
                        "> { <http://127.0.0.1:3030/" + str(resultid) +
                        "> <http://127.0.0.1:3030/ds/data?graph=" +
                        username.replace('@', '') + "#workflowid> \"" +
                        workflowid +
                        "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                    ], shell=True)


def ug_store_results(gi, galaxyemail, galaxypass, server, workflowid,
                     username, password, storage, groups,
                     investigations, date, historyid):
    """Store results that have been generated 
    without the use of a Galaxy workflow

    Arguments:
        gi: The Galaxy instance.
        galaxyemail: The Galaxy email address.
        galaxypass: The Galaxy passaword
        server: The Galaxy server URL.
        workflowid: The Galaxy workflow ID.
        username: Username used for the storage location.
        password: Password used for the storage location.
        storage: The URL for the storage location
        groups: A list of studies.
        investigations: A list of investigations.
        date: The current date and time.
        historyid: The Galaaxy history ID.
    """
    resultid = uuid.uuid1()
    outputs = get_output(galaxyemail, galaxypass, server)
    n = 0
    for iname in outputs[1]:
        cont = subprocess.Popen([
            "curl -s -k " + server + outputs[0][n]
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        old_name = date + "_" + iname
        with open(username + "/" + old_name, "w") as inputfile:
            inputfile.write(cont)
        new_name = sha1sum(username + "/" + old_name) + "_" + old_name
        os.rename(username + "/" + old_name, username + "/" + new_name)
        time.sleep(5)
        # export = gi.histories.export_history(
        #         historyid,
        #         include_deleted=False,
        #         include_hidden=True)
        # home = str(Path.home()) + "/"
        # call(["touch", home + username + "/" + historyid + ".tar"])
        # f = open(home + username + "/" + historyid + ".tar", 'rb+')
        # gi.histories.download_history(
        #     historyid,
        #     export,
        #     f)
        # shaname = sha1sum(f.name) + "_" + f.name.split('/')[-1]
        # os.rename(f.name, home + username + "/" +
        #           strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname)
        # history_tar = strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname
        for i in investigations:
            for g in groups:
                call([
                    "curl -s -k -u " + username + ":" + password +
                    " -X MKCOL " + storage + "/" + i.replace(
                        '"', '') + "/" + g.replace('"', '') + "/results_" +
                    str(resultid)
                ], shell=True)
                call([
                    "curl -s -k -u " + username + ":" + password + " -T " +
                    username + "/" + new_name + " " + storage + "/" +
                    i.replace('"', '') + "/" + g.replace('"', '') +
                    "/results_" + str(resultid) + "/" + new_name + " "
                ], shell=True)
                # call([
                #     "curl -s -k -u " + username + ":" + password + " -T " +
                #     username + "/" + new_name + " " + storage + "/" +
                #     i.replace('"', '') + "/" + g.replace('"', '') +
                #     "/results_" + str(resultid) + "/" + history_tar + " "
                # ], shell=True)
                call([
                    "curl http://127.0.0.1:3030/ds/update -X POST --data "
                    "'update=INSERT DATA { "
                    "GRAPH <http://127.0.0.1:3030/ds/data/" +
                    username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                    str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                    username.replace('@', '') + "#pid> \"" + storage + "/" +
                    i.replace('"', '') + "/" + g.replace('"', '') +
                    "/results_" + str(resultid) + "/" + new_name +
                    " \" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                ], shell=True)
                call([
                    "curl http://127.0.0.1:3030/ds/update -X POST --data "
                    "'update=INSERT DATA { "
                    "GRAPH <http://127.0.0.1:3030/ds/data/" +
                    username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                    str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                    username.replace('@', '') + "#results_id> \"" +
                    str(resultid) + "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                ], shell=True)
                call([
                    "curl http://127.0.0.1:3030/ds/update -X POST --data "
                    "'update=INSERT DATA { "
                    "GRAPH <http://127.0.0.1:3030/ds/data/" +
                    username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                    str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                    username.replace('@', '') + "#historyid> \"" +
                    str(historyid) +
                    "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                ], shell=True)
                call([
                    "curl http://127.0.0.1:3030/ds/update -X POST --data "
                    "'update=INSERT DATA { "
                    "GRAPH <http://127.0.0.1:3030/ds/data/" +
                    username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                    str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                    username.replace('@', '') + "#group_id> \"" +
                    g.replace('"', '') +
                    "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                ], shell=True)
                call([
                    "curl http://127.0.0.1:3030/ds/update -X POST --data "
                    "'update=INSERT DATA { "
                    "GRAPH <http://127.0.0.1:3030/ds/data/" +
                    username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                    str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                    username.replace('@', '') +
                    "#workflow> \"No Workflow used\" } }' "
                    "-H 'Accept: text/plain,*/*;q=0.9'"
                ], shell=True)
                call([
                    "curl http://127.0.0.1:3030/ds/update -X POST --data "
                    "'update=INSERT DATA { "
                    "GRAPH <http://127.0.0.1:3030/ds/data/" +
                    username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                    str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                    username.replace('@', '') + "#workflowid> \"" +
                    workflowid + "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                ], shell=True)
                call([
                    "curl http://127.0.0.1:3030/ds/update -X POST --data "
                    "'update=INSERT DATA { "
                    "GRAPH <http://127.0.0.1:3030/ds/data/" +
                    username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                    str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                    username.replace('@', '') + "#investigation_id> \"" +
                    i.replace('"', '') +
                    "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                ], shell=True)
                call([
                    "curl http://127.0.0.1:3030/ds/update -X POST --data "
                    "'update=INSERT DATA { "
                    "GRAPH <http://127.0.0.1:3030/ds/data/" +
                    username.replace('@', '') + "> { <http://127.0.0.1:3030/" +
                    str(resultid) + "> <http://127.0.0.1:3030/ds/data?graph=" +
                    username.replace('@', '') + "#date> \"" + date +
                    "\" } }' -H 'Accept: text/plain,*/*;q=0.9'"
                ], shell=True)
        call(["rm", username + "/" + new_name])
        call(["rm", username + "/" + old_name])
        n += 1


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
    password = request.session.get('password')
    storage = request.session.get('storage')
    inputs = {}
    out = {}
    result = ""
    workflow = []
    resid = 0
    wf = False
    if request.method == 'POST':
        request.session['stored_results'] = request.POST
        return render_to_response('results.html', context={'outputs': out})
    else:
        if username is not None:
            old_post = request.session.get('stored_results')
            investigations = old_post['investigations']
            group = old_post['group']
            group = group.split(',')
            resultid = old_post['resultid']
            resultid = resultid.split(',')
            if request.session.get('storage_type') == "SEEK":
                resultid = resultid[0].replace('"', '').strip("[").strip("]")
                results = get_seek_result(storage, resultid)
                for rid, rname in results.items():
                    if "_input_" in rname:
                        inputs[rid] = rname
                    elif ".ga" in rname:
                        call(
                            [
                                "wget -O " + username + "/workflow.ga " +
                                storage + "/data_files/" + rid +
                                "/download?version=1"
                            ], shell=True
                        )
                        workflow = read_workflow(username + "/workflow.ga")
                        out[rid] = rname
                        get_file_cmd = (
                            "curl -X GET \"" + storage + "/data_files/" + rid + "\" -H \"accept: application/json\"")
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
                    myplots = {}
                    for outputid, outputname in out.items():
                        if ".ga" not in outputname:
                            format = "tabular"
                            if format == "tabular":
                                call(
                                    [
                                        "wget -O " + username + "/" + outputname + " " +
                                        storage + "/data_files/" + outputid +
                                        "/download?version=1"
                                    ], shell=True
                                )
                                filename = username + "/" + outputname
                                values = []
                                pielabels = []
                                with open(filename) as data_file_test:
                                    headers = data_file_test.readline().split('\t')
                                    if len(headers) > 1:
                                        for line in data_file_test:
                                            line = line.strip('\n')
                                            values.append(line.split('\t'))
                                            pielabels.append(line.split('\t')[-1])
                                        uniquepielabels = list(set(pielabels))
                                        sortedvalues = sorted(pielabels)
                                        pievalues = [len(list(group)) for key, group in groupby(sortedvalues)]
                                        # colors = ['#21317f', '#e7f3ff']
                                        colors = []
                                        def r(): return random.randint(200, 255)
                                        for dummyx in range(len(uniquepielabels)):
                                            colors.append(('#%02X%02X%02X' % (r(), r(), r())))
                                        pietrace = go.Pie(
                                            labels=uniquepielabels,
                                            values=pievalues,
                                            hoverinfo='label+percent',
                                            textinfo='value',
                                            textfont=dict(size=20),
                                            marker=dict(colors=colors,
                                                        line=dict(color='#000000', width=2)))
                                        trace = go.Table(
                                            columnorder=list(range(len(headers))),
                                            header=dict(
                                                values=headers,
                                                fill = dict(color = '#21317f'),
                                                align = ['center'] * 5,
                                                font = dict(color = 'white', size = 14)),
                                            cells=dict(
                                                values=list(map(list, zip(*values))),
                                                fill = dict(color = '#e7f3ff'),
                                                align = ['center'] * 5,
                                                font = dict(color = '#21317f', size = 14)))
                                        cmd = ['xrandr']
                                        cmd2 = ['grep', '*']
                                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                                        p2 = subprocess.Popen(cmd2, stdin=p.stdout, stdout=subprocess.PIPE)
                                        p.stdout.close()
                                        resolution_string, dummyjunk = p2.communicate()
                                        resolution = resolution_string.split()[0].decode()
                                        width, dummyheight = resolution.split('x')
                                        layout = dict(
                                            width=int(width)-500,
                                            height=500,
                                            paper_bgcolor='rgba(0,0,0,0)',
                                            plot_bgcolor='rgba(0,0,0,0)'
                                        )
                                        data = [trace]
                                        piedata = [pietrace]
                                        fig = go.Figure(data=data, layout=layout)
                                        piefig = go.Figure(data=piedata, layout=layout)
                                        config = {
                                            "showLink": False,
                                            "displaylogo": False,
                                            'modeBarButtonsToRemove': ['pan2d','lasso2d']
                                            }
                                        # fig = dict(data=data, layout=layout)
                                        myplots[outputname] = (plotly.offline.plot(fig, output_type='div', config=config))
                                        myplots["pie_" + outputname] = (plotly.offline.plot(piefig, output_type='div', config=config))
                                call(["rm " + username + "/" + outputname], shell=True)
                return render(request, 'results.html', context={
                    'storagetype': request.session.get('storage_type'),
                    'inputs': inputs,
                    'outputs': out,
                    'workflow': workflow,
                    'storage': storage,
                    'resultid': resultid,
                    'workflowid': wid,
                    'plots': myplots})
            else:
                result = get_results(group, resultid, investigations,
                                     username, password, storage)
                cid = 0
                for r in result:
                    if ".ga" in r:
                        wf = True
                        nres = r.split('/')
                        cont = subprocess.Popen([
                            "curl -s -k -u " + username + ":" + password + " " +
                            storage + "/" + nres[len(nres) - 4] + "/" +
                            nres[len(nres) - 3] + "/" + nres[len(nres) - 2] + "/" +
                            nres[len(nres) - 1]
                        ], stdout=subprocess.PIPE, shell=True
                        ).communicate()[0].decode()
                        with open(username + "/" + nres[len(nres)-1], "w") as ga:
                            ga.write(cont)
                        workflow = read_workflow(ga.name)
                        workflowid = subprocess.Popen([
                            "curl -s -k http://127.0.0.1:3030/ds/query -X POST "
                            "--data 'query=SELECT DISTINCT ?workflowid FROM "
                            "<http://127.0.0.1:3030/ds/data/" +
                            username.replace('@', '') +
                            "> { VALUES (?workflow) {(\"" + ga.name +
                            "\")}{ ?s <http://127.0.0.1:3030/ds/data?graph=" +
                            username.replace(
                                '@', '') + "#workflowid> "
                            "?workflowid . ?s "
                            "<http://127.0.0.1:3030/ds/data?graph=" +
                            username.replace('@', '') +
                            "#workflow> ?workflow . } "
                            "} ORDER BY (?workflowid)' -H "
                            "'Accept: application/sparql-results+json,*/*;q=0.9'"
                        ], stdout=subprocess.PIPE, shell=True
                        ).communicate()[0].decode()
                        wid = json.dumps(workflowid)
                        wfid = json.loads(workflowid)
                        wid = json.dumps(
                            (wfid["results"]["bindings"]
                             [0]["workflowid"]["value"])
                        )
                    if not wf:
                        wid = "0"
                    if "input_" in r:
                        nres = r.split('/')
                        if nres[len(nres)-1] != "":
                            inputs[str(cid)] = nres[len(nres)-1]
                            cid += 1
                    else:
                        nres = r.split('/')
                        if nres[len(nres)-1] != "":
                            out[str(cid)] = nres[len(nres)-1]
                            cid += 1
                    if investigation == "-":
                        resid = nres[len(nres)-3] + "/" + nres[len(nres)-2]
                    else:
                        try:
                            resid = (nres[len(nres)-4] + "/" +
                                     nres[len(nres)-3] + "/" + nres[len(nres)-2])
                        except IndexError:
                            pass
                return render(request, 'results.html', context={
                    'storagetype': request.session.get('storage_type'),
                    'inputs': inputs,
                    'outputs': out,
                    'workflow': workflow,
                    'storage': storage,
                    'resultid': resid,
                    'workflowid': wid})
        else:
            return HttpResponseRedirect(reverse('index'))


def get_results(group, resultid, investigations, username, password, storage):
    """Gets the result selected by the user.

    Arguments:
        group: The group ID of the selected result.
        resultid: The result ID of the selected result.
        investigations: List of investigation(s) of the 
        selected result
        username: The username of the logged in user.
        password: Password of the logged in user.
        storage: The file location of the selected result.

    Returns:
        A list of all files and folders of the selected result.
    """
    groups = []
    results = []
    for g in group:
        groups.append(
            g.replace('[', '').replace('"', '').replace(']', ''))
    for r in resultid:
        results.append(
            r.replace('[', '').replace('"', '').replace(']', ''))
    for invest in investigations.split(','):
        investigation = invest.replace(
            '[', '').replace('"', '').replace(']', '')
        for group in groups:
            if investigation != "-":
                oc_folders = subprocess.Popen([
                    "curl -s -X PROPFIND -u " + username + ":" +
                    password + " '" + storage + '/' + investigation +
                    '/' + group +
                    "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
                ], stdout=subprocess.PIPE, shell=True
                ).communicate()[0].decode().split("\n")
            else:
                oc_folders = subprocess.Popen([
                    "curl -s -X PROPFIND -u " + username + ":" +
                    password + " '" + storage + '/' + group +
                    "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
                ], stdout=subprocess.PIPE, shell=True
                ).communicate()[0].decode().split("\n")
            oc_folders = list(filter(None, oc_folders))
            for folder in oc_folders:
                if "results_" in folder:
                    if investigation != "-":
                        result = subprocess.Popen([
                            "curl -s -X PROPFIND -u " +
                            username + ":" + password + " '" +
                            storage + '/' + investigation + '/' +
                            group + '/' + 'results_' + results[0] +
                            "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
                        ], stdout=subprocess.PIPE, shell=True
                        ).communicate()[0].decode().split("\n")
                    else:
                        result = subprocess.Popen([
                            "curl -s -X PROPFIND -u " +
                            username + ":" + password + " '" +
                            storage + '/' + group + '/' +
                            'results_' + results[0] +
                            "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
                        ], stdout=subprocess.PIPE, shell=True
                        ).communicate()[0].decode().split("\n")
    return result


def get_seek_result(storage, assay):
    """Get the results based on the SEEK assay name.
    Returns data file IDs and titles to show in the result page.
    
    Arguments:
        storage: SEEK URL
        assay: Name of the assay where the result is stored.
    
    Returns:
        A Dictionary with data IDs and titles.
    """
    assay = assay.strip("[").strip("]")
    get_assays_cmd = ("curl -X GET \"" + storage +
                      "\"/assays -H \"accept: application/json\"")
    all_assays = subprocess.Popen(
        [get_assays_cmd],
        stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    json_assays = json.loads(all_assays)
    fileidlist = []
    results = {}
    for ar in range(0, len(json_assays["data"])):
        if json_assays["data"][ar]["attributes"]["title"] == assay:
            assayid = json_assays["data"][ar]["id"]
    get_assay_cmd = ("curl -X GET \"" + storage + "\"/assays/" +
                     assayid + " -H \"accept: application/json\"")
    selected_assay = subprocess.Popen(
        [get_assay_cmd],
        stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    json_assay = json.loads(selected_assay)
    for df in range(0, len(json_assay["data"]["relationships"]["data_files"]["data"])):
        fileidlist.append(
            json_assay["data"]["relationships"]["data_files"]["data"][df]["id"])
    for fileid in fileidlist:
        get_file_cmd = ("curl -X GET \"" + storage + "\"/data_files/" +
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
        historyid = get_history_id(galaxyemail, galaxypass, server)
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


@csrf_exempt
def import_galaxy_history(request):
    """Download the Galaxy history .tar file from the storage location.

    Arguments:
        request: Request data to download the Galaxy history.
    """
    username = request.session.get("username")
    password = request.session.get("password")
    tar = request.POST.get("tar")
    resultid = request.POST.get("resultid").strip("\n")
    call([
        "curl -s -k -u " + username + ":" + password + " " +
        request.session.get("storage") + "/" + resultid + "/" + tar +
        " --output " + str(Path.home()) + "/" + username + "/" + tar
    ], shell=True)
    return HttpResponseRedirect(reverse("results"))


@csrf_exempt
def store_history(request):
    """Store the results from the Galaxy history to the 
    storage location and add the information to the triple store.

    Arguments:
        request: A request to receive information to store an existing
        Galaxy history.
    """
    if request.session.get('galaxyemail') is None:
        return HttpResponseRedirect(reverse("index"))
    else:
        server = request.POST.get('server')
        gi = GalaxyInstance(url=server,
                            email=request.session.get("galaxyemail"),
                            password=request.session.get("galaxypass"))
        home = str(Path.home()) + "/"
        username = request.POST.get('username')
        password = request.POST.get('password')
        storage = request.POST.get('storage')
        groups = request.POST.get('folder')
        investigation = request.POST.get('inv')
        date = format(datetime.now() + timedelta(hours=2))
        url = []
        names = []
        resultid = uuid.uuid1()
        if request.method == 'POST':
            if request.session.get('storagetype') == "SEEK":
                pass
            else:
                historyid = request.POST.get('history')
                inputs = []
                input_ids = []
                output = []
                hist = gi.histories.show_history(historyid,
                                                contents='all')
                export = gi.histories.export_history(
                    historyid,
                    include_deleted=False,
                    include_hidden=True)
                call(["touch", home + username + "/" + historyid + ".tar"])
                f = open(home + username + "/" + historyid + ".tar", 'rb+')
                gi.histories.download_history(
                    historyid,
                    export,
                    f)
                shaname = sha1sum(f.name) + "_" + f.name.split('/')[-1]
                os.rename(f.name, home + username + "/" +
                        date + "_" + shaname)
                url.append(date + "_" + shaname)
                state = hist['state_ids']
                dump = json.dumps(state)
                status = json.loads(dump)
                files = status['ok']
                for o in files:
                    oug = gi.datasets.show_dataset(
                        o, deleted=False, hda_ldda='hda')
                    if "input_" in oug['name']:
                        if oug['visible']:
                            url.append(server + oug['download_url'])
                            names.append(oug['name'])
                        inputs.append(oug['id'])
                    else:
                        if oug['visible']:
                            url.append(server + oug['download_url'])
                            names.append(oug['name'])
                        output.append(oug)
                for i in inputs:
                    iug = gi.datasets.show_dataset(
                        i, deleted=False, hda_ldda='hda')
                    input_ids.append(iug)
                count = 0
                for u in url:
                    if server in u:
                        cont = subprocess.Popen([
                            "curl -s -k " + u
                        ], stdout=subprocess.PIPE, shell=True
                        ).communicate()[0].decode()
                        old_name = date + "_" + names[count].replace('/', '_').replace(' ', '_')
                        with open(username + "/" + old_name, "w") as newfile:
                            newfile.write(cont)
                        new_name = sha1sum(newfile.name) + "_" + old_name
                        os.rename(username + "/" + old_name, username +
                                "/" + new_name)
                        count += 1
                    else:
                        new_name = u
                    for g in groups.split(','):
                        pid = (storage + "/" + g.replace('"', '') +
                            "/results_" + str(resultid) + "/" + new_name)
                        call([
                            "curl -s -k -u " + username + ":" + password +
                            " -X MKCOL " + storage + "/" + investigation + "/" +
                            g.replace('"', '') + "/results_" + str(resultid)
                        ], shell=True)
                        call([
                            "curl -s -k -u " + username + ":" + password + " -T " +
                            '\'' + username + "/" + new_name + '\'' + " " +
                            storage + "/" + investigation + "/" +
                            g.replace('"', '') + "/results_" + str(resultid) +
                            "/" + new_name
                        ], shell=True)
                        call([
                            "bash ~/myFAIR/static/bash/triples_history.sh "
                            "-t1 -u " + username.replace('@', '') + " -r " +
                            str(resultid) + " -p " + pid + " -s " +
                            g.replace('"', '') + " -i " + investigation + " -d " +
                            date + " -w " + hist["name"] + " -e 0 -g " +
                            str(historyid)
                        ], shell=True, stdout=subprocess.PIPE)
                    call(["rm", username + "/" + new_name])
                call(["rm", home + username + "/" + shaname])
                return HttpResponseRedirect(reverse('index'))


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


def rerun_seek(gi, storage, resultid, galaxyemail, galaxypass, ftp,
               username, history_id):
    """Upload input files from a previous run to the Galaxy server.
    Get the JSON data from the Galaxy workflow file and return this to
    the rerun function to import the workflow.

    Arguments:
        gi: The Galaxy instance.
        storage: SEEK URL to search an download the data files.
        resultid: The ID of the result to rerun.
        galaxyemail: Email address used for Galaxy login.
        galaxypass: Password used in Galaxy.
        ftp: The Galaxy server's FTP address.
        username: The username used when logged in to myFAIR.
        history_id: The Galaxy history ID.

    Returns:
        A JSON string of the Galaxy workflow file.
    
    Raises:
        CalledProcessError: An error occurred when uploading data 
        to the Galaxy server using the FTP address.
    """
    df_id_list = []
    uploaded_files = []
    gacont = None
    get_assays = (
        "curl -X GET \"" +
        storage + "/assays\" "
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
        storage + "/assays/" + str(aid) + "\" "
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
            storage + "/data_files/" + str(did) + "\" "
            "-H \"accept: application/json\""
        )
        data_file = subprocess.Popen(
            [get_data_file], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode()
        json_result_data = json.loads(data_file)
        if "input_" in json_result_data["data"]["attributes"]["title"]:
            dataid = json_result_data["data"]["id"]
            filename = (json_result_data["data"]["attributes"]
                        ["content_blobs"][0]["original_filename"])
            call(
                [
                    "wget -O " + username + "/" + filename + " " +
                    storage + "/data_files/" + dataid + "/download"
                ], shell=True
            )
            check_call([
                "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                " -e \"put " + username + "/" + filename + "; bye\""], shell=True)
            gi.tools.upload_from_ftp(
                filename, history_id, file_type="auto", dbkey="?")
            uploaded_files.append(filename)
            call(["rm", username + "/" + filename])
        if ".ga" in json_result_data["data"]["attributes"]["title"]:
            workflowfileid = json_result_data["data"]["id"]
            gacont = subprocess.Popen(
                ["curl -s -k " + storage + "/data_files/" +
                    workflowfileid + "/download"],
                stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
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
    return gacont


def rerun_seek_workflow(request, gi, workflowid, history_id, gacont):
    """Start the Galaxy workflow after uploading the data files to the 
    Galaxy server. 
    
    FIXME: Workflow fails in Galaxy. Files will upload correctly but 
    workflow does not finish.

    Arguments:
        request: Request information from the rerun_analysis function.
        gi: Galaxy instance of the logged in user.
        workflowid: ID of the workflow used in this analysis.
        history_id: ID of the new Galaxy history.
        gacont: JSON content of the workflow used in the analysis.

    Raises:
        IndexError: An error occurred when searching ffor the input name labels
        in the Galaxy workflow file.
    """
    with open(request.session.get('username') + "/workflow.ga", 'w') as gafile:
        json_ga = json.loads(gacont)
        for i, dummyj in json_ga.items():
            if i == 'name':
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
            datasets = get_input_data(
                request.session.get('galaxyemail'),
                request.session.get('galaxypass'),
                request.session.get('server'))[0]
            for dname, did in datasets.items():
                if k in dname:
                    datamap[v] = {'src': "hda", 'id': did}
        gi.workflows.run_workflow(
            newworkflowid, datamap, history_id=history_id)
        gi.workflows.delete_workflow(newworkflowid)
        call(["rm", gafile.name])


def rerun_owncloud(request, gi, urls, ftp, history_id):
    """Gets the data from a owncloud/nextcloud location to 
    rerun an analysis.

    Arguments:
        request: Request information from the rerun_analysis function.
        gi: Galaxy Instance of the current user.
        urls: List of input file URLs
        ftp: The FTP URL to upload data to the Galaxy server.
        history_id: The Galaxy history ID to upload data to.
    
    Returns:
        A Galaxy workflow file.
    
    Raises:
        CalledProcessError: An error occurred when uploading data 
        to the Galaxy server using the FTP address.
    """
    uploaded_files = []
    for url in urls:
        cont = subprocess.Popen([
            "curl -s -u " + request.session.get('username') + ":" +
            request.session.get('password') + " " +
            request.session.get('storage') + "/" + url
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        filename = url.split('/')
        with open(
            request.session.get('username') + "/" +
            filename[len(filename)-1], "w"
        ) as infile:
            infile.write(cont)
        check_call([
            "lftp -u " + request.session.get('galaxyemail') + ":" + 
            request.session.get('galaxypass') + " " + ftp +
            " -e \"put " + infile.name + "; bye\""], shell=True)
        gi.tools.upload_from_ftp(
            infile.name.split("/")[-1],
            history_id,
            file_type="auto",
            dbkey="?"
        )
        uploaded_files.append(infile.name.split("/")[-1])
        call(["rm", infile.name])
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
                        "lftp -u " + request.session.get('galaxyemail') + ":" +
                        request.session.get('galaxypass') + " " + ftp +
                        " -e \"rm -r " + uf + "; bye\""
                    ], shell=True)
                except subprocess.CalledProcessError:
                    pass
            break
    folderurl = ""
    for i in range(len(filename)-1):
        folderurl += (filename[i] + "/")
    oc_folders = subprocess.Popen([
        "curl -s -X PROPFIND -u " + request.session.get('username') + ":" +
        request.session.get('password') + " '" +
        request.session.get('storage') + "/" + folderurl +
        "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
    ], stdout=subprocess.PIPE, shell=True
    ).communicate()[0].decode().split("\n")
    for f in oc_folders:
        if ".ga" in f:
            if "/owncloud/" in request.session.get('storage'):
                ga = f.replace('/owncloud/remote.php/webdav/', '')
            else:
                ga = f.replace('/remote.php/webdav/', '')
            gacont = subprocess.Popen([
                "curl -s -u " + request.session.get('username') + ":" +
                request.session.get('password') + " " +
                request.session.get('storage') + "/" + ga
            ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            ga = ga.split('/')
            with open(request.session.get('username') + "/" +
                      ga[len(ga)-1], "w") as gafile:
                json_ga = json.loads(gacont)
                for i, dummyj in json_ga.items():
                    if i == 'name':
                        json_ga[i] = 'TEMP_WORKFLOW'
                json.dump(json_ga, gafile, indent=2)
    return gafile


def rerun_owncloud_workflow(request, gi, gafile, history_id):
    """Start a Galaxy workflow when using owncloud/nextcloud as a 
    storage location when rerunning a previous analysis.
    
    Arguments:
        gi: Galaxy Instance of the current logged in user.
        gafile: The Galaxy workflow file to import into 
        the Galaxy server
    
    Raises:
        IndexError: An error occurred searching for the input names
        in the Galaxy workflow file.
    """
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
        datasets = get_input_data(
            request.session.get('galaxyemail'),
            request.session.get('galaxypass'),
            request.session.get('server')
        )[0]
        for dname, did in datasets.items():
            if k in dname:
                datamap[v] = {'src': "hda", 'id': did}
    gi.workflows.run_workflow(
        newworkflowid,
        datamap,
        history_id=history_id
    )
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
    if "bioinf-galaxian" in ftp:
        ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
    gi.histories.create_history(name=request.POST.get('resultid'))
    history_id = get_history_id(
        request.session.get('galaxyemail'),
        request.session.get('galaxypass'),
        request.session.get('server')
    )
    if request.session.get('storage_type') == "SEEK":
        gacont = rerun_seek(
            gi,
            request.session.get('storage'),
            request.POST.get('resultid'),
            request.session.get("galaxyemail"),
            request.session.get("galaxypass"),
            ftp,
            request.session.get('username'),
            history_id
        )
        if workflowid != "0":
            rerun_seek_workflow(
                request,
                gi,
                workflowid,
                history_id,
                gacont
            )
    else:
        gafile = rerun_owncloud(
            request,
            gi,
            urls,
            ftp,
            history_id
        )
        if workflowid != "0":
            rerun_owncloud_workflow(
                request,
                gi,
                gafile,
                history_id
            )
    return HttpResponseRedirect(reverse("index"))


@csrf_exempt
def onto(disgenet, edam):
    """Find ontology URLs based on tagged data when indexing.

    Arguments:
        disgenet: Name of the DisGeNet disease entered when indexing.
        edam: Name of the EDAM method enetered when indexing.

    Returns:
        The DisGeNET and EDAM URIs found based on the search query.

    Raises:
        IndexError, ValueError: Could not find any DisGeNET or EDAM records.
    """
    disgenet = disgenet.replace(' ', '+').replace("'", "%27")
    edam = edam.replace(' ', '+').replace("'", "%27")
    disid = subprocess.Popen([
        "curl -s -k http://127.0.0.1:3030/ds/query -X POST --data "
        "'query=PREFIX+rdf%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F1999%2F02"
        "%2F22-rdf-syntax-ns%23%3E%0APREFIX+dcterms%3A+%3Chttp%3A%2F%2F"
        "purl.org%2Fdc%2Fterms%2F%3E%0APREFIX+ncit%3A+%3C"
        "http%3A%2F%2Fncicb.nci.nih.gov%2Fxml%2F"
        "owl%2FEVS%2FThesaurus.owl%23%3E%0A"
        "SELECT+DISTINCT+%0A%09%3Fdisease+%0AFROM+%3Chttp%3A%2F%2F"
        "rdf.disgenet.org%3E+%0AWHERE+%7B%0A++"
        "SERVICE+%3Chttp%3A%2F%2Frdf.disgenet.org%2Fsparql%2F%3E+%7B%0A++++"
        "%3Fdisease+rdf%3Atype+ncit%3AC7057+%3B%0A++++%09dcterms%3Atitle+%22" +
        disgenet + "%22%40en+.%0A%7D%0A%7D' -H 'Accept: "
        "application/sparql-results+json,*/*;q=0.9'"
    ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    edam_id = subprocess.Popen([
        "curl -s 'https://www.ebi.ac.uk/ols/api/search?q=" + edam +
        "&ontology=edam' 'Accept: application/json'"
    ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    try:
        jdisease = json.loads(disid)
        # umllist = []
        umls = jdisease['results']['bindings'][0]['disease']['value']
    except (IndexError, ValueError):
        umls = "No disgenet record"
    try:
        jedam = json.loads(edam_id)
        eid = jedam['response']['docs'][0]['iri']
    except (IndexError, ValueError):
        eid = "No EDAM record"
    return umls, eid


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
        "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>" +
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>" +
        "PREFIX owl: <http://www.w3.org/2002/07/owl#>" +
        "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>" +
        "PREFIX dcterms: <http://purl.org/dc/terms/>" +
        "PREFIX foaf: <http://xmlns.com/foaf/0.1/>" +
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>" +
        "PREFIX void: <http://rdfs.org/ns/void#>" +
        "PREFIX sio: <http://semanticscience.org/resource/>" +
        "PREFIX ncit: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>" +
        "PREFIX up: <http://purl.uniprot.org/core/>" +
        "PREFIX dcat: <http://www.w3.org/ns/dcat#>" +
        "PREFIX dctypes: <http://purl.org/dc/dcmitype/>" +
        "PREFIX wi: <http://http://purl.org/ontology/wi/core#>" +
        "PREFIX eco: <http://http://purl.obolibrary.org/obo/eco.owl#>" +
        "PREFIX prov: <http://http://http://www.w3.org/ns/prov#>" +
        "PREFIX pav: <http://http://http://purl.org/pav/>" +
        "PREFIX obo: <http://purl.obolibrary.org/obo/>" +
        "SELECT * " +
        "WHERE { SERVICE <http://rdf.disgenet.org/sparql/> { " +
        "?uri dcterms:title ?disease . " +
        "?disease bif:contains \'\"" + disgenet + "\"\' ." + 
        "} " +
        "} LIMIT 30"
    )
    g = rdflib.ConjunctiveGraph('SPARQLStore')
    g.open("http://127.0.0.1:8890/sparql/")
    for row in g.query(sparql_query):
        disgenet_uri[row[0].strip("rdflib.term.URIRef")] = row[1]
    return disgenet_uri
