import os
import sys
import yaml

def config(workspace_folder=None):
    """Initialize or display Shalev configuration."""
    config_file = ".shalev.yaml"

    if workspace_folder is None:
        # Display current config
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                print(f"Current configuration in {config_file}:")
                print(yaml.dump(config_data, default_flow_style=False))
        else:
            print(f"No {config_file} found.")
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

        # Create or update .shalev.yaml
        config_data = {"workspace_folder": workspace_folder}

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        print(f"✓ Created {config_file}")
        print(f"  workspace_folder: {workspace_folder}")