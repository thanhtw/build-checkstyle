import os
import sys
import subprocess
import datetime
import urllib.request
import logging
from pathlib import Path

# Status markers
SUCCESS = "SUCCESS"
ERROR = "ERROR"
WARNING = "WARNING"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class CheckstyleRunner:
    """Handles running Checkstyle on Java code"""
    
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.reports_dir = Path(repo_path) / "checkstyle-reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.txt_report = self.reports_dir / f"checkstyle-report-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"       
        self.violations = []
        self.violations_count = 0
        self.files_with_violations = 0
    
    def download_checkstyle(self):
        """Download the latest Checkstyle jar file and save it in a permanent location"""
        # Use a permanent directory in user's home directory
        home_dir = Path(os.getcwd())
        checkstyle_dir = home_dir / "checkstyle"
        checkstyle_jar = checkstyle_dir / "checkstyle.jar"        
        # Create directory if it doesn't exist
        checkstyle_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if checkstyle jar already exists
        if checkstyle_jar.exists():
            logger.info(f"{SUCCESS} Checkstyle jar already exists at {checkstyle_jar}")
            return str(checkstyle_jar)        
        # Download the latest checkstyle jar
        try:
            logger.info("Downloading Checkstyle jar...")
            checkstyle_url = "https://github.com/checkstyle/checkstyle/releases/download/checkstyle-10.21.3/checkstyle-10.21.3-all.jar"
            urllib.request.urlretrieve(checkstyle_url, checkstyle_jar)
            logger.info(f"{SUCCESS} Downloaded Checkstyle jar to {checkstyle_jar}")
            return str(checkstyle_jar)
        except Exception as e:
            logger.error(f"{ERROR} Failed to download Checkstyle jar: {str(e)}")
            return None
    
    def checkstyle_config(self):
        """Create an improved Checkstyle configuration file that catches common issues"""
        home_dir = Path(os.getcwd())
        checkstyle_dir = home_dir / "checkstyle"
        config_file = checkstyle_dir / "sun_checks.xml"
        
        # Create directory if it doesn't exist
        checkstyle_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if config file already exists
        if config_file.exists():
            logger.info(f"{SUCCESS} Using existing improved Checkstyle config: {config_file}")
            return str(config_file)
        
        
        # Write the improved config file
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_file)
        
        logger.info(f"{SUCCESS} Created improved Checkstyle config at {config_file}")
        return str(config_file)
    
    
    def run_checkstyle(self, custom_config=None):
        """Run Checkstyle on the Java project and save results to a text file"""
        logger.info("\nRunning Checkstyle on the project...")
        logger.info("=" * 60)        
        # Download or use existing Checkstyle jar
        checkstyle_jar = self.download_checkstyle()
        if not checkstyle_jar:
            logger.error(f"{ERROR} Cannot run Checkstyle without the jar file")
            return False
        
        # Use custom config if provided, otherwise use improved config
        if custom_config and Path(custom_config).exists():
            config_file = custom_config
            logger.info(f"Using custom Checkstyle config: {config_file}")
        else:
            # Use our improved config instead of a simple one
            config_file = self.checkstyle_config()
            if not config_file:
                logger.error(f"{ERROR} Cannot run Checkstyle without a config file")
                return False
        
        try:
            # Find all Java files
            src_dir = Path(self.repo_path) / "src"
            java_files = []
            
            # Check if src directory exists
            if src_dir.exists() and src_dir.is_dir():
                # First check for files directly in src directory
                java_files.extend(list(src_dir.glob("*.java")))
                
                # Then check for files in subdirectories of src
                java_files.extend(list(src_dir.glob("**/*.java")))
            else:
                # If no src directory, look for Java files anywhere in the repo
                java_files = list(Path(self.repo_path).glob("**/*.java"))
            
            # Remove duplicates
            java_files = list(set(java_files))
            
            if not java_files:
                logger.error(f"{ERROR} No Java files found in the repository")
                return False
            
            logger.info(f"Found {len(java_files)} Java files to check:")
            for java_file in java_files:
                logger.info(f"  - {java_file.relative_to(self.repo_path)}")
            
            # Open the text report file with UTF-8 encoding
            with open(self.txt_report, 'w', encoding='utf-8') as report:
                report.write(f"=== Checkstyle Report for {self.repo_path} ===\n")
                report.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                report.write(f"Configuration: {config_file}\n\n")
                
                # Create a consolidated report for all files
                all_violations = []
                violations_count = 0
                files_with_violations = 0
                
                # Process each file individually for better control
                for i, java_file in enumerate(java_files):
                    file_name = java_file.name
                    rel_path = java_file.relative_to(self.repo_path)
                    
                    report.write(f"\n--- File: {rel_path} ---\n")
                    logger.info(f"\nRunning Checkstyle on file {i+1}/{len(java_files)}: {rel_path}")
                    
                    # Run with plain text format for immediate feedback using UTF-8 encoding
                    text_cmd = f"java -Dfile.encoding=UTF-8 -jar {checkstyle_jar} -c {config_file} {java_file}"
                    text_result = subprocess.run(text_cmd, shell=True, capture_output=True, universal_newlines=True, env=dict(os.environ, JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF-8"))
                    
                    # Write the output to the report
                    if text_result.stdout:
                        report.write(text_result.stdout)
                    if text_result.stderr:
                        report.write(text_result.stderr)
                        # Check if there's a checkstyle error (not just a style violation)
                        if "CheckstyleException" in text_result.stderr:
                            logger.warning(f"Checkstyle error (not a style violation): {text_result.stderr.strip()}")
                            logger.warning("This might be a compatibility issue with the Checkstyle configuration.")
                            continue
                    
                    # Check for violations in the text output
                    file_has_violations = False
                    file_violations = []
                    
                    if text_result.stderr and "error" in text_result.stderr.lower() and "CheckstyleException" not in text_result.stderr:
                        file_has_violations = True
                        logger.info(f"{WARNING} Found style violations in {file_name}")
                        
                        # Try to parse violations from text output
                        lines = text_result.stderr.splitlines()
                        for line in lines:
                            if ":" in line and "[ERROR]" in line:
                                file_violations.append(line)
                    
                    if text_result.stdout and "error" in text_result.stdout.lower():
                        file_has_violations = True
                        logger.info(f"{WARNING} Found style violations in {file_name}")
                        
                        # Try to parse violations from text output
                        lines = text_result.stdout.splitlines()
                        for line in lines:
                            if ":" in line and "[ERROR]" in line:
                                file_violations.append(line)
                    
                    # If we found violations, update our counts
                    if file_has_violations:
                        files_with_violations += 1
                        violations_count += len(file_violations)
                        all_violations.extend(file_violations)
                
                # Write summary
                report.write("\n\n=== Summary ===\n")
                if violations_count > 0:
                    report.write(f"Total: {violations_count} style violations in {files_with_violations} files\n")
                    logger.info(f"\n{WARNING} Checkstyle found {violations_count} style violations in {files_with_violations} files")
                    self.violations = all_violations
                    self.violations_count = violations_count
                    self.files_with_violations = files_with_violations                     
                    return False
                else:
                    report.write("No Checkstyle errors found.\n")
                    logger.info(f"{SUCCESS} Checkstyle passed with no violations")
                    return True
                    
        except Exception as e:
            logger.error(f"{ERROR} Error during Checkstyle check: {str(e)}")
            return False
        
        logger.info(f"Checkstyle report saved to: {self.txt_report}")
        return False
        
    def get_report_path(self):
        """Return the path to the checkstyle report file"""
        return self.txt_report
        
    def get_violations_summary(self):
        """Return a summary of the violations found"""
        return {
            'violations': self.violations,
            'count': self.violations_count,
            'files_with_violations': self.files_with_violations
        }