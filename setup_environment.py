#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import logging
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def install_python_dependencies():
    """Install required Python packages from requirements.txt"""
    logger.info("Installing Python dependencies...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        logger.error("requirements.txt not found!")
        return False
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        logger.info("Python dependencies installed successfully!")
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to install Python dependencies: {str(e)}")
        return False

def check_java_installation():
    """
    Check if Java is installed and available.
    Returns:
        tuple: (is_installed, javac_path)
    """
    # First check if javac is in PATH
    javac_path = shutil.which("javac")
    if javac_path:
        try:
            # Verify it works
            result = subprocess.run([javac_path, "-version"], 
                                    capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Java found: {javac_path}")
                logger.info(f"Java version: {result.stderr.strip() or result.stdout.strip()}")
                return True, javac_path
        except Exception as e:
            logger.warning(f"Java found but encountered an error: {str(e)}")
    
    # Check JAVA_HOME
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        if platform.system() == "Windows":
            candidate_path = os.path.join(java_home, "bin", "javac.exe")
        else:
            candidate_path = os.path.join(java_home, "bin", "javac")
            
        if os.path.exists(candidate_path):
            logger.info(f"Java found via JAVA_HOME: {candidate_path}")
            try:
                result = subprocess.run([candidate_path, "-version"], 
                                       capture_output=True, text=True)
                logger.info(f"Java version: {result.stderr.strip() or result.stdout.strip()}")
            except Exception:
                pass
            return True, candidate_path
    
    # If we get here, Java is not properly installed/configured
    logger.warning(f"Java JDK not found. Will attempt to install.")
    return False, None

def install_java():
    """
    Attempt to install Java if it's not already installed.
    Returns:
        bool: True if installation was successful, False otherwise
    """
    system = platform.system()
    
    if system == "Linux":
        # Check which package manager is available
        if shutil.which("apt-get"):
            logger.info("Attempting to install OpenJDK using apt-get...")
            try:
                # Update package list
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                # Install OpenJDK
                subprocess.run(["sudo", "apt-get", "install", "-y", "default-jdk"], check=True)
                logger.info("Java JDK installed successfully!")
                return True
            except subprocess.SubprocessError as e:
                logger.error(f"Failed to install Java: {str(e)}")
        
        elif shutil.which("yum"):
            logger.info("Attempting to install OpenJDK using yum...")
            try:
                subprocess.run(["sudo", "yum", "install", "-y", "java-11-openjdk-devel"], check=True)
                logger.info("Java JDK installed successfully!")
                return True
            except subprocess.SubprocessError as e:
                logger.error(f"Failed to install Java: {str(e)}")
        
        elif shutil.which("dnf"):
            logger.info("Attempting to install OpenJDK using dnf...")
            try:
                subprocess.run(["sudo", "dnf", "install", "-y", "java-11-openjdk-devel"], check=True)
                logger.info("Java JDK installed successfully!")
                return True
            except subprocess.SubprocessError as e:
                logger.error(f"Failed to install Java: {str(e)}")
    
    elif system == "Windows":
        logger.error("Automatic Java installation on Windows is not supported.")
        logger.info("Please download and install Java JDK manually from: https://adoptium.net/")
        logger.info("After installation, restart this script.")
        
    logger.error("Could not install Java automatically. Please install it manually.")
    return False

def main():
    """Set up the environment for the quality checker."""
    logger.info("Setting up environment for Java Project Quality Checker...")
    
    # Check for Java installation
    java_installed, _ = check_java_installation()
    if not java_installed:
        if install_java():
            logger.info("Java installation successful.")
        else:
            logger.error("Java installation failed. Please install manually.")
           
            return False
    
    # Install Python dependencies
    # if not install_python_dependencies():
    #     logger.error("Failed to install Python dependencies.")
    #     return False
    
    logger.info("Environment setup complete!")
    logger.info("You can now run the quality checker.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)