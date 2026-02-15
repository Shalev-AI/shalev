import os
import sys
from openai import OpenAI
from dataclasses import dataclass, field
import difflib
import yaml
from pprint import pprint
from yaspin import yaspin
from typing import List
from shalev.shalev_eachrun_setup import ShalevWorkspace  # <-- adjust path if needed
from shalev.shalev_config import get_openai_api_key

SIZE_LIMIT = 30000

# Lazy load the OpenAI client
_client = None

def get_client():
    global _client
    if _client is None:
        api_key = get_openai_api_key()
        try:
            if api_key:
                _client = OpenAI(api_key=api_key)
            else:
                if not os.environ.get("OPENAI_API_KEY"):
                    print("No OpenAI API key found. Set one with: shalev config --openai-api-key <key>", file=sys.stderr)
                    sys.exit(1)
                _client = OpenAI()
        except Exception:
            print(f"Problem with OpenAI client - check API key.", file=sys.stderr)
            sys.exit(1)
    return _client

@dataclass
class ActionPrompt:
    agent_command_name: str
    main_source_label: str
    system_prompt: dict
    user_prompt: dict
    # additional_source_label: field(repr = False) QQQQ

def load_agent_configs_from_folder(folder_path: str, include_category: bool = False):
    """Load agent configs from folder and subdirectories.

    Searches the root folder and subdirectories (global/, project/, component/).
    Actions in subdirectories are categorized by their folder name.

    Args:
        folder_path: Path to the action_prompts folder
        include_category: If True, returns dict of {name: (ActionPrompt, category)}
                         If False, returns dict of {name: ActionPrompt}
    """
    agent_configs = {}

    # Define search locations: (subfolder, category_name)
    # None subfolder means root folder
    search_locations = [
        (None, 'uncategorized'),
        ('global', 'global'),
        ('project', 'project'),
        ('component', 'component'),
    ]

    for subfolder, category in search_locations:
        if subfolder:
            search_path = os.path.join(folder_path, subfolder)
        else:
            search_path = folder_path

        if not os.path.isdir(search_path):
            continue

        for filename in os.listdir(search_path):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                filepath = os.path.join(search_path, filename)
                # Skip if it's a directory
                if os.path.isdir(filepath):
                    continue
                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)
                action_prompt = ActionPrompt(**data)
                if include_category:
                    agent_configs[action_prompt.agent_command_name] = (action_prompt, category)
                else:
                    agent_configs[action_prompt.agent_command_name] = action_prompt

    return agent_configs


def agent_action_single_component(workspace_data: ShalevWorkspace, action_handle, project_handle, component_handle):
    agent_configs = load_agent_configs_from_folder(workspace_data.action_prompts_folder) #QQQQ do someplace else
    try:
        action_prompt = agent_configs[action_handle]
    except KeyError:
        print(f"No agent action {action_handle}.", file=sys.stderr)
        sys.exit(1)
    component_path = os.path.join(workspace_data.projects[project_handle].components_folder, component_handle)
    try:
        file_size = os.path.getsize(component_path)
        if file_size > SIZE_LIMIT:
            raise ValueError(f"File {component_path} is too large ({file_size} bytes; limit is {SIZE_LIMIT} bytes).")
        with open(component_path, "r", encoding="utf-8") as f:
            component_text = f.read()
    except Exception as e:
        print(f"Failed to read component file: {e}", file=sys.stderr)
        sys.exit(1)    
    messages = make_LLM_messages_single_component(action_prompt, component_text)
    client = get_client()
    try:
        with yaspin(text="Waiting for LLM response...") as spinner:
            response = client.chat.completions.create(model="gpt-4o",messages=messages)
    except Exception as e:
        print(f"OpenAI API error: {e}")
        sys.exit(1)
    revised_component_text = response.choices[0].message.content
    overwrite_component(component_path, revised_component_text)
    # compare_strings_succinct(component_text, revised_component_text)
    # logger.info("start_job", job_id=689, status="running") #QQQQ still doesn't work

def agent_action_source_and_dest_components(workspace_data: ShalevWorkspace, 
                                            action_handle, 
                                            source_project_handle, source_component_handle,
                                            dest_project_handle, dest_component_handle):
    # print(f"{source_project_handle=}, {source_component_handle=}, {dest_project_handle=}, {dest_component_handle=}")
    agent_configs = load_agent_configs_from_folder(workspace_data.action_prompts_folder) #QQQQ do someplace else
    try:
        action_prompt = agent_configs[action_handle]
    except KeyError:
        print(f"No agent action {action_handle}.", file=sys.stderr)
        sys.exit(1)
    source_component_path = os.path.join(workspace_data.projects[source_project_handle].components_folder, source_component_handle)
    dest_component_path = os.path.join(workspace_data.projects[dest_project_handle].components_folder, dest_component_handle)
    try:
        source_file_size = os.path.getsize(source_component_path)
        if source_file_size > SIZE_LIMIT:
            raise ValueError(f"File {source_component_path} is too large ({file_size} bytes; limit is {SIZE_LIMIT} bytes).")
        with open(source_component_path, "r", encoding="utf-8") as f:
            source_component_text = f.read()
    except Exception as e:
        print(f"Failed to read component file: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        dest_file_size = os.path.getsize(dest_component_path)
        if dest_file_size > SIZE_LIMIT:
            raise ValueError(f"File {dest_component_path} is too large ({file_size} bytes; limit is {SIZE_LIMIT} bytes).")
        with open(dest_component_path, "r", encoding="utf-8") as f:
            dest_component_text = f.read()
    except Exception as e:
        print(f"Failed to read component file: {e}", file=sys.stderr)
        sys.exit(1)        
    messages = make_LLM_messages_source_and_dest_components(action_prompt, source_component_text, dest_component_text)
    client = get_client()
    try:
        with yaspin(text="Waiting for LLM response...") as spinner:
            response = client.chat.completions.create(model="gpt-4o",messages=messages)
    except Exception as e:
        print(f"OpenAI API error: {e}")
        sys.exit(1)
    revised_dest_component_text = response.choices[0].message.content
    overwrite_component(dest_component_path, revised_dest_component_text)

def overwrite_component(component_path, revised_component_text):
    if os.path.isfile(component_path):
        old_size = os.path.getsize(component_path)
    else:
        old_size = 0
    new_size = len(revised_component_text.encode('utf-8'))
    with open(component_path, 'w', encoding='utf-8') as f:
        f.write(revised_component_text)
    print(f"Wrote new content to {component_path}.")
    print(f"Previous file size: {old_size} bytes")
    print(f"New file size: {new_size} bytes ({'increased' if new_size > old_size else 'decreased' if new_size < old_size else 'unchanged'})")

def make_LLM_messages_single_component(action_prompt, component_text):
    messages=[
                {
                "role": "system",
                "content": action_prompt.system_prompt["content"],
                },
                {
                "role": "user",
                "content": component_text
                }
            ]
    return messages

def make_LLM_messages_source_and_dest_components(action_prompt, source_component_text, dest_component_text):
    messages=[
                {
                "role": "system",
                "content": action_prompt.system_prompt["content"],
                },
                {
                "role": "user",
                "content": "**INPUT**\n"+source_component_text+"\n\n**TARGET**\n"+dest_component_text
                }
            ]
    return messages


def make_LLM_messages_multi_input_components(action_prompt, input_texts: List[str], target_text: str):
    """Build LLM messages with multiple numbered inputs and one target.

    Format:
    **INPUT 1**
    {text1}

    **INPUT 2**
    {text2}

    **TARGET**
    {target}
    """
    user_content_parts = []
    for i, text in enumerate(input_texts, 1):
        user_content_parts.append(f"**INPUT {i}**\n{text}")
    user_content_parts.append(f"**TARGET**\n{target_text}")

    messages = [
        {
            "role": "system",
            "content": action_prompt.system_prompt["content"],
        },
        {
            "role": "user",
            "content": "\n\n".join(user_content_parts)
        }
    ]
    return messages


def agent_action_multi_input_components(
    workspace_data: ShalevWorkspace,
    action_handle: str,
    input_projects_components: List[tuple],  # [(project, component), ...]
    target_project: str,
    target_component: str
):
    """Run an agent action with multiple input components and one target component.

    Input components are read-only examples. The target component is transformed
    based on the style/content of the inputs and overwritten in place.
    """
    agent_configs = load_agent_configs_from_folder(workspace_data.action_prompts_folder)
    try:
        action_prompt = agent_configs[action_handle]
    except KeyError:
        print(f"No agent action {action_handle}.", file=sys.stderr)
        sys.exit(1)

    # Read all input components
    input_texts = []
    total_size = 0
    for project, component in input_projects_components:
        component_path = os.path.join(workspace_data.projects[project].components_folder, component)
        try:
            file_size = os.path.getsize(component_path)
            if file_size > SIZE_LIMIT:
                raise ValueError(f"File {component_path} is too large ({file_size} bytes; limit is {SIZE_LIMIT} bytes).")
            total_size += file_size
            with open(component_path, "r", encoding="utf-8") as f:
                input_texts.append(f.read())
        except Exception as e:
            print(f"Failed to read input component file: {e}", file=sys.stderr)
            sys.exit(1)

    # Read target component
    target_component_path = os.path.join(workspace_data.projects[target_project].components_folder, target_component)
    try:
        target_file_size = os.path.getsize(target_component_path)
        if target_file_size > SIZE_LIMIT:
            raise ValueError(f"File {target_component_path} is too large ({target_file_size} bytes; limit is {SIZE_LIMIT} bytes).")
        total_size += target_file_size
        with open(target_component_path, "r", encoding="utf-8") as f:
            target_text = f.read()
    except Exception as e:
        print(f"Failed to read target component file: {e}", file=sys.stderr)
        sys.exit(1)

    # Check total message size (inputs + target)
    total_limit = SIZE_LIMIT * 3  # Allow larger total for multi-input
    if total_size > total_limit:
        print(f"Total message size ({total_size} bytes) exceeds limit ({total_limit} bytes).", file=sys.stderr)
        sys.exit(1)

    messages = make_LLM_messages_multi_input_components(action_prompt, input_texts, target_text)
    client = get_client()
    try:
        with yaspin(text="Waiting for LLM response...") as spinner:
            response = client.chat.completions.create(model="gpt-4o", messages=messages)
    except Exception as e:
        print(f"OpenAI API error: {e}")
        sys.exit(1)

    revised_target_text = response.choices[0].message.content
    overwrite_component(target_component_path, revised_target_text)


def compare_strings_succinct(original, corrected):
    diff = difflib.unified_diff(original.split(), corrected.split(), lineterm='')
    # Join and print the differences
    print('\n'.join(diff))

