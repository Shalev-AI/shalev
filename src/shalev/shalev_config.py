import os
import sys
import yaml

CONFIG_FILE = ".shalev.yaml"
SECRETS_FILE = os.path.expanduser("~/.shalev.secrets.yaml")

# Default action prompts to install with --init-actions
DEFAULT_ACTIONS = {
    'global': {
        'fix_grammar.yaml': {
            'agent_command_name': 'gr',
            'main_source_label': '__single_input_component_text',
            'system_prompt': {
                'content': 'Fix any grammar, spelling, and punctuation errors in the text.\n'
                           'Return the corrected text without explanations.\n'
                           'Preserve the original meaning and style.\n'
            },
            'user_prompt': {'content': '__single_input_component_text'},
        },
        'remove_whitespace.yaml': {
            'agent_command_name': 'ws',
            'main_source_label': '__single_input_component_text',
            'system_prompt': {
                'content': 'Remove excessive whitespace from the text.\n'
                           'Normalize line breaks and spacing.\n'
                           'Return the cleaned text without explanations.\n'
            },
            'user_prompt': {'content': '__single_input_component_text'},
        },
        'style_transfer.yaml': {
            'agent_command_name': 'st',
            'main_source_label': '__single_input_component_text',
            'system_prompt': {
                'content': 'You will be provided with text under the title INPUT.\n'
                           'You will also be provided another body of text under the title EXAMPLE.\n'
                           'Your task is to modify the input to have a similar style to EXAMPLE.\n'
                           'Return the modified text without any explanations.\n'
                           'Do not make any changes to meaning, only to the writing style based on EXAMPLE.\n'
            },
            'user_prompt': {'content': '**INPUT**\n__single_input_component_text\n**EXAMPLE**\n__single_example_component_text'},
        },
        'style_transfer_multi.yaml': {
            'agent_command_name': 'stm',
            'main_source_label': '__multi_input_component_texts',
            'system_prompt': {
                'content': 'You will be provided with multiple example texts under INPUT 1, INPUT 2, etc.\n'
                           'These examples demonstrate a particular writing style.\n'
                           'You will also be provided a target text under TARGET.\n'
                           'Your task is to rewrite the TARGET to match the style shown in the INPUT examples.\n'
                           'Return only the rewritten text without explanations.\n'
                           'Preserve the meaning and structure of TARGET, only change the style.\n'
            },
            'user_prompt': {'content': '__multi_input_component_texts'},
        },
    },
    'project': {},
    'component': {},
}


def get_openai_api_key():
    """Read openai_api_key from the secrets file, returns None if missing."""
    if not os.path.exists(SECRETS_FILE):
        return None
    with open(SECRETS_FILE, 'r') as f:
        data = yaml.safe_load(f) or {}
    return data.get('openai_api_key', None)


def save_openai_api_key(key):
    """Write or update the OpenAI API key in the secrets file."""
    if os.path.exists(SECRETS_FILE):
        with open(SECRETS_FILE, 'r') as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    data['openai_api_key'] = key

    with open(SECRETS_FILE, 'w') as f:
        f.write("# Shalev secrets — do NOT commit or share this file.\n")
        yaml.dump(data, f, default_flow_style=False)


def get_aliases():
    """Read aliases from .shalev.yaml, returns empty dict if none exist."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r') as f:
        config_data = yaml.safe_load(f) or {}
    return config_data.get('aliases', {})


def save_alias(short_name, full_component):
    """Add or update an alias in .shalev.yaml."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Run 'shalev config -w <workspace>' first.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE, 'r') as f:
        config_data = yaml.safe_load(f) or {}

    if 'aliases' not in config_data:
        config_data['aliases'] = {}

    config_data['aliases'][short_name] = full_component

    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)


def get_default_project():
    """Read default project from .shalev.yaml, returns None if not set."""
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, 'r') as f:
        config_data = yaml.safe_load(f) or {}
    return config_data.get('default_project', None)


def save_default_project(project_handle):
    """Set the default project in .shalev.yaml."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Run 'shalev config -w <workspace>' first.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE, 'r') as f:
        config_data = yaml.safe_load(f) or {}

    config_data['default_project'] = project_handle

    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)


def init_actions():
    """Initialize action prompt folder structure with default actions."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Run 'shalev config -w <workspace>' first.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE, 'r') as f:
        config_data = yaml.safe_load(f) or {}

    workspace_folder = config_data.get('workspace_folder')
    if not workspace_folder:
        print(f"Error: workspace_folder not set in {CONFIG_FILE}.", file=sys.stderr)
        sys.exit(1)

    # Read workspace config to find action_prompts folder
    workspace_config_path = os.path.join(workspace_folder, "workspace_config.yaml")
    if not os.path.exists(workspace_config_path):
        print(f"Error: workspace_config.yaml not found in '{workspace_folder}'", file=sys.stderr)
        sys.exit(1)

    with open(workspace_config_path, 'r') as f:
        ws_config = yaml.safe_load(f)

    action_prompts_rel = ws_config.get('workspace', {}).get('action_prompts_folder', './action_prompts')
    action_prompts_folder = os.path.join(workspace_folder, action_prompts_rel)

    # Create category subdirectories
    created_dirs = []
    for category in ['global', 'project', 'component']:
        cat_path = os.path.join(action_prompts_folder, category)
        if not os.path.exists(cat_path):
            os.makedirs(cat_path, exist_ok=True)
            created_dirs.append(category)

    if created_dirs:
        print(f"Created subdirectories: {', '.join(created_dirs)}")
    else:
        print("Subdirectories already exist.")

    # Write default actions (skip if file already exists)
    created_actions = []
    skipped_actions = []
    for category, actions in DEFAULT_ACTIONS.items():
        cat_path = os.path.join(action_prompts_folder, category)
        for filename, action_data in actions.items():
            filepath = os.path.join(cat_path, filename)
            if os.path.exists(filepath):
                skipped_actions.append(f"{category}/{filename}")
            else:
                with open(filepath, 'w') as f:
                    yaml.dump(action_data, f, default_flow_style=False, sort_keys=False)
                created_actions.append(f"{category}/{filename}")

    if created_actions:
        print(f"Created {len(created_actions)} default action(s):")
        for action in created_actions:
            print(f"  {action}")
    if skipped_actions:
        print(f"Skipped {len(skipped_actions)} existing action(s):")
        for action in skipped_actions:
            print(f"  {action}")

    print("\nAction prompts initialized. Run 'shalev agent --list' to see available actions.")


def config(workspace_folder=None, openai_api_key=None):
    """Initialize or display Shalev configuration."""
    if openai_api_key is not None:
        save_openai_api_key(openai_api_key)
        print(f"OpenAI API key saved to {SECRETS_FILE}")

    if workspace_folder is None and openai_api_key is None:
        # Display current config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config_data = yaml.safe_load(f)
                print(f"Current configuration in {CONFIG_FILE}:")
                print(yaml.dump(config_data, default_flow_style=False))
        else:
            print(f"No {CONFIG_FILE} found.")
            print(f"Usage: shalev config -w <workspace_folder>")
            sys.exit(1)
        if get_openai_api_key() is None:
            print("No OpenAI API key configured.")
            print("Set one with: shalev config --openai-api-key <key>")
        else:
            print("OpenAI API key: configured")
    elif workspace_folder is not None:
        # Set workspace folder
        workspace_folder = os.path.abspath(workspace_folder)

        # Check if workspace folder exists
        if not os.path.isdir(workspace_folder):
            print(f"Error: Workspace folder '{workspace_folder}' does not exist.", file=sys.stderr)
            sys.exit(1)

        # Check if workspace_config.yaml exists in the workspace folder
        workspace_config_path = os.path.join(workspace_folder, "workspace_config.yaml")
        if not os.path.exists(workspace_config_path):
            print(f"Warning: workspace_config.yaml not found in '{workspace_folder}'", file=sys.stderr)
            print(f"Make sure your workspace folder contains a workspace_config.yaml file.", file=sys.stderr)

        # Create or update config file
        config_data = {"workspace_folder": workspace_folder}

        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        print(f"Created {CONFIG_FILE}")
        print(f"  workspace_folder: {workspace_folder}")