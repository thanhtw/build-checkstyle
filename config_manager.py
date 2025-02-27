import sys
import argparse
import yaml
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Status markers
SUCCESS = "SUCCESS"
ERROR = "ERROR"
WARNING = "WARNING"

class ConfigManager:
    """Handles configuration loading and command-line arguments"""
    
    def __init__(self):
        self.args = self.parse_arguments()
    
    def load_config(self, config_path):
        """Load configuration from a YAML file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as config_file:
                config = yaml.safe_load(config_file)
            logger.info(f"{SUCCESS} Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"{ERROR} Failed to load configuration: {str(e)}")
            sys.exit(1)
    
    def parse_arguments(self):
        """Parse command line arguments and merge with config file if provided"""
        parser = argparse.ArgumentParser(description='Clone a GitLab Java project and perform quality checks')
        parser.add_argument('--config', help='Path to configuration file (YAML)')
        parser.add_argument('--gitlab-url', help='GitLab server URL (API endpoint)')
        parser.add_argument('--token', help='GitLab personal access token')
        parser.add_argument('--project-id', help='GitLab project ID or path (e.g., group/project)')
        parser.add_argument('--project-hw', help='GitLab project hw or path (e.g., group/hw)')
        parser.add_argument('--branch', default=None, help='Branch to checkout (default: main)')
        parser.add_argument('--workspace', default=None, help='Local directory to clone into (default: temporary directory)')
        parser.add_argument('--checkstyle-config', help='Path to custom Checkstyle configuration')  
        parser.add_argument('--ssh-url', help='Custom SSH URL for cloning (overrides the URL from GitLab API)')
        parser.add_argument('--accept-hostkey', action='store_true', help='Accept SSH host key automatically')
        parser.add_argument('--username', help='Username for GitLab authentication')
        parser.add_argument('--password', help='Password for GitLab authentication')
        parser.add_argument('--fail-on-issues', action='store_true', help='Exit with error code if quality issues are found')
        
        args = parser.parse_args()
        
        # Load config file if provided and merge with command line args
        if args.config:
            config = self.load_config(args.config)
            args = self.merge_config_with_args(args, config)
        
        # Validate required arguments
        self.validate_required_args(args)
        
        return args
    
    def merge_config_with_args(self, args, config):
        """Merge config file values with command line arguments"""
        # GitLab connection settings
        if not args.gitlab_url and 'gitlab' in config and 'url' in config['gitlab']:
            args.gitlab_url = config['gitlab']['url']
        
        if not args.token and 'gitlab' in config and 'token' in config['gitlab']:
            args.token = config['gitlab']['token']
        
        # Project settings
        if not args.project_id and 'project' in config and 'id' in config['project']:
            args.project_id = config['project']['id']
            args.project_hw = config['project']['hw']
        
        if args.branch is None and 'project' in config and 'branch' in config['project']:
            args.branch = config['project']['branch']
        elif args.branch is None:
            args.branch = 'main'  # Default branch if not specified
        
        # Workspace settings
        if args.workspace is None and 'workspace' in config and 'path' in config['workspace']:
            args.workspace = config['workspace']['path']
        
        # Checkstyle settings
        if not args.checkstyle_config and 'checkstyle' in config and 'config_path' in config['checkstyle']:
            args.checkstyle_config = config['checkstyle']['config_path']
        
        # Git connection settings
        if not args.ssh_url and 'git' in config and 'ssh_url' in config['git']:
            args.ssh_url = config['git']['ssh_url']
            
        if not args.accept_hostkey and 'git' in config and 'accept_hostkey' in config['git']:
            args.accept_hostkey = config['git']['accept_hostkey']
            
        if not args.username and 'git' in config and 'username' in config['git']:
            args.username = config['git']['username']
            
        if not args.password and 'git' in config and 'password' in config['git']:
            args.password = config['git']['password']
            
        # Other settings
        if not args.fail_on_issues and 'quality' in config and 'fail_on_issues' in config['quality']:
            args.fail_on_issues = config['quality']['fail_on_issues']
        
        return args
    
    def validate_required_args(self, args):
        """Validate that required arguments are present"""
        if not args.gitlab_url:
            logger.error(f"{ERROR} GitLab URL is required. Provide it via --gitlab-url or in config file.")
            sys.exit(1)
        
        if not args.token:
            logger.error(f"{ERROR} GitLab token is required. Provide it via --token or in config file.")
            sys.exit(1)
        
        if not args.project_id:
            logger.error(f"{ERROR} Project ID is required. Provide it via --project-id or in config file.")
            sys.exit(1)