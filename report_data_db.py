"""
Copyright 2022 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sarthak
Created On : Thu Apr 24 2022
Modified On: Mon 07 2025
File : report_data_db.py
"""
import sys
import threading
import subprocess
import logging
import os
import configparser
import json
from packaging.version import parse as parse_version

logger = logging.getLogger(__name__)


# User can set this variable directly in code
user_java_path = ""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Determine the correct Java executable name
java_exec = "java.exe" if os.name == "nt" else "java"
DEFAULT_JAVA_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', '..', 'jre', 'bin', java_exec))
# Check JAVA_HOME and construct the java path
java_home = os.environ.get('JAVA_HOME')
if user_java_path != "":
    JAVA_PATH = user_java_path
elif java_home:
    JAVA_PATH = os.path.join(java_home, 'bin', java_exec)
else:
    JAVA_PATH = DEFAULT_JAVA_PATH

if not os.path.exists(JAVA_PATH):
    error_msg = (
        f"Java executable not found at: {JAVA_PATH}\n"
        "Please ensure Java is installed and accessible. You can:\n"
        "1. Set the JAVA_HOME environment variable to your Java installation directory\n"
        "2. Manually set the 'user_java_path' variable in this file:\n"
        f"   {os.path.abspath(__file__)}\n"
        f"   Example: user_java_path = r'C:\\Program Files\\Java\\jdk-11\\bin\\{java_exec}'"
    )
    logger.error(error_msg)
    sys.exit(error_msg)

print(f"Using Java path: {JAVA_PATH}")  # Debugging line to check the Java path
JAR_PATH = os.path.join(BASE_DIR, '..', '..', 'samples', 'customreport_helper', 'DbConnection.jar')
properties_file = os.path.join(BASE_DIR, '..', '..', 'config', 'core', 'core.db.properties')

if not os.path.exists(JAR_PATH):
    error_msg = (
        "DbConnection.jar is missing at: "
        f"{os.path.abspath(JAR_PATH)}. "
        "This means your Code Insight server is older than 2025 R3. "
        "Please upgrade to 2025 R3 or later, or get DbConnection.jar file from support "
        "and place it in <Install Location>\\samples\\customreport_helper."
    )
    logger.error(error_msg)
    sys.exit(error_msg)

class InteractiveDbQueryRunner:
    def __init__(self, jar_path, java_path=JAVA_PATH):
        try:
            # Get absolute path to properties file
            abs_properties_path = os.path.abspath(properties_file)
            logger.info(f"Starting Java process with: {java_path} -jar {jar_path} {abs_properties_path}")
            
            self.proc = subprocess.Popen(
                [java_path, "-jar", jar_path, abs_properties_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            logger.info(f"Java process started with PID: {self.proc.pid}")
            
            # Check if process started successfully
            import time
            time.sleep(0.1)  # Give it a moment to start
            if self.proc.poll() is not None:
                stderr_output = self.proc.stderr.read() if self.proc.stderr else "No stderr available"
                raise RuntimeError(f"Java process terminated immediately. Exit code: {self.proc.returncode}, stderr: {stderr_output}")
                
        except Exception as e:
            logger.error(f"Failed to start Java process: {e}")
            raise
        
        self.lock = threading.Lock()
        
        # Try to set autocommit on
        try:
            self.run_query("SET autocommit = true;")
            logger.info("Set database autocommit to true")
        except Exception as e:
            logger.warning(f"Could not set autocommit mode: {e}")

    def run_query(self, sql_query):
        with self.lock:
            if self.proc.poll() is not None:
                raise RuntimeError("Java process is not running")
            self.proc.stdin.write(sql_query + "\n")
            self.proc.stdin.flush()
            output = ""
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    break
                output += line
                if line.strip().endswith("]") or line.strip().endswith("}"):
                    break
            
            try:
                result = json.loads(output)
                # For INSERT, UPDATE, DELETE operations, try to commit automatically
                if any(keyword in sql_query.upper() for keyword in ['INSERT', 'UPDATE', 'DELETE']) and 'COMMIT' not in sql_query.upper():
                    try:
                        self.proc.stdin.write("COMMIT;\n")
                        self.proc.stdin.flush()
                        commit_output = ""
                        while True:
                            line = self.proc.stdout.readline()
                            if not line:
                                break
                            commit_output += line
                            if line.strip().endswith("]") or line.strip().endswith("}"):
                                break
                    except Exception as e:
                        logger.warning(f"Auto-commit failed: {e}")
                
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}, Raw output: {output}")
                return []

    def close(self):
        if self.proc and self.proc.poll() is None:
            try:
                if self.proc.stdin:
                    self.proc.stdin.write("exit\n")
                    self.proc.stdin.flush()
            except Exception as e:
                logger.warning(f"Error sending exit to Java process: {e}")
            try:
                self.proc.terminate()
            except Exception as e:
                logger.warning(f"Error terminating Java process: {e}")
            self.proc = None
db_runner = InteractiveDbQueryRunner(JAR_PATH, JAVA_PATH)


def get_db_vendor():
    global db_vendor # Declare db_vendor as global variable
    is_property_file_exists = check_properties_file_exists()
    if is_property_file_exists:
        logger.info("Reading core.db.properties file")
        with open(properties_file, 'r') as file:
            # Add a dummy section header to make it compatible with configparser
            lines = ['[DEFAULT]\n']
            for line in file:
                # Skip comments starting with #
                if not line.strip().startswith('#'):
                    lines.append(line)
    
        config = configparser.ConfigParser()
        config.read_string(''.join(lines))

        # Read database configuration from the selected section
        db_vendor = config['DEFAULT']['db.vendor']
        if db_vendor is not None:
            return db_vendor.lower()

def check_properties_file_exists():
    try:
        with open(properties_file, 'r') as file:
            return True
    except FileNotFoundError:
        print(f"Properties file {properties_file} not found.")
        return False

def get_projects_data(project_id):
    sql = f"SELECT NAME_ AS topLevelProjectName FROM PAS_PROJECT WHERE ID_ = {project_id};"
    result = db_runner.run_query(sql)
    if result and isinstance(result, list) and len(result) > 0 and 'topLevelProjectName' in result[0]:
        return result[0]['topLevelProjectName']
    else:
        logger.warning(f"No project found for ID {project_id}")
        return None

def get_inventory_data(project_id):
    sql = f"""SELECT INV_GRP.ID_ AS inventoryId, INV_GRP.NAME_ AS inventoryItemName, COMP.NAME_ AS componentName, COMP.URL_ AS componentUrl, COMP_VER.ID_ AS componentVersionId, COMP_VER.VERSION_NAME_ AS componentVersionName, LIC.NAME_ AS selectedLicenseName, LIC.SPDX_LICENSE_IDENTIFIER_ AS spdxIdentifier, LIC.SPDX_LICENSE_NAME_ AS spdxLicName, LIC.URL_ AS licenseUrl, INV_GRP.USER_STATUS_ID_ AS approvalStatus, INV_GRP.USAGE_TEXT_ AS usageText, CASE WHEN EXISTS (SELECT 1 FROM pdl_comp_ver_vulnerability VUL WHERE VUL.COMPONENT_VERSION_ID_ = COMP_VER.ID_) THEN 'Yes' ELSE 'No' END AS hasVulnerabilities FROM PSE_INVENTORY_GROUPS INV_GRP JOIN PAS_REPOSITORY_ITEM REPO_TAB ON INV_GRP.REPOSITORY_ITEM_ID_ = REPO_TAB.ID_ JOIN PDL_COMPONENT COMP ON REPO_TAB.COMPONENT_ID_ = COMP.ID_ LEFT JOIN PDL_COMPONENT_VERSION COMP_VER ON REPO_TAB.COMPONENT_VERSION_ID_ = COMP_VER.ID_ JOIN PDL_LICENSE LIC ON REPO_TAB.LICENSE_ID_ = LIC.ID_ WHERE INV_GRP.PROJECT_ID_ = {project_id} AND INV_GRP.PUBLISHED_ = 1;"""
    return db_runner.run_query(sql)

def get_inventory_data_custom(project_id):
    sql = f"""SELECT INV_GRP.ID_ AS inventoryId, INV_GRP.NAME_ AS inventoryItemName, COMP.NAME_ AS componentName, COMP.URL_ AS componentUrl, COMP_VER.ID_ AS componentVersionId, CUST_COMP_VER.VERSION_NAME_ AS componentVersionName, LIC.NAME_ AS selectedLicenseName, LIC.SPDX_LICENSE_IDENTIFIER_ AS spdxIdentifier, LIC.SPDX_LICENSE_NAME_ AS spdxLicName, LIC.URL_ AS licenseUrl, INV_GRP.USER_STATUS_ID_ AS approvalStatus, INV_GRP.USAGE_TEXT_ AS usageText, CASE WHEN EXISTS (SELECT 1 FROM pdl_comp_ver_vulnerability VUL WHERE VUL.COMPONENT_VERSION_ID_ = COMP_VER.ID_) THEN 'Yes' ELSE 'No' END AS hasVulnerabilities FROM PSE_INVENTORY_GROUPS INV_GRP JOIN PAS_REPOSITORY_ITEM REPO_TAB ON INV_GRP.REPOSITORY_ITEM_ID_ = REPO_TAB.ID_ JOIN PDL_COMPONENT COMP ON REPO_TAB.COMPONENT_ID_ = COMP.ID_ JOIN PDL_COMPONENT_VERSION_CUSTOM CUST_COMP_VER ON REPO_TAB.COMPONENT_VERSION_ID_ = CUST_COMP_VER.ID_ JOIN PDL_LICENSE LIC ON REPO_TAB.LICENSE_ID_ = LIC.ID_ LEFT JOIN PDL_COMPONENT_VERSION COMP_VER ON REPO_TAB.COMPONENT_VERSION_ID_ = COMP_VER.ID_ WHERE INV_GRP.PROJECT_ID_ = {project_id} AND INV_GRP.PUBLISHED_ = 1;"""
    return db_runner.run_query(sql)

def get_child_projects(project_id):
    project_ids = [project_id]
    subproject_ids_to_process = [project_id]
    while subproject_ids_to_process:
        current_project_id = subproject_ids_to_process.pop(0)
        sql = f"SELECT SUBPROJECT_ID_ as subProjectId FROM PAS_PROJECT_HIERARCHY WHERE PROJECT_ID_ = {current_project_id};"
        result = db_runner.run_query(sql)
        sub_ids = []
        if isinstance(result, list) and result:
            sub_ids = [row['subProjectId'] for row in result if 'subProjectId' in row and row['subProjectId'] is not None]
        elif result:
            logger.warning(f"Unexpected result format in get_child_projects for project {current_project_id}: {result}")
        if not sub_ids:
            logger.info(f"No subprojects found for project {current_project_id}")
        for sub_id in sub_ids:
            if sub_id not in project_ids:
                project_ids.append(sub_id)
                subproject_ids_to_process.append(sub_id)
    return project_ids

def get_custom_field_id(field_label="Licensable"):
    logger.info(f"Getting custom field ID for field label: '{field_label}'")
    
    try:
        # Get the field metadata for the specified field
        sql_meta = f"SELECT ID_, FIELD_NAME_ FROM PAS_INVENTORY_FLEX_FIELDS_METADATA WHERE FIELD_LABEL_ = '{field_label}';"
        meta_result = db_runner.run_query(sql_meta)
        
        if not meta_result or len(meta_result) == 0:
            logger.error(f"Custom field metadata for '{field_label}' not found. Please create it first in the system.")
            return None
        
        field_id = meta_result[0]['ID_']
        field_name = meta_result[0].get('FIELD_NAME_', 'Unknown')
        logger.info(f"Found custom field: ID={field_id}, FIELD_NAME={field_name}, LABEL={field_label}")
        
        return field_id
        
    except Exception as e:
        logger.error(f"Error in get_custom_field_id: {e}")
        return None



def get_project_hierarchy(project_id):
    logger.info(f"Building project hierarchy for project ID: {project_id}")
    
    def build_hierarchy(current_project_id):
        """Recursively build hierarchy for a given project ID"""
        # Get project name
        project_name = get_projects_data(current_project_id)
        if not project_name:
            logger.warning(f"No project name found for ID: {current_project_id}")
            project_name = f"Unknown Project {current_project_id}"
        
        # Get direct children of current project
        sql = f"SELECT SUBPROJECT_ID_ as subProjectId FROM PAS_PROJECT_HIERARCHY WHERE PROJECT_ID_ = {current_project_id};"
        result = db_runner.run_query(sql)
        
        child_projects = []
        if isinstance(result, list) and result:
            child_ids = [row['subProjectId'] for row in result if 'subProjectId' in row and row['subProjectId'] is not None]
            
            # Recursively build hierarchy for each child
            for child_id in child_ids:
                child_hierarchy = build_hierarchy(child_id)
                if child_hierarchy:
                    child_projects.append(child_hierarchy)
        
        return {
            'id': current_project_id,
            'name': project_name,
            'childProject': child_projects
        }
    
    try:
        hierarchy = build_hierarchy(project_id)
        logger.info(f"Successfully built project hierarchy: {hierarchy}")
        return hierarchy
    except Exception as e:
        logger.error(f"Error building project hierarchy: {e}")
        # Return basic structure in case of error
        project_name = get_projects_data(project_id) or f"Unknown Project {project_id}"
        return {
            'id': project_id,
            'name': project_name,
            'childProject': []
        }
    



