import sys
import os
import json
import subprocess
import time

def test_mcp_client_connection():
    """
    Test the MCP client connection using the direct protocol approach.
    This uses the same approach as the updated Streamlit app.
    """
    print("Starting test for direct protocol MCP client connection...")
    
    # Start the server as a subprocess
    server_path = "server.py"
    print(f"Starting server from path: {server_path}")
    server_process = subprocess.Popen(
        [sys.executable, server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,  # Line buffered
        text=True   # Text mode for easier handling
    )
    
    # Give the server a moment to initialize
    time.sleep(2)
    
    if server_process.poll() is not None:
        print("Error: Server process exited prematurely")
        stderr = server_process.stderr.read()
        print(f"Server stderr: {stderr}")
        return
    
    print("Server started, attempting to connect...")
    
    try:
        # Send initialize request
        print("Sending initialize request...")
        initialize_request = {"type": "initialize"}
        server_process.stdin.write(json.dumps(initialize_request) + "\n")
        server_process.stdin.flush()
        
        # Read response with timeout
        response_text = read_with_timeout(server_process.stdout, 5)
        if not response_text:
            print("Failed to initialize: no response received")
            return
        
        # Parse the response
        print(f"Response received: {response_text}")
        response = json.loads(response_text)
        if response.get("type") != "initialize_result":
            print(f"Failed to initialize: unexpected response type: {response.get('type')}")
            return
        
        # Get tools
        tools = response.get("tools", [])
        print("✅ Successfully initialized connection!")
        
        # Verify connectivity by listing tools
        print("\nSending list_tools request...")
        list_tools_request = {"type": "list_tools"}
        server_process.stdin.write(json.dumps(list_tools_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        response_text = read_with_timeout(server_process.stdout, 5)
        if not response_text:
            print("Failed to list tools: no response received")
            return
        
        # Parse the response
        print(f"Response received: {response_text}")
        list_response = json.loads(response_text)
        if list_response.get("type") != "list_tools_result":
            print(f"Failed to list tools: unexpected response type: {list_response.get('type')}")
            return
        
        print(f"✅ Successfully listed tools: {len(tools)} tools found")
        for tool in tools:
            print(f"  - {tool.get('name')}: {tool.get('description')}")
        
        # Execute get_time tool
        print("\nExecuting get_time tool...")
        execute_request = {
            "type": "execute_tool",
            "name": "get_time",
            "arguments": {}
        }
        
        server_process.stdin.write(json.dumps(execute_request) + "\n")
        server_process.stdin.flush()
        
        # Read response
        response_text = read_with_timeout(server_process.stdout, 5)
        if not response_text:
            print("Failed to execute tool: no response received")
            return
        
        # Parse the response
        print(f"Response received: {response_text}")
        tool_response = json.loads(response_text)
        if tool_response.get("type") != "execute_tool_result":
            print(f"Failed to execute tool: unexpected response type: {tool_response.get('type')}")
            return
        
        print(f"✅ Successfully executed get_time tool: {tool_response.get('content')}")
        
        print("\n✅ Connection test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        # Terminate the server process
        if server_process and server_process.poll() is None:
            print("Terminating server process...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Warning: Server process did not terminate cleanly, forcing kill")
                server_process.kill()

def read_with_timeout(stream, timeout):
    """Read a line from the stream with a timeout."""
    import select
    
    readable, _, _ = select.select([stream], [], [], timeout)
    
    if readable:
        return stream.readline().strip()
    else:
        return None

if __name__ == "__main__":
    test_mcp_client_connection() 