import os
import sys
import logging
from pathlib import Path

# Import our modules
from config_manager import ConfigManager
from gitlab_connector import GitLabConnector, RepositoryManager
from build_checker import BuildChecker
from checkstyle_runner import CheckstyleRunner

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Status markers
SUCCESS = "SUCCESS"
ERROR = "ERROR"
WARNING = "WARNING"

class JavaProjectChecker:
    """Main class to orchestrate the GitLab Java project quality check"""
    
    def __init__(self):
        # Initialize config manager
        self.config_manager = ConfigManager()
        self.args = self.config_manager.args
        
        # Setup workspace
        if not self.args.workspace:
            self.args.workspace = str(Path(os.getcwd()) / "java-projects")
        
        # Initialize GitLab connector
        self.gitlab_connector = GitLabConnector(self.args.gitlab_url, self.args.token)
        
        # Initialize repository manager
        self.repo_manager = RepositoryManager(self.gitlab_connector.gl, self.args.workspace)
        
        # Store results for retrieval
        self.repo_path = None
        self.build_checker = None
        self.checkstyle_runner = None
        self.build_success = False
        self.checkstyle_success = False
        self.quality_success = False
    
    def run(self):
        """Run the project quality checks"""
        logger.info("\n# Starting GitLab Java Project Quality Check")
        logger.info("=" * 60)
        
        # Print configuration source
        if self.args.config:
            logger.info(f"Using configuration from file: {self.args.config}")
        else:
            logger.info("Using command-line arguments")
        
        # Clone the repository
        self.repo_path = self.repo_manager.clone_repository(
            self.args.project_id, 
            self.args.project_hw, 
            self.args.branch, 
            self.args.ssh_url, 
            self.args.accept_hostkey, 
            self.args.username, 
            self.args.password
        )
        
        # Always run build check first
        logger.info("\nRunning build check...")
        self.build_checker = BuildChecker(self.repo_path)
        self.build_success = self.build_checker.check_build()
        
        # Track overall quality success
        self.quality_success = self.build_success
        
        # Handle build failure based on fail_on_issues setting
        self.checkstyle_success = True
        if not self.build_success:
            if self.args.fail_on_issues:
                logger.info("\nBuild failed and fail_on_issues is set to true. Exiting without running checkstyle.")
                sys.exit(1)
            else:
                logger.info("\nBuild failed but fail_on_issues is false. Continuing with checkstyle check.")
        
        # Run Checkstyle regardless of build result (unless we've already exited)
        logger.info("\nRunning Checkstyle for quality checks...")
        self.checkstyle_runner = CheckstyleRunner(self.repo_path)
        self.checkstyle_success = self.checkstyle_runner.run_checkstyle(self.args.checkstyle_config)
        if not self.checkstyle_success:
            self.quality_success = False
        
        # Print summary
        logger.info("\n# Summary Report")
        logger.info("=" * 60)
        
        logger.info(f"Build check: {SUCCESS + ' PASSED' if self.build_success else ERROR + ' FAILED'}")
        
        # Report on checkstyle check regardless of build status
        logger.info(f"Checkstyle check: {SUCCESS + ' PASSED' if self.checkstyle_success else WARNING + ' ISSUES FOUND'}")
        
        # Provide appropriate summary based on build and checkstyle results
        if self.build_success:
            if self.quality_success:
                logger.info(f"\n{SUCCESS} Success! The project builds and passes all quality checks.")
            else:
                logger.info(f"\n{WARNING} The project builds but has quality issues.")
        else:
            if self.checkstyle_success:
                logger.info(f"\n{ERROR} The project failed to build, but passes style checks.")
            else:
                logger.info(f"\n{ERROR} The project failed to build and has style issues.")
        
        # Print locations of logs and reports
        logger.info(f"\nBuild logs directory: {Path(self.repo_path) / 'build-logs'}")
        logger.info(f"Checkstyle reports directory: {Path(self.repo_path) / 'checkstyle-reports'}")
        
        # Exit with error code if requested and any issues found (build or checkstyle)
        if self.args.fail_on_issues and not self.quality_success:
            logger.warning("Exiting with error code due to quality issues (--fail-on-issues flag is set)")
            sys.exit(1)
        # Note: We've already handled the case where build fails and fail_on_issues is true earlier
        
        return {
            'repo_path': self.repo_path,
            'build_success': self.build_success,
            'checkstyle_success': self.checkstyle_success,
            'quality_success': self.quality_success,
            'build_log': self.build_checker.get_log_path() if self.build_checker else None,
            'checkstyle_report': self.checkstyle_runner.get_report_path() if self.checkstyle_runner else None
        }

if __name__ == "__main__":
    checker = JavaProjectChecker()
    checker.run()