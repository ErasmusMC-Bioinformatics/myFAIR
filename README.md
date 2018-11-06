# myFAIR

[Dependencies](#dependencies)<br>
[Installation Instructions](#installation-instructions)<br>
[Install myFAIR](#install-myfair)<br>
[Install SEEK](#install-seek)<br>
[Galaxy](#galaxy)<br>
[Run myFAIR with B2DROP](#run-myfair-b2drop)<br>
[Create a new study](#create-new-study)<br>
[Create a new assay](#create-new-assay)<br>
[Upload fies to SEEK](#upload-files-seek)<br>
[Run myFAIR with SEEK](#run-myfair-seek)<br>
[See results](#see-results)<br>
[Store your history](#store-history)<br>
[Run the analysis again](#rerun-analysis)

For this testcase we are using variant selection by GEMINI analysis using genome in the bottle data. Specifically, we will be using Ashkenazim Father-Mother-Son trio data from the Personal Genome Project. You can download the down sampled version of the dataset created by the GEMINI team from a GIAB trio dataset.
The vcf file can be found [here](https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F8ae2ca084c0c0c70/datasets/e4e82f84348cba8c) and the ped file can be found [here](https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F8ae2ca084c0c0c70/datasets/5e4dbb32432c1676).

## <a name="dependencies">Dependencies</a>

* Python 3.6 or higher
* Django 2.1.2 or higher
* Bioblend 0.11.0 or higer
* rdflib 4.2.2 or higher
* lftp 4.8.1 or higher
* python-magic 0.4.15 or higher
* plotly 3.3.0 or higher
* An account on a local or external Galaxy server with the following tools available:
    1. GEMINI (load, autosomal recessive/dominant, de novo, comp hets)
    2. Add Column, Strip Header and File Concatenate (all can be found under the name file_manipulation in the Galaxy tool shed)
    3. The Galaxy server should allow an FTP connection in order for myFAIR to send the data.
* An account to an external SEEK server or a local SEEK server.

## <a name="installation-instructions">Installation Instructions</a>

### <a name="install=myfair">Install myFAIR</a>

To install myFAIR on your existing Virtual Machine follow these steps:

#### Install dependencies

```bash
sudo apt update
sudo apt upgrade
sudo apt install python3 python3-pip lftp
pip3 install django bioblend rdflib plotly python-magic
```

#### Get myFAIR

```bash
git clone https://github.com/ErasmusMC-Bioinformatics/myFAIR
```

#### Run the server

Run the following command to run the myFAIR server.

```bash
python3 myFAIR/manage.py runserver 0.0.0.0:8080
```

#### Set permissions

If manage.py does not have the right permissions run the following command:

```bash
chmod +x myFAIR/manage.py
```

#### Test the server

Go to 127.0.0.1:8080 (or other chosen port) and check if the myFAIR login page is visible.

### <a name="install-seek">Install SEEK</a>

You can download the latest version of SEEK [here](https://github.com/seek4science/seek). For more information on installing SEEK click [here](https://docs.seek4science.org/tech/install.html).

Follow [these](https://docs.seek4science.org/tech/setting-up-virtuoso.html) instructions to install the Virtuoso triple store and connect the triple store to your SEEK server.


### <a name="galaxy">Galaxy</a>

Go to [usegalaxy](https://usegalaxy.eu) and create an account or log in with an existing account to see if it is still working.

#### Importing the GEMINI workflow

Import the GEMINI workflow using this url: https://usegalaxy.eu/u/rickjansen/w/geminivcfanalysis.



<!-- # <a name="run-myfair-b2drop"></a> Run myFAIR with B2DROP
In order to run myFAIR you need to follow these steps:

1. Follow the Installation Instructions.
2. Open or download a browser (Firefox or Chrome recommended).
3. Go to the usegalaxy page: https://usegalaxy.eu/
4. Login to your account or create a new account by clicking "Login or register" and then clicking "Register".
5. Visit the B2DROP or page and create a folder where you can put your datafiles. You can also use the bioinf-galaxian Owncloud if you have an account.
    * If you do not have a B2DROP account please visit: https://b2drop.eudat.eu/index.php/login and click register.
    * If you have a B2DROP account, please log in and create a new folder with the name of your investigation.
    * Add a folder with the name of your study.
    * Add the .vcf and .ped file to the study folder.
6. Visit the myFAIR analysis page on 127.0.0.1:8080 (if selected other port please make sure the url is correct)
7. Login using your Galaxy credentials (username/email and password) and your B2DROP or bioinf-galaxian credentials.
8. Upload files to the Fuseki server:
    * Click on the "Index you data" link.
    * Select the investigation folder and click "See studies".
    * Select the study folder where your datafiles are located and click "See files".
    * You will now see the two files you added to this folder in step 6.
    * Choose which file is your datafile (vcf file) and which file is your metadata (ped file).
    * Tag the data with a disease and with a type of operation. If the tagged disease is found in DisGeNET a link will be stored in the triple store, if the type of operation is found in EDAM a link to the EDAM page will be stored.
    * Click "Store Triples" to start the creation of new triples and store them in the Fuseki server.
    * You will be send back to the homepage.

9. Find your files or samples:

    a. Find your files using a sample name:
    *   Enter a sample name in the Find Data textbox.
    *   Click on the "Search >>" button to start searching for your files.
    
    b. Find your files using a study name:
    *   Enter the name of the study in the Find data textbox.
    *   Click on the "Search >>" button to start searching for your files.

    c. Find samples with a specific disease:
    *   Enter the name of the disease in the Find data textbox.
    *   Click on the "Search >>" button to start searching for your files.

10. Send the files to Galaxy and run a workflow:
    *   After finding your files, select the "GEMINI_VCF_Analysis" workflow by clicking on the dropdown menu.
    *   Select the file you want to send and choose the options you want to use.
    *   Enter a new history name or leave empty to automatically generate a new history name.
    *   Then click on the "send to galaxy" button to start sending the files to the Galaxy ftp folder and import the files in a new history. After importing the files run the selected workflow.
11. A cat will appear to let you know that the files are being send to Galaxy and that the workflow is running (if you have selected a workflow).
A checkmark will appear when the files are send to galaxy and the workflow is finished (if you selected a workflow).
If something went wrong (workflow failed, not selected a file or you get timed-out) an error message will appear.
12. If you do not want to use a workflow you can choose "Use Galaxy" to only send the datafiles to Galaxy and work with the files directly in Galaxy.
13. You can visit the Galaxy page to see if the workflow is running by going to https://usegalaxy.eu/ or go to the next step. -->

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

## <a name="see-results">See results</a>

The following steps can be used to view the results of your analysis.

1. Enter the study name that you want to get the results from.
2. Click on the *Search >>* button to start searching for all results based on that study.
3. Select the results you want to view.
4. Click on the *Show results* button.
5. A new page will open with the input and output files  and the analysis details.
6. Click on the view icon to view the SEEK data in the SEEK GUI or click on the download icon to download that file to your computer.

## <a name="store-history">Store your history</a>

myFAIR will not upload your results to Owncloud or B2DROP when there was no workflow used. To send your results to Owncloud or B2DROP and make them searchable, please follow these steps:

1. Choose an investigation folder in the dropdown menu (top level folder).
2. Click the "Get studies" button to find all studies in the investigation.
3. Select the history you want to store in the Owncloud folder.
4. Select the study you want to store the results in (sub folder in the investigation folder).
5. Click on the *Send history to Owncloud* button.
6. A new page will appear telling you the results are stored and are now searchable in myFAIR.
7. Follow the *See results* steps to view your results.

## <a name="rerun-analysis">Run the analysis again</a>

Follow these steps to run the analysis shown in the result page again:

1. In the results page click on the *Run again* button.
2. A cat will appear to show that the analysis is running.
3. After the files are send to Galaxy a checkmark will appear and you will be redirected the result page.
4. Visit the Galaxy page to see the analysis.

The results generated from rerunning the analysis will not be stored in SEEK or ownCloud. To store a new result please run a new analysis with the same data and same workflow. Click on the Erasmus MC logo to go back to the homepage and search for another result or do run another analysis.
