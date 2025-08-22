'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Oct 06 2021
File : create_report.py
'''
import sys, os, logging, argparse, json, re
from datetime import datetime
import shutil
import upload_reports
import _version
import report_data
import report_artifacts
import report_errors
import report_archive

###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info < (3, 6):
    raise Exception("The current version of Python is less than 3.6 which is unsupported.\n Script created/tested against python version 3.6.8. ")
else:
    pass

propertiesFile = "../server_properties.json"  # Created by installer or manually
propertiesFile = logfileName = os.path.dirname(os.path.realpath(__file__)) + "/" +  propertiesFile
logfileName = os.path.dirname(os.path.realpath(__file__)) + "/_sbom_report.log"

###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)-3d  %(levelname)-8s [%(filename)-30s:%(lineno)-4d]  %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)

logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module

####################################################################################
# Create command line argument options
parser = argparse.ArgumentParser(
    description="""Usage Examples:

Windows:
  python create_report.py -pid <projectID> -reportOpts "{\\"includeChildProjects\\": \\"True\\", \\"includeVulnerabilities\\": \\"False\\"}"   #####      

Linux:
  python3 create_report.py -pid <projectID> -reportOpts '{"includeChildProjects":"True", "includeVulnerabilities":"False"}'   #####      

Note:
  - The -pid flag is mandatory.
  - The -reportOpts flag is optional. If omitted, all values will default to "includeChildProjects":"True" and "includeVulnerabilities":"False".
  Example: python3 create_report.py -pid <projectID>
"""
)
parser.add_argument('-pid', "--projectID", help="Project ID")
parser.add_argument("-rid", "--reportID", help="Report ID")
parser.add_argument("-authToken", "--authToken", help="Code Insight Authorization Token")
parser.add_argument("-reportOpts", "--reportOptions", help="Options for report content")

#----------------------------------------------------------------------#
def main():

    reportName = "SBOM Report with Usage Guidance"
    reportVersion = _version.__version__

    logger.info("Creating %s - %s" %(reportName, reportVersion))
    print("Creating %s - %s" %(reportName, reportVersion))
    print("    Logfile: %s" %(logfileName))


    #####################################################################################################
    #  Code Insight System Information
    #  Pull the base URL from the same file that the installer is creating
    if os.path.exists(propertiesFile):
        try:
            file_ptr = open(propertiesFile, "r")
            configData = json.load(file_ptr)
            baseURL = configData["core.server.url"]
            file_ptr.close()
            logger.info("Using baseURL from properties file: %s" %propertiesFile)
        except:
            logger.error("Unable to open properties file: %s" %propertiesFile)

        # Is there a self signed certificate to consider?
        try:
            certificatePath = configData["core.server.certificate"]
            os.environ["REQUESTS_CA_BUNDLE"] = certificatePath
            os.environ["SSL_CERT_FILE"] = certificatePath
            logger.info("Self signed certificate added to env")
        except:
            logger.info("No self signed certificate in properties file")

    else:
        baseURL = "http://localhost:8888"   # Required if the core.server.properties files is not used
        logger.info("Using baseURL from create_report.py")

    # See what if any arguments were provided
    args = parser.parse_args()
    projectID = (
        args.projectID
        if args.projectID is not None
        else sys.exit("Project ID -pid flag is mandatory")
    )
    reportID = (
        args.reportID
        if args.reportID is not None
        else print("Ignoring as -rid flag is not needed")
    )
    authToken = (
        args.authToken
        if args.authToken is not None
        else print("Ignoring as -authToken flag is not needed")
    )
    if args.reportOptions is not None:
        reportOptions = args.reportOptions
        if sys.platform.startswith("linux"):
            logger.info(f"Before Double Quote replacement: {reportOptions}")
            if '""' in reportOptions:
                reportOptions = reportOptions.replace('""', '"')[1:-1]
    else:
        reportOptions = '{"includeChildProjects":"True", "includeVulnerabilities":"False"}'
        if sys.platform.startswith("linux"):
            reportOptions = '{"includeChildProjects":"True", "includeVulnerabilities":"False"}'
    logger.info(f"Using default report options: {reportOptions}")

    fileNameTimeStamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    reportTimeStamp = datetime.strptime(fileNameTimeStamp, "%Y%m%d-%H%M%S").strftime("%B %d, %Y at %H:%M:%S")
    reportOptions = json.loads(reportOptions)
    reportOptions = verifyOptions(reportOptions) 

    logger.debug("Custom Report Provided Arguments:")	
    logger.debug("    projectID:  %s" %projectID)	
    logger.debug("    reportID:   %s" %reportID)	
    logger.debug("    baseURL:  %s" %baseURL)	
    logger.debug("    reportOptions:  %s" %reportOptions)	

    reportData = {}
    reportData["projectID"] = projectID
    reportData["reportName"] = reportName
    reportData["reportVersion"] = reportVersion
    reportData["reportOptions"] = reportOptions
    reportData["releaseVersion"] = "N/A"
    reportData["fileNameTimeStamp"] = fileNameTimeStamp
    reportData["reportTimeStamp"] = reportTimeStamp

    # Did we fail the options validation?
    if "errorMsg" in reportOptions.keys():

        reportFileNameBase = reportName.replace(" ", "_") + "-Creation_Error-" + fileNameTimeStamp

        reportData["errorMsg"] = reportOptions["errorMsg"]
        reportData["reportName"] = reportName
        reportData["reportFileNameBase"] = reportFileNameBase
        
        reports = report_errors.create_error_report(reportData)
        print("    *** ERROR  ***  Error found validating report options")
    else:
        print("    Collect data for %s" %reportName)
        reportData = report_data.gather_data_for_report(baseURL, projectID, authToken, reportData)
        print("    Report data has been collected")
        
        projectName = reportData["topLevelProjectName"]
        projectNameForFile = re.sub(r"[^a-zA-Z0-9]+", '-', projectName )  # Remove special characters from project name for artifacts
        
		# Are there child projects involved?  If so have the artifact file names reflect this fact
        if len(reportData["projectList"])==1:
            reportFileNameBase = projectNameForFile + "-" + str(projectID) + "-" + reportName.replace(" ", "_") + "-" + fileNameTimeStamp
        else:
            reportFileNameBase = projectNameForFile + "-with-children-" + str(projectID) + "-" + reportName.replace(" ", "_") + "-" + fileNameTimeStamp

        reportData["reportFileNameBase"] = reportFileNameBase

        # Was there any errors while collection the report data?
        if "errorMsg" in reportData.keys():
            reports = report_errors.create_error_report(reportData)
            print("    Error report artifacts have been created")
        else:
            reports = report_artifacts.create_report_artifacts(reportData)
            print("    Report artifacts have been created")

    print("    Create report archive for upload")
    uploadZipfile = report_archive.create_report_zipfile(reports, reportFileNameBase)
    print("    Upload zip file creation completed")
    if authToken is not None:
        upload_reports.upload_project_report_data(baseURL, projectID, reportID, authToken, uploadZipfile)
        print("    Report uploaded to Code Insight")

		#########################################################
		# Remove the file since it has been uploaded to Code Insight
        try:
            os.remove(uploadZipfile)
        except OSError:
            logger.error("Error removing %s" %uploadZipfile)
            print("Error removing %s" %uploadZipfile)
    else:
        # Get the current path and directory
        current_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_path)
        logger.info(f"Current directory: {current_directory}")

        # Define the DBReports directory path
        quickDBReports_dir = os.path.join(current_directory, "reportsBackup")

        # Check if quickDBReports directory exists, if not create it
        if not os.path.exists(quickDBReports_dir):
            os.makedirs(quickDBReports_dir)
            logger.info(f"Created directory: {quickDBReports_dir}")

        # Check if there are any previous reports in quickDBReports directory
        previous_reports = [
            f
            for f in os.listdir(quickDBReports_dir)
            if os.path.isfile(os.path.join(quickDBReports_dir, f))
        ]
        if previous_reports:
            # Create a Backup directory inside quickDBReports
            backup_dir = os.path.join(quickDBReports_dir, "Backup")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                logger.info(f"Created backup directory: {backup_dir}")

            # Create a timestamped backup directory inside Backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamped_backup_dir = os.path.join(backup_dir, f"Backup_{timestamp}")
            os.makedirs(timestamped_backup_dir)
            logger.info(
                f"Created timestamped backup directory: {timestamped_backup_dir}"
            )

            # Move all previous reports to the timestamped backup directory
            for report in previous_reports:
                shutil.move(
                    os.path.join(quickDBReports_dir, report),
                    os.path.join(timestamped_backup_dir, report),
                )
                logger.info(f"Moved report {report} to backup directory")

        # Move new reports to the quickDBReports directory
        # Only move the uploadZipfile since that's the actual created file
        if os.path.exists(uploadZipfile):
            shutil.move(uploadZipfile, quickDBReports_dir)
            logger.info(f"Moved new report {uploadZipfile} to {quickDBReports_dir}")
        else:
            logger.error(f"Report file {uploadZipfile} does not exist")
            print(f"Error: Report file {uploadZipfile} does not exist")

        # Check if the base zip file exists before trying to move it
        base_zip_file = reportFileNameBase + ".zip"
        if os.path.exists(base_zip_file):
            shutil.move(base_zip_file, quickDBReports_dir)
            logger.info(f"Moved base report {base_zip_file} to {quickDBReports_dir}")
        else:
            logger.warning(f"Base zip file {base_zip_file} does not exist, skipping move")

        logger.info("Completed creating %s" %reportName)
        print("Completed creating %s" %reportName)


#----------------------------------------------------------------------# 
def verifyOptions(reportOptions):
    '''
    Expected Options for report:
        includeChildProjects - True/False
    '''
    reportOptions["errorMsg"] = []
    trueOptions = ["true", "t", "yes", "y"]
    falseOptions = ["false", "f", "no", "n"]

    includeChildProjects = reportOptions["includeChildProjects"]
    includeVulnerabilities = reportOptions["includeVulnerabilities"]


    if includeChildProjects.lower() in trueOptions:
        reportOptions["includeChildProjects"] = True
    elif includeChildProjects.lower() in falseOptions:
        reportOptions["includeChildProjects"] = False
    else:
        reportOptions["errorMsg"].append("Invalid option for including child projects: <b>%s</b>.  Valid options are <b>True/False</b>" %includeChildProjects)

    if includeVulnerabilities.lower() in trueOptions:
        reportOptions["includeVulnerabilities"] = True
    elif includeVulnerabilities.lower() in falseOptions:
        reportOptions["includeVulnerabilities"] = False
    else:
        reportOptions["errorMsg"].append("Invalid option for including vulnerability data: <b>%s</b>.  Valid options are <b>True/False</b>" %includeVulnerabilities)


    if not reportOptions["errorMsg"]:
        reportOptions.pop('errorMsg', None)
    
    return reportOptions


#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  