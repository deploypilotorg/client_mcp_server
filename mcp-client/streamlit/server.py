import sys
import json
import asyncio
import os
import shutil
import tempfile
import subprocess
from datetime import datetime
from typing import Any, Dict
import fnmatch
import time
import uuid

# Fix imports to match current MCP package structure
from mcp import Tool
from mcp.server import Server

# Define a ToolExecution class since it doesn't seem to be available in the current MCP version
class ToolExecution:
    def __init__(self, content: str):
        self.content = content

# Define tools
class TimeToolHandler:
    async def execute(self, params: Dict[str, Any]) -> ToolExecution:
        """Get the current time"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ToolExecution(content=current_time)

class CalcToolHandler:
    async def execute(self, params: Dict[str, Any]) -> ToolExecution:
        """Perform a calculation"""
        expression = params.get("expression", "")
        try:
            # Safely evaluate mathematical expressions
            result = eval(expression, {"__builtins__": {}}, {
                "add": lambda x, y: x + y,
                "subtract": lambda x, y: x - y,
                "multiply": lambda x, y: x * y,
                "divide": lambda x, y: x / y if y != 0 else "Division by zero error"
            })
            return ToolExecution(content=str(result))
        except Exception as e:
            return ToolExecution(content=f"Error: {str(e)}")

class WeatherToolHandler:
    async def execute(self, params: Dict[str, Any]) -> ToolExecution:
        """Get mock weather data for a location"""
        location = params.get("location", "")
        if not location:
            return ToolExecution(content="Error: Location not provided")
            
        # Mock weather data
        weather_data = {
            "New York": {"condition": "Sunny", "temperature": "72°F"},
            "London": {"condition": "Rainy", "temperature": "60°F"},
            "Tokyo": {"condition": "Cloudy", "temperature": "65°F"},
            "Sydney": {"condition": "Partly Cloudy", "temperature": "70°F"},
            "Paris": {"condition": "Clear", "temperature": "68°F"}
        }
        
        if location in weather_data:
            data = weather_data[location]
            return ToolExecution(content=f"Weather in {location}: {data['condition']}, {data['temperature']}")
        else:
            return ToolExecution(content=f"No weather data available for {location}")

class GitHubRepoToolHandler:
    def __init__(self):
        # Store the currently cloned repo information
        self.repo_path = None
        self.repo_name = None
        self.repo_url = None

    async def execute(self, params: Dict[str, Any]) -> ToolExecution:
        """Clone and analyze GitHub repositories"""
        action = params.get("action", "")
        
        if action == "clone":
            # Clone a repository
            repo_url = params.get("repo_url", "")
            if not repo_url:
                return ToolExecution(content="Error: Repository URL not provided")
            
            # Clean up any previous repo
            if self.repo_path and os.path.exists(self.repo_path):
                shutil.rmtree(self.repo_path)
            
            # Create a temporary directory
            self.repo_path = tempfile.mkdtemp()
            self.repo_url = repo_url
            self.repo_name = repo_url.split("/")[-1].replace(".git", "")
            
            try:
                # Clone the repository
                result = subprocess.run(
                    ["git", "clone", repo_url, self.repo_path], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                return ToolExecution(content=f"Successfully cloned repository: {repo_url} to {self.repo_path}")
            except subprocess.CalledProcessError as e:
                return ToolExecution(content=f"Error cloning repository: {e.stderr}")
        
        elif action == "list_files":
            # List files in the repository
            if not self.repo_path:
                return ToolExecution(content="Error: No repository is currently cloned")
            
            path = params.get("path", "")
            full_path = os.path.join(self.repo_path, path) if path else self.repo_path
            
            if not os.path.exists(full_path):
                return ToolExecution(content=f"Error: Path {path} does not exist in the repository")
            
            try:
                file_list = []
                for root, dirs, files in os.walk(full_path):
                    rel_path = os.path.relpath(root, self.repo_path)
                    rel_path = "" if rel_path == "." else rel_path
                    
                    for dir_name in dirs:
                        file_list.append(f"📁 {os.path.join(rel_path, dir_name)}")
                    
                    for file_name in files:
                        file_list.append(f"📄 {os.path.join(rel_path, file_name)}")
                
                file_list_str = "\n".join(file_list)
                return ToolExecution(content=f"Files in repository {self.repo_name}:\n\n{file_list_str}")
            except Exception as e:
                return ToolExecution(content=f"Error listing files: {str(e)}")
        
        elif action == "read_file":
            # Read the contents of a file
            if not self.repo_path:
                return ToolExecution(content="Error: No repository is currently cloned")
            
            file_path = params.get("file_path", "")
            if not file_path:
                return ToolExecution(content="Error: File path not provided")
            
            full_path = os.path.join(self.repo_path, file_path)
            
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                return ToolExecution(content=f"Error: File {file_path} does not exist in the repository")
            
            try:
                with open(full_path, 'r') as f:
                    file_content = f.read()
                
                return ToolExecution(content=f"Contents of {file_path}:\n\n```\n{file_content}\n```")
            except Exception as e:
                return ToolExecution(content=f"Error reading file: {str(e)}")
        
        elif action == "get_repo_info":
            # Get information about the repository
            if not self.repo_path:
                return ToolExecution(content="Error: No repository is currently cloned")
            
            try:
                # Get the size of the repository
                total_size = 0
                file_count = 0
                for root, dirs, files in os.walk(self.repo_path):
                    file_count += len(files)
                    total_size += sum(os.path.getsize(os.path.join(root, name)) for name in files)
                
                size_kb = total_size / 1024
                size_mb = size_kb / 1024
                
                # Get information about the repository
                current_dir = os.getcwd()
                os.chdir(self.repo_path)
                
                # Get the current branch
                branch_result = subprocess.run(
                    ["git", "branch", "--show-current"], 
                    capture_output=True, 
                    text=True
                )
                current_branch = branch_result.stdout.strip()
                
                # Get the last commit
                last_commit_result = subprocess.run(
                    ["git", "log", "-1", "--pretty=format:%h - %s (%cr)"], 
                    capture_output=True, 
                    text=True
                )
                last_commit = last_commit_result.stdout.strip()
                
                # Change back to the original directory
                os.chdir(current_dir)
                
                repo_info = {
                    "name": self.repo_name,
                    "url": self.repo_url,
                    "branch": current_branch,
                    "last_commit": last_commit,
                    "file_count": file_count,
                    "size": f"{size_mb:.2f} MB ({size_kb:.2f} KB)"
                }
                
                info_str = "\n".join([f"{key}: {value}" for key, value in repo_info.items()])
                return ToolExecution(content=f"Repository Information:\n\n{info_str}")
            except Exception as e:
                return ToolExecution(content=f"Error getting repository information: {str(e)}")
        
        else:
            return ToolExecution(content=f"Error: Unknown action '{action}'. Available actions: clone, list_files, read_file, get_repo_info")

class CommandExecutionToolHandler:
    async def execute(self, params: Dict[str, Any]) -> ToolExecution:
        """Execute a command and return the result"""
        command = params.get("command", "")
        if not command:
            return ToolExecution(content="Error: Command not provided")
        
        working_dir = params.get("working_dir", None)
        timeout = params.get("timeout", 30)  # Default timeout of 30 seconds
        
        try:
            # Set up the execution environment
            env = os.environ.copy()
            
            # Execute the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True,
                cwd=working_dir,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
                
                if process.returncode != 0:
                    result = f"Command execution failed with exit code {process.returncode}:\n\nSTDOUT:\n{stdout_str}\n\nSTDERR:\n{stderr_str}"
                else:
                    result = f"Command executed successfully:\n\nSTDOUT:\n{stdout_str}"
                    if stderr_str.strip():
                        result += f"\n\nSTDERR:\n{stderr_str}"
                
                return ToolExecution(content=result)
            
            except asyncio.TimeoutError:
                process.kill()
                return ToolExecution(content=f"Error: Command execution timed out after {timeout} seconds")
                
        except Exception as e:
            return ToolExecution(content=f"Error executing command: {str(e)}")

class UIGeneratorToolHandler:
    def __init__(self):
        # Share the repo path with the GitHub repo handler
        self.repo_path = None
        self.repo_name = None
        self.repo_url = None
        self.ui_processes = {}  # Store running UI processes
        
    async def execute(self, params: Dict[str, Any]) -> ToolExecution:
        """Generate and run UI for applications in the repository"""
        action = params.get("action", "")
        
        if not self.repo_path:
            return ToolExecution(content="Error: No repository is currently cloned. Please clone a repository first.")
        
        if action == "scan_apps":
            # Scan the repository for app entry points
            try:
                app_files = []
                
                # Look for common app entry points
                patterns = [
                    "**/*.py",  # Python files
                    "**/app.py",
                    "**/main.py",
                    "**/server.py",
                    "**/index.js",
                    "**/app.js",
                    "**/main.js",
                    "**/index.html",
                    "**/package.json",
                    "**/requirements.txt"
                ]
                
                for pattern in patterns:
                    for root, _, files in os.walk(self.repo_path):
                        for filename in files:
                            if fnmatch.fnmatch(filename, pattern.split('/')[-1]):
                                rel_path = os.path.relpath(os.path.join(root, filename), self.repo_path)
                                app_files.append(rel_path)
                
                if not app_files:
                    return ToolExecution(content="No potential application entry points found in the repository.")
                
                # Analyze the potential app entry points
                app_info = []
                for file_path in app_files:
                    full_path = os.path.join(self.repo_path, file_path)
                    file_type = file_path.split('.')[-1] if '.' in file_path else 'unknown'
                    
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read(2000)  # Read the first 2000 characters for analysis
                        
                        app_type = self._detect_app_type(file_path, content)
                        if app_type:
                            app_info.append({
                                "path": file_path,
                                "type": app_type,
                                "description": self._generate_app_description(file_path, content)
                            })
                    except Exception as e:
                        # Skip files that can't be read
                        continue
                
                if not app_info:
                    return ToolExecution(content="No recognizable applications found in the repository.")
                
                # Format the results
                result = "Found potential applications in the repository:\n\n"
                for idx, app in enumerate(app_info, 1):
                    result += f"{idx}. {app['path']} ({app['type']})\n"
                    result += f"   Description: {app['description']}\n\n"
                
                result += "\nYou can generate and run a UI for any of these applications using the 'generate_ui' action."
                return ToolExecution(content=result)
            
            except Exception as e:
                return ToolExecution(content=f"Error scanning for applications: {str(e)}")
        
        elif action == "generate_ui":
            # Generate a UI for a specific application
            app_path = params.get("app_path", "")
            if not app_path:
                return ToolExecution(content="Error: Application path not provided")
            
            full_path = os.path.join(self.repo_path, app_path)
            if not os.path.exists(full_path):
                return ToolExecution(content=f"Error: Application path '{app_path}' does not exist")
            
            try:
                # Determine the app type and generate appropriate UI
                if app_path.endswith('.py'):
                    return await self._run_python_app(app_path)
                elif app_path.endswith('.js'):
                    return await self._run_js_app(app_path)
                elif app_path.endswith('.html'):
                    return await self._serve_html(app_path)
                else:
                    return ToolExecution(content=f"Unsupported application type for {app_path}. Currently supporting .py, .js, and .html files.")
            
            except Exception as e:
                return ToolExecution(content=f"Error generating UI: {str(e)}")
        
        elif action == "stop_ui":
            # Stop a running UI
            session_id = params.get("session_id", "")
            if not session_id or session_id not in self.ui_processes:
                return ToolExecution(content="Error: Invalid or unknown session ID")
            
            try:
                process_info = self.ui_processes[session_id]
                if process_info['process'].poll() is None:  # Check if still running
                    process_info['process'].terminate()
                    try:
                        process_info['process'].wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process_info['process'].kill()
                
                del self.ui_processes[session_id]
                return ToolExecution(content=f"UI session {session_id} has been stopped")
            
            except Exception as e:
                return ToolExecution(content=f"Error stopping UI: {str(e)}")
        
        else:
            return ToolExecution(content=f"Error: Unknown action '{action}'. Available actions: scan_apps, generate_ui, stop_ui")
    
    def _detect_app_type(self, file_path, content):
        """Detect the type of application"""
        if file_path.endswith('.py'):
            if 'streamlit' in content.lower():
                return 'Streamlit'
            elif 'flask' in content.lower():
                return 'Flask'
            elif 'django' in content.lower():
                return 'Django'
            elif 'fastapi' in content.lower():
                return 'FastAPI'
            return 'Python'
        
        elif file_path.endswith('.js'):
            if 'react' in content.lower():
                return 'React'
            elif 'express' in content.lower():
                return 'Express.js'
            elif 'vue' in content.lower():
                return 'Vue.js'
            return 'JavaScript'
        
        elif file_path.endswith('.html'):
            return 'HTML'
        
        elif file_path == 'package.json':
            return 'Node.js'
        
        elif file_path == 'requirements.txt':
            return 'Python'
        
        return None
    
    def _generate_app_description(self, file_path, content):
        """Generate a description for the application"""
        # Extract first non-empty comment lines as potential description
        lines = content.split('\n')
        comment_blocks = []
        current_block = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                # Handle comments
                comment_text = stripped.lstrip('#').lstrip('/').lstrip('*').strip()
                if comment_text:
                    current_block.append(comment_text)
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                # Handle docstrings
                docstring_text = stripped.lstrip('"').lstrip("'").strip()
                if docstring_text:
                    current_block.append(docstring_text)
            elif current_block:
                comment_blocks.append(' '.join(current_block))
                current_block = []
                
        if current_block:
            comment_blocks.append(' '.join(current_block))
        
        if comment_blocks:
            # Use the first substantial comment block as description
            for block in comment_blocks:
                if len(block) > 10:  # Arbitrary threshold for a meaningful comment
                    return block[:200] + "..." if len(block) > 200 else block
        
        # If no good comments, generate a basic description based on file type
        if file_path.endswith('.py'):
            return "Python application"
        elif file_path.endswith('.js'):
            return "JavaScript application"
        elif file_path.endswith('.html'):
            return "HTML application"
        elif file_path == 'package.json':
            return "Node.js application"
        elif file_path == 'requirements.txt':
            return "Python application with dependencies"
        
        return "Application with unknown type"
    
    async def _run_python_app(self, app_path):
        """Run a Python application"""
        full_path = os.path.join(self.repo_path, app_path)
        app_dir = os.path.dirname(full_path)
        
        # Check for dependencies
        requirements_path = os.path.join(app_dir, 'requirements.txt')
        has_requirements = os.path.exists(requirements_path)
        
        # Determine the app type
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        port = self._get_available_port()
        session_id = f"ui_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        cmd = []
        app_url = ""
        
        if 'streamlit' in content.lower():
            # Streamlit app
            cmd = [sys.executable, "-m", "streamlit", "run", full_path, "--server.port", str(port)]
            app_url = f"http://localhost:{port}"
        elif 'flask' in content.lower():
            # Flask app
            env = os.environ.copy()
            env["FLASK_APP"] = full_path
            env["FLASK_ENV"] = "development"
            cmd = [sys.executable, "-m", "flask", "run", "--port", str(port)]
            app_url = f"http://localhost:{port}"
        elif 'fastapi' in content.lower():
            # FastAPI app
            cmd = [sys.executable, "-m", "uvicorn", os.path.basename(full_path).replace('.py', ':app'), "--port", str(port)]
            app_url = f"http://localhost:{port}"
        else:
            # Generic Python script
            cmd = [sys.executable, full_path]
            app_url = "No web interface available for this script type"
        
        # Prepare the process
        try:
            if has_requirements:
                # Install dependencies
                install_process = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", requirements_path],
                    capture_output=True,
                    text=True,
                    cwd=app_dir
                )
                
                if install_process.returncode != 0:
                    return ToolExecution(content=f"Error installing dependencies:\n{install_process.stderr}")
            
            # Start the application
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=app_dir
            )
            
            # Store the process
            self.ui_processes[session_id] = {
                'process': process,
                'app_path': app_path,
                'url': app_url,
                'port': port
            }
            
            # Give it some time to start
            await asyncio.sleep(3)
            
            # Check if it's still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                return ToolExecution(content=f"Application failed to start:\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}")
            
            return ToolExecution(content=f"""
UI generated for {app_path}!

Session ID: {session_id}
URL: {app_url}

The application is now running. You can access it at the URL above.
To stop the application, use the 'stop_ui' action with the session ID.
            """.strip())
            
        except Exception as e:
            return ToolExecution(content=f"Error running Python application: {str(e)}")
    
    async def _run_js_app(self, app_path):
        """Run a JavaScript application"""
        full_path = os.path.join(self.repo_path, app_path)
        app_dir = os.path.dirname(full_path)
        
        # Check for package.json
        package_json_path = os.path.join(app_dir, 'package.json')
        has_package_json = os.path.exists(package_json_path)
        
        port = self._get_available_port()
        session_id = f"ui_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        try:
            cmd = []
            app_url = ""
            
            if has_package_json:
                # Read package.json to determine application type and start script
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                
                # Install dependencies
                install_process = subprocess.run(
                    ["npm", "install"],
                    capture_output=True,
                    text=True,
                    cwd=app_dir
                )
                
                if install_process.returncode != 0:
                    return ToolExecution(content=f"Error installing npm dependencies:\n{install_process.stderr}")
                
                # Determine start script
                if 'scripts' in package_data and 'start' in package_data['scripts']:
                    cmd = ["npm", "start"]
                    app_url = f"http://localhost:{port}"  # Assuming standard port, may need adjustment
                else:
                    # Fallback to node
                    cmd = ["node", full_path]
                    app_url = "No web interface directly available for this Node.js script"
            else:
                # Simple Node.js script
                cmd = ["node", full_path]
                app_url = "No web interface directly available for this Node.js script"
            
            # Start the application
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=app_dir
            )
            
            # Store the process
            self.ui_processes[session_id] = {
                'process': process,
                'app_path': app_path,
                'url': app_url,
                'port': port
            }
            
            # Give it some time to start
            await asyncio.sleep(3)
            
            # Check if it's still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                return ToolExecution(content=f"Application failed to start:\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}")
            
            return ToolExecution(content=f"""
UI generated for {app_path}!

Session ID: {session_id}
URL: {app_url}

The application is now running. You can access it at the URL above.
To stop the application, use the 'stop_ui' action with the session ID.
            """.strip())
            
        except Exception as e:
            return ToolExecution(content=f"Error running JavaScript application: {str(e)}")
    
    async def _serve_html(self, app_path):
        """Serve an HTML file using a simple HTTP server"""
        full_path = os.path.join(self.repo_path, app_path)
        app_dir = os.path.dirname(full_path)
        
        port = self._get_available_port()
        session_id = f"ui_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Start a simple HTTP server
            cmd = [sys.executable, "-m", "http.server", str(port)]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=app_dir
            )
            
            # Store the process
            file_name = os.path.basename(full_path)
            app_url = f"http://localhost:{port}/{file_name}"
            self.ui_processes[session_id] = {
                'process': process,
                'app_path': app_path,
                'url': app_url,
                'port': port
            }
            
            # Give it some time to start
            await asyncio.sleep(2)
            
            # Check if it's still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                return ToolExecution(content=f"Server failed to start:\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}")
            
            return ToolExecution(content=f"""
HTTP server started for {app_path}!

Session ID: {session_id}
URL: {app_url}

The HTML file is now being served. You can access it at the URL above.
To stop the server, use the 'stop_ui' action with the session ID.
            """.strip())
            
        except Exception as e:
            return ToolExecution(content=f"Error serving HTML file: {str(e)}")
    
    def _get_available_port(self):
        """Get an available port"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

class CodeAnalysisToolHandler:
    def __init__(self):
        # Share the repo path with the GitHub repo handler
        self.repo_path = None
        self.repo_name = None
        self.repo_url = None
        
    async def execute(self, params: Dict[str, Any]) -> ToolExecution:
        """Analyze code in the repository"""
        action = params.get("action", "")
        
        if not self.repo_path:
            return ToolExecution(content="Error: No repository is currently cloned. Please clone a repository first.")
        
        if action == "summarize_repo":
            # Generate a summary of the repository
            try:
                # Count files by type
                file_counts = {}
                total_files = 0
                total_lines = 0
                largest_files = []
                
                for root, _, files in os.walk(self.repo_path):
                    for filename in files:
                        if filename.startswith('.') or '__pycache__' in root:
                            continue
                            
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, self.repo_path)
                        
                        # Get file extension
                        ext = os.path.splitext(filename)[1].lower()
                        if not ext:
                            ext = 'no_extension'
                        
                        # Count by extension
                        if ext not in file_counts:
                            file_counts[ext] = 0
                        file_counts[ext] += 1
                        total_files += 1
                        
                        # Count lines and track large files
                        try:
                            line_count = 0
                            if os.path.getsize(full_path) < 1000000:  # Skip files over 1MB
                                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                                    for _ in f:
                                        line_count += 1
                            
                                total_lines += line_count
                                
                                # Track largest files
                                largest_files.append((rel_path, line_count))
                                largest_files = sorted(largest_files, key=lambda x: x[1], reverse=True)[:10]
                        except:
                            # Skip files that can't be read
                            pass
                
                # Format the results
                result = "Repository Summary:\n\n"
                
                result += f"Total Files: {total_files}\n"
                result += f"Total Lines of Code: {total_lines}\n\n"
                
                result += "Files by Type:\n"
                for ext, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True):
                    result += f"  {ext}: {count}\n"
                
                result += "\nLargest Files:\n"
                for path, lines in largest_files:
                    result += f"  {path}: {lines} lines\n"
                
                result += "\nTo analyze specific files or directories, use the 'analyze_code' action."
                return ToolExecution(content=result)
            
            except Exception as e:
                return ToolExecution(content=f"Error summarizing repository: {str(e)}")
        
        elif action == "analyze_code":
            # Analyze a specific file or directory
            target_path = params.get("path", "")
            if not target_path:
                return ToolExecution(content="Error: Path not provided")
            
            full_path = os.path.join(self.repo_path, target_path)
            if not os.path.exists(full_path):
                return ToolExecution(content=f"Error: Path '{target_path}' does not exist")
            
            try:
                if os.path.isfile(full_path):
                    # Analyze a single file
                    return await self._analyze_file(target_path, full_path)
                else:
                    # Analyze a directory
                    return await self._analyze_directory(target_path, full_path)
            
            except Exception as e:
                return ToolExecution(content=f"Error analyzing code: {str(e)}")
        
        elif action == "find_patterns":
            # Find specific patterns in the code
            pattern = params.get("pattern", "")
            if not pattern:
                return ToolExecution(content="Error: Search pattern not provided")
            
            path = params.get("path", "")
            full_path = os.path.join(self.repo_path, path) if path else self.repo_path
            
            if not os.path.exists(full_path):
                return ToolExecution(content=f"Error: Path '{path}' does not exist")
            
            try:
                # Use grep to find patterns
                extensions = params.get("extensions", "")
                if extensions:
                    ext_list = extensions.split(',')
                    ext_pattern = ' '.join([f'--include="*.{ext.strip()}"' for ext in ext_list])
                    cmd = f'grep -r {ext_pattern} -n "{pattern}" {full_path}'
                else:
                    cmd = f'grep -r -n "{pattern}" {full_path}'
                
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
                
                stdout, stderr = await process.communicate()
                
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
                
                if process.returncode != 0 and process.returncode != 1:
                    # grep returns 1 if no matches found, which is not an error
                    return ToolExecution(content=f"Error searching for pattern:\n\n{stderr_str}")
                
                if not stdout_str.strip():
                    return ToolExecution(content=f"No matches found for pattern: '{pattern}'")
                
                # Format the results
                result = f"Matches for pattern '{pattern}':\n\n"
                
                # Limit results for readability
                max_matches = 50
                matches = stdout_str.strip().split('\n')
                
                if len(matches) > max_matches:
                    result += "\n".join(matches[:max_matches])
                    result += f"\n\n... and {len(matches) - max_matches} more matches."
                else:
                    result += stdout_str
                
                return ToolExecution(content=result)
            
            except Exception as e:
                return ToolExecution(content=f"Error searching for pattern: {str(e)}")
        
        elif action == "dependency_analysis":
            # Analyze dependencies
            try:
                dependencies = {}
                
                # Check for package.json (Node.js)
                package_json_path = os.path.join(self.repo_path, 'package.json')
                if os.path.exists(package_json_path):
                    try:
                        with open(package_json_path, 'r', encoding='utf-8') as f:
                            package_data = json.load(f)
                        
                        dependencies['Node.js'] = {
                            'dependencies': package_data.get('dependencies', {}),
                            'devDependencies': package_data.get('devDependencies', {})
                        }
                    except:
                        dependencies['Node.js'] = 'Error reading package.json'
                
                # Check for requirements.txt (Python)
                requirements_paths = []
                for root, _, files in os.walk(self.repo_path):
                    if 'requirements.txt' in files:
                        requirements_paths.append(os.path.join(root, 'requirements.txt'))
                
                if requirements_paths:
                    python_deps = []
                    for req_path in requirements_paths:
                        try:
                            with open(req_path, 'r', encoding='utf-8') as f:
                                reqs = f.readlines()
                            
                            rel_path = os.path.relpath(req_path, self.repo_path)
                            python_deps.append({
                                'path': rel_path,
                                'dependencies': [r.strip() for r in reqs if r.strip() and not r.startswith('#')]
                            })
                        except:
                            python_deps.append({
                                'path': os.path.relpath(req_path, self.repo_path),
                                'error': 'Error reading requirements.txt'
                            })
                    
                    dependencies['Python'] = python_deps
                
                # Format the results
                if not dependencies:
                    return ToolExecution(content="No dependency information found in the repository.")
                
                result = "Dependency Analysis:\n\n"
                
                for lang, deps in dependencies.items():
                    result += f"{lang} Dependencies:\n"
                    
                    if lang == 'Node.js':
                        if isinstance(deps, str):
                            result += f"  {deps}\n"
                        else:
                            result += "  Production Dependencies:\n"
                            for name, version in deps.get('dependencies', {}).items():
                                result += f"    {name}: {version}\n"
                            
                            result += "\n  Development Dependencies:\n"
                            for name, version in deps.get('devDependencies', {}).items():
                                result += f"    {name}: {version}\n"
                    
                    elif lang == 'Python':
                        for req_file in deps:
                            if 'error' in req_file:
                                result += f"  {req_file['path']}: {req_file['error']}\n"
                            else:
                                result += f"  {req_file['path']}:\n"
                                for dep in req_file['dependencies']:
                                    result += f"    {dep}\n"
                
                return ToolExecution(content=result)
            
            except Exception as e:
                return ToolExecution(content=f"Error analyzing dependencies: {str(e)}")
        
        else:
            return ToolExecution(content=f"Error: Unknown action '{action}'. Available actions: summarize_repo, analyze_code, find_patterns, dependency_analysis")
    
    async def _analyze_file(self, rel_path, full_path):
        """Analyze a single file"""
        file_ext = os.path.splitext(full_path)[1].lower()
        
        # Get basic file information
        result = f"Analysis of {rel_path}:\n\n"
        
        try:
            # Get line count and basic stats
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            lines = content.split('\n')
            line_count = len(lines)
            empty_lines = sum(1 for line in lines if not line.strip())
            comment_lines = 0
            
            # Count comment lines based on file type
            if file_ext in ['.py']:
                comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
            elif file_ext in ['.js', '.ts', '.java', '.c', '.cpp', '.cs']:
                comment_lines = sum(1 for line in lines if line.strip().startswith('//'))
            
            result += f"Line Count: {line_count}\n"
            result += f"Empty Lines: {empty_lines}\n"
            result += f"Comment Lines: {comment_lines}\n"
            result += f"Code Lines: {line_count - empty_lines - comment_lines}\n\n"
            
            # Analyze imports/dependencies
            if file_ext == '.py':
                # Find Python imports
                import_lines = [line for line in lines if line.strip().startswith(('import ', 'from '))]
                if import_lines:
                    result += "Imports:\n"
                    for imp in import_lines[:20]:  # Limit to first 20 imports
                        result += f"  {imp.strip()}\n"
                    
                    if len(import_lines) > 20:
                        result += f"  ... and {len(import_lines) - 20} more imports\n"
                    
                    result += "\n"
            
            elif file_ext in ['.js', '.ts']:
                # Find JavaScript/TypeScript imports
                import_lines = [line for line in lines if line.strip().startswith(('import ', 'require('))]
                if import_lines:
                    result += "Imports:\n"
                    for imp in import_lines[:20]:  # Limit to first 20 imports
                        result += f"  {imp.strip()}\n"
                    
                    if len(import_lines) > 20:
                        result += f"  ... and {len(import_lines) - 20} more imports\n"
                    
                    result += "\n"
            
            # Show file preview (first 20 lines)
            result += "File Preview:\n"
            result += "```\n"
            preview_lines = lines[:20]
            result += "\n".join(preview_lines)
            if line_count > 20:
                result += f"\n... {line_count - 20} more lines ..."
            result += "\n```"
            
            return ToolExecution(content=result)
        
        except Exception as e:
            return ToolExecution(content=f"Error analyzing file {rel_path}: {str(e)}")
    
    async def _analyze_directory(self, rel_path, full_path):
        """Analyze a directory"""
        try:
            # Get directory statistics
            result = f"Analysis of directory: {rel_path}\n\n"
            
            file_count = 0
            dir_count = 0
            file_types = {}
            total_lines = 0
            
            for root, dirs, files in os.walk(full_path):
                dir_count += len(dirs)
                for filename in files:
                    if filename.startswith('.') or '__pycache__' in root:
                        continue
                    
                    file_count += 1
                    ext = os.path.splitext(filename)[1].lower() or 'no_extension'
                    
                    if ext not in file_types:
                        file_types[ext] = 0
                    file_types[ext] += 1
                    
                    # Count lines in text files
                    file_path = os.path.join(root, filename)
                    try:
                        if os.path.getsize(file_path) < 1000000:  # Skip files over 1MB
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                                line_count = sum(1 for _ in f)
                            total_lines += line_count
                    except:
                        # Skip binary or unreadable files
                        pass
            
            result += f"Files: {file_count}\n"
            result += f"Subdirectories: {dir_count}\n"
            result += f"Total Lines: {total_lines}\n\n"
            
            result += "File Types:\n"
            for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                result += f"  {ext}: {count}\n"
            
            result += "\nDirectory Contents:\n"
            
            # List immediate contents (not recursive)
            items = os.listdir(full_path)
            dirs = [d for d in items if os.path.isdir(os.path.join(full_path, d))]
            files = [f for f in items if os.path.isfile(os.path.join(full_path, f))]
            
            result += "Directories:\n"
            for d in sorted(dirs):
                if d.startswith('.') or d == '__pycache__':
                    continue
                result += f"  📁 {d}\n"
            
            result += "\nFiles:\n"
            for f in sorted(files):
                if f.startswith('.'):
                    continue
                result += f"  📄 {f}\n"
            
            return ToolExecution(content=result)
        
        except Exception as e:
            return ToolExecution(content=f"Error analyzing directory {rel_path}: {str(e)}")

class AutoDeployToolHandler:
    def __init__(self):
        # Share the repo path with the GitHub repo handler
        self.repo_path = None
        self.repo_name = None
        self.repo_url = None
        self.deploy_processes = {}  # Store running deploy processes
        
    async def execute(self, params: Dict[str, Any]) -> ToolExecution:
        """Deploy applications from the repository"""
        action = params.get("action", "")
        
        if not self.repo_path:
            return ToolExecution(content="Error: No repository is currently cloned. Please clone a repository first.")
        
        if action == "autodeploy":
            # Automatically detect and deploy the application
            try:
                # First, analyze the repository to determine application type
                app_type, entry_point, framework = await self._detect_application()
                
                if not app_type:
                    return ToolExecution(content="Could not determine application type for automatic deployment. Please specify deployment settings manually.")
                
                # Generate deployment files based on app type
                dockerfile_path, compose_path = await self._generate_deployment_files(app_type, entry_point, framework)
                
                # Build and run the application
                result = await self._deploy_application(app_type, dockerfile_path, compose_path)
                
                return ToolExecution(content=result)
            
            except Exception as e:
                return ToolExecution(content=f"Error during autodeploy: {str(e)}")
        
        elif action == "generate_deployment_files":
            # Generate deployment files without actually deploying
            app_type = params.get("app_type", "")
            entry_point = params.get("entry_point", "")
            framework = params.get("framework", "")
            
            if not app_type:
                return ToolExecution(content="Error: Application type not provided. Valid types: python, node, static")
            
            if not entry_point:
                return ToolExecution(content="Error: Entry point not provided (e.g., app.py, server.js, index.html)")
            
            try:
                dockerfile_path, compose_path = await self._generate_deployment_files(app_type, entry_point, framework)
                
                # Read the generated files to show to the user
                dockerfile_content = ""
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()
                
                compose_content = ""
                with open(compose_path, 'r') as f:
                    compose_content = f.read()
                
                result = f"""
Deployment files generated successfully!

Dockerfile ({dockerfile_path}):
```dockerfile
{dockerfile_content}
```

Docker Compose ({compose_path}):
```yaml
{compose_content}
```

You can now build and run the application with Docker:
```
cd {self.repo_path}
docker-compose up --build
```
                """
                
                return ToolExecution(content=result)
            
            except Exception as e:
                return ToolExecution(content=f"Error generating deployment files: {str(e)}")
        
        elif action == "deploy":
            # Deploy with specific settings
            app_type = params.get("app_type", "")
            entry_point = params.get("entry_point", "")
            framework = params.get("framework", "")
            
            if not app_type:
                return ToolExecution(content="Error: Application type not provided. Valid types: python, node, static")
            
            if not entry_point:
                return ToolExecution(content="Error: Entry point not provided (e.g., app.py, server.js, index.html)")
            
            try:
                # Generate deployment files
                dockerfile_path, compose_path = await self._generate_deployment_files(app_type, entry_point, framework)
                
                # Build and run the application
                result = await self._deploy_application(app_type, dockerfile_path, compose_path)
                
                return ToolExecution(content=result)
            
            except Exception as e:
                return ToolExecution(content=f"Error during deployment: {str(e)}")
        
        elif action == "stop":
            # Stop a running deployment
            deploy_id = params.get("deploy_id", "")
            
            if not deploy_id or deploy_id not in self.deploy_processes:
                return ToolExecution(content="Error: Invalid or unknown deployment ID")
            
            try:
                # Stop the deployment
                result = await self._stop_deployment(deploy_id)
                return ToolExecution(content=result)
            
            except Exception as e:
                return ToolExecution(content=f"Error stopping deployment: {str(e)}")
        
        else:
            return ToolExecution(content=f"Error: Unknown action '{action}'. Available actions: autodeploy, generate_deployment_files, deploy, stop")
    
    async def _detect_application(self):
        """Detect the application type, entry point, and framework"""
        # Check for common file patterns
        app_type = None
        entry_point = None
        framework = None
        
        # Check for package.json (Node.js)
        package_json_path = os.path.join(self.repo_path, 'package.json')
        if os.path.exists(package_json_path):
            app_type = "node"
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                
                # Check for main entry point in package.json
                if 'main' in package_data:
                    entry_point = package_data['main']
                else:
                    # Look for common Node.js entry points
                    candidates = ['server.js', 'app.js', 'index.js']
                    for candidate in candidates:
                        if os.path.exists(os.path.join(self.repo_path, candidate)):
                            entry_point = candidate
                            break
                
                # Detect framework
                dependencies = package_data.get('dependencies', {})
                if 'express' in dependencies:
                    framework = "express"
                elif 'react' in dependencies:
                    framework = "react"
                elif 'next' in dependencies:
                    framework = "next"
                    
            return app_type, entry_point, framework
                    
        # Check for requirements.txt (Python)
        requirements_path = os.path.join(self.repo_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            app_type = "python"
            
            # Look for common Python entry points
            candidates = ['app.py', 'main.py', 'server.py', 'application.py']
            for candidate in candidates:
                if os.path.exists(os.path.join(self.repo_path, candidate)):
                    entry_point = candidate
                    break
            
            # Try to detect Python framework
            with open(requirements_path, 'r') as f:
                requirements = f.read().lower()
                if 'flask' in requirements:
                    framework = "flask"
                elif 'django' in requirements:
                    framework = "django"
                elif 'fastapi' in requirements:
                    framework = "fastapi"
                elif 'streamlit' in requirements:
                    framework = "streamlit"
            
            # If entry point not found, try to find any .py file
            if not entry_point:
                for file in os.listdir(self.repo_path):
                    if file.endswith('.py'):
                        entry_point = file
                        break
            
            return app_type, entry_point, framework
        
        # Check for index.html (static site)
        index_path = os.path.join(self.repo_path, 'index.html')
        if os.path.exists(index_path):
            app_type = "static"
            entry_point = "index.html"
            return app_type, entry_point, None
        
        # Default - couldn't determine app type
        return None, None, None
    
    async def _generate_deployment_files(self, app_type, entry_point, framework=None):
        """Generate Dockerfile and docker-compose.yml for the application"""
        dockerfile_path = os.path.join(self.repo_path, 'Dockerfile')
        compose_path = os.path.join(self.repo_path, 'docker-compose.yml')
        
        # Generate Dockerfile based on app type
        if app_type == "python":
            # Python Dockerfile
            dockerfile_content = "FROM python:3.9-slim\n\n"
            dockerfile_content += "WORKDIR /app\n\n"
            dockerfile_content += "COPY . .\n\n"
            dockerfile_content += "RUN pip install --no-cache-dir -r requirements.txt\n\n"
            
            # Adjust for specific frameworks
            if framework == "flask":
                dockerfile_content += "ENV FLASK_APP=" + entry_point + "\n"
                dockerfile_content += "ENV FLASK_ENV=production\n\n"
                dockerfile_content += "EXPOSE 5000\n\n"
                dockerfile_content += 'CMD ["flask", "run", "--host=0.0.0.0"]\n'
            elif framework == "django":
                dockerfile_content += "EXPOSE 8000\n\n"
                dockerfile_content += 'CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]\n'
            elif framework == "fastapi":
                dockerfile_content += "EXPOSE 8000\n\n"
                dockerfile_content += f'CMD ["uvicorn", "{os.path.splitext(entry_point)[0]}:app", "--host", "0.0.0.0", "--port", "8000"]\n'
            elif framework == "streamlit":
                dockerfile_content += "EXPOSE 8501\n\n"
                dockerfile_content += f'CMD ["streamlit", "run", "{entry_point}", "--server.port=8501", "--server.address=0.0.0.0"]\n'
            else:
                # Generic Python
                dockerfile_content += "EXPOSE 8000\n\n"
                dockerfile_content += f'CMD ["python", "{entry_point}"]\n'
        
        elif app_type == "node":
            # Node.js Dockerfile
            dockerfile_content = "FROM node:14-alpine\n\n"
            dockerfile_content += "WORKDIR /app\n\n"
            dockerfile_content += "COPY package*.json ./\n\n"
            dockerfile_content += "RUN npm install\n\n"
            dockerfile_content += "COPY . .\n\n"
            
            # Adjust for specific frameworks
            if framework == "react":
                dockerfile_content += "RUN npm run build\n\n"
                dockerfile_content += "EXPOSE 3000\n\n"
                dockerfile_content += 'CMD ["npm", "start"]\n'
            elif framework == "next":
                dockerfile_content += "RUN npm run build\n\n"
                dockerfile_content += "EXPOSE 3000\n\n"
                dockerfile_content += 'CMD ["npm", "start"]\n'
            else:
                # Generic Node.js
                dockerfile_content += "EXPOSE 3000\n\n"
                dockerfile_content += f'CMD ["node", "{entry_point}"]\n'
        
        elif app_type == "static":
            # Static site Dockerfile using Nginx
            dockerfile_content = "FROM nginx:alpine\n\n"
            dockerfile_content += "WORKDIR /usr/share/nginx/html\n\n"
            dockerfile_content += "COPY . .\n\n"
            dockerfile_content += "EXPOSE 80\n\n"
            dockerfile_content += 'CMD ["nginx", "-g", "daemon off;"]\n'
        
        else:
            raise ValueError(f"Unsupported application type: {app_type}")
        
        # Write Dockerfile
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        # Generate docker-compose.yml
        compose_content = "version: '3'\n\n"
        compose_content += "services:\n"
        compose_content += f"  {self.repo_name.lower()}:\n"
        compose_content += "    build: .\n"
        
        # Set port mapping based on app type
        if app_type == "python":
            if framework == "flask":
                compose_content += "    ports:\n      - '5000:5000'\n"
            elif framework == "streamlit":
                compose_content += "    ports:\n      - '8501:8501'\n"
            else:
                compose_content += "    ports:\n      - '8000:8000'\n"
        elif app_type == "node":
            compose_content += "    ports:\n      - '3000:3000'\n"
        elif app_type == "static":
            compose_content += "    ports:\n      - '8080:80'\n"
        
        # Add volumes for development
        compose_content += "    volumes:\n"
        compose_content += "      - .:/app\n"
        
        # Write docker-compose.yml
        with open(compose_path, 'w') as f:
            f.write(compose_content)
        
        return dockerfile_path, compose_path
    
    async def _deploy_application(self, app_type, dockerfile_path, compose_path):
        """Build and run the application using Docker Compose"""
        # Generate a unique ID for this deployment
        deploy_id = f"deploy_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Go to the repository directory
            current_dir = os.getcwd()
            os.chdir(self.repo_path)
            
            # Build the Docker image
            build_process = await asyncio.create_subprocess_shell(
                "docker-compose build",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            build_stdout, build_stderr = await build_process.communicate()
            
            if build_process.returncode != 0:
                os.chdir(current_dir)
                return f"Error building Docker image:\n\n{build_stderr.decode('utf-8')}"
            
            # Start the application
            start_process = await asyncio.create_subprocess_shell(
                "docker-compose up -d",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            start_stdout, start_stderr = await start_process.communicate()
            
            if start_process.returncode != 0:
                os.chdir(current_dir)
                return f"Error starting application with Docker Compose:\n\n{start_stderr.decode('utf-8')}"
            
            # Get container information
            container_process = await asyncio.create_subprocess_shell(
                "docker-compose ps",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            container_stdout, container_stderr = await container_process.communicate()
            
            # Change back to the original directory
            os.chdir(current_dir)
            
            # Store the deployment information
            self.deploy_processes[deploy_id] = {
                'app_type': app_type,
                'repo_path': self.repo_path,
                'deploy_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Determine the URL to access the application
            access_url = ""
            if app_type == "python":
                if "flask" in app_type or app_type == "python":
                    access_url = "http://localhost:5000"
                elif "streamlit" in app_type:
                    access_url = "http://localhost:8501"
                else:
                    access_url = "http://localhost:8000"
            elif app_type == "node":
                access_url = "http://localhost:3000"
            elif app_type == "static":
                access_url = "http://localhost:8080"
            
            # Format the result
            result = f"""
Application deployed successfully!

Deployment ID: {deploy_id}
Access URL: {access_url}
Application Type: {app_type.capitalize()}

Container Information:
{container_stdout.decode('utf-8')}

To stop the deployment, use the 'stop' action with the deployment ID.
            """
            
            return result
        
        except Exception as e:
            # Change back to the original directory in case of exception
            try:
                os.chdir(current_dir)
            except:
                pass
            
            raise e
    
    async def _stop_deployment(self, deploy_id):
        """Stop a running deployment"""
        if deploy_id not in self.deploy_processes:
            return "Error: Invalid or unknown deployment ID"
        
        try:
            # Get deployment info
            deploy_info = self.deploy_processes[deploy_id]
            
            # Go to the repository directory
            current_dir = os.getcwd()
            os.chdir(deploy_info['repo_path'])
            
            # Stop the containers
            stop_process = await asyncio.create_subprocess_shell(
                "docker-compose down",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )
            
            stop_stdout, stop_stderr = await stop_process.communicate()
            
            # Change back to the original directory
            os.chdir(current_dir)
            
            if stop_process.returncode != 0:
                return f"Error stopping deployment:\n\n{stop_stderr.decode('utf-8')}"
            
            # Remove the deployment from our tracking
            del self.deploy_processes[deploy_id]
            
            return f"""
Deployment {deploy_id} stopped successfully!

{stop_stdout.decode('utf-8')}
            """
            
        except Exception as e:
            # Change back to the original directory in case of exception
            try:
                os.chdir(current_dir)
            except:
                pass
            
            return f"Error stopping deployment: {str(e)}"

async def main():
    # Create server
    server_instance = Server(name="github-repo-server")
    
    # Create a shared instance of the UI generator that has access to the GitHub repo data
    github_handler = GitHubRepoToolHandler()
    ui_generator_handler = UIGeneratorToolHandler()
    code_analysis_handler = CodeAnalysisToolHandler()
    auto_deploy_handler = AutoDeployToolHandler()
    
    # Create the tools
    time_tool = Tool(
        name="get_time",
        description="Get the current time",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=TimeToolHandler()
    )
    
    calc_tool = Tool(
        name="calculate",
        description="Perform a simple calculation",
        inputSchema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The expression to calculate (e.g., 'add(3, 4)', 'subtract(5, 2)', 'multiply(3, 3)', 'divide(10, 2)')"
                }
            },
            "required": ["expression"]
        },
        handler=CalcToolHandler()
    )
    
    weather_tool = Tool(
        name="get_weather",
        description="Get weather information for a location",
        inputSchema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The location to get weather for (e.g., 'New York', 'London', 'Tokyo', 'Sydney', 'Paris')"
                }
            },
            "required": ["location"]
        },
        handler=WeatherToolHandler()
    )
    
    github_repo_tool = Tool(
        name="github_repo",
        description="Clone and analyze GitHub repositories",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform",
                    "enum": ["clone", "list_files", "read_file", "get_repo_info"]
                },
                "repo_url": {
                    "type": "string",
                    "description": "The URL of the GitHub repository"
                },
                "path": {
                    "type": "string",
                    "description": "The path to list files from (for list_files action)"
                },
                "file_path": {
                    "type": "string",
                    "description": "The path of the file to read (for read_file action)"
                }
            },
            "required": ["action"]
        },
        handler=github_handler
    )
    
    command_execution_tool = Tool(
        name="execute_command",
        description="Execute a command in the system shell and return the result",
        inputSchema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute"
                },
                "working_dir": {
                    "type": "string",
                    "description": "The working directory to execute the command in (optional)"
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (default: 30)"
                }
            },
            "required": ["command"]
        },
        handler=CommandExecutionToolHandler()
    )
    
    ui_generator_tool = Tool(
        name="ui_generator",
        description="Generate and run UI for applications in the repository",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform",
                    "enum": ["scan_apps", "generate_ui", "stop_ui"]
                },
                "app_path": {
                    "type": "string",
                    "description": "The path to the application entry point (for generate_ui action)"
                },
                "session_id": {
                    "type": "string",
                    "description": "The session ID of a running UI (for stop_ui action)"
                }
            },
            "required": ["action"]
        },
        handler=ui_generator_handler
    )
    
    code_analysis_tool = Tool(
        name="code_analysis",
        description="Analyze code in the repository",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform",
                    "enum": ["summarize_repo", "analyze_code", "find_patterns", "dependency_analysis"]
                },
                "path": {
                    "type": "string",
                    "description": "The path to analyze (for analyze_code and find_patterns actions)"
                },
                "pattern": {
                    "type": "string",
                    "description": "The pattern to search for (for find_patterns action)"
                },
                "extensions": {
                    "type": "string",
                    "description": "Comma-separated list of file extensions to search (for find_patterns action, e.g., 'py,js,html')"
                }
            },
            "required": ["action"]
        },
        handler=code_analysis_handler
    )
    
    auto_deploy_tool = Tool(
        name="auto_deploy",
        description="Deploy applications from the repository",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform",
                    "enum": ["autodeploy", "generate_deployment_files", "deploy", "stop"]
                },
                "app_type": {
                    "type": "string",
                    "description": "The type of application (python, node, static)"
                },
                "entry_point": {
                    "type": "string",
                    "description": "The entry point file (e.g., app.py, server.js, index.html)"
                },
                "framework": {
                    "type": "string",
                    "description": "The framework used (e.g., flask, react, express)"
                },
                "deploy_id": {
                    "type": "string",
                    "description": "The ID of a running deployment (for stop action)"
                }
            },
            "required": ["action"]
        },
        handler=auto_deploy_handler
    )
    
    # Share the repo path between handlers
    def update_repo_path(path):
        github_handler.repo_path = path
        ui_generator_handler.repo_path = path
        code_analysis_handler.repo_path = path
        auto_deploy_handler.repo_path = path
        # Share other properties to ensure consistency
        ui_generator_handler.repo_name = github_handler.repo_name
        ui_generator_handler.repo_url = github_handler.repo_url
        code_analysis_handler.repo_name = github_handler.repo_name
        code_analysis_handler.repo_url = github_handler.repo_url
        auto_deploy_handler.repo_name = github_handler.repo_name
        auto_deploy_handler.repo_url = github_handler.repo_url

    # Update the GitHub handler to share its repo path
    original_execute = github_handler.execute
    async def wrapped_execute(params):
        result = await original_execute(params)
        # Make sure to sync the repo path after any github_repo action that might change it
        update_repo_path(github_handler.repo_path)
        return result
    
    github_handler.execute = wrapped_execute

    # Add repo_name and repo_url to other handlers
    ui_generator_handler.repo_name = None
    ui_generator_handler.repo_url = None
    code_analysis_handler.repo_name = None
    code_analysis_handler.repo_url = None
    auto_deploy_handler.repo_name = None
    auto_deploy_handler.repo_url = None

    # Wrap the code_analysis execute method to validate repository
    original_code_analysis_execute = code_analysis_handler.execute
    async def code_analysis_wrapped_execute(params):
        # Ensure we have a valid repository path
        if not code_analysis_handler.repo_path or not os.path.exists(code_analysis_handler.repo_path):
            return ToolExecution(content="Error: No valid repository is currently cloned. Please clone a repository first.")
        
        # Double-check if the path is a git repository
        try:
            current_dir = os.getcwd()
            os.chdir(code_analysis_handler.repo_path)
            is_git_repo = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                check=False
            )
            os.chdir(current_dir)
            
            if is_git_repo.returncode != 0:
                return ToolExecution(content="Error: The current path is not a valid git repository. Please clone a repository first.")
        except Exception:
            return ToolExecution(content="Error: Could not verify if the current path is a git repository. Please clone a repository first.")
        
        # Call the original method
        return await original_code_analysis_execute(params)

    code_analysis_handler.execute = code_analysis_wrapped_execute

    # Also wrap UI generator execute method to validate repository
    original_ui_generator_execute = ui_generator_handler.execute
    async def ui_generator_wrapped_execute(params):
        # Ensure we have a valid repository path
        if not ui_generator_handler.repo_path or not os.path.exists(ui_generator_handler.repo_path):
            return ToolExecution(content="Error: No valid repository is currently cloned. Please clone a repository first.")
        
        # Call the original method
        return await original_ui_generator_execute(params)

    ui_generator_handler.execute = ui_generator_wrapped_execute

    # Wrap the auto_deploy execute method to validate repository
    original_auto_deploy_execute = auto_deploy_handler.execute
    async def auto_deploy_wrapped_execute(params):
        # Ensure we have a valid repository path
        if not auto_deploy_handler.repo_path or not os.path.exists(auto_deploy_handler.repo_path):
            return ToolExecution(content="Error: No valid repository is currently cloned. Please clone a repository first.")
        
        # Call the original method
        return await original_auto_deploy_execute(params)

    auto_deploy_handler.execute = auto_deploy_wrapped_execute

    # Store all tools in the server's tools list
    server_instance.tools = [
        time_tool, 
        calc_tool, 
        weather_tool, 
        github_repo_tool, 
        command_execution_tool, 
        ui_generator_tool, 
        code_analysis_tool,
        auto_deploy_tool
    ]
    
    # Implement a direct I/O approach that's compatible with the MCP protocol
    reader = asyncio.StreamReader()
    read_protocol = asyncio.StreamReaderProtocol(reader)
    
    # Get the event loop
    loop = asyncio.get_event_loop()
    
    # Connect pipes
    await loop.connect_read_pipe(lambda: read_protocol, sys.stdin)
    write_transport, _ = await loop.connect_write_pipe(asyncio.Protocol, sys.stdout)
    
    while True:
        try:
            # Read a line of input (a JSON-encoded request)
            line = await reader.readline()
            if not line:
                break
                
            # Decode and process the request
            request = json.loads(line.decode('utf-8'))
            
            if request.get("type") == "initialize":
                # Handle initialize request
                response = {
                    "type": "initialize_result",
                    "supportedVersions": ["0.1.0"],
                    "tools": [{
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    } for tool in server_instance.tools]
                }
                
            elif request.get("type") == "list_tools":
                # Handle list_tools request
                response = {
                    "type": "list_tools_result",
                    "tools": [{
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    } for tool in server_instance.tools]
                }
                
            elif request.get("type") == "execute_tool":
                # Handle execute_tool request
                tool_name = request.get("name")
                tool_args = request.get("arguments", {})
                
                # Find the tool
                tool = next((t for t in server_instance.tools if t.name == tool_name), None)
                
                if tool:
                    # Execute the tool
                    result = await tool.handler.execute(tool_args)
                    response = {
                        "type": "execute_tool_result",
                        "content": result.content
                    }
                else:
                    response = {
                        "type": "error",
                        "message": f"Tool '{tool_name}' not found"
                    }
            else:
                # Unknown request type
                response = {
                    "type": "error",
                    "message": f"Unknown request type: {request.get('type')}"
                }
            
            # Send response - write directly to transport to avoid drain_helper issue
            response_json = json.dumps(response).encode('utf-8') + b'\n'
            write_transport.write(response_json)
                
        except asyncio.CancelledError:
            # Handle cancellation
            break
        except json.JSONDecodeError as e:
            # Handle JSON decode error
            error_msg = json.dumps({
                "type": "error",
                "message": f"Invalid JSON: {str(e)}"
            }).encode('utf-8') + b'\n'
            write_transport.write(error_msg)
        except Exception as e:
            # Handle other errors
            error_msg = json.dumps({
                "type": "error",
                "message": f"Server error: {str(e)}"
            }).encode('utf-8') + b'\n'
            write_transport.write(error_msg)
    
    # Clean up
    if write_transport:
        write_transport.close()

if __name__ == "__main__":
    asyncio.run(main()) 