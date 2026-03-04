#!/usr/bin/env python3
"""
Minimal ReAct Agent for MCP Jose

A fully functional ReAct (Reasoning + Acting) agent that can use MCP tools,
skills, and follow the AGENTS.md guidelines. Supports:
- Tool calling (search, vision, LLM, WhatsApp, navigation, OCR, etc.)
- Reasoning/thinking steps
- Action execution
- Final answer generation

Usage:
    python react_agent.py "What is the weather in Tokyo?"
    python react_agent.py --prompt "Find and summarize the latest AI news"
    python react_agent.py --interactive
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
env_file = Path(__file__).parent.parent / "auth" / ".env"
if env_file.exists():
    load_dotenv(env_file)


@dataclass
class Tool:
    """Represents an available tool."""

    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable[..., Any]


@dataclass
class Step:
    """Represents a single step in the ReAct loop."""

    step_type: str  # 'thought', 'action', 'observation', 'final_answer'
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    tool_output: Optional[Any] = None


@dataclass
class Skill:
    """Represents a loaded skill."""

    name: str
    description: str
    content: str


class SkillLoader:
    """Loads skills from the .agents/skills directory."""

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            self.skills_dir = Path(__file__).parent.parent / ".agents" / "skills"
        else:
            self.skills_dir = skills_dir

    def load_skill(self, skill_name: str) -> Optional[Skill]:
        """Load a specific skill by name."""
        skill_path = self.skills_dir / skill_name / "SKILL.md"
        if not skill_path.exists():
            return None

        content = skill_path.read_text()

        # Extract description from first paragraph
        lines = content.split("\n")
        description = ""
        for line in lines[1:]:  # Skip title
            line = line.strip()
            if line and not line.startswith("#"):
                description = line
                break

        return Skill(
            name=skill_name,
            description=description or f"Skill: {skill_name}",
            content=content,
        )

    def list_skills(self) -> List[str]:
        """List all available skills."""
        if not self.skills_dir.exists():
            return []

        skills = []
        for item in self.skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skills.append(item.name)
        return sorted(skills)

    def load_all_skills(self) -> Dict[str, Skill]:
        """Load all available skills."""
        skills = {}
        for skill_name in self.list_skills():
            skill = self.load_skill(skill_name)
            if skill:
                skills[skill_name] = skill
        return skills


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._init_tools()

    def _init_tools(self):
        """Initialize all available MCP tools."""
        try:
            # Import providers
            from providers import ProviderFactory
            from providers.search import SearchFactory

            # Initialize filesystem tools
            from tools.filesystem import FilesystemTools

            self.fs_tools = FilesystemTools()

            # Filesystem tools
            self.register_tool(
                Tool(
                    name="read_file",
                    description="Read contents of a text file. Optionally specify head=N or tail=N lines",
                    parameters={
                        "path": "str",
                        "head": "optional int",
                        "tail": "optional int",
                    },
                    func=self._read_file,
                )
            )

            self.register_tool(
                Tool(
                    name="list_directory",
                    description="List directory contents with [FILE] or [DIR] prefixes",
                    parameters={"path": "str"},
                    func=self._list_directory,
                )
            )

            self.register_tool(
                Tool(
                    name="write_file",
                    description="Write content to a file (creates parent directories if needed)",
                    parameters={"path": "str", "content": "str"},
                    func=self._write_file,
                )
            )

            self.register_tool(
                Tool(
                    name="create_directory",
                    description="Create a directory (creates parent directories if needed)",
                    parameters={"path": "str"},
                    func=self._create_directory,
                )
            )

            self.register_tool(
                Tool(
                    name="move_file",
                    description="Move or rename a file or directory",
                    parameters={"source": "str", "destination": "str"},
                    func=self._move_file,
                )
            )

            self.register_tool(
                Tool(
                    name="get_file_info",
                    description="Get detailed file/directory metadata (size, permissions, timestamps)",
                    parameters={"path": "str"},
                    func=self._get_file_info,
                )
            )

            self.register_tool(
                Tool(
                    name="search_files",
                    description="Search for files matching a glob pattern recursively",
                    parameters={
                        "path": "str",
                        "pattern": "str",
                        "exclude_patterns": "optional list",
                    },
                    func=self._search_files,
                )
            )

            self.register_tool(
                Tool(
                    name="list_allowed_directories",
                    description="List directories the filesystem tools are allowed to access",
                    parameters={},
                    func=self._list_allowed_directories,
                )
            )

            # Search tool
            self.register_tool(
                Tool(
                    name="search",
                    description="Search the web using DuckDuckGo or Google",
                    parameters={"query": "str"},
                    func=self._search,
                )
            )

            # Navigation tool
            self.register_tool(
                Tool(
                    name="navigate_to_url",
                    description="Navigate to a URL and extract content (HTML or PDF)",
                    parameters={"url": "str"},
                    func=self._navigate,
                )
            )

            # LLM tool
            self.register_tool(
                Tool(
                    name="call_llm",
                    description="Generate text using OpenAI LLM",
                    parameters={"prompt": "str"},
                    func=self._call_llm,
                )
            )

            # Vision tools
            self.register_tool(
                Tool(
                    name="openai_vision",
                    description="Process image with OpenAI vision model",
                    parameters={"image_path": "str", "prompt": "str"},
                    func=self._openai_vision,
                )
            )

            self.register_tool(
                Tool(
                    name="gemini_vision",
                    description="Process image with Gemini vision model",
                    parameters={"image_path": "str", "prompt": "str"},
                    func=self._gemini_vision,
                )
            )

            # Image generation
            self.register_tool(
                Tool(
                    name="generate_image",
                    description="Generate an image from text using Gemini",
                    parameters={"prompt": "str", "output_path": "optional str"},
                    func=self._generate_image,
                )
            )

            # OCR
            self.register_tool(
                Tool(
                    name="google_ocr",
                    description="Extract text from images or PDFs using Google Vision OCR",
                    parameters={"input_file": "str"},
                    func=self._google_ocr,
                )
            )

            # Transcription
            self.register_tool(
                Tool(
                    name="transcribe_audio",
                    description="Transcribe audio file to text using OpenAI Whisper",
                    parameters={
                        "audio_path": "str",
                        "model": "optional str",
                        "language": "optional str",
                    },
                    func=self._transcribe_audio,
                )
            )

            # WhatsApp
            self.register_tool(
                Tool(
                    name="send_ws_msg",
                    description="Send a WhatsApp message using Meta Cloud API",
                    parameters={
                        "destination": "optional str",
                        "message": "str",
                        "template_name": "optional str",
                    },
                    func=self._send_whatsapp,
                )
            )

        except Exception as e:
            print(f"Warning: Some tools may not be available: {e}")

    def register_tool(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[Tool]:
        """List all registered tools."""
        return list(self.tools.values())

    def get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for the LLM."""
        descriptions = []
        for tool in self.tools.values():
            desc = f"- {tool.name}: {tool.description}\n"
            desc += f"  Parameters: {json.dumps(tool.parameters)}"
            descriptions.append(desc)
        return "\n".join(descriptions)

    # Tool implementations
    def _search(self, query: str) -> Dict[str, Any]:
        from providers.search import SearchFactory

        provider = SearchFactory.create()
        return provider.search(query)

    def _navigate(self, url: str) -> Dict[str, Any]:
        from tools.navigation import extract_html_content, extract_pdf_content
        from core.http_client import HTTPClient
        from core.utils import is_pdf_file

        client = HTTPClient()

        try:
            if is_pdf_file(url):
                pdf_content = extract_pdf_content(url, client)
                if pdf_content:
                    return {"content": pdf_content, "url": url, "type": "pdf"}

            content = extract_html_content(url, client)
            return {"content": content, "url": url, "type": "html"}
        except Exception as e:
            return {"error": str(e), "url": url}

    def _call_llm(self, prompt: str) -> Dict[str, str]:
        from providers import ProviderFactory

        llm = ProviderFactory.create_llm("openai")
        result = llm.complete(prompt)
        return {"text": result}

    def _openai_vision(self, image_path: str, prompt: str, **kwargs) -> Dict[str, str]:
        from providers import ProviderFactory

        vision = ProviderFactory.create_vision("openai")
        result = vision.process_image(image_path, prompt)
        return {"text": result}

    def _gemini_vision(self, image_path: str, prompt: str, **kwargs) -> Dict[str, str]:
        from providers import ProviderFactory

        vision = ProviderFactory.create_vision("gemini")
        result = vision.process_image(image_path, prompt)
        return {"text": result}

    def _generate_image(
        self, prompt: str, output_path: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        from providers import ProviderFactory

        gen = ProviderFactory.create_image_generator("gemini")
        return gen.generate(prompt, output_path)

    def _google_ocr(self, input_file: str, **kwargs) -> Dict[str, Any]:
        from providers import ProviderFactory

        ocr = ProviderFactory.create_ocr("google")
        annotations = ocr.extract_text(input_file)
        return {"annotations": annotations}

    def _transcribe_audio(
        self,
        audio_path: str,
        model: str = "gpt-4o-transcribe",
        language: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        from providers import ProviderFactory

        trans = ProviderFactory.create_transcription("openai")
        result = trans.transcribe(audio_path, model=model, language=language)
        return {"text": result if isinstance(result, str) else str(result)}

    def _send_whatsapp(
        self,
        destination: Optional[str] = None,
        message: str = "",
        template_name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        from tools.whatsapp import WhatsAppCloudAPIClient, WhatsAppSendResult

        default_dest = os.getenv("WHATSAPP_DEFAULT_DESTINATION")
        dest = destination or default_dest

        if not dest:
            return {"error": "No destination provided"}

        try:
            api = WhatsAppCloudAPIClient(
                access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
                phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            )
            result = api.send_text_message(dest, message, template_name)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    # Filesystem tool implementations
    def _read_file(
        self,
        path: str,
        head: Optional[int] = None,
        tail: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        return self.fs_tools.read_text_file(path, head, tail)

    def _list_directory(self, path: str, **kwargs) -> Dict[str, Any]:
        return self.fs_tools.list_directory(path)

    def _write_file(self, path: str, content: str, **kwargs) -> Dict[str, Any]:
        return self.fs_tools.write_file(path, content)

    def _create_directory(self, path: str, **kwargs) -> Dict[str, Any]:
        return self.fs_tools.create_directory(path)

    def _move_file(self, source: str, destination: str, **kwargs) -> Dict[str, Any]:
        return self.fs_tools.move_file(source, destination)

    def _get_file_info(self, path: str, **kwargs) -> Dict[str, Any]:
        return self.fs_tools.get_file_info(path)

    def _search_files(
        self,
        path: str,
        pattern: str,
        exclude_patterns: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        return self.fs_tools.search_files(path, pattern, exclude_patterns)

    def _list_allowed_directories(self, **kwargs) -> Dict[str, Any]:
        return self.fs_tools.list_allowed_directories()


class ReActAgent:
    """
    ReAct Agent implementing the Reasoning + Acting pattern.

    The agent follows this loop:
    1. Thought: Reason about what to do next
    2. Action: Execute a tool call
    3. Observation: Process the result
    4. Repeat until ready for final answer
    5. Final Answer: Provide the response
    """

    def __init__(self, max_iterations: int = 10, verbose: bool = True):
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.tool_registry = ToolRegistry()
        self.skill_loader = SkillLoader()
        self.steps: List[Step] = []

        # Load AGENTS.md context
        self.agents_md = self._load_agents_md()

        # Initialize LLM for reasoning
        self._init_llm()

    def _load_agents_md(self) -> str:
        """Load AGENTS.md for context."""
        agents_md_path = Path(__file__).parent.parent / "AGENTS.md"
        if agents_md_path.exists():
            return agents_md_path.read_text()
        return ""

    def _init_llm(self):
        """Initialize the LLM provider."""
        try:
            from providers import ProviderFactory

            self.llm = ProviderFactory.create_llm("openai")
        except Exception as e:
            print(f"Warning: Could not initialize LLM: {e}")
            self.llm = None

    def _build_system_prompt(self, skills_context: str = "") -> str:
        """Build the system prompt with tool descriptions and guidelines."""
        tool_descriptions = self.tool_registry.get_tool_descriptions()
        available_skills = ", ".join(self.skill_loader.list_skills())

        prompt = f"""You are a ReAct agent that solves tasks by reasoning and taking actions.

## Available Tools
{tool_descriptions}

## Available Skills
{available_skills}

## Guidelines
{self.agents_md[:2000] if self.agents_md else "Follow best practices for tool usage."}

{skills_context}

## Response Format
You MUST respond with EXACTLY ONE of these formats per turn:

1. **For reasoning and tool use (ONLY ONE ACTION PER RESPONSE):**
Thought: [Your reasoning about what to do next]
Action: [Exactly one tool name from the list above]
Action Input: [Valid JSON object with required parameters]

2. **For final answer (when task is complete):**
Thought: [Your final reasoning about why you have enough information]
Final Answer: [Your complete, helpful response to the user's original question]

## Critical Rules
- ONLY ONE Thought-Action pair per response (never multiple actions)
- After each Action, you will receive an Observation - WAIT for it
- Always start with exactly one Thought
- Use exact tool names from the available tools list
- Action Input MUST be valid JSON with no extra characters
- Only give Final Answer when you have ALL needed information
- Never hallucinate tool names - only use tools from the list above
- If a tool fails, reason about alternatives in your next Thought
"""
        return prompt

    def _parse_response(
        self, response: str
    ) -> Tuple[str, Optional[str], Optional[Dict]]:
        """
        Parse the LLM response to extract thought, action, and action input.
        Only processes the FIRST Thought-Action pair, ignoring later content.

        Returns:
            Tuple of (thought, action_name_or_final, action_input)
        """
        # Find the first Thought in the response
        thought_match = re.search(
            r"Thought:\s*(.+?)(?=\nAction:|\nFinal Answer:|\nThought:|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        thought = thought_match.group(1).strip() if thought_match else ""

        # Check if there's an Action before any Final Answer
        # Look for Action that comes after the first Thought
        thought_pos = thought_match.start() if thought_match else 0
        response_after_thought = response[thought_pos:]

        # Find first Action after the Thought
        action_match = re.search(
            r"Action:\s*(\w+)", response_after_thought, re.IGNORECASE
        )

        # Find first Final Answer after the Thought
        final_match = re.search(
            r"Final Answer:\s*(.+)", response_after_thought, re.DOTALL | re.IGNORECASE
        )

        # Determine which comes first: Action or Final Answer
        action_pos = action_match.start() if action_match else float("inf")
        final_pos = final_match.start() if final_match else float("inf")

        if action_match and action_pos < final_pos:
            # Process the action
            action_name = action_match.group(1).strip()

            # Extract action input (only look after the Action line)
            action_end_pos = action_pos + len(action_match.group(0))
            response_after_action = response_after_thought[action_end_pos:]

            input_match = re.search(
                r"Action Input:\s*(\{.*?\}|\[.*?\]|.+?)(?=\n\w+:|\nAction:|\nThought:|\nFinal Answer:|$)",
                response_after_action,
                re.DOTALL | re.IGNORECASE,
            )
            action_input = None
            if input_match:
                input_str = input_match.group(1).strip()
                
                # Clean up common issues: remove trailing invalid characters after JSON
                # If it looks like JSON, try to extract just the valid JSON part
                if input_str.startswith('{') or input_str.startswith('['):
                    # Try to find the end of the JSON structure
                    try:
                        # Attempt to parse progressively shorter strings to find valid JSON
                        for end_pos in range(len(input_str), 0, -1):
                            try:
                                action_input = json.loads(input_str[:end_pos])
                                break  # Found valid JSON
                            except json.JSONDecodeError:
                                continue
                    except Exception:
                        pass
                
                # If we still don't have valid input, try the original approach
                if action_input is None:
                    try:
                        action_input = json.loads(input_str)
                    except json.JSONDecodeError:
                        # Try to parse as simple string (but clean it first)
                        # Remove any non-printable or invalid Unicode characters
                        input_str_clean = ''.join(char for char in input_str if char.isprintable() or char in '\n\r\t')
                        action_input = (
                            {"query": input_str_clean}
                            if action_name == "search"
                            else {"prompt": input_str_clean}
                        )

            return thought, action_name, action_input

        elif final_match:
            # Return final answer
            return thought, final_match.group(1).strip(), None

        # No action or final answer found
        return thought, None, None

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a tool and return the result."""
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' not found"}

        try:
            return tool.func(**tool_input)
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM."""
        if self.llm:
            return self.llm.complete(prompt)
        else:
            # Fallback: simple rule-based response
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        """Simple fallback when LLM is not available."""
        # Check if we can answer directly
        if "search" in prompt.lower() and "query" in prompt.lower():
            # Extract query
            match = re.search(r"User task: (.+?)(?=\n|$)", prompt)
            if match:
                query = match.group(1).strip()
                return f'Thought: I need to search for information about \'{query}\'\nAction: search\nAction Input: {{"query": "{query}"}}'

        return "Thought: I don't have access to an LLM. Please configure OpenAI API key.\nFinal Answer: I cannot process this request without an LLM."

    def run(self, task: str, use_skills: Optional[List[str]] = None) -> str:
        """
        Run the ReAct agent on a task.

        Args:
            task: The user's task/prompt
            use_skills: Optional list of skill names to load for context

        Returns:
            The final answer
        """
        # Load skills if specified
        skills_context = ""
        if use_skills:
            skill_parts = []
            for skill_name in use_skills:
                skill = self.skill_loader.load_skill(skill_name)
                if skill:
                    skill_parts.append(f"### {skill.name}\n{skill.content[:1000]}...")
                else:
                    print(f"Warning: Skill '{skill_name}' not found")
            skills_context = "\n\n".join(skill_parts)

        # Build conversation
        system_prompt = self._build_system_prompt(skills_context)
        conversation = f"System: {system_prompt}\n\nUser task: {task}\n\n"

        if self.verbose:
            print(f"\n{'=' * 60}")
            print(f"Task: {task}")
            print(f"{'=' * 60}\n")

        # ReAct loop
        for iteration in range(self.max_iterations):
            if self.verbose:
                print(f"\n--- Iteration {iteration + 1} ---")

            # Get LLM response
            response = self._get_llm_response(conversation)

            if self.verbose:
                print(f"LLM Response:\n{response}\n")

            # Parse response
            thought, action_or_final, action_input = self._parse_response(response)

            # Check for final answer
            if action_or_final and action_input is None:
                # This is a final answer
                step = Step(
                    step_type="final_answer",
                    content=action_or_final,
                    tool_name=None,
                    tool_input=None,
                    tool_output=None,
                )
                self.steps.append(step)

                if self.verbose:
                    print(f"\n{'=' * 60}")
                    print("FINAL ANSWER")
                    print(f"{'=' * 60}\n")

                return action_or_final

            # This is an action
            if action_or_final and action_input is not None:
                # Record thought
                thought_step = Step(
                    step_type="thought",
                    content=thought,
                    tool_name=None,
                    tool_input=None,
                    tool_output=None,
                )
                self.steps.append(thought_step)

                # Record action
                action_step = Step(
                    step_type="action",
                    content=f"Using tool: {action_or_final}",
                    tool_name=action_or_final,
                    tool_input=action_input,
                    tool_output=None,
                )
                self.steps.append(action_step)

                # Execute tool
                if self.verbose:
                    print(f"Executing: {action_or_final}({json.dumps(action_input)})")

                result = self._execute_tool(action_or_final, action_input)

                # Record observation
                observation = json.dumps(result, indent=2)
                obs_step = Step(
                    step_type="observation",
                    content=observation,
                    tool_name=None,
                    tool_input=None,
                    tool_output=result,
                )
                self.steps.append(obs_step)

                if self.verbose:
                    # Show first 1000 chars in console but full observation goes to LLM
                    display_obs = observation if len(observation) <= 1000 else observation[:1000] + "\n... (truncated for display)"
                    print(f"Observation: {display_obs}")

                # Update conversation
                conversation += f"Thought: {thought}\n"
                conversation += f"Action: {action_or_final}\n"
                conversation += f"Action Input: {json.dumps(action_input)}\n"
                conversation += f"Observation: {observation}\n\n"
            else:
                # No clear action or final answer
                conversation += f"Response: {response}\n\n"
                conversation += "System: Please provide either an Action with Action Input, or a Final Answer.\n\n"

        # Max iterations reached
        return "Maximum iterations reached without a final answer."

    def get_history(self) -> List[Step]:
        """Get the execution history."""
        return self.steps

    def clear_history(self):
        """Clear the execution history."""
        self.steps = []


def main():
    """Main entry point with CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="ReAct Agent for MCP Jose")
    parser.add_argument("prompt", nargs="?", help="The task/prompt to execute")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument(
        "--skills", "-s", nargs="+", help="Skills to load (e.g., mcpjose-research docx)"
    )
    parser.add_argument(
        "--max-iterations",
        "-m",
        type=int,
        default=10,
        help="Maximum iterations (default: 10)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Minimal output (only final answer)"
    )
    parser.add_argument(
        "--list-skills", action="store_true", help="List available skills and exit"
    )
    parser.add_argument(
        "--list-tools", action="store_true", help="List available tools and exit"
    )

    args = parser.parse_args()

    # Create agent
    agent = ReActAgent(max_iterations=args.max_iterations, verbose=not args.quiet)

    # List skills
    if args.list_skills:
        skills = agent.skill_loader.list_skills()
        print("Available Skills:")
        for skill in skills:
            loaded = agent.skill_loader.load_skill(skill)
            print(f"  - {skill}: {loaded.description if loaded else 'No description'}")
        return

    # List tools
    if args.list_tools:
        tools = agent.tool_registry.list_tools()
        print("Available Tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        return

    # Interactive mode
    if args.interactive:
        print("ReAct Agent - Interactive Mode")
        print("Type 'exit' or 'quit' to exit\n")

        while True:
            try:
                task = input("\nTask: ").strip()
                if task.lower() in ("exit", "quit", "q"):
                    break
                if not task:
                    continue

                result = agent.run(task, use_skills=args.skills)
                print(f"\n{result}")
                agent.clear_history()

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

    # Single prompt mode
    elif args.prompt:
        result = agent.run(args.prompt, use_skills=args.skills)
        print(result)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
