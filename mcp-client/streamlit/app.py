import streamlit as st
import asyncio
import threading
import sys
from queue import Queue
from typing import Optional, List, Dict, Any
import os
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

# Check if Anthropic API key is set
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key or anthropic_api_key == "your_api_key_here":
    st.error("Please set your Anthropic API key in the .env file")
    st.stop()

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = None
        self.anthropic = Anthropic()
        self.tools = []
        self.connected = False
        self.messages_history = []
        
    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server"""
        from contextlib import AsyncExitStack
        
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')

        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        self.exit_stack = AsyncExitStack()
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        self.tools = response.tools
        tool_names = [tool.name for tool in self.tools]
        self.connected = True
        
        return tool_names

    async def process_query(self, query: str, history: List[Dict]) -> Dict:
        """Process a query using Claude and available tools"""
        messages = history + [
            {
                "role": "user",
                "content": query
            }
        ]

        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in self.tools
        ]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=messages,
            tools=available_tools
        )

        full_response = {"text": "", "tools_used": []}
        
        for content in response.content:
            if content.type == 'text':
                full_response["text"] += content.text
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                
                tool_call = {
                    "name": tool_name,
                    "args": tool_args,
                    "result": result.content
                }
                full_response["tools_used"].append(tool_call)
                
                if hasattr(content, 'text') and content.text:
                    messages.append({
                        "role": "assistant",
                        "content": content.text
                    })
                
                # Add tool result as a user message
                messages.append({
                    "role": "user",
                    "content": f"Tool result: {result.content}"
                })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    messages=messages,
                )
                
                for content_item in response.content:
                    if content_item.type == 'text':
                        full_response["text"] += f"\n\n{content_item.text}"

        return full_response

    async def cleanup(self):
        """Clean up resources"""
        if self.exit_stack:
            await self.exit_stack.aclose()


# Initialize session state
if "client" not in st.session_state:
    st.session_state.client = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "tools" not in st.session_state:
    st.session_state.tools = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "repo_cloned" not in st.session_state:
    st.session_state.repo_cloned = False
if "repo_url" not in st.session_state:
    st.session_state.repo_url = ""

# Helper function to run async tasks
def run_async(coro):
    loop = asyncio.new_event_loop()
    return loop.run_until_complete(coro)

# App header
st.title("GitHub Repository Assistant")
st.caption("Powered by Claude and MCP")

# Sidebar for server connection
with st.sidebar:
    st.header("Server Connection")
    server_script = st.text_input("Server Script Path", value="server.py")
    
    if st.button("Connect to Server"):
        if server_script:
            with st.spinner("Connecting to server..."):
                try:
                    st.session_state.client = MCPClient()
                    tool_names = run_async(st.session_state.client.connect_to_server(server_script))
                    st.session_state.connected = True
                    st.session_state.tools = tool_names
                    st.success(f"Connected to server with tools: {', '.join(tool_names)}")
                except Exception as e:
                    st.error(f"Failed to connect to server: {str(e)}")
        else:
            st.error("Please provide a server script path")
    
    if st.session_state.connected:
        st.success("Status: Connected")
        st.write("Available tools:")
        for tool in st.session_state.tools:
            st.write(f"- {tool}")
    else:
        st.error("Status: Disconnected")

# Main content area
if not st.session_state.connected:
    st.info("Please connect to the server first using the sidebar.")
else:
    # GitHub repo input
    if not st.session_state.repo_cloned:
        st.header("GitHub Repository")
        repo_url = st.text_input("GitHub Repository URL", value="https://github.com/deploypilotorg/example-repo")
        
        if st.button("Analyze Repository"):
            if repo_url:
                with st.spinner("Cloning repository..."):
                    try:
                        response = run_async(st.session_state.client.process_query(
                            f"Clone and analyze this GitHub repository: {repo_url}",
                            st.session_state.chat_history
                        ))
                        
                        st.session_state.messages.append({"role": "user", "content": f"Clone and analyze this GitHub repository: {repo_url}"})
                        st.session_state.messages.append({"role": "assistant", "content": response["text"]})
                        
                        # Update chat history for Claude
                        st.session_state.chat_history.append({"role": "user", "content": f"Clone and analyze this GitHub repository: {repo_url}"})
                        st.session_state.chat_history.append({"role": "assistant", "content": response["text"]})
                        
                        st.session_state.repo_cloned = True
                        st.session_state.repo_url = repo_url
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to clone repository: {str(e)}")
            else:
                st.error("Please provide a GitHub repository URL")
    else:
        # Display chat interface
        st.header(f"GitHub Repository: {st.session_state.repo_url}")
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        user_input = st.chat_input("Ask about the repository or request tasks (e.g., 'Create a deployment workflow for this code')")
        
        if user_input:
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Get response from Claude with tools
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        response = run_async(st.session_state.client.process_query(
                            user_input,
                            st.session_state.chat_history
                        ))
                        
                        # Display assistant response
                        st.markdown(response["text"])
                        
                        # Add assistant message to chat
                        st.session_state.messages.append({"role": "assistant", "content": response["text"]})
                        
                        # Update chat history for Claude
                        st.session_state.chat_history.append({"role": "user", "content": user_input})
                        st.session_state.chat_history.append({"role": "assistant", "content": response["text"]})
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        # Reset button
        if st.button("Analyze a different repository"):
            st.session_state.repo_cloned = False
            st.session_state.repo_url = ""
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.experimental_rerun()

# Handle cleanup when the app is closed
# Note: This doesn't work perfectly in Streamlit as there's no clean way to detect app shutdown
# The resources will be cleaned up when the Streamlit server stops
def cleanup():
    if st.session_state.client:
        run_async(st.session_state.client.cleanup())

# Register cleanup
st.session_state.stop_callback = cleanup 