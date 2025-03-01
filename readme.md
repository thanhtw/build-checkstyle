# Java Project Quality Checker

This tool automatically clones a GitLab Java project and performs quality checks including build verification and checkstyle analysis.

## Prerequisites

Before using the Java Project Quality Checker, you must have Java Development Kit (JDK) installed on your system as the tool requires `javac` to build Java projects.

### Installing JDK on Ubuntu/Linux

```bash
# Update package lists
sudo apt update

# Install the default JDK package
sudo apt install default-jdk
```

Verify the installation:
```bash
javac -version
```

### Installing JDK on Windows

1. Download the latest JDK installer from the [Oracle website](https://www.oracle.com/java/technologies/downloads/) or [OpenJDK](https://adoptium.net/)
2. Run the installer and follow the installation wizard
3. Add Java to your PATH environment variable:
   - Right-click on 'This PC' or 'My Computer' and select 'Properties'
   - Click on 'Advanced system settings'
   - Click on 'Environment Variables'
   - Under 'System variables', find and select 'Path', then click 'Edit'
   - Click 'New' and add the path to the JDK bin directory (typically `C:\Program Files\Java\jdk-VERSION\bin`)
   - Click 'OK' to close all dialogs

Verify the installation by opening Command Prompt and typing:
```
javac -version


## Project Structure

The project has been organized into separate modules for better maintainability:

- `config_manager.py` - Handles configuration loading and command-line arguments
- `gitlab_connector.py` - Manages GitLab connections and repository cloning
- `build_checker.py` - Verifies that Java code builds correctly
- `checkstyle_runner.py` - Runs Checkstyle code quality checks
- `main.py` - Contains the main `JavaProjectChecker` class that orchestrates the process
- `run_checker.py` - Script to run the quality check and retrieve logs
- `__init__.py` - Makes the directory a Python package for easier imports

## How to Use

### Basic Usage

1. Make sure you have all the files in the same directory
2. Run the main script:

```bash
python run_checker.py
```

### Configuration

You can configure the tool using a YAML file:

```bash
python run_checker.py --config config.yaml
```

Or with command-line arguments:

```bash
python run_checker.py --gitlab-url "http://your-gitlab-server" --token "your-token" --project-id "your-project" --project-hw "HW3"
```

## Workflow

1. The script first builds the Java project
2. If `fail_on_issues` is `true` and the build fails, the script exits
3. If `fail_on_issues` is `false` or the build succeeds, it runs checkstyle
4. Results are logged and summary reports are saved

## Getting Results

When running through `run_checker.py`, logs and reports are copied to a `quality-check-results` directory, and a summary JSON file is created. The script also offers to display the log content.

## Configuration Options

- `gitlab.url` - GitLab server URL
- `gitlab.token` - GitLab personal access token
- `project.id` - Project ID
- `project.hw` - Project homework ID
- `project.branch` - Branch to checkout
- `workspace.path` - Local directory to clone into
- `quality.fail_on_issues` - Whether to exit with error code on quality issues
- `checkstyle.config_path` - Path to custom Checkstyle configuration
- `git.ssh_url` - Custom SSH URL for cloning
- `git.accept_hostkey` - Accept SSH host key automatically
- `git.username` - Username for GitLab authentication
- `git.password` - Password for GitLab authentication