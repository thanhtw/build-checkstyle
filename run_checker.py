#!/usr/bin/env python3
import sys
import logging
import os
from pathlib import Path
import json
import datetime
import re

# Add the current directory to the path so we can import our modules
sys.path.append(os.getcwd())

# Import the main checker
try:
    from main import JavaProjectChecker
except ImportError:
    print("Error: Cannot import JavaProjectChecker. Make sure main.py is in the current directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def read_log_file(log_path):
    """
    Read the content of a log file
    
    Args:
        log_path (str): Path to the log file
    
    Returns:
        str: Content of the log file or None if file doesn't exist
    """
    if not log_path or not os.path.exists(log_path):
        return None
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading log file {log_path}: {str(e)}")
        return None

def parse_build_log(log_content):
    """
    Parse build log content into a structured object with detailed sections,
    focusing especially on compilation errors
    
    Args:
        log_content (str): Content of the build log
        
    Returns:
        dict: Structured build log data
    """
    if not log_content:
        return None
    
    # Create a structured object for the build log
    build_data = {
        "header": {},
        "environment": {},
        "project_structure": {
            "total_files": 0,
            "files": []
        },
        "compilation": {
            "commands": [],
            "file_results": []
        },
        "errors": {
            "count": 0,
            "details": []
        },
        "summary": {
            "status": None,
            "success_rate": 0,
            "error_count": 0,
            "output_directory": None
        }
    }
    
    # Extract header information
    repo_match = re.search(r"=== Build Log for (.*?) ===", log_content)
    if repo_match:
        build_data["header"]["repository_path"] = repo_match.group(1).strip()
    
    date_match = re.search(r"Date: (.*?)$", log_content, re.MULTILINE)
    if date_match:
        build_data["header"]["timestamp"] = date_match.group(1).strip()
    
    # Extract environment info (java version, encoding)
    java_encoding_match = re.search(r"-encoding UTF-8", log_content)
    if java_encoding_match:
        build_data["environment"]["encoding"] = "UTF-8"
    
    java_tool_options_match = re.search(r"Picked up JAVA_TOOL_OPTIONS: (.*?)$", log_content, re.MULTILINE)
    if java_tool_options_match:
        build_data["environment"]["java_tool_options"] = java_tool_options_match.group(1).strip()
    
    # Extract project structure information
    files_count_match = re.search(r"Found (\d+) Java files to compile:", log_content)
    if files_count_match:
        file_count = int(files_count_match.group(1))
        build_data["project_structure"]["total_files"] = file_count
    
    files_section = re.search(r"Found .*? Java files to compile:(.*?)(?=\nCompiling:|$)", log_content, re.DOTALL)
    if files_section:
        files_text = files_section.group(1)
        file_paths = re.findall(r"- (.*?)$", files_text, re.MULTILINE)
        
        for file_path in file_paths:
            file_path = file_path.strip()
            if file_path:
                # Get just the filename
                filename = os.path.basename(file_path)
                # Get directory relative to repo
                directory = os.path.dirname(file_path)
                
                build_data["project_structure"]["files"].append({
                    "path": file_path,
                    "filename": filename,
                    "directory": directory
                })
    
    # Extract output directory
    output_dir_match = re.search(r"-d (.*?)[ \n]", log_content)
    if output_dir_match:
        build_data["summary"]["output_directory"] = output_dir_match.group(1).strip()
    
    # Extract compilation commands and results with more robust pattern
    compilation_sections = re.findall(r"Compiling: (.*?)$.*?Running: (javac.*?)$(.*?)(?=Compiling:|$|ERROR Compilation failed)", 
                                      log_content, re.MULTILINE | re.DOTALL)
    
    successful_compilations = 0
    
    for section in compilation_sections:
        file_path = section[0].strip()
        command = section[1].strip()
        output = section[2].strip()
        
        # Extract errors from output
        is_success = "error" not in output.lower() and "exception" not in output.lower()
        
        # Add to commands list
        build_data["compilation"]["commands"].append({
            "file": file_path,
            "command": command
        })
        
        # Add to file results
        result = {
            "file": file_path,
            "success": is_success,
            "output": output if not is_success else ""  # Only include output for failures
        }
        
        build_data["compilation"]["file_results"].append(result)
        
        if is_success:
            successful_compilations += 1
    
    # Look specifically for compilation failures
    failed_compilation = re.findall(r"ERROR Compilation failed for (.*?)$", log_content, re.MULTILINE)
    
    for failed_file in failed_compilation:
        failed_file = failed_file.strip()
        
        # Find the error message for this file
        error_section = re.search(f"({failed_file}.*?error:.*?)(?=Compiling:|$|ERROR Compilation failed)", 
                                 log_content, re.DOTALL)
        
        if error_section:
            error_text = error_section.group(1)
            
            # Try to extract line number and error message
            line_error_match = re.search(r"(.*?):(\d+): error: (.*?)$", error_text, re.MULTILINE)
            
            if line_error_match:
                file_with_error = line_error_match.group(1).strip()
                line_num = int(line_error_match.group(2))
                error_message = line_error_match.group(3).strip()
                
                # Find code context and column position
                code_line = None
                column = None
                
                # Look for the line with the ^ marker showing column position
                pointer_lines = re.findall(r"(.*?)\n([ \t]*)\^", error_text, re.DOTALL)
                if pointer_lines:
                    code_line = pointer_lines[0][0].strip()
                    column = len(pointer_lines[0][1]) + 1
                
                error_detail = {
                    "file": file_with_error,
                    "line": line_num,
                    "message": error_message,
                    "severity": "error"
                }
                
                if column:
                    error_detail["column"] = column
                
                if code_line:
                    error_detail["code_context"] = code_line
                
                # Count errors reported
                error_count_match = re.search(r"(\d+) error", error_text)
                if error_count_match:
                    error_detail["error_count"] = int(error_count_match.group(1))
                
                # Add raw error text
                error_detail["raw_error"] = error_text.strip()
                
                # Add to errors list
                build_data["errors"]["details"].append(error_detail)
                build_data["errors"]["count"] += 1
            else:
                # If we couldn't parse the detailed format, add the raw error
                build_data["errors"]["details"].append({
                    "file": failed_file,
                    "message": "Compilation failed",
                    "raw_error": error_text.strip(),
                    "severity": "error"
                })
                build_data["errors"]["count"] += 1
    
    # If we didn't find any errors but compilation failed, try a broader approach
    if build_data["errors"]["count"] == 0 and "Compilation failed" in log_content:
        # Look for any error pattern in the entire log
        all_errors = re.findall(r"(.*?):(\d+): error: (.*?)$", log_content, re.MULTILINE)
        
        for error_match in all_errors:
            file_with_error = error_match[0].strip()
            line_num = int(error_match[1])
            error_message = error_match[2].strip()
            
            error_detail = {
                "file": file_with_error,
                "line": line_num,
                "message": error_message,
                "severity": "error"
            }
            
            # Look for context after this error
            context_section = log_content[log_content.find(error_message) + len(error_message):]
            pointer_match = re.search(r"\n([ \t]*)\^", context_section)
            if pointer_match:
                error_detail["column"] = len(pointer_match.group(1)) + 1
            
            build_data["errors"]["details"].append(error_detail)
            build_data["errors"]["count"] += 1
    
    # Calculate success rate
    if build_data["project_structure"]["total_files"] > 0:
        build_data["summary"]["success_rate"] = (successful_compilations / build_data["project_structure"]["total_files"]) * 100
    
    # Extract final status
    if "All Java files compiled successfully" in log_content:
        build_data["summary"]["status"] = "SUCCESS"
    elif "Compilation failed for" in log_content:
        build_data["summary"]["status"] = "FAILED"
        # Get the specific file that failed
        failure_match = re.search(r"Compilation failed for (.*?)$", log_content, re.MULTILINE)
        if failure_match:
            build_data["summary"]["failed_file"] = failure_match.group(1).strip()
    
    # Count total errors
    build_data["summary"]["error_count"] = build_data["errors"]["count"]
    
    # Include the raw content in a separate field
    build_data["raw_content"] = log_content
    
    return build_data

def parse_checkstyle_log(log_content):
    """
    Parse checkstyle log content into a detailed structured object,
    focusing especially on error details
    
    Args:
        log_content (str): Content of the checkstyle log
        
    Returns:
        dict: Structured checkstyle log data
    """
    if not log_content:
        return None
    
    checkstyle_data = {
        "header": {},
        "configuration": {
            "ruleset": None,
            "path": None
        },
        "analysis": {
            "total_files_checked": 0,
            "files_checked": []
        },
        "violations": {
            "count": 0,
            "details": []
        },
        "summary": {
            "status": None,
            "total_violations": 0,
            "files_with_violations_count": 0
        }
    }
    
    # Extract header info
    repo_match = re.search(r"=== Checkstyle Report for (.*?) ===", log_content)
    if repo_match:
        checkstyle_data["header"]["repository_path"] = repo_match.group(1).strip()
    
    date_match = re.search(r"Date: (.*?)$", log_content, re.MULTILINE)
    if date_match:
        checkstyle_data["header"]["timestamp"] = date_match.group(1).strip()
    
    # Extract configuration info
    config_match = re.search(r"Configuration: (.*?)$", log_content, re.MULTILINE)
    if config_match:
        config_path = config_match.group(1).strip()
        checkstyle_data["configuration"]["path"] = config_path
        
        # Try to determine ruleset type from the config path
        if "sun_checks" in config_path.lower():
            checkstyle_data["configuration"]["ruleset"] = "Sun Style"
        elif "google_checks" in config_path.lower():
            checkstyle_data["configuration"]["ruleset"] = "Google Style"
        else:
            checkstyle_data["configuration"]["ruleset"] = "Custom"
    
    # Extract file sections and process each file
    file_sections = re.findall(r"--- File: (.*?) ---\n(.*?)(?=--- File:|=== Summary ===)", log_content, re.DOTALL)
    checkstyle_data["analysis"]["total_files_checked"] = len(file_sections)
    
    for section in file_sections:
        file_name = section[0].strip()
        file_content = section[1].strip()
        
        # Add to files checked list
        checkstyle_data["analysis"]["files_checked"].append(file_name)
        
        # Extract violations for this file - specifically focusing on the error pattern
        # Pattern: [ERROR] file:line: message [rule]
        # Example: [ERROR] C:\GitProjects\D0948363\HW3\src\MultiplicationTable.java:1: Missing package-info.java file. [JavadocPackage]
        error_lines = re.findall(r"\[ERROR\] (.*?)$", file_content, re.MULTILINE)
        
        for error_line in error_lines:
            # Try several patterns to match the error line
            
            # Pattern 1: filepath:line: message [rule]
            pattern1 = re.match(r"(.*?):(\d+): (.*?) \[(.*?)\]", error_line)
            
            # Pattern 2: filepath:line:column: message [rule]
            pattern2 = re.match(r"(.*?):(\d+):(\d+): (.*?) \[(.*?)\]", error_line)
            
            # Pattern 3: filepath:line: message (no rule)
            pattern3 = re.match(r"(.*?):(\d+): (.*?)$", error_line)
            
            if pattern1:
                file_path = pattern1.group(1).strip()
                line_num = int(pattern1.group(2))
                message = pattern1.group(3).strip()
                rule = pattern1.group(4).strip()
                
                violation = {
                    "file": file_path,
                    "line": line_num,
                    "message": message,
                    "rule": rule,
                    "severity": "error",
                    "raw_message": error_line
                }
                checkstyle_data["violations"]["details"].append(violation)
                checkstyle_data["violations"]["count"] += 1
                
            elif pattern2:
                file_path = pattern2.group(1).strip()
                line_num = int(pattern2.group(2))
                column = int(pattern2.group(3))
                message = pattern2.group(4).strip()
                rule = pattern2.group(5).strip()
                
                violation = {
                    "file": file_path,
                    "line": line_num,
                    "column": column,
                    "message": message,
                    "rule": rule,
                    "severity": "error",
                    "raw_message": error_line
                }
                checkstyle_data["violations"]["details"].append(violation)
                checkstyle_data["violations"]["count"] += 1
                
            elif pattern3:
                file_path = pattern3.group(1).strip()
                line_num = int(pattern3.group(2))
                message = pattern3.group(3).strip()
                
                # Look for a rule name in square brackets at the end
                rule_match = re.search(r"\[(.*?)\]$", message)
                rule = rule_match.group(1) if rule_match else "Unknown"
                
                if rule_match:
                    # Remove the rule from the message
                    message = message[:rule_match.start()].strip()
                
                violation = {
                    "file": file_path,
                    "line": line_num,
                    "message": message,
                    "rule": rule,
                    "severity": "error",
                    "raw_message": error_line
                }
                checkstyle_data["violations"]["details"].append(violation)
                checkstyle_data["violations"]["count"] += 1
                
            else:
                # If we can't parse it with the above patterns, add a simpler entry
                violation = {
                    "file": file_name,
                    "message": error_line,
                    "severity": "error",
                    "raw_message": error_line
                }
                checkstyle_data["violations"]["details"].append(violation)
                checkstyle_data["violations"]["count"] += 1
    
    # Extract summary information
    summary_section = re.search(r"=== Summary ===(.*?)$", log_content, re.DOTALL)
    if summary_section:
        summary_text = summary_section.group(1).strip()
        
        if "No Checkstyle errors found" in summary_text:
            checkstyle_data["summary"]["status"] = "PASSED"
            checkstyle_data["summary"]["total_violations"] = 0
            checkstyle_data["summary"]["files_with_violations_count"] = 0
        else:
            # Try to extract violation counts
            violations_match = re.search(r"Total: (\d+) style violations in (\d+) files", summary_text)
            if violations_match:
                checkstyle_data["summary"]["status"] = "ISSUES FOUND"
                checkstyle_data["summary"]["total_violations"] = int(violations_match.group(1))
                checkstyle_data["summary"]["files_with_violations_count"] = int(violations_match.group(2))
    else:
        # If we couldn't find a summary section, calculate it from our parsed data
        checkstyle_data["summary"]["total_violations"] = checkstyle_data["violations"]["count"]
        
        # Count unique files with violations
        files_with_violations = set()
        for violation in checkstyle_data["violations"]["details"]:
            if "file" in violation:
                files_with_violations.add(violation["file"])
        
        checkstyle_data["summary"]["files_with_violations_count"] = len(files_with_violations)
        
        if checkstyle_data["violations"]["count"] > 0:
            checkstyle_data["summary"]["status"] = "ISSUES FOUND"
        else:
            checkstyle_data["summary"]["status"] = "PASSED"
    
    # Include the raw content in a separate field
    checkstyle_data["raw_content"] = log_content
    
    return checkstyle_data

def run_quality_check():
    """
    Run the Java project quality checker and export logs to JSON
    """
    # Create and run the checker
    checker = JavaProjectChecker()
    results = checker.run()
    
    # Get the necessary information
    repo_path = results.get('repo_path')
    build_success = results.get('build_success')
    checkstyle_success = results.get('checkstyle_success')
    quality_success = results.get('quality_success')
    build_log_path = results.get('build_log')
    checkstyle_report_path = results.get('checkstyle_report')
    # Check if we're using fail_on_issues flag
    fail_on_issues = checker.args.fail_on_issues
    # Create a timestamp for the report
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    # Create results directory
    results_dir = Path("quality-check-results")
    results_dir.mkdir(exist_ok=True)
    
    # Prepare the JSON data structure
    json_data = {
        "meta": {
            "timestamp": timestamp,
            "repo_path": str(repo_path),
            "project_id": checker.args.project_id,
            "project_hw": checker.args.project_hw,
            "branch": checker.args.branch,
            "fail_on_issues": fail_on_issues
        },
        "results": {
            "build_success": build_success,
            "checkstyle_success": checkstyle_success,
            "overall_quality_success": quality_success
        },
        "logs": {}
    }
    
    # Process build log if available - always include build log
    if build_log_path and os.path.exists(build_log_path):
        build_log_content = read_log_file(build_log_path)
        if build_log_content:
            # Parse build log into structured format, focusing on errors
            build_data = parse_build_log(build_log_content)
            json_data["logs"]["build"] = build_data
    
    # Always include checkstyle log, regardless of build success or fail_on_issues
    if checkstyle_report_path and os.path.exists(checkstyle_report_path):
        checkstyle_content = read_log_file(checkstyle_report_path)
        if checkstyle_content:
            # Parse checkstyle log into structured format
            checkstyle_data = parse_checkstyle_log(checkstyle_content)
            json_data["logs"]["checkstyle"] = checkstyle_data
    
    # Save the data to a JSON file
    json_file = results_dir / f"quality-check-report-{timestamp}.json"
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        logger.info(f"Quality check report saved to: {json_file}")
    except Exception as e:
        logger.error(f"Error saving JSON report: {str(e)}")
    
    # Handle exit code based on build success and fail_on_issues
    exit_code = 0
    if not build_success and fail_on_issues:
        exit_code = 1
    elif not quality_success and fail_on_issues:
        exit_code = 1
    
    return {
        "json_file": str(json_file),
        "build_success": build_success,
        "checkstyle_success": checkstyle_success,
        "quality_success": quality_success,
        "fail_on_issues": fail_on_issues,
        "exit_code": exit_code
    }

if __name__ == "__main__":
    # Run the quality check and export to JSON
    logger.info("\n# Running Java Project Quality Check")
    logger.info("=" * 60)
    
    results = run_quality_check()
    
    # Print summary for user
    logger.info("\n# Quality Check Summary")
    logger.info("=" * 60)
    logger.info(f"Build success: {results['build_success']}")
    logger.info(f"Checkstyle success: {results['checkstyle_success']}")
    logger.info(f"Overall quality: {results['quality_success']}")
    logger.info(f"Report saved to: {results['json_file']}")
    
    # Exit with appropriate code based on exit_code in results
    sys.exit(results['exit_code'])