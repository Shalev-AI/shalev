import os
import sys
import yaml

CONFIG_FILE = ".shalev.yaml"


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


def config(workspace_folder=None):
    """Initialize or display Shalev configuration."""
    if workspace_folder is None:
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
    else:
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