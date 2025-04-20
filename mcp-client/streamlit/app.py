import streamlit as st
import subprocess
import sys
import os
import asyncio
import threading
from queue import Queue
from typing import List, Dict
from contextlib import AsyncExitStack
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
import time

# Load environment variables from the .env file 
load_dotenv(".env")

# Check if Anthropic API key is set
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key or anthropic_api_key == "your_api_key_here":
    st.error("Please set your Anthropic API key in the .env file")
    st.stop()

# Main class for handling MCP communication
class MCPGitHubClient:
    def __init__(self):
        self.server_process = None
        self.anthropic = Anthropic()
        self.queue = Queue()
        self.client_session = None
        self.exit_stack = None
        self.tools = []
        
    def start_server(self, server_path):
        """Start the MCP server as a subprocess"""
        try:
            # Start the server process
            self.server_process = subprocess.Popen(
                [sys.executable, server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            return True
        except Exception as e:
            st.error(f"Failed to start server: {str(e)}")
            return False
    
    async def connect_to_server(self):
        """Connect to the running MCP server"""
        try:
            self.exit_stack = AsyncExitStack()
            
            # Create server parameters to connect to the running server
            server_params = StdioServerParameters(
                command=sys.executable,  # Use Python executable as command
                args=[],
                env=None,
                stdin=self.server_process.stdin,
                stdout=self.server_process.stdout
            )
            
            # Connect to the server
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.client_session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            await self.client_session.initialize()
            
            # List available tools
            response = await self.client_session.list_tools()
            self.tools = response.tools
            
            return [tool.name for tool in self.tools]
        except Exception as e:
            st.error(f"Failed to connect to server: {str(e)}")
            return []
    
    async def process_query(self, query: str, history: List[Dict]) -> Dict:
        """Process a query using Claude and available tools"""
        if not self.client_session:
            return {"text": "Error: Not connected to server"}
        
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
                result = await self.client_session.call_tool(tool_name, tool_args)
                
                tool_call = {
                    "name": tool_name,
                    "args": tool_args,
                    "result": result.content
                }
                full_response["tools_used"].append(tool_call)
                
                # Add tool result as a user message
                messages.append({
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "tool_use_id": content.id,
                            "name": tool_name,
                            "input": tool_args
                        }
                    ]
                })
                
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_call_id": content.id,
                            "content": result.content
                        }
                    ]
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
        
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()

# Helper function to run async tasks
def run_async(coro):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()

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

# App header
st.title("GitHub Repository Assistant")
st.caption("Powered by Claude and MCP")

# Server connection section
with st.sidebar:
    st.header("Server Connection")
    server_path = st.text_input("Server Script Path", value="server.py")
    
    if st.button("Start Server & Connect"):
        with st.spinner("Starting server and connecting..."):
            # Create client and start server
            st.session_state.client = MCPGitHubClient()
            
            # Start the server
            if not st.session_state.client.start_server(server_path):
                st.error("Failed to start the server")
                st.stop()
            
            # Give the server a moment to initialize
            time.sleep(2)
            
            # Connect to the server
            tool_names = run_async(st.session_state.client.connect_to_server())
            
            if tool_names:
                st.session_state.connected = True
                st.session_state.tools = tool_names
                st.success(f"Connected to server with tools: {', '.join(tool_names)}")
            else:
                st.error("Failed to connect to the server")
                run_async(st.session_state.client.cleanup())
                st.session_state.client = None

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
    if not st.session_state.repo_cloned:
        # GitHub repo input
        st.header("GitHub Repository Analysis")
        repo_url = st.text_input("GitHub Repository URL", value="https://github.com/deploypilotorg/example-repo")
        
        if st.button("Analyze Repository"):
            if repo_url:
                with st.spinner("Analyzing repository..."):
                    # Ask Claude to analyze the repository
                    response = run_async(st.session_state.client.process_query(
                        f"Clone and analyze this GitHub repository: {repo_url}. Please list the files and provide a brief summary of what the repository contains.",
                        st.session_state.chat_history
                    ))
                    
                    st.session_state.messages.append({"role": "user", "content": f"Clone and analyze this GitHub repository: {repo_url}"})
                    st.session_state.messages.append({"role": "assistant", "content": response["text"]})
                    
                    st.session_state.chat_history.append({"role": "user", "content": f"Clone and analyze this GitHub repository: {repo_url}"})
                    st.session_state.chat_history.append({"role": "assistant", "content": response["text"]})
                    
                    st.session_state.repo_cloned = True
                    st.session_state.repo_url = repo_url
                    st.experimental_rerun()
            else:
                st.error("Please enter a GitHub repository URL")
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

# Handle cleanup when the session ends
def cleanup():
    if st.session_state.client:
        run_async(st.session_state.client.cleanup())

# Register cleanup
st.session_state.cleanup = cleanup