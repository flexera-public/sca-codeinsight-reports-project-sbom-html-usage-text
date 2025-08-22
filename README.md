# sca-codeinsight-reports-project-sbom

The sca-codeinsight-reports-project-sbom repository is a example report for Revenera's Code Insight product. This report allows a user to get a quick high level summary of the inventory items within a project. This report will take into account any child projects (recursively) and display a hierarchy chart of the project structure.

This repository utilizes the following via CDN for the creation of the report artifacts.

-  [Bootstrap](https://getbootstrap.com/)
-  [DataTables](https://datatables.net/)
-  [jsTree](https://www.jstree.com/)

## Prerequisites

**Code Insight Release Requirements**


|Repository Tag | Minimum Code Insight Release |
|--|--|
|1.0.x |2021R3 |

**Repository Cloning**

This repository should be cloned directly into the **$CODEINSIGHT_INSTALLDIR/custom_report_scripts** directory. If no prior custom reports has been installed, this directory will need to be created prior to cloning.

**Python Requirements**

The required python modules can be installed with the use of the [requirements.txt](requirements.txt) file which can be loaded via.

	pip install -r requirements.txt

Offline Mode
The sca-codeinsight-reports-project-sbom custom report can be used in offline mode, meaning the Code Insight server does not need to be running.

For Windows:
Open a command prompt at the location:
$CODEINSIGHT_INSTALLDIR/custom_report_scripts/sca-codeinsight-reports-project-sbom
Run the following command
python create_report.py -pid <projectID> -reportOpts "{\"includeChildProjects\": \"True\", \"includeVulnerabilities\": \"False\"}"

For Linux:
Open a terminal at the location:
$CODEINSIGHT_INSTALLDIR/custom_report_scripts/sca-codeinsight-reports-project-sbom
Run the following command:
python3 create_report.py -pid <projectID> -reportOpts '{"includeChildProjects":"True","includeVulnerabilities":"False"}'

Notes:
The -pid flag is mandatory.
The -reportOpts flag is optional. If omitted, all values will default to "True".
Example: python3 create_report.py -pid <projectID>

Report Locations:
Recently Generated Reports:
$CODEINSIGHT_INSTALLDIR/custom_report_scripts/sca-codeinsight-reports-project-sbom/DBReports
Older Reports:
$CODEINSIGHT_INSTALLDIR/custom_report_scripts/sca-codeinsight-reports-project-sbom/DBReports/Backup

## Configuration and Report Registration

It is optional but recommended to have the Code Insight server up and running if you intend to trigger this report from the Code Insight UI under the reports tab.
For registration purposes the file **server_properties.json** should be created and located in the **$CODEINSIGHT_INSTALLDIR/custom_report_scripts/** directory.  This file contains a json with information required to register the report within Code Insight as shown  here:

>     {
>         "core.server.url": "http://localhost:8888" ,
>         "core.server.token" : "Admin authorization token from Code Insight"
>     }

The value for core.server.url is also used within [create_report.py](create_report.py) for any project or inventory based links back to the Code Insight server within a generated report.

If the common **server_properties.json** files is not used then the information the the following files will need to be updated:

[registration.py](registration.py)  -  Update the **baseURL** and **adminAuthToken** values. These settings allow the report itself to be registered on the Code Insight server.

[create_report.py](create_report.py)  -  Update the **baseURL** value. This URL is used for links within the reports.

Report option default values can also be specified in [registration.py](registration.py) within the reportOptions dictionaries.

### Registering the Report

Prior to being able to call the script directly from within Code Insight it must be registered. The [registration.py](registration.py) file can be used to directly register the report once the contents of this repository have been added to the custom_report_script folder at the base Code Insight installation directory.

To register this report:

	python registration.py -reg

To unregister this report:
	
	python registration.py -unreg

To update this report configuration:
	
	python registration.py -update

## Usage

This report is executed directly from within Revenera's Code Insight product. From the project reports tab of each Code Insight project it is possible to *generate* the **SBOM Report** via the Custom Report Framework.

The following report options can be set once the report generation has been initiated:

- Including child projects (True/False) - Determine if child project data will be included or not.
- Include presence of vulnerabilities - (True/False) - Display if the component has any vulnerabilities or not.

The above values will be used in place of the **Project Name** for any project references within the generated artifacts to allow users the ability abstract the project name for the application SBOM report.

The Code Insight Custom Report Framework will provide the following to the custom report when initiated:

- Project ID
- Report ID
- Authorization Token

For this example report these three items are passed on to a batch or sh file which will in turn execute a python script. This script will then:

- Collect data for the report via REST API using the Project ID and Authorization Token
- Take this collected data and generate an html as well as an xlsx file with details about the project inventory
- The html files will be marked as the *"viewable"* file
- A zip file will be created containing the html and xlsx files which will be the *"downloadable"* file.
- Create a zip file with the viewable file and the downloadable file
- Upload this combined zip file to Code Insight via REST API
- Delete the report artifacts that were created as the script ran

## License

[MIT](LICENSE)
