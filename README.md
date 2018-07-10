# myFAIR analysis @ EMC

  * [Dependencies](#dependencies)
  * [Installation Instructions](#installation-instructions)
  * [Run the myFAIR analysis](#run-the-myfair-analysis)
  * [See results](#see-results)
  * [Using GEO files](#using-geo)
  * [Store your history](#store-history)
  * [Run the analysis again](#rerun-analysis)

For this testcase we are using variant selection by GEMINI analysis using genome in the bottle data. Specifically, we will be using Ashkenazim Father-Mother-Son trio data from the Personal Genome Project. You can download the down sampled version of the dataset created by the GEMINI team from a GIAB trio dataset.
The vcf file can be found [here](https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F8ae2ca084c0c0c70/datasets/e4e82f84348cba8c) and the ped file can be found [here](https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F8ae2ca084c0c0c70/datasets/5e4dbb32432c1676).
For the GEO data matrix option there is a workflow available that is using DEseq2. You can follow the steps to filter the data matrix and metadata based on selected samples and send them to Galaxy. You can find these steps under the "Using GEO files" header.

# <a name="dependencies"></a>Dependencies
* Python 3.5 or higher
* Django 2.0.1 or higher
* Bioblend 0.8.1 or hger
* rdflib
* lftp 4.6.3a
* Java SE Development Kit 8u112
* Apache Jena Fuseki 2.4.1
* Galaxy 16.07 (or higher) or an existing Galaxy server with the following tools available:
    * GEMINI (load, autosomal recessive/dominant, de novo, comp hets)
    * Add Column, Strip Header and File Concatenate (all can be found under the name file_manipulation in the Galaxy tool shed)
    * The Galaxy server should allow an FTP connection in order for myFAIR to send the data.

# <a name="installation-instructions"></a> Installation Instructions
**Install myFAIR on your existing VM**

To install myFAIR on your existing Virtual Machine follow these steps:

1. Install all dependencies.
2. Download or clone myFAIR to your home directory. The latest version can be found [here](https://github.com/ErasmusMC-Bioinformatics/myFAIR).
3. Change the Galaxy server setting by changing the **galaxy.ini.sample** file. Change the port to 8000 (change port if needed) and change the host to 0.0.0.0
4. Run the server by opening the terminal and type: **myFAIR/manage.py runserver 0.0.0.0:8080 (change port if needed)** (please make sure manage.py have the right permissions: **chmod +x manage.py**)
5. To run the Apache Fuseki Server open the terminal and type:  **fuseki location/fuseki start**
7. Create a new dataset in Fuseki called "ds".
8. Start the Galaxy server by opening the terminal and type: **galaxy location/run.sh**
9. Download the Gemini workflow by importing a workflow using this url: https://usegalaxy.org/u/rickjansen/w/training-gemini-vcfanalysis-11112016.
10. Test if 127.0.0.1:8080(or other chosen port) shows the myFAIR login page and that 127.0.0.1:8000(or other chosen port) shows the Galaxy page. To test fuseki go to 127.0.0.1:3030 and see if there is a green circle next to "Server status".
11. Download the Gemini annotation files [here](https://bioinf-galaxian.erasmusmc.nl/owncloud/index.php/s/JuH6c97y5lAVSf2) and place the folder "gemini_annotation" in the home folder.

After these steps, you can run the myFAIR analysis.

**Install and use our VM**

You can test myFAIR on our existing Virtual Machine.
Everything is already pre-installed and can be used after following these steps below:

1. Download the Virtual Machine [here](https://bioinf-galaxian.erasmusmc.nl/owncloud/index.php/s/Qr5Nu6CBotyvG1Z). **(The size of the Virtual Machine will be large due to the annotation files needed for Gemini, please make sure you have enough free space to run the Virtual Machine)**
2. Add the Virtual Machine and start the Virtual Machine (Password is "fair@emc")
3. Download or clone myFAIR to your home directory. The latest version can be found [here](https://github.com/ErasmusMC-Bioinformatics/myFAIR).
4. Overwrite the old myFAIR version with the new version.
4. Open the terminal and start the Fuseki Server by typing: **.local/apache-jena-fuseki-2.4.1/fuseki start**
5. Test if 127.0.0.1:8080 shows the myFAIR login page and that https://usegalaxy.org shows the Galaxy page. To see if the fuseki server is running, go to 127.0.0.1:3030 and see if there is a green circle next to "Server status:".

# <a name="run-the-myfair-analysis"></a> Run the myFAIR analysis
In order to run the myFAIR analysis you need to follow these steps:

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

# <a name="using-geo"></a> Using GEO files
To split GEO files and send only specific samples to a new Galaxy history follow these steps:

1. Download the GSE51403_expression_matrix_full.txt and  GSE51403_design_matrix_full_depth.txt file from https://bioinf-galaxian.erasmusmc.nl/galaxy/library/list#folders/F451c39ee14117b54
2. Download the differential_gene_expression workflow from https://usegalaxy.org/u/rickjansen/w/differential-gene-expression and import the workflow.
3. Change the header called sample-name in sample_id.
4. Place the data matrix and metadata in a study folder in B2DROP.
5. Index the data matrix by clicking on the Index your data link. Then selecting the investigation folder where the study is located and click the "See studies" button. Select the study with the data matrix, then select the matrix file as the datafile and teh design file as the metadata file.
6. Tag the data with the disease Unknown and the type of operation is RNA-seq read count analysis.
7. click on the "Store Triples" button.
8. On the homepage: enter the name of the study folder where the data matrix is located.
9. Click on the "Search >>" button to start searching for all available samples in the data matrix.
10. A list of samples will be shown in the results table. On the right side you will see a checkbox to select the file you want to use, on the left side are two checkboxes with the options A and B.
11. Select a file you want to use.
12. Select the samples you want to use in group A (control) and group B (test) by checking the checkboxes next to the sample name.
13. Choose the file format tabular or auto.
14. Enter a new history name or leave empty to automatically generate a new history name.
15. Select the "Send datafile only" option when using the "differential_gene_expression workflow".
16. Click the "send to galaxy" button.
17. The new data matrix and metadata (if no workflow is selected) based on the selected samples will be send to Galaxy and will also be uploaded to B2DROP. If the workflow is used a tabular output and pdf file will also be stored in B2DROP.
18. Visit the Galaxy page to view the uploaded and to start working with them.


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
