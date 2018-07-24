# myFAIR analysis @ EMC

  * [Dependencies](#dependencies)
  * [Installation Instructions](#installation-instructions)
  * [Run myFAIR with B2DROP](#run-myfair-b2drop)
  * [Upload fies to SEEK](#upload-files-seek)
  * [Run myFAIR with SEEK](#run-myfair-seek)
  * [See results](#see-results)
  * [Using GEO files](#using-geo)
  * [Store your history](#store-history)
  * [Run the analysis again](#rerun-analysis)

For this testcase we are using variant selection by GEMINI analysis using genome in the bottle data. Specifically, we will be using Ashkenazim Father-Mother-Son trio data from the Personal Genome Project. You can download the down sampled version of the dataset created by the GEMINI team from a GIAB trio dataset.
The vcf file can be found [here](https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F8ae2ca084c0c0c70/datasets/e4e82f84348cba8c) and the ped file can be found [here](https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F8ae2ca084c0c0c70/datasets/5e4dbb32432c1676).

# <a name="dependencies"></a>Dependencies
* Python 3.6 or higher
* Django 2.0 or higher
* Bioblend 0.8.1 or hger
* rdflib
* lftp 4.6.3a
* Java SE Development Kit 8u112
* Apache Jena Fuseki 2.4.1
* An account on a local or external Galaxy server with the following tools available:
    * GEMINI (load, autosomal recessive/dominant, de novo, comp hets)
    * Add Column, Strip Header and File Concatenate (all can be found under the name file_manipulation in the Galaxy tool shed)
    * The Galaxy server should allow an FTP connection in order for myFAIR to send the data.

# <a name="installation-instructions"></a> Installation Instructions
**Install myFAIR on your existing VM**

To install myFAIR on your existing Virtual Machine follow these steps:

1. Install all dependencies.
2. Download or clone myFAIR to your home directory. The latest version can be found [here](https://github.com/ErasmusMC-Bioinformatics/myFAIR).
3. Change the Galaxy server setting by changing the **galaxy.ini.sample** file. Change the port to 8000 (change port if needed) and change the host to 0.0.0.0
4. Run the server by opening the terminal and type: **python3 myFAIR/manage.py runserver 0.0.0.0:8080 (change port if needed)** (please make sure manage.py have the right permissions: **chmod +x manage.py**)
5. To run the Apache Fuseki Server open the terminal and type:  **fuseki location/fuseki start**
6. Create a new dataset in Fuseki called "ds".
7. Start the Galaxy server by opening the terminal and type: **galaxy location/run.sh**
8. Download the Gemini workflow by importing a workflow using this url: https://usegalaxy.org/u/rickjansen/w/training-gemini-vcfanalysis-11112016.
9. Test if 127.0.0.1:8080(or other chosen port) shows the myFAIR login page and that 127.0.0.1:8000(or other chosen port) shows the Galaxy page. To test fuseki go to 127.0.0.1:3030 and see if there is a green circle next to "Server status".
10. Download the Gemini annotation files [here](https://bioinf-galaxian.erasmusmc.nl/owncloud/index.php/s/JuH6c97y5lAVSf2) and place the folder "gemini_annotation" in the home folder.

Optional:

11. Install a SEEK server. You can download SEEK [here](https://github.com/seek4science/seek). Click [here](https://docs.seek4science.org/tech/install.html) on how to install a local SEEK server.

After these steps, you can run the myFAIR analysis.

**Install and use our VM**

You can test myFAIR on our existing Virtual Machine.
Everything is already pre-installed and can be used after following these steps below:

1. Download the Virtual Machine [here](https://bioinf-galaxian.erasmusmc.nl/owncloud/index.php/s/Qr5Nu6CBotyvG1Z). **(The size of the Virtual Machine will be large due to the annotation files needed for Gemini, please make sure you have enough free space to run the Virtual Machine)**
2. Add the Virtual Machine and start the Virtual Machine (Password is "fair@emc")
3. Download or clone myFAIR to your home directory. The latest version can be found [here](https://github.com/ErasmusMC-Bioinformatics/myFAIR).
4. Overwrite the old myFAIR version with the new version.
5. Open the terminal and start the Fuseki Server by typing: **.local/apache-jena-fuseki-2.4.1/fuseki start**
6. Test if 127.0.0.1:8080 shows the myFAIR login page and that https://usegalaxy.org shows the Galaxy page. To see if the fuseki server is running, go to 127.0.0.1:3030 and see if there is a green circle next to "Server status:".

Optional:

7. Install a SEEK server. You can download SEEK [here](https://github.com/seek4science/seek). Click [here](https://docs.seek4science.org/tech/install.html) on how to install a local SEEK server.

# <a name="run-myfair-b2drop"></a> Run myFAIR with B2DROP
In order to run myFAIR you need to follow these steps:

1. Follow the Installation Instructions.
2. Open or download a browser (Firefox or Chrome recommended).
3. Go to the usegalaxy page: https://usegalaxy.org/
4. Login to your account or create a new account by clicking "User" and then clicking "Register".
5. Visit the B2DROP or page and create a folder where you can put your datafiles. You can also use the bioinf-galaxian Owncloud if you have an account.
    * If you do not have a B2DROP account please visit: https://b2drop.eudat.eu/index.php/login and click register.
    * If you have a B2DROP account, please log in and create a new folder with the name of your investigation.
    * Add a folder with the name of your study.
    * Add the .vcf and .ped file to the study folder.
    If you are using the GEO data matrix, please put that file in a folder.
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
    * If you are using the GEO data matrix, please choose the "datafile" option for all data matrix files you want to upload. If you do not have a metadata file, click "Store Triples". If you already have a metadata file please select "metadata" for that file and then click "Store Triples".
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
    *   After finding your files, select the "Training_gemini_vcfanalysis_11112016" workflow by clicking on the dropdown menu.
    *   Select the file you want to send and choose the options you want to use.
    *   Enter a new history name or leave empty to automatically generate a new history name.
    *   Then click on the "send to galaxy" button to start sending the files to the Galaxy ftp folder and import the files in a new history. After importing the files run the selected workflow.
11. A cat will appear to let you know that the files are being send to Galaxy and that the workflow is running (if you have selected a workflow).
A checkmark will appear when the files are send to galaxy and the workflow is finished (if you selected a workflow).
If something went wrong (workflow failed, not selected a file or you get timed-out) an error message will appear.
12. If you do not want to use a workflow you can choose "Use Galaxy" to only send the datafiles to Galaxy and work with the files directly in Galaxy.
13. You can visit the Galaxy page to see if the workflow is running by going to https://usegalaxy.org/ or go to the next step.

# <a name="upload-files-seek"></a> Upload files to SEEK
1. Follow the Installation Instructions.
2. Open or download a browser (Firefox or Chrome recommended).
3. Go to the SEEK URL to create a new project.
4. Add an investigation to that project.
5. Logon to the myFAIR webpage with your Galaxy and SEEK credentials.
6. Got to the "Upload to SEEK" page.
7. Select the project you have just created and then select the investigation.
8. Select the create new study option.
9. Enter a study name, title and description.
10. Click on the create study button.
11. After creating a study select the newly created study.
12. Select the create new assay option.
13. Enter an assay name, title and description.
14. Select an assay type and a technology type.
15. Click on the create assay button.
16. Select the newly created assay.
17. Enter a data file title and description.
18. Select the file to upload.
19. Click upload file.
20. Go to the homepage.

# <a name="run-myfair-b2drop"></a> Run myFAIR with SEEK
To run myFAIR with SEEK data you need to follow the Upload files to SEEK steps first. After uploading the data files you can search the data from the homepage.

You can search the SEEK data based on the investigation, study or assay. You can search in on of the three available textboxes.

Follow the next steps to search for data files linked to an investigation, study or assay:
1. Enter the investigation name in the first textbox or a study name in the second textbox or an assay name in the third textbox to search for the data linked to an investigation, study or assay.
2. Click the Search button to show the results.
3. Select the data you want to send to Galaxy and select the "Send datafile only" option.
4. Select the filetype and database.
5. Enter a history name and click the send to Galaxy button.

# <a name="see-results"></a> See results
The following steps can be used to view the results of your analysis.

1. Enter the study name that you want to get the results from.
2. Click on the "Search >>" button to start searching for all results based on that study.
3. Select the results you want to view.
4. Click on the "Show results" button.
5. A new page will open with the input and output files  and the analysis details.
6. Click on any of the "Download" buttons to download that file.

# <a name="store-history"></a> Store your history
myFAIR will not upload your results to Owncloud or B2DROP when there was no workflow used. In order to send your results to Owncloud or B2DROP to make them searchable follow these steps:

1. Choose an investigation folder in the dropdown menu (top level folder).
2. Click the "Get studies" button to find all studies in the investigation.
3. Select the history you want to store in the Owncloud folder.
4. Select the study you want to store the results in (sub folder in the investigation folder).
3. Click on the "Send history to Owncloud" button.
4. A new page will appear telling you the results are stored and are now searchable in myFAIR.
5. Follow the "See results" steps to view your results.

# <a name="rerun-analysis"></a> Run the analysis again
Follow these steps to run the analysis shown in the result page again:

1. In the results page click on the "Run again" button.
2. A cat will appear to show that the analysis is running.
3. After the files are send to Galaxy a checkmark will appear and you will be redirected the homepage.
4. Visit the Galaxy page to see the analysis.
