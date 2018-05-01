import csv
import hashlib
import json
import os
import re
import subprocess
import time
import uuid

from subprocess import call
from subprocess import check_call
from time import strftime, gmtime
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.client import ConnectionError
from django.shortcuts import render_to_response, render, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path


@csrf_exempt
def login(request):
    """Login page where Galaxy server, email address, Galaxy password,
    storage location, username and password are stored in a session.

    Arguments:
        request -- Login details filled in from the login page.
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
        request -- Getting the user details from request.session.
    """

    login(request)
    if (
        'username' not in request.session or
        'galaxypass' not in request.session
    ):
        err = ""
        login(request)
        return render_to_response('login.html', context={
            'error': err})
    else:
        call(["mkdir", request.session.get('username')])
        if request.POST.get('inv') is not None:
            investigation = request.POST.get('inv')
        else:
            investigation = ""
        folders = []
        investigations = []
        if investigation is not None and investigation != "":
            username = request.POST.get('username')
            password = request.POST.get('password')
            storage = request.POST.get('storage')
            server = request.POST.get('server')
            oc_folders, inv_folders = get_study_folders(
                storage, username, password, investigation)
        else:
            username = request.session.get('username')
            password = request.session.get('password')
            storage = request.session.get('storage')
            server = request.session.get('server')
            inv_folders, oc_folders = get_investigation_folders(
                storage, username, password)
        for inv in inv_folders:
            if "/owncloud/" in request.session.get('storage'):
                investigation_name = inv.replace(
                    '/owncloud/remote.php/webdav/', '').replace('/', '')
                if "." not in investigation_name:
                    new = investigation_name
                    investigations.append(new)
            elif "seek" in storage:
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
            elif "seek" in storage:
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
                    request.POST.get("galaxypass"))
            else:
                gusername, workflows, his, dbkeys = get_galaxy_info(
                    request.session.get('server'),
                    request.session.get('galaxyemail'),
                    request.session.get("galaxypass"))
        except Exception:
            request.session.flush()
            return render_to_response('login.html', context={
                'error': 'Credentials incorrect. Please try again'})
        return render(request, 'home.html',
                      context={'workflows': workflows, 'histories': his,
                               'user': gusername, 'username': username,
                               'password': password, 'server': server,
                               'storage': storage,
                               'investigations': investigations,
                               'studies': folders, 'inv': investigation,
                               'dbkeys': dbkeys,
                               'galaxyemail': request.session.get(
                                   'galaxyemail'),
                               'galaxypass': request.session.get(
                                   'galaxypass')})


def get_investigation_folders(storage, username, password):
    """Gets the user's investigation folders from the storage URL,
    This will be shown on the homepage for storing existing Galaxy 
    histories.

    Arguments:
        storage {str} -- The URL of the ISA structure storage.
        username {str} -- The username of the ISA structure storage.
        password {str} -- The password of the ISA structure storage.

    Returns:
        list -- List of investigation folders.
        list -- List of study folders.
    """
    oc_folders = ""
    if "seek" not in storage:
        inv_folders = subprocess.Popen([
            "curl -s -X PROPFIND -u" + username + ":" + password +
            " '" + storage + "/' | grep -oPm250 '(?<=<d:href>)[^<]+'"
        ], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    else:
        inv_folders = []
        seek_investigations = get_seek_investigations(
            username, password, storage)
        for it, ii in seek_investigations.items():
            inv_folders.append(it)
            get_seek_studies(username, password, storage, ii)
    return inv_folders, oc_folders


def get_study_folders(storage, username, password, investigation):
    """Gets the study folders based on the selected investigation from the
    homepage. This is used to store existing Galaxt histories.

    Arguments:
        storage {str} -- The URL of the ISA structure storage.
        username {str} -- The username of the ISA structure storage.
        password {str} -- The password of the ISA structure storage.
        investigation {str} -- Investigation ID

    Returns:
        list -- List of study folders
        list -- List of investigation folders
    """
    if "seek" not in storage:
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
            username, password, storage, investigation)
        oc_folders = []
        for st, dummysi in seek_study.items():
            oc_folders.append(st)
    return oc_folders, inv_folders


def get_galaxy_info(url, email, password):
    """Gets the Galaxy information from the logged in user.

    Arguments:
        url {str} -- The Galaxy server URL.
        email {str} -- The users email address for the Galaxy server.
        password {str} -- The Galaxy server password.

    Returns:
        str -- Galaxy username of the logged in user.
        list -- Available Galaxy workflows.
        list -- List of Galaxy histories from the user's account.
        list -- List of available dbkeys.
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


def get_seek_investigations(username, password, storage):
    """Get all SEEK investigations that the logged in user has access to.

    Arguments:
        username {str} -- The SEEK username.
        password {str} -- The SEEK password.
        storage {str} -- The SEEK URL.

    Returns:
        dict -- Dictionary with investigations and URLs.
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
        username {str} -- The SEEK username.
        password {str} -- The SEEK password.
        storage {str} -- The SEEK URL.
        investigation {str} -- Investigation ID

    Returns:
        dict -- Dictionary with studies and URLs.
    """
    studies = {}
    investigation_id = investigation.split("/")[-1]
    study_titles = subprocess.Popen([
        "curl -s -u \'" + username + "\':" + password + " " + storage +
        "/investigations/" + investigation_id +
        ".xml | grep -e \'study xlink\' | "
        "sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
    ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
    study_titles = study_titles.split("\n")
    study_titles = list(filter(None, study_titles))
    for st in study_titles:
        study_id = subprocess.Popen([
            "curl -s -u \'" + username + "\':" + password +
            " " + storage + "/investigations/" + investigation_id +
            ".xml | grep -e \'" + st +
            "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        if study_id is not None or study_id != '':
            studies[st] = study_id.strip("\n")
    return studies


def get_seek_assays(username, password, storage, study):
    """Gets the SEEK assays based on a study.

    Arguments:
        username {str} -- The SEEK username.
        password {str} -- The SEEK password.
        storage {str} -- The SEEK URL.
        study {str} -- Study ID

    Returns:
        dict -- Dictionary with assay IDs and URLs.
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
        request -- A string with all selected samples that the user wants
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
        request -- A request to get the current session.
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
        request -- A request to get the current session.
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
        if "seek" in request.session.get("storage"):
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
                elif "seek" in request.session.get("storage"):
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
                    if "seek" not in request.session.get('storage'):
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
                    elif "seek" in request.session.get('storage'):
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
        request -- A request to get the current session.
    """
    if request.session.get('username') is not None:
        if "/owncloud/" in request.session.get('storage'):
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
                if "/owncloud/" in request.session.get('storage'):
                    new = oc.replace(
                        '/owncloud/remote.php/webdav/', '').replace('/', '')
                    if "." not in new:
                        folders.append(new)
                elif "seek" in request.session.get('storage'):
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
                if "/owncloud/" in request.session.get('storage'):
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
                    for it, ii in inv_names.items():
                        if it == request.POST.get('folder'):
                            studydict = get_seek_studies(
                                request.session.get('username'),
                                request.session.get('password'),
                                request.session.get('storage'), ii)
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
                        elif "seek" in request.session.get('storage'):
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
        request -- A request to receive all the information that needs
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
        galaxyemail {str} -- The Galaxy email address.
        galaxypass {str} -- The Galaxy password.
        server {str} -- The Galaxy server URL.

    Returns:
        str -- The Galaxy history ID.
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
        galaxyemail {str} -- The Galaxy email address.
        galaxypass {str} -- The Galaxy password.
        server {str} -- The Galaxy server URL.

    Returns:
        list -- Input files from the Galacxy history.
        int -- The amount of input datasets in the history.
    """
    gi = GalaxyInstance(url=server, email=galaxyemail, password=galaxypass)
    history_id = get_history_id(galaxyemail, galaxypass, server)
    hist_contents = gi.histories.show_history(history_id, contents=True)
    inputs = []
    datacount = 0
    datasets = [dataset for dataset in hist_contents if not dataset['deleted']]
    for dataset in datasets:
        inputs.append(dataset['id'])
        datacount += 1
    return inputs, datacount


def createMetadata(request, datafile):
    """Create a metadata file when there is none available.
    Only for GEO data matrices.

    Arguments:
        request -- A request to get the current session.
        datafile {str} -- The GEO data matrix.

    Returns:
        file -- Metadata file created from the GEO data matrix.
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
        iselect {list} -- The Selected investigation names.
        gselect {list} -- The Selected study names.
        select {list} -- The Selected datafiles.
        mselect {list} -- The Selected metadata files.

    Returns:
        list -- List of selected investigations.
        list -- List of selected studies.
        list -- List ofselected datafiles.
        list -- List ofselected metadata files.
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
        gi {GalaxyInstance} -- The Galaxy Instance.
        galaxyemail {str} -- The Galaxy email address.
        galaxypass {str} -- The Galaxy password.
        server {str} -- The Galaxy server URL.
        workflowid {str} -- The Galaxy workflow ID.
        files {list} -- A List of files to upload.
        new_hist {str} -- The new history name.

    Returns:
        str -- A new Galaxy history ID.
    """
    if workflowid != "0":
        if len(list(filter(None, files))) > 0:
            workflow = gi.workflows.show_workflow(workflowid)
            if new_hist is None or new_hist == "":
                new_hist_name = (strftime(workflow['name'] +
                                          "_%d_%b_%Y_%H:%M:%S", gmtime()))
            else:
                new_hist_name = new_hist
            gi.histories.create_history(name=new_hist_name)
            history_id = get_history_id(galaxyemail, galaxypass, server)
        else:
            pass
    else:
        if len(list(filter(None, files))) > 0:
            if new_hist is None or new_hist == "":
                new_hist_name = strftime("Use_Galaxy_%d_%b_%Y_%H:%M:%S",
                                         gmtime())
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
        username {str} -- Username used for the storage location.
        filename {str} -- Name of the file that needs to be split.
        control {str} -- Samples in control group.
        test {str} -- Samples in test group.

    Returns:
        list -- A list with samples in group A.
        list -- A list with samples in group B.
        file -- A File with samples from group A.
        file -- A File with samples from group B.
        file -- The Complete datafile.
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
                    control, test, history_id, filetype, dbkey):
    """Create datafiles and send them to the Galaxy server.

    Arguments:
        gi {GalaxyInstance} -- The Galaxy Instance.
        files {list} -- A list of files to use within Galaxy
        username {str} -- Username used for the storage location.
        password {str} -- Password used for the storage location.
        galaxyemail {str} -- The Galaxy email address.
        galaxypass {str} -- The Galaxy passaword
        control {str} -- Samples in control group.
        test {str} -- Samples in test group.
        history_id {str} -- The Galaxy history ID to send files to.
        filetype {str} -- The filetype option when sending data to Galaxy.
        dbkey {str} -- The genome db to use in Galaxy.
    """
    uploaded_files = []
    # if "bioinf-galaxian" in request.session.get("server"):
    ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
    # else: 
    #     ftp = gi.config.get_config()["ftp_upload_site"]
    for file in files:
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
        time.sleep(20)
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
                check_call([
                    "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                    " -e \"rm -r " + uf + "; bye\""
                ], shell=True)
            break


def split_meta_files(username, metadatafile, control, test):
    """Creates new metadata file when data is split into classes.

    Arguments:
        username {str} -- Username used for the storage location.
        metadatafile {file} -- Metadata file that will be edited.
        control {list} -- Samples in control group
        test {list} -- Samples in test group

    Returns:
        file -- A new metadata file
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
        gi {GalaxyInstance} -- The Galaxy Instance.
        mfiles {files} -- A list of metadata files.
        username {str} -- Username used for the storage location.
        password {str} -- Password used for the storage location.
        galaxyemail {str} -- The Galaxy email address.
        galaxypass {str} -- The Galaxy passaword
        control {str} -- Samples in control group.
        test {str} -- Samples in test group.
        history_id {str} -- The Galaxy history ID to send files to.
    """
    uploaded_files = []
    # ftp = gi.config.get_config()["ftp_upload_site"]
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
        time.sleep(20)
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
                check_call([
                    "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                    " -e \"rm -r " + uf + "; bye\""
                ], shell=True)
            break


@csrf_exempt
def upload(request):
    """Call all function needed to send data and metadata files 
    to the Galaxy server and start the workflow if selected.

    Arguments:
        request {[type]} -- A request to receive information needed to upload
        files to the Galaxy server.
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
    onlydata = request.POST.get('onlydata')
    makecol = request.POST.get('col')
    data_ids = []
    control = request.POST.get('samples')
    test = request.POST.get('samplesb')
    new_hist = request.POST.get('historyname')
    group = request.POST.get('group')
    investigation = request.POST.get('investigation')
    date = strftime("%d_%b_%Y_%H:%M:%S", gmtime())
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
        if onlydata == "true":
            make_data_files(gi, files, request.session.get('username'),
                            request.session.get('password'),
                            request.session.get('galaxyemail'),
                            request.session.get('galaxypass'),
                            control, test, history_id, filetype, dbkey)
        else:
            make_data_files(gi, files, request.session.get('username'),
                            request.session.get('password'),
                            request.session.get('galaxyemail'),
                            request.session.get('galaxypass'),
                            control, test, history_id, filetype, dbkey)
            make_meta_files(gi, mfiles, request.session.get('username'),
                            request.session.get('password'),
                            request.session.get('galaxyemail'),
                            request.session.get('galaxypass'),
                            control, test, history_id)
        if workflowid != "0":
            in_count = 0
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
                    mydict["in%s" % (
                        str(i + 1))] = gi.workflows.get_workflow_inputs(
                            workflowid, label=label)[0]
            for k, v in mydict.items():
                k
                datamap[v] = {'src': "hda", 'id': get_input_data(
                    request.session.get('galaxyemail'),
                    request.session.get('galaxypass'),
                    request.session.get('server')
                )[0][in_count]}
                data_ids.append(get_input_data(
                    request.session.get('galaxyemail'),
                    request.session.get(
                        'galaxypass'),
                    request.session.get('server'))[0][in_count])
                in_count += 1
            if makecol == "true":
                gi.histories.create_dataset_collection(
                    history_id, make_collection(data_ids))
            gi.workflows.invoke_workflow(
                workflowid, datamap, history_id=history_id)
            gi.workflows.export_workflow_to_local_path(
                workflowid,
                request.session.get('username'),
                True)
            datafiles = get_output(request.session.get('galaxyemail'),
                                   request.session.get('galaxypass'),
                                   request.session.get('server'))
            store_results(1, datafiles, request.session.get('server'),
                          request.session.get('username'),
                          request.session.get('password'),
                          request.session.get('storage'),
                          groups, resultid, investigations, date)
            store_results(3, datafiles, request.session.get('server'),
                          request.session.get('username'),
                          request.session.get('password'),
                          request.session.get('storage'),
                          groups, resultid, investigations, date)
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
            if makecol == "true":
                history_data = gi.histories.show_history(
                    history_id, contents=True)
                for c in range(0, len(history_data)):
                    data_ids.append(history_data[c]['id'])
                gi.histories.create_dataset_collection(
                    history_id, make_collection(data_ids))
            ug_store_results(
                request.session.get(
                    'galaxyemail'), request.session.get('galaxypass'),
                request.session.get('server'), workflowid,
                request.session.get(
                    'username'), request.session.get('password'),
                request.session.get('storage'), groups, investigations, date)
            return HttpResponseRedirect(reverse("index"))


def make_collection(data_ids):
    """Create a dataset collection in Galaxy

    Arguments:
        data_ids {list} -- A list of Galaxy dataset IDs

    Returns:
        dict -- A Galaxy data collection.
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


def store_results(column, datafiles, server, username, password,
                  storage, groups, resultid, investigations, date):
    """Store input and output files that where created or used in a 
    Galaxy workflow.

    Arguments:
        column {int} -- Column number containing 1 or 3. 
        1 for data and 3 for metadata.
        datafiles {list} -- A List of datafiles
        server {str} -- The Galaxy server URL.
        username {str} -- Username used for the storage location.
        password {str} -- Password used for the storage location.
        storage {str} -- The URL for the storage location
        groups {list} -- A list of studies.
        resultid {str} -- The result ID. 
        investigations {list} -- A list of investigations.
        date {str} -- The current date and time.
    """
    o = 0
    for name in datafiles[column]:
        cont = subprocess.Popen([
            "curl -s -k " + server + datafiles[column-1][o]
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        old_name = strftime(
            "%d_%b_%Y_%H:%M:%S", gmtime()
        ) + "_" + name.replace('/', '_').replace(' ', '_')
        with open(username + "/" + old_name, "w") as outputfile:
            outputfile.write(cont)
        new_name = sha1sum(username + "/" + old_name) + "_" + old_name
        os.rename(username + "/" + old_name, username + "/" + new_name)
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
        call(["rm", username + "/" + new_name])
        call(["rm", username + "/" + old_name])
        o += 1


def ga_store_results(username, password, workflowid, storage,
                     resultid, groups, investigations):
    """Store information about the used Galaxy workflow.

    Arguments:
        username {str} -- Username used for the storage location.
        password {str} -- Password used for the storage location.
        workflowid {str} -- The ID of the workflow used for analysis.
        storage {str} -- The URL for the storage location
        resultid {str} -- The result ID.
        groups {list} -- A list of studies.
        groups {list} -- A list of investigations.
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
            call(["rm", username + "/" + new_name])


def ug_store_results(galaxyemail, galaxypass, server, workflowid, username,
                     password, storage, groups, investigations, date):
    """Store results that have been generated 
    without the use of a Galaxy workflow

    Arguments:
        galaxyemail {str} -- The Galaxy email address.
        galaxypass {str} -- The Galaxy passaword
        server {str} -- The Galaxy server URL.
        workflowid {str} -- The Galaxy workflow ID.
        username {str} -- Username used for the storage location.
        password {str} -- Password used for the storage location.
        storage {str} -- The URL for the storage location
        groups {list} -- A list of studies.
        investigations {list} -- A list of investigations.
        date {str} -- The current date and time.
    """
    resultid = uuid.uuid1()
    outputs = get_output(galaxyemail, galaxypass, server)
    n = 0
    for iname in outputs[1]:
        cont = subprocess.Popen([
            "curl -s -k " + server + outputs[0][n]
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        old_name = strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + iname
        with open(username + "/" + old_name, "w") as inputfile:
            inputfile.write(cont)
        new_name = sha1sum(username + "/" + old_name) + "_" + old_name
        os.rename(username + "/" + old_name, username + "/" + new_name)
        time.sleep(5)
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
        filename {file} -- Filename to generate sha1 hash.

    Keyword Arguments:
        blocksize {int} -- Used blocksize (default: {65536})

    Returns:
        hash -- The sha1 hash generated from the datafile.
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
        request -- A request to receive the information 
        to show results.
    """
    username = request.session.get('username')
    password = request.session.get('password')
    storage = request.session.get('storage')
    # groups = []
    # results = []
    inputs = []
    out = []
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
            result = get_results(group, resultid, investigations,
                                  username, password, storage)
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
                        username.replace('@', '') + "#workflow> ?workflow . } "
                        "} ORDER BY (?workflowid)' -H "
                        "'Accept: application/sparql-results+json,*/*;q=0.9'"
                    ], stdout=subprocess.PIPE, shell=True
                    ).communicate()[0].decode()
                    wid = json.dumps(workflowid)
                    wfid = json.loads(workflowid)
                    wid = json.dumps(
                        wfid["results"]["bindings"][0]["workflowid"]["value"])
                if not wf:
                    wid = "0"
                if "input_" in r:
                    nres = r.split('/')
                    inputs.append(nres[len(nres)-1])
                else:
                    nres = r.split('/')
                    out.append(nres[len(nres)-1])
                if investigation == "-":
                    resid = nres[len(nres)-3] + "/" + nres[len(nres)-2]
                else:
                    try:
                        resid = (nres[len(nres)-4] + "/" +
                                 nres[len(nres)-3] + "/" + nres[len(nres)-2])
                    except IndexError:
                        pass
                out = list(filter(None, out))
                inputs = list(filter(None, inputs))
            return render(request, 'results.html', context={
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
        group {str} -- The group ID of the selected result.
        resultid {str} -- The result ID of the selected result.
        investigations {list} -- List of investigation(s) of the 
        selected result
        username {str} -- The username of the logged in user.
        password {str} -- Password of the logged in user.
        storage {str} -- The file location of the selected result.
    
    Returns:
        list -- A list of all files and folders of the selected result.
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


def logout(request):
    """Flush the exisiting session with the users login details.

    Arguments:
        request -- Request the session so it can be flushed and the folder
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
        galaxyemail {str} -- The Galaxy email address.
        galaxypass {str} -- The Galaxy password.
        server {str} -- The Galaxy server URL.

    Returns:
        list -- A list with Galaxy inputfile URLs
        list -- A list with Galaxy inputfile names
        list -- A list with galaxy outputfile URLs
        list -- A list with Galaxy outputfile names
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
            time.sleep(20)
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


def import_galaxy_history(username, password, resultid):
    """[summary]
    
    TODO: Create history import functionality.

    Arguments:
        username {[type]} -- [description]
        password {[type]} -- [description]
        resultid {[type]} -- [description]
    """
    pass


@csrf_exempt
def store_history(request):
    """Store the results from the Galaxy history to the 
    storage location and add the information to the triple store.

    Arguments:
        request -- A request to receive information to store an existing
        Galaxy history.
    """
    if request.session.get('galaxyemail') is None:
        return HttpResponseRedirect(reverse("index"))
    else:
        server = request.POST.get('server')
        gi = GalaxyInstance(url=server,
                            email=request.session.get("galaxyemail"),
                            password=request.session.get("galaxypass"))
        home = str(Path.home())+ "/"
        username = request.POST.get('username')
        password = request.POST.get('password')
        storage = request.POST.get('storage')
        groups = request.POST.get('folder')
        investigation = request.POST.get('inv')
        date = strftime("%d_%b_%Y_%H:%M:%S", gmtime())
        url = []
        names = []
        resultid = uuid.uuid1()
        if request.method == 'POST':
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
                      strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname)
            url.append(strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname)
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
                    old_name = strftime(
                        "%d_%b_%Y_%H:%M:%S", gmtime()
                    ) + "_" + names[count].replace('/', '_').replace(' ', '_')
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
            # ug_context = {'outputs': output, 'inputs': input_ids,
                        #   'hist': hist, 'server': server}
            return HttpResponseRedirect(reverse('index'))


def read_workflow(filename):
    """Read workflow file to retrieve the steps within the workflow.

    Arguments:
        filename {str} -- The name of the Galaxy workflow file.

    Returns:
        list -- A list of all the steps used in the workflow.
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


@csrf_exempt
def rerun_analysis(request):
    """Rerun an analysis stored in the triple store.
    Search for a result on the homepage and view the results.
    In the resultspage there is an option to rerun the analysis.

    Arguments:
        request -- A request to receive information to rerun previously
        generated results.
    """
    workflowid = request.POST.get('workflowid')
    workflowid = workflowid.replace('"', '')
    resultid = request.POST.get('resultid')
    gi = GalaxyInstance(url=request.session.get('server'),
                        email=request.session.get('galaxyemail'),
                        password=request.session.get("galaxypass"))
    if "bioinf-galaxian" in request.session.get("server"):
        ftp = "bioinf-galaxian.erasmusmc.nl"
    else: 
        ftp = gi.config.get_config()["ftp_upload_site"]
    galaxyemail = request.session.get("galaxyemail")
    galaxypass = request.session.get("galaxypass")
    uploaded_files = []
    urls = request.POST.get('urls')
    urls = urls.split(',')
    gi.histories.create_history(name=resultid)
    history_id = get_history_id(request.session.get('galaxyemail'),
                                request.session.get('galaxypass'),
                                request.session.get('server'))
    for u in urls:
        filename = u.replace("[", "").replace("]", "").replace(
            " ", "").replace('"', '')
        cont = subprocess.Popen([
            "curl -s -u " + request.session.get('username') + ":" +
            request.session.get('password') + " " +
            request.session.get('storage') + "/" + filename
        ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        file = filename.split('/')
        with open(request.session.get('username') + "/" +
                  file[len(file)-1], "w") as infile:
            infile.write(cont)
        check_call([
            "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
            " -e \"put " + infile.name + "; bye\""], shell=True)
        gi.tools.upload_from_ftp(infile.name.split("/")[-1],
                                 history_id,
                                 file_type="auto", 
                                 dbkey="?")
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
        time.sleep(20)
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
                check_call([
                    "lftp -u " + galaxyemail + ":" + galaxypass + " " + ftp +
                    " -e \"rm -r " + uf + "; bye\""
                ], shell=True)
            break
    oc_folders = subprocess.Popen([
        "curl -s -X PROPFIND -u " + request.session.get('username') + ":" +
        request.session.get('password') + " '" +
        request.session.get('storage') + "/" + resultid +
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
                gafile.write(gacont)
    time.sleep(30)
    if workflowid != "0":
        gi.workflows.import_workflow_from_local_path(gafile.name)
        workflows = gi.workflows.get_workflows(published=False)
        jwf = json.loads(gacont)
        in_count = 0
        datamap = dict()
        mydict = {}
        for workflow in workflows:
            if "API" in workflow["name"]:
                newworkflowid = workflow["id"]
                jsonwf = gi.workflows.export_workflow_json(newworkflowid)
            elif jwf["name"] in workflow["name"]:
                newworkflowid = workflow["id"]
                jsonwf = gi.workflows.export_workflow_json(newworkflowid)
        for i in range(len(jsonwf["steps"])):
            if jsonwf["steps"][str(i)]["name"] == "Input dataset":
                try:
                    label = jsonwf["steps"][str(i)]["inputs"][0]["name"]
                except IndexError:
                    label = jsonwf["steps"][str(i)]["label"]
                mydict["in%s" % (str(i+1))] = gi.workflows.get_workflow_inputs(
                    newworkflowid, label=label
                )[0]
        for dummyk, v in mydict.items():
            datamap[v] = {'src': "hda",
                          'id': get_input_data(
                              request.session.get('galaxyemail'),
                              request.session.get('galaxypass'),
                              request.session.get('server'))[0][in_count]}
            in_count += 1
        gi.workflows.invoke_workflow(
            newworkflowid, datamap, history_id=history_id)
        gi.workflows.delete_workflow(newworkflowid)
        call(["rm", gafile.name])
    return HttpResponseRedirect(reverse("index"))


@csrf_exempt
def onto(disgenet, edam):
    """Find ontology URLs based on tagged data when indexing.

    Arguments:
        disgenet {str} -- Name of the DisGeNet disease entered when indexing.
        edam {str} -- Name of the EDAM method enetered when indexing.

    Returns:
        str -- The DisGeNet URL.
        str -- The EDAM ID.
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
