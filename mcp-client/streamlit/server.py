import sys
import json
import asyncio
import os
import shutil
import tempfile
import subprocess
from datetime import datetime
from typing import Any, Dict

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

async def main():
    # Create server
    server_instance = Server(name="github-repo-server")
    
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
    
    github_tool = Tool(
        name="github_repo",
        description="Clone and interact with GitHub repositories",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform (clone, list_files, read_file, get_repo_info)",
                    "enum": ["clone", "list_files", "read_file", "get_repo_info"]
                },
                "repo_url": {
                    "type": "string",
                    "description": "The URL of the GitHub repository (required for 'clone' action)"
                },
                "path": {
                    "type": "string",
                    "description": "The path within the repository (for 'list_files' action)"
                },
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read (for 'read_file' action)"
                }
            },
            "required": ["action"]
        },
        handler=GitHubRepoToolHandler()
    )
    
    # Add tools to the server
    server_instance.tools = [time_tool, calc_tool, weather_tool, github_tool]
    
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