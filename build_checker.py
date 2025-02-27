import os
import sys
import subprocess
import datetime
import logging
from pathlib import Path

# Status markers
SUCCESS = "SUCCESS"
ERROR = "ERROR"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class BuildChecker:
    """Handles Java project build verification"""
    
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.logs_dir = Path(repo_path) / "build-logs"
        self.logs_dir.mkdir(exist_ok=True)
        self.log_file = self.logs_dir / f"build-log-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    
    def check_build(self):
        """Check if the Java project builds successfully and save logs to a text file"""
        logger.info("\nChecking if the project builds...")
        logger.info("=" * 60)
        
        # Open the log file with UTF-8 encoding
        with open(self.log_file, 'w', encoding='utf-8') as log:
            log.write(f"=== Build Log for {self.repo_path} ===\n")
            log.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")  

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
                    # Remove duplicates that might have been found
                java_files = list(set(java_files))
                    
                if not java_files:
                    log.write(f"{ERROR} No Java files found in the repository\n")
                    logger.info(f"{ERROR} No Java files found in the repository")
                    return False                    
                log.write(f"Found {len(java_files)} Java files to compile:\n")
                logger.info(f"Found {len(java_files)} Java files to compile:")
                
                for java_file in java_files:
                    rel_path = java_file.relative_to(self.repo_path)
                    log.write(f"  - {rel_path}\n")
                    logger.info(f"  - {rel_path}")
                    
                # Create a bin output directory
                output_dir = Path(self.repo_path) / "bin"
                output_dir.mkdir(exist_ok=True)
                    
                # Try to compile each Java file with UTF-8 encoding
                success = True
                for java_file in java_files:
                    rel_path = java_file.relative_to(self.repo_path)
                    log.write(f"\nCompiling: {rel_path}\n")
                    logger.info(f"\nCompiling: {rel_path}")
                        
                    # Add -encoding UTF-8 to the javac command
                    cmd = f"javac -encoding UTF-8 -d {output_dir} {java_file}"
                    log.write(f"Running: {cmd}\n")
                    logger.info(f"Running: {cmd}")
                    result = subprocess.run(cmd, shell=True, capture_output=True, universal_newlines=True, env=dict(os.environ, JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF-8"))                        
                    log.write(result.stdout or "")
                    log.write(result.stderr or "")
                        
                    if result.returncode != 0:
                        log.write(f"{ERROR} Compilation failed for {java_file.name}\n")
                        logger.info(f"{ERROR} Compilation failed for {java_file.name}")
                        logger.info("\nCompilation Errors:")
                        logger.info(result.stderr or result.stdout or "")
                        success = False
                        break                    
                if success:
                    log.write(f"\n{SUCCESS} All Java files compiled successfully\n")
                    logger.info(f"\n{SUCCESS} All Java files compiled successfully")
                    return True
                else:
                    # Last resort: try to compile everything at once with UTF-8 encoding
                    log.write("\nIndividual compilation failed.\n")
                    logger.info("\nIndividual compilation failed.")                                           
            except Exception as e:
                error_msg = f"{ERROR} Error during build check: {str(e)}"
                log.write(f"{error_msg}\n")
                logger.error(error_msg)
                return False        
        logger.info(f"Build log saved to: {self.log_file}")
        return False
        
    def get_log_path(self):
        """Return the path to the build log file"""
        return self.log_file