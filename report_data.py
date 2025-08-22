'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Oct 06 2021
File : report_data.py
'''
import logging
from collections import OrderedDict

# import common.api.project.get_project_information
import report_data_db

logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module


#-------------------------------------------------------------------#
def gather_data_for_report(baseURL, projectID, authToken, reportData):
    logger.info("Entering gather_data_for_report")

    # Parse report options
    reportOptions = reportData["reportOptions"]
    includeChildProjects = reportOptions["includeChildProjects"]  # True/False
    includeVulnerabilities = reportOptions["includeVulnerabilities"]  # True/False

    projectList = [] # List to hold parent/child details for report
    inventoryData = {}  # Create a dictionary containing the inventory data using inventoryID as keys
    projectData = {} # Create a dictionary containing the project level summary data using projectID as keys
    licenseDetails = {} # Dictionary to store license details to avoid multiple lookups for same id
    applicationDetails = {} # Dictionary to allow a project to be mapped to an application name/version

    project_Name = report_data_db.get_projects_data(projectID)
    if includeChildProjects:
        projectList = report_data_db.get_child_projects(projectID)
    else:
        projectList = []
        projectList.append(projectID)
    
    topLevelProjectName = project_Name

    # Get the list of parent/child projects start at the base project
    if includeChildProjects:
        projectHierarchy = report_data_db.get_project_hierarchy(projectID)
        # Convert hierarchy to flat list with parent-child relationships
        if baseURL is None:
            baseURL = "http://localhost:8888"
        flatProjectList = build_project_list_from_hierarchy(projectHierarchy, baseURL)
    else:
        # For top-level only, create simple hierarchy and flat list
        projectHierarchy = {
            'id': projectID,
            'name': project_Name,
            'childProject': []
        }
        if baseURL is None:
            baseURL = "http://localhost:8888"
        # Create flat list with only the top-level project
        flatProjectList = [{
            'projectID': str(projectID),
            'parent': '#',
            'projectName': project_Name,
            'projectLink': f"{baseURL}/codeinsight/FNCI#myprojectdetails/?id={projectID}&tab=projectInventory",
            'inventoryLinkBase': f"{baseURL}/codeinsight/FNCI#myprojectdetails/?id={projectID}&tab=projectInventory&pinv=",
            'applicationNameVersion': project_Name
        }]
    
    projectInventoryCount = {}

    #  Gather the details for each project and summerize the data
    for project in projectList:

        projectID = project
        projectName = report_data_db.get_projects_data(projectID)
        if baseURL is None:
            baseURL = "http://localhost:8888"
        projectLink= f"{baseURL}/codeinsight/FNCI#myprojectdetails/?id={projectID}&tab=projectInventory"

        # Fetch inventory data
        inventoryItems = report_data_db.get_inventory_data(projectID)
        if inventoryItems is None:
            inventoryItems = []

        # Fetch custom inventory data
        inventoryItemsCustom = report_data_db.get_inventory_data_custom(projectID)

        # Merge using ID_ as the key
        inventory_dict = {item['inventoryId']: item for item in inventoryItems}

        # Update or add items from inventoryItemsCustom
        for item in inventoryItemsCustom:
            inventory_dict[item['inventoryId']] = item

        # Convert back to list
        inventoryItems = list(inventory_dict.values())

        
        if not inventoryItems:
            logger.warning("    Project contains no inventory items")
            print("Project contains no inventory items.")

        # Create empty dictionary for project level data for this project
        projectData[projectName] = {}
        projectInventoryCount[projectName] = len(inventoryItems)

        for inventoryItem in inventoryItems:

            inventoryID = inventoryItem["inventoryId"]
            inventoryItemName = inventoryItem["inventoryItemName"]
            componentName = inventoryItem["componentName"]
            componentVersionName = inventoryItem["componentVersionName"]
            if inventoryItem.get("spdxIdentifier") and inventoryItem["spdxIdentifier"].strip():
                selectedLicenseName = inventoryItem["spdxIdentifier"].strip()
            elif inventoryItem.get("spdxLicName") and inventoryItem["spdxLicName"].strip():
                selectedLicenseName = inventoryItem["spdxLicName"].strip()
            else:
                selectedLicenseName = inventoryItem.get("selectedLicenseName", "")
                if selectedLicenseName and selectedLicenseName.strip():
                    selectedLicenseName = selectedLicenseName.strip()
                    if selectedLicenseName == "I don't know":
                        selectedLicenseName = ""
                else:
                    selectedLicenseName = ""

            selectedLicenseUrl = inventoryItem["licenseUrl"]
            componentUrl = inventoryItem["componentUrl"]
            
            # If there is no component URL set it to blank
            if componentUrl is None:
                componentUrl = ""
                
            if inventoryItem["approvalStatus"] == "4":
                approvalStatus = "Not Reviewed"
            elif inventoryItem["approvalStatus"] == "6":
                approvalStatus = "Approved" 
            elif inventoryItem["approvalStatus"] == "7":
                approvalStatus = "Rejected"
            else:
                approvalStatus = "Unknown"

            if inventoryItem["usageText"] is not None:
                usageText = inventoryItem["usageText"]
            else:
                usageText = ""
            hasVulnerabilities = inventoryItem["hasVulnerabilities"]
            # If there is no specific version just leave it blank
            if componentVersionName == None:
                componentVersionName = ""

            # If there is no license URL set it to blank
            if selectedLicenseUrl is None:
                selectedLicenseUrl = ""

            inventoryLink = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(projectID) + "&tab=projectInventory&pinv=" + str(inventoryID)


            # Store the data for the inventory item for reporting
            inventoryData[inventoryID] = {
                "projectName" : projectName,
                "inventoryItemName" : inventoryItemName,
                "componentName" : componentName,
                "componentVersionName" : componentVersionName,
                "selectedLicenseName" : selectedLicenseName,
                "componentUrl" : componentUrl,
                "selectedLicenseUrl" : selectedLicenseUrl,
                "inventoryLink" : inventoryLink,
                "approvalStatus" : approvalStatus,
                "usageText" : usageText,
                "projectLink" : projectLink,
                "hasVulnerabilities" : hasVulnerabilities,
                # "applicationNameVersion" : applicationNameVersion
            }

            projectData[projectName]["projectLink"] = projectLink

    # Sort the inventory data by Component Name / Component Version / Selected License Name
    sortedInventoryData = OrderedDict(sorted(inventoryData.items(), key=lambda x: (x[1]['componentName'],  x[1]['componentVersionName'], x[1]['selectedLicenseName'])  ) )

    # Build up the data to return for the
    reportData["projectHierarchy"] = projectHierarchy
    reportData["topLevelProjectName"] = topLevelProjectName
    reportData["inventoryData"] = sortedInventoryData
    reportData["projectList"] = projectList
    reportData["flatProjectList"] = flatProjectList
    reportData["reportOptions"] = reportOptions
    reportData["projectInventoryCount"] = projectInventoryCount
    reportData["applicationDetails"] = applicationDetails

    return reportData


def build_project_list_from_hierarchy(projectHierarchy, baseURL, parent_id='#'):
    """
    Convert hierarchical project structure to flat list with parent-child relationships.
    
    Args:
        projectHierarchy: Hierarchical dict with 'id', 'name', 'childProject' keys
        baseURL: Base URL for creating project links
        parent_id: Parent project ID (default '#' for root)
        
    Returns:
        list: Flat list of project dictionaries with parent references
    """
    project_list = []
    
    def traverse_hierarchy(node, parent):
        # Create project entry for current node
        project_id = str(node['id'])
        project_name = node['name']
        
        project_entry = {
            'projectID': project_id,
            'parent': parent,
            'projectName': project_name,
            'projectLink': f"{baseURL}/codeinsight/FNCI#myprojectdetails/?id={project_id}&tab=projectInventory",
            'inventoryLinkBase': f"{baseURL}/codeinsight/FNCI#myprojectdetails/?id={project_id}&tab=projectInventory&pinv=",
            'applicationNameVersion': project_name
        }
        
        project_list.append(project_entry)
        
        # Process child projects
        if 'childProject' in node and node['childProject']:
            for child in node['childProject']:
                traverse_hierarchy(child, project_id)
    
    # Start traversal from root
    traverse_hierarchy(projectHierarchy, parent_id)
    
    return project_list


#----------------------------------------------#
def create_project_hierarchy(project, parentID, projectList, baseURL):
    logger.debug("Entering create_project_hierarchy.")
    logger.debug("    Project Details: %s" %project)

    # Are there more child projects for this project?
    if len(project["childProject"]):

        # Sort by project name of child projects
        for childProject in sorted(project["childProject"], key = lambda i: i['name'] ) :

            uniqueProjectID = str(parentID) + "-" + str(childProject["id"])
            nodeDetails = {}
            nodeDetails["projectID"] = childProject["id"]
            nodeDetails["parent"] = parentID
            nodeDetails["uniqueID"] = uniqueProjectID
            nodeDetails["projectName"] = childProject["name"]
            nodeDetails["projectLink"] = baseURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(childProject["id"]) + "&tab=projectInventory"

            projectList.append( nodeDetails )

            create_project_hierarchy(childProject, uniqueProjectID, projectList, baseURL)

    return projectList

#----------------------------------------------#
# def determine_application_details(baseURL, projectName, projectID, authToken):
#     logger.debug("Entering determine_application_details.")
#     # Create a application name for the report if the custom fields are populated
#     # Default values
#     applicationName = projectName
#     applicationVersion = ""
#     applicationPublisher = ""
#     applicationDetailsString = ""

#     projectInformation = common.api.project.get_project_information.get_project_information_summary(baseURL, projectID, authToken)

#     # Project level custom fields added in 2022R1
#     if "customFields" in projectInformation:
#         customFields = projectInformation["customFields"]

#         # See if the custom project fields were propulated for this project
#         for customField in customFields:

#             # Is there the reqired custom field available?
#             if customField["fieldLabel"] == "Application Name":
#                 if customField["value"]:
#                     applicationName = customField["value"]

#             # Is the custom version field available?
#             if customField["fieldLabel"] == "Application Version":
#                 if customField["value"]:
#                     applicationVersion = customField["value"]     

#             # Is the custom Publisher field available?
#             if customField["fieldLabel"] == "Application Publisher":
#                 if customField["value"]:
#                     applicationPublisher = customField["value"]    



    # Join the custom values to create the application name for the report artifacts
    if applicationName != projectName:
        if applicationVersion != "":
            applicationNameVersion = applicationName + " - " + applicationVersion
        else:
            applicationNameVersion = applicationName
    else:
        applicationNameVersion = projectName

    if applicationPublisher != "":
        applicationDetailsString += "Publisher: " + applicationPublisher + " | "

    # This will either be the project name or the supplied application name
    applicationDetailsString += "Application: " + applicationName + " | "

    if applicationVersion != "":
        applicationDetailsString += "Version: " + applicationVersion
    else:
        # Rip off the  | from the end of the string if the version was not there
        applicationDetailsString = applicationDetailsString[:-3]

    applicationDetails = {}
    applicationDetails["applicationName"] = applicationName
    applicationDetails["applicationVersion"] = applicationVersion
    applicationDetails["applicationPublisher"] = applicationPublisher
    applicationDetails["applicationNameVersion"] = applicationNameVersion
    applicationDetails["applicationDetailsString"] = applicationDetailsString

    logger.info("    applicationDetails: %s" %applicationDetails)

    return applicationDetails