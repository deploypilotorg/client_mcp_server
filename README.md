# GitHub Repository Assistant

A tool that uses the MCP (Model Control Protocol) to connect Claude with GitHub repositories, allowing users to analyze code and get assistance with tasks like creating deployment workflows.

## Features

- Clone and analyze any GitHub repository
- Interact with repositories through Claude 3.5 Sonnet
- Request deployment workflows and other code generation tasks
- Seamless integration via Streamlit frontend
- MCP server with specialized tools for repository interaction

## Requirements

- Python 3.13 or higher
- Git installed and available in PATH
- An Anthropic API key

## Installation

1. Clone this repository:
   ```
   git clone <your-repo-url>
   cd <repo-directory>
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set your Anthropic API key in the `.env` file:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

## Usage

1. Start the Streamlit application:
   ```
   streamlit run app.py
   ```

2. In the sidebar, connect to the MCP server by entering `server.py` in the "Server Script Path" field and clicking "Connect to Server".

3. Enter a GitHub repository URL (e.g., `https://github.com/deploypilotorg/example-repo`) and click "Analyze Repository".

4. Once the repository is analyzed, you can interact with it by asking questions or requesting tasks like:
   - "What files are in this repository?"
   - "What does the main.py file do?"
   - "Create a GitHub Actions workflow for deploying this code"
   - "Generate a Dockerfile for this application"

## How It Works

The application uses the Model Control Protocol (MCP) to enable Claude to interact with GitHub repositories through specialized tools:

1. The MCP server (`server.py`) provides tools for cloning, analyzing, and reading from GitHub repositories
2. The Streamlit frontend (`app.py`) provides a user-friendly interface for interactions
3. Claude uses the provided tools to understand repository structure and generate relevant responses

## Limitations

- Currently only supports public GitHub repositories
- Large repositories may take longer to clone and analyze
- Generated deployment workflows may need manual adjustments based on specific requirements