'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Wed Oct 27 2021
File : report_artifacts_html.py
'''
import logging
import os
import base64

import _version

logger = logging.getLogger(__name__)


#------------------------------------------------------------------#
def generate_html_report(reportData):
    logger.info("    Entering generate_html_report")

    reportName = reportData["reportName"]
    projectName = reportData["topLevelProjectName"]
    reportFileNameBase = reportData["reportFileNameBase"]
    reportTimeStamp =  reportData["reportTimeStamp"] 
    inventoryData = reportData["inventoryData"]
    projectList = reportData["flatProjectList"]
    reportOptions = reportData["reportOptions"]
    projectInventoryCount = reportData["projectInventoryCount"]
    applicationDetails = projectName
 
    scriptDirectory = os.path.dirname(os.path.realpath(__file__))
    cssFile =  os.path.join(scriptDirectory, "common/branding/css/revenera_common.css")
    logoImageFile =  os.path.join(scriptDirectory, "common/branding/images/logo_reversed.svg")
    iconFile =  os.path.join(scriptDirectory, "common/branding/images/favicon-revenera.ico")

    #########################################################
    #  Encode the image files
    encodedLogoImage = encodeImage(logoImageFile)
    encodedfaviconImage = encodeImage(iconFile)

    htmlFile = reportFileNameBase + ".html"

    #---------------------------------------------------------------------------------------------------
    # Create a simple HTML file to display
    #---------------------------------------------------------------------------------------------------
    try:
        html_ptr = open(htmlFile,"w")
    except:
        logger.error("Failed to open htmlfile %s:" %htmlFile)
        raise

    html_ptr.write("<html>\n") 
    html_ptr.write("    <head>\n")

    html_ptr.write("        <!-- Required meta tags --> \n")
    html_ptr.write("        <meta charset='utf-8'>  \n")
    html_ptr.write("        <meta name='viewport' content='width=device-width, initial-scale=1, shrink-to-fit=no'> \n")

    html_ptr.write(''' 
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.1/css/bootstrap.min.css" integrity="sha384-VCmXjywReHh4PwowAiWNagnWcLhlEJLA5buUprzK8rxFgeH0kww/aWY76TfkUoSX" crossorigin="anonymous">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.1.3/css/bootstrap.css">
        <link rel="stylesheet" href="https://cdn.datatables.net/1.10.21/css/dataTables.bootstrap4.min.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.2.1/themes/default/style.min.css">
    ''')


    html_ptr.write("        <style>\n")

    # Add the contents of the css file to the head block
    try:
        f_ptr = open(cssFile)
        for line in f_ptr:
            html_ptr.write("            %s" %line)
        f_ptr.close()
    except:
        logger.error("Unable to open %s" %cssFile)
        print("Unable to open %s" %cssFile)


    html_ptr.write("        </style>\n")  

    html_ptr.write("    	<link rel='icon' type='image/png' href='data:image/png;base64, {}'>\n".format(encodedfaviconImage.decode('utf-8')))
    html_ptr.write("        <title>%s</title>\n" %(reportName))
    html_ptr.write("    </head>\n") 

    html_ptr.write("<body>\n")
    html_ptr.write("<div class=\"container-fluid\">\n")

    #---------------------------------------------------------------------------------------------------
    # Report Header
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN HEADER -->\n")
    html_ptr.write("<div class='header'>\n")
    html_ptr.write("  <div class='logo'>\n")
    html_ptr.write("    <img src='data:image/svg+xml;base64,{}' style='height: 5%;'>\n".format(encodedLogoImage.decode('utf-8')))
    html_ptr.write("  </div>\n")
    html_ptr.write("<div class='report-title'>%s</div>\n" %reportName)
    html_ptr.write("</div>\n")
    html_ptr.write("<!-- END HEADER -->\n")

    #---------------------------------------------------------------------------------------------------
    # Body of Report
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN BODY -->\n")  


    # If there is some sort of hierarchy then show specific project summaries
    if len(projectList) > 1:
        
        # How much space to we need to give each canvas
        # based on the amount of projects in the hierarchy
        canvasHeight = len(projectList) * 20   

        # We need a minimum size to cover font as well
        if canvasHeight < 180:
            canvasHeight = 180
        # The entire column needs to hold the three canvas items
        columnHeight = canvasHeight *3

        html_ptr.write("<hr class='small'>\n")

#######################################################################
        #  Create table to hold the project summary charts.
        #  js script itself is added later

        html_ptr.write("<table id='projectSummary' class='table' style='width:90%'>\n")
        html_ptr.write("    <thead>\n")
        html_ptr.write("        <tr>\n")
        html_ptr.write("            <th colspan='8' class='text-center'><h4>%s - Project Hierarchy</h4></th>\n" %(applicationDetails) )
        html_ptr.write("        </tr>\n") 
        html_ptr.write("    </thead>\n")
        html_ptr.write("</table>\n")

        html_ptr.write("<div class='container'>\n")
        html_ptr.write("    <div class='row'>\n")

        html_ptr.write("        <div class='col-sm'>\n")
        html_ptr.write("            <div id='project_hierarchy'></div>\n")
        html_ptr.write("        </div>\n")
        html_ptr.write("    </div>\n")
        html_ptr.write("</div>\n")

        html_ptr.write("<hr class='small'>")
 
    html_ptr.write("<table id='inventoryData' class='table table-hover table-sm row-border' style='width:90%'>\n")

    html_ptr.write("    <thead>\n")
    html_ptr.write("        <tr>\n")
    html_ptr.write("            <th colspan='9' class='text-center'><p style='font-size:24px'>Software Bill of Materials</p>\n") 
    html_ptr.write("            <p style='font-size:16px'>%s</p></th>\n" %(applicationDetails))

    html_ptr.write("        </tr>\n") 
    html_ptr.write("        <tr>\n")
    
    if len(projectList) > 1: 
        html_ptr.write("            <th style='width: 25%' class='text-center'>PROJECT</th>\n") 

    html_ptr.write("            <th style='width: 15%' class='text-center'>COMPONENT</th>\n")
    html_ptr.write("            <th style='width: 10%' class='text-center'>VERSION</th>\n")
    html_ptr.write("            <th style='width: 15%' class='text-center'>LICENSE</th>\n") 
    html_ptr.write("            <th style='width: 5%' class='text-center'>Approval Status</th>\n") 
    html_ptr.write("            <th style='width: 25%' class='text-center'>Usage Text</th>\n")

    if reportOptions["includeVulnerabilities"]:
        html_ptr.write("            <th style='width: 5%' class='text-center'>VULNERABILITES</th>\n") 

    html_ptr.write("        </tr>\n")
    html_ptr.write("    </thead>\n")  
    html_ptr.write("    <tbody>\n")  


    ######################################################
    # Cycle through the inventory to create the 
    # table with the results
    for inventoryID in inventoryData:

        logger.debug("        Reporting for inventory item %s" %inventoryID)
        projectName = inventoryData[inventoryID]["projectName"]
        inventoryItemName = inventoryData[inventoryID]["inventoryItemName"]
        componentName = inventoryData[inventoryID]["componentName"]
        componentUrl = inventoryData[inventoryID]["componentUrl"]
        componentVersionName = inventoryData[inventoryID]["componentVersionName"]
        selectedLicenseName = inventoryData[inventoryID]["selectedLicenseName"]
        selectedLicenseUrl = inventoryData[inventoryID]["selectedLicenseUrl"]
        hasVulnerabilities = inventoryData[inventoryID]["hasVulnerabilities"]
        approvalStatus = inventoryData[inventoryID]["approvalStatus"]
        usageText = inventoryData[inventoryID]["usageText"]

        applicationNameVersion = applicationDetails

        logger.debug("            Project Name:  %s   Inventory Name %s" %(projectName, inventoryItemName))

        html_ptr.write("        <tr> \n")
        if len(projectList) > 1:
            html_ptr.write("            <td class='text-left'>%s</td>\n" %(projectName))

        #  Is there a valid URL to link to?
        if componentUrl == "N/A":
            html_ptr.write("            <td class='text-left'>%s</td>\n" %(componentName))
        else:
            html_ptr.write("            <td class='text-left'><a href='%s' target='_blank'>%s</a></td>\n" %(componentUrl, componentName))

        html_ptr.write("            <td class='text-left'>%s</td>\n" %(componentVersionName))


        #  Is there a valid URL to link to?
        if selectedLicenseUrl == "":
            html_ptr.write("            <td class='text-left'>%s</td>\n" %(selectedLicenseName))
        else:
            html_ptr.write("            <td class='text-left'><a href='%s' target='_blank'>%s</a></td>\n" %(selectedLicenseUrl, selectedLicenseName))

        html_ptr.write("            </td>\n")

        # Apply color styling based on approval status
        if approvalStatus == "Not Reviewed":
            html_ptr.write("            <td class='text-left'><span style='color: #007bff;'>%s</span></td>\n" %(approvalStatus))
        elif approvalStatus == "Approved":
            html_ptr.write("            <td class='text-left' style='color: green;'>%s</td>\n" %(approvalStatus))
        elif approvalStatus == "Rejected":
            html_ptr.write("            <td class='text-left' style='color: red;'>%s</td>\n" %(approvalStatus))
        else:
            html_ptr.write("            <td class='text-left'>%s</td>\n" %(approvalStatus))
        
        html_ptr.write("            <td class='text-left'>%s</td>\n" %(usageText))


        if reportOptions["includeVulnerabilities"]:
            if hasVulnerabilities:
                html_ptr.write("            <td class='text-left'>Yes</td>\n")
            else:
                html_ptr.write("            <td class='text-left'>&nbsp</td>\n")

        html_ptr.write("        </tr>\n") 
    html_ptr.write("    </tbody>\n")
    html_ptr.write("</table>\n")  

    html_ptr.write("<!-- END BODY -->\n")  

    #---------------------------------------------------------------------------------------------------
    # Report Footer
    #---------------------------------------------------------------------------------------------------
    html_ptr.write("<!-- BEGIN FOOTER -->\n")
    html_ptr.write("<div class='report-footer'>\n")
    html_ptr.write("  <div style='float:right'>Generated on %s</div>\n" %reportTimeStamp)
    html_ptr.write("<br>\n")
    html_ptr.write("  <div style='float:right'>Report Version: %s</div>\n" %_version.__version__)
    html_ptr.write("</div>\n")
    html_ptr.write("<!-- END FOOTER -->\n")   

    html_ptr.write("</div>\n")

    #---------------------------------------------------------------------------------------------------
    # Add javascript 
    #---------------------------------------------------------------------------------------------------

    html_ptr.write('''

    <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
    <script src="https://cdn.datatables.net/1.10.21/js/jquery.dataTables.min.js"></script>  
    <script src="https://cdn.datatables.net/1.10.21/js/dataTables.bootstrap4.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.3.10/jstree.min.js"></script>
    ''')

    html_ptr.write("<script>\n")
    
    # Logic for datatable for inventory details
    if len(projectList) > 1:
        # The project names are included so the inventory row is column 1
        sortByColumn = 1
    else:
        # Inventory items are the first column
        sortByColumn = 0
    
    add_inventory_datatable(html_ptr, sortByColumn)

    

    if len(projectList) > 1:
        # Add the js for the project summary stacked bar charts
        generate_project_hierarchy_tree(html_ptr, projectList, projectInventoryCount)


    html_ptr.write("</script>\n")

    html_ptr.write("</body>\n") 
    html_ptr.write("</html>\n") 
    html_ptr.close() 

    logger.info("    Exiting generate_html_report")
    return htmlFile


####################################################################
def encodeImage(imageFile):

    #############################################
    # Create base64 variable for branding image
    try:
        with open(imageFile,"rb") as image:
            encodedImage = base64.b64encode(image.read())
            return encodedImage
    except:
        logger.error("Unable to open %s" %imageFile)
        raise


#----------------------------------------------------------------------------------------#
def add_inventory_datatable(html_ptr, sortByColumn):
    # Add the js for inventory datatable
    html_ptr.write('''

            $(document).ready(function (){
                var table = $('#inventoryData').DataTable({
                    "order": [ ''' +  str(sortByColumn) + ''', 'asc' ],
                    "lengthMenu": [ [25, 50, 100, -1], [25, 50, 100, "All"] ],
                });
            });
        ''')    

#----------------------------------------------------------------------------------------#
def generate_project_hierarchy_tree(html_ptr, projectHierarchy, projectInventoryCount):
    logger.info("    Entering generate_project_hierarchy_tree")

    html_ptr.write('''var hierarchy = [\n''')

    for project in projectHierarchy:

        inventoryCount = projectInventoryCount[project["projectName"]]

        # is this the top most parent or a child project with a parent
        if "uniqueID" in project:
            projectIdentifier = project["uniqueID"]
        else:
            projectIdentifier = project["projectID"]

        html_ptr.write('''{
            'id': '%s', 
            'parent': '%s', 
            'text': '%s',
            'a_attr': {
                'href': '%s'
            }
        },\n'''  %(projectIdentifier, project["parent"], project["applicationNameVersion"] + " (" + str(inventoryCount) + " items)" , project["projectLink"]))

    html_ptr.write('''\n]''')

    html_ptr.write('''

        $('#project_hierarchy').jstree({ 'core' : {
            'data' : hierarchy
        } });

        $('#project_hierarchy').on('ready.jstree', function() {
            $("#project_hierarchy").jstree("open_all");               

        $("#project_hierarchy").on("click", ".jstree-anchor", function(evt)
        {
            var link = $(evt.target).attr("href");
            window.open(link, '_blank');
        });


        });

    ''' )




