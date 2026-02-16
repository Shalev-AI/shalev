import os
import subprocess
import sys
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pprint import pprint

@dataclass
class ShalevProject:
    build_folder: str
    components_folder: str
    description: str
    name: str
    project_folder: str
    root_component: str
    project_handle: str
    results_folder: str
    supporting_files_folder: str
    compose_targets: Optional[Dict[str, str]] = None
    compose_wrapper: Optional[str] = None

@dataclass
class ShalevWorkspace:
    action_prompts_folder: str
    description: str
    name: str
    projects: Dict[str, ShalevProject]
    workspace_system_prompts: Dict[str, str]

def add_prefix_to_project_folders(proj: ShalevProject, prefix: str):
    proj.build_folder = os.path.join(prefix, proj.project_folder, proj.build_folder)
    proj.components_folder = os.path.join(prefix, proj.project_folder, proj.components_folder)
    proj.root_component = os.path.join(proj.components_folder, proj.root_component)
    proj.results_folder = os.path.join(prefix, proj.project_folder, proj.results_folder)
    proj.supporting_files_folder = os.path.join(prefix, proj.project_folder, proj.supporting_files_folder)
    if proj.compose_wrapper:
        proj.compose_wrapper = os.path.join(proj.components_folder, proj.compose_wrapper)
    proj.project_folder = os.path.join(prefix, proj.project_folder)
    return proj

def add_prefix_to_workspace_folders(ws: ShalevWorkspace, prefix: str):
    ws.action_prompts_folder = os.path.join(prefix, ws.action_prompts_folder)
    return ws

def workspace_from_dict(data: dict, workspace_folder: str) -> ShalevWorkspace:
    ws = data['workspace']
    projects_list = [add_prefix_to_project_folders(ShalevProject(**proj), workspace_folder) for proj in ws['projects']]
    projects = {proj.project_handle: proj for proj in projects_list} #QQQQ deal with error if two projects have same handle
    return add_prefix_to_workspace_folders(ShalevWorkspace(
        action_prompts_folder = ws['action_prompts_folder'],
        description = ws['description'],
        name = ws['name'],
        projects = projects,
        workspace_system_prompts = ws['workspace_system_prompts']
    ), workspace_folder)

def check_workspace_data_valid(workspace_data: ShalevWorkspace) -> List[str]:
    folders_to_check = []
    folders_to_check.append(workspace_data.action_prompts_folder)
    for project in workspace_data.projects.values():
        folders_to_check.extend([
            project.project_folder,
            project.build_folder,
            project.components_folder,
            project.results_folder,
            project.supporting_files_folder,
        ])
    return [path for path in folders_to_check if not os.path.isdir(path)]

def check_workspace_health(workspace_data: ShalevWorkspace, workspace_folder: str):
    """Run health checks: git repo presence and .gitignore coverage of build folders."""
    # 1. Check if workspace is inside a git repo
    result = subprocess.run(
        ['git', '-C', workspace_folder, 'rev-parse', '--git-dir'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Warning: Workspace folder is not inside a git repository. Consider running 'git init'.")

    # 2. Check .gitignore for build folders
    gitignore_path = os.path.join(workspace_folder, '.gitignore')
    gitignore_content = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()

    missing_entries = []
    for proj in workspace_data.projects.values():
        rel_build = os.path.relpath(proj.build_folder, workspace_folder)
        if rel_build not in gitignore_content:
            missing_entries.append(rel_build)

    if missing_entries:
        print("Warning: The following build folders are not in .gitignore:")
        for entry in missing_entries:
            print(f"  {entry}")
        answer = input("Add them to .gitignore? [y/n]: ").strip().lower()
        if answer == "y":
            with open(gitignore_path, 'a') as f:
                for entry in missing_entries:
                    f.write(entry + "\n")
            print("Updated .gitignore.")


def setup_workspace(fn = ".shalev.yaml"):
    try:
        with open(fn) as dot_shalev_file:
            dot_shalev_dict = yaml.safe_load(dot_shalev_file)
            if "workspace_folder" in dot_shalev_dict:
                workspace_folder = dot_shalev_dict["workspace_folder"]
            else:
                print(f"workspace_folder is not properly set in {fn}")
                sys.exit(1)
    except FileNotFoundError:
        print(f"Error: {fn} file does not exist, try:\n\t shalev config -w <workspace folder location>", file=sys.stderr)
        sys.exit(1)
    # print("QQQQ:", workspace_folder) todo - log this is our workspace_folder
    try:
        fn = os.path.join(workspace_folder, "workspace_config.yaml")
        with open(fn) as config_file:
            try:
                workspace_dict = yaml.safe_load(config_file)
            except yaml.YAMLError as e:
                print("YAML error:", e, file=sys.stderr)
                sys.exit(1)
            workspace_data = workspace_from_dict(workspace_dict, dot_shalev_dict["workspace_folder"])
            missing_folders = check_workspace_data_valid(workspace_data)
            if missing_folders:
                print("Missing required folders:")
                for folder in missing_folders:
                    print(f"  {folder}")
                answer = input("Create these folders? [y/n]: ").strip().lower()
                if answer == "y":
                    for folder in missing_folders:
                        os.makedirs(folder, exist_ok=True)
                        print(f"  Created: {folder}")
                else:
                    sys.exit(1)
            check_workspace_health(workspace_data, workspace_folder)
            return workspace_data
    except FileNotFoundError:
        print(f"Error: {fn} file does not exist, try:\n\t shalev config -w <workspace folder location>", file=sys.stderr)
        sys.exit(1)

    # workspace_name = config["workspace"]["name"]
    # # print(f"{workspace_name=}")
    # workspace_data["action_prompts_path"] = os.path.join(workspace_dir, config["workspace"]["action_prompts_folder"])

    # projects = config["workspace"]["projects"]
    # workspace_data["projects"] = {}
    # for project in projects:
    #     project_data = {}
    #     project_short_name = project["short_name"]
    #     project_data["name"] = project["name"]
    #     project_data["components_path"] = os.path.join(workspace_dir, project["project_folder"], project["components_folder"])
    #     project_data["supporting_files_path"] = os.path.join(workspace_dir, project["project_folder"], project["supporting_files_folder"])
    #     project_data["results_path"] = os.path.join(workspace_dir, project["project_folder"], project["results_folder"])
    #     project_data["build_path"] = os.path.join(workspace_dir, project["project_folder"], project["build_folder"])

    #     components_path = Path(project_data["components_path"])
    #     components = []
    #     for file_path in components_path.rglob("*"):
    #         if file_path.is_file():
    #             component_full_name = file_path.relative_to(components_path).as_posix()
    #             components.append(component_full_name)
    #     short_name_dict = assign_short_names(components)
    #     project_data["components_short"] = short_name_dict
        
    #     workspace_data["projects"][project_short_name] = project_data


    # return workspace_data

# def setup_action_prompt_templates(action_prompts_path):
#     action_prompt_templates = {}
#     for file_path in glob.glob(os.path.join(action_prompts_path, "*.yaml")):
#         with open(file_path, 'r') as file:
#             action_prompt_yaml_data = yaml.safe_load(file)
#             action_prompt_templates[action_prompt_yaml_data["agent_command_name"]] = action_prompt_yaml_data
#     return action_prompt_templates

# def workspace_info(workspace_data, action_prompt_templates):
#     print("Actions: ", ", ".join(action_prompt_templates.keys()))
#     print("Projects: ", ", ".join(workspace_data["projects"].keys()))
#     example_project = ""
#     example_component = ""
#     for project in workspace_data["projects"]:
#         short_component_names = list(workspace_data["projects"][project]["components_short"].keys())
#         if example_project == "":
#             example_project = project
#             example_component = short_component_names[0]
#         print(f"Components for {project}: ", end="")
#         print(", ".join(short_component_names) if len(short_component_names) > 0 else "NONE")

#     example_action = list(action_prompt_templates.keys())[0]
    
#     print(f"Example usage:\n\tshalev agent {example_action} {example_project} {example_component}")

