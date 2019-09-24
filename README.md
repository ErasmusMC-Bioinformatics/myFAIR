# myFAIR

[Dependencies](#dependencies)\
[Installation Instructions](#installation-instructions)\
[Install myFAIR](#install-myfair)\
[Install SEEK](#install-seek)\
[Galaxy](#galaxy)\
[Create a new study](#create-new-study)\
[Create a new assay](#create-new-assay)\
[Upload fies to SEEK](#upload-files-seek)\
[Run myFAIR with SEEK](#run-myfair-seek)\
[Run myFAIR with Omics DI](#run-myfair-omicsdi)\
[See results](#see-results)\
[Store your history](#store-history)\
[Run the analysis again](#rerun-analysis)

For this testcase we are using variant selection by GEMINI analysis using genome in the bottle data. Specifically, we will be using Ashkenazim Father-Mother-Son trio data from the Personal Genome Project. You can download the down sampled version of the dataset created by the GEMINI team from a GIAB trio dataset.
The vcf file can be found [here](https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F8ae2ca084c0c0c70/datasets/e4e82f84348cba8c) and the ped file can be found [here](https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F8ae2ca084c0c0c70/datasets/5e4dbb32432c1676).

## <a name="dependencies">Dependencies</a>

* Python 3.6 or higher
* Django 2.1.10 or higher
* Bioblend 0.11.0 or higer
* rdflib 4.2.2 or higher
* lftp 4.8.1 or higher
* python-magic 0.4.15 or higher
* sparqlwrapper 1.8.2 or higher
* EDAM browser
* An account on a local or external Galaxy server with the following tools available:
    1. GEMINI (load, autosomal recessive/dominant, de novo, comp hets)
    2. Add Column, Strip Header and File Concatenate (all can be found under the name file_manipulation in the Galaxy tool shed)
    3. The Galaxy server should allow an FTP to send data files larger than 2GB.
* An account to an external SEEK server or a local SEEK server.

## <a name="installation-instructions">Installation Instructions</a>

### <a name="install=myfair">Install myFAIR</a>

To install myFAIR on your existing Virtual Machine follow these steps:

#### Install dependencies

```bash
sudo apt update
sudo apt upgrade
sudo apt install python3 python3-pip lftp
pip3 install django bioblend rdflib python-magic sparqlwrapper
```

#### Get myFAIR and EDAM browser

```bash
git clone https://github.com/ErasmusMC-Bioinformatics/myFAIR
git clone https://github.com/IFB-ElixirFr/edam-browser
```

#### Change SEEK and Virtuoso URL

Open settings.py in the myFAIR folder and change the following variables:\
SEEK_URL = "http://127.0.0.1:3000"\
SEEK_JS_URL = SEEK_URL\
VIRTUOSO_URL = "http://127.0.0.1:8890/sparql/"\
VIRTUOSO_JS_URL = VIRTUOSO_URL

#### Run myFAIR

```bash
python3 myFAIR/manage.py runserver 0.0.0.0:8080
```

#### Run EDAM browser

```bash
cd edam-browser
python start_edam_stand_alone_browser.py
```

#### Set permissions

If manage.py does not have the right permissions run the following command:

```bash
chmod +x myFAIR/manage.py
```

#### Test the servers

Go to 127.0.0.1:8080 (or other chosen port) and check if the myFAIR login page is visible.\
Go to 127.0.0.1:20080 to see if the EDAM browser is available.

### <a name="install-seek">Install SEEK</a>

You can download the latest version of SEEK [here](https://github.com/seek4science/seek). For more information on installing SEEK click [here](https://docs.seek4science.org/tech/install.html).\
Follow [these](https://docs.seek4science.org/tech/setting-up-virtuoso.html) instructions to install the Virtuoso triple store and connect the triple store to your SEEK server.

### <a name="galaxy">Galaxy</a>

Go to [usegalaxy](https://usegalaxy.eu) and create an account or log in with an existing account to see if it is still working.

#### Importing the GEMINI workflow

Import the GEMINI workflow using this url: https://usegalaxy.eu/u/rickjansen/w/geminivcfanalysis.

## <a name="isa-structure">ISA structure</a>

### <a name="create-new-study">Create a new study</a>

Follow these steps to create a new study on the SEEK server you entered when logging in.

1. Logon to the myFAIR webpage with your Galaxy and SEEK credentials.
2. Got to the *Upload to SEEK* page.
3. Enter your full name (same as registered in SEEK)
4. Select the project from the dropdown menu.
5. Select the investigation from the dropdown menu.
6. Select the *create new study?* option.
7. Enter a name, title and description for the new study. Click *Create new study*

### <a name="create-new-assay">Create a new assay</a>

Follow these steps to create a new assay on the SEEK server you entered when logging in. This option only works when you have the right permissions to the SEEK study.

1. Logon to the myFAIR webpage with your Galaxy and SEEK credentials.
2. Got to the *Upload to SEEK* page.
3. Enter your full name (same as registered in SEEK)
4. Select the project from the dropdown menu.
5. Select the investigation from the dropdown menu.
6. Select the study from the dropdown menu.
7. Select the *create new assay?* option.
8. Enter a name, title and description for the new assay.
9. Select assay type from the dropdown menu.
10. Select technology type from the dropdown menu.
11. Click on the *Create new assay* button.

## <a name="upload-files-seek">Upload files to SEEK</a>

Follow these steps to upload a data file to an assay on the SEEK server. This option only works when you have the right permissions to the SEEK assay.

1. Logon to the myFAIR webpage with your Galaxy and SEEK credentials.
2. Got to the *Upload to SEEK* page.
3. Enter your full name (same as registered in SEEK)
4. Select the project from the dropdown menu.
5. Select the investigation from the dropdown menu.
6. Select the study from the dropdown menu.
7. Select the assay from the dropdown menu.
8. Enter a data file title and description.
9. Select the file to upload.
10. Tag the data file with a diseas by entering a disease in the DisGeNET textbox and click the *Search* button. Select the disease from the dropdown menu after the search is finished.
11. tag the data file with an EDAM operation by selecting the type of operation from the EDAM browser. Click the *Select this ontology* button to add this ontology.

## <a name="run-myfair-seek">Run myFAIR with SEEK</a>

To run myFAIR with SEEK data you need to follow the Upload files to SEEK steps first or make sure data is already uploaded using the SEEK GUI instead. After uploading the data files you can search the data from the homepage.

You can search the SEEK data based on the investigation, study or assay. You can search in on of the three available textboxes.

Follow the next steps to search for data files linked to an investigation, study or assay:

1. Enter the investigation name in the first textbox or a study name in the second textbox or an assay name in the third textbox to search for the data linked to an investigation, study or assay.
2. Click the Search button to show the results.
3. Select the data you want to send to Galaxy and select the "Send datafile only" option.
4. Select the filetype and database.
5. Enter a history name and click the send to Galaxy button.

Results will be automaticallyuploaded to the SEEK server. A new assay will be created with the studyname + __result__ + a unique ID. This is done to make it an easier process to find assays that are results instead of the regular assays created by the user.

## <a name="run-myfair-omicsdi">Run myFAIR with Omics DI</a>

In order to run myFAIR using datasets from Omics DI a new assay has to be created without any data files present.

Enter the assay name in the assay serachbox from the myFAIR homepage. No results will be displayed in the results table but there is a textbox available were you can enter an Omics DI accession ID. Select a workflow and enter an accession ID in the textbox an press *send to Galaxy*. All available datasets linked to the accession ID will be downloaded and send to the Galaxy server. The results will be stored in a new assay with a tag containing the Omics DI accession ID.

## <a name="see-results">See results</a>

The following steps can be used to view the results of your analysis.

1. Enter the study name that you want to get the results from.
2. Click on the *Search >>* button to start searching for all results based on that study.
3. Select the results you want to view.
4. Click on the *Show results* button.
5. A new page will open with the input and output files  and the analysis details.
6. Click on the view icon to view the SEEK data in the SEEK GUI or click on the download icon to download that file to your computer.

## <a name="rerun-analysis">Run the analysis again</a>

Follow these steps to run the analysis shown in the result page again:

1. In the results page click on the *Rerun* button.
2. A cat will appear to show that the analysis is running.
3. After the files are send to Galaxy a checkmark will appear and you will be redirected the result page.
4. Visit the Galaxy page to see the analysis.

The results generated from rerunning the analysis will not be stored in SEEK or ownCloud. To store a new result please run a new analysis with the same data and same workflow. Click on the Erasmus MC logo to go back to the homepage and search for another result or do run another analysis.
