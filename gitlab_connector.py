import os
import sys
import subprocess
import logging
from pathlib import Path

# Import required packages
try:
    import gitlab
except ImportError:
    logging.info("Required package 'gitlab' not found. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "gitlab"])
    import gitlab

# Status markers
SUCCESS = "SUCCESS"
ERROR = "ERROR"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class GitLabConnector:
    """Handles connections to GitLab"""
    
    def __init__(self, gitlab_url, token):
        self.gitlab_url = gitlab_url
        self.token = token
        self.gl = self.connect()
    
    def connect(self):
        """Connect to GitLab server and authenticate"""
        try:
            gl = gitlab.Gitlab(self.gitlab_url, private_token=self.token)
            gl.auth()
            logger.info(f"{SUCCESS} Successfully connected to GitLab server at {self.gitlab_url}")
            return gl
        except gitlab.exceptions.GitlabAuthenticationError:
            logger.error(f"{ERROR} Authentication failed. Please check your GitLab token.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"{ERROR} Failed to connect to GitLab: {str(e)}")
            sys.exit(1)


class RepositoryManager:
    """Handles repository cloning and management"""
    
    def __init__(self, gl, workspace):
        self.gl = gl
        self.workspace = workspace or str(Path(os.getcwd()) / "java-projects")
    
    def clone_repository(self, project_id, project_hw, branch, custom_ssh_url=None, accept_hostkey=False, username=None, password=None):
        """Clone the specified GitLab repository"""
        try:  
            full_project_id = f"{project_id}/{project_hw}"       
            clone_path = Path(f"{self.workspace}/{full_project_id}")
            
            if not os.path.isdir(clone_path):
                clone_path.mkdir(parents=True, exist_ok=True)
                logger.info("Attempting clone with simplest approach...")
                simple_url = f"{self.gl._base_url.replace('/api/v4', '')}/{full_project_id}.git"
                logger.info(f"Clone URL: {simple_url}")
                
                cmd = f"git clone {simple_url} {str(clone_path)}"        
                logger.info(f"Running command: {cmd}")
                
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, universal_newlines=True)
                    if result.returncode == 0:
                        logger.info(f"{SUCCESS} Repository cloned successfully")
                        return clone_path
                    else:
                        logger.error(f"Clone failed: {result.stderr}")
                        sys.exit(1)
                except Exception as e:
                    logger.error(f"Error during clone: {str(e)}")
                    sys.exit(1)
            else:
                logger.info(f"{SUCCESS} Repository already exists at: {clone_path}")
                return clone_path
        
        except Exception as e:
            logger.error(f"{ERROR} Error during repository cloning: {str(e)}")
            sys.exit(1)