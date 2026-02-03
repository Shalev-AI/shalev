import click
import logging
import os
import shutil
from datetime import datetime
import json
import sys
import subprocess
import yaml

#################
# logging setup #
#################
# global list to store logs

class JSONFileHandler(logging.Handler):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def emit(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        with open(self.path, "a") as f:
            json_record = {
                "timestamp": timestamp,
                "level": record.levelname,
                "message": record.getMessage(),
            }
            f.write(json.dumps(json_record) + "\n")

def setup_logging(log_file="shalev_log.jsonl", show_log=False):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    if show_log:
        stream = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
        stream.setFormatter(formatter)
        logger.addHandler(stream)

    file_handler = JSONFileHandler(log_file)
    logger.addHandler(file_handler)


from shalev.agent_actions import *
from shalev.compose_actions import *
from shalev.split_actions import split_component
from shalev.shalev_eachrun_setup import *
from shalev.shalev_config import get_aliases, save_alias, get_default_project, save_default_project, config as config_func

# workspace_data is lazily loaded by commands that need it
# action_prompt_templates = setup_action_prompt_templates(workspace_data["action_prompts_path"])

@click.group()
def cli():
    """Shalev - AI-powered document composition tool.

    Manage projects, compose documents from components, and run LLM agent actions.
    """
    pass


def enable_verbose_logging():
    """Add a stream handler to show log messages on stdout."""
    logger = logging.getLogger()
    stream = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
    stream.setFormatter(formatter)
    logger.addHandler(stream)


def resolve_project(workspace_data, project):
    """Resolve and validate the project argument.

    If project is provided, validate it exists. If omitted, auto-select when
    there's exactly one project, or list available projects and exit otherwise.
    """
    available = list(workspace_data.projects.keys())

    if project is not None:
        if project not in workspace_data.projects:
            click.echo(f"Error: project '{project}' not found. Available projects: {', '.join(available)}")
            sys.exit(1)
        return project

    if len(available) == 1:
        project = available[0]
        click.echo(f"Single project in workspace, using: {project}")
        return project

    default = get_default_project()
    if default is not None:
        if default not in workspace_data.projects:
            click.echo(f"Error: default project '{default}' not found in workspace. Available projects: {', '.join(available)}")
            sys.exit(1)
        click.echo(f"Using default project: {default}")
        return default

    click.echo(f"Multiple projects in workspace. Please specify one: {', '.join(available)}")
    sys.exit(1)


##################
# shalev compose #
##################
@click.command()
@click.argument('project', required=False, default=None)
@click.option('--show-log', is_flag=True, help="Show full LaTeX compilation log")
@click.option('--show-shalev-log', is_flag=True, help="Show shalev internal log messages")
def compose(project, show_log, show_shalev_log):
    """Compose components into a document and compile with LaTeX.

    Recursively resolves !!!>include() directives starting from the root
    component, assembles a single LaTeX source file, and compiles it with
    pdflatex.

    PROJECT is the project handle as defined in workspace_config.yaml. If
    omitted, auto-selects when there is a single project or uses the default
    project.
    """
    if show_shalev_log:
        enable_verbose_logging()
    workspace_data = setup_workspace()
    project = resolve_project(workspace_data, project)
    logging.info(f"Running compose on project: {project}")
    if compose_action(workspace_data.projects[project], show_log=show_log):
        print(f"To view the output, run: shalev view {project}")

################
# shalev agent #
################
@click.command()
@click.argument('action', required=False, default=None)
@click.argument('projcomps', nargs=-1)
@click.option('--all', 'all_ext', default=None, help="Run action on all files with given extension (e.g., .jl) in the folder")
@click.option('--list', '-l', 'list_actions', is_flag=True, help="List all available actions")
@click.option('--show-shalev-log', is_flag=True, help="Show shalev internal log messages")
def agent(action, projcomps, all_ext, list_actions, show_shalev_log):
    """Run an LLM agent action on one or two components.

    ACTION is the name of an agent action defined in the workspace's
    action_prompts folder (use --list to see available actions).

    PROJCOMPS are one or two component references in project~component
    format. If a default project is set, you can omit the project prefix
    and just write the component name.

    \b
    Examples:
      shalev agent general_proofread myproject~root
      shalev agent transform myproject~source myproject~dest
      shalev agent action myproject~folder --all .jl
    """
    if show_shalev_log:
        enable_verbose_logging()
    workspace_data = setup_workspace()

    if list_actions:
        from shalev.agent_actions.agent import load_agent_configs_from_folder
        agent_configs = load_agent_configs_from_folder(workspace_data.action_prompts_folder)
        if not agent_configs:
            click.echo("No actions found.")
            return
        click.echo(f"Available actions ({len(agent_configs)}):\n")
        for name, prompt in agent_configs.items():
            click.echo(f"  {name}")
            system_content = prompt.system_prompt.get("content", "").strip()
            if system_content:
                for line in system_content.splitlines():
                    click.echo(f"    {line}")
            click.echo()
        return

    if action is None:
        raise click.UsageError("Missing argument 'ACTION'. Use --list to see available actions.")

    # Resolve aliases
    aliases = get_aliases()
    resolved_projcomps = []
    for pc in projcomps:
        if pc in aliases:
            resolved = aliases[pc]
            click.echo(f"Using alias '{pc}' -> '{resolved}'")
            resolved_projcomps.append(resolved)
        else:
            resolved_projcomps.append(pc)
    projcomps = tuple(resolved_projcomps)

    # Resolve bare components (no ~) using default project
    fully_resolved = []
    for pc in projcomps:
        if '~' not in pc:
            default_proj = resolve_project(workspace_data, None)
            fully_resolved.append(f"{default_proj}~{pc}")
        else:
            if pc.count('~') != 1:
                raise click.UsageError(f"'{pc}' has too many '~'. Format should be project~component")
            fully_resolved.append(pc)
    projcomps = tuple(fully_resolved)

    logging.info(f"Agent action '{action}' on: {projcomps}")

    # Handle --all mode: find all files with extension in folder
    if all_ext is not None:
        if len(projcomps) != 1:
            raise click.UsageError("--all mode requires exactly one project~folder argument")

        project, folder = projcomps[0].split('~', 1)
        if project not in workspace_data.projects:
            raise click.UsageError(f"Project '{project}' not found")

        folder_path = os.path.join(workspace_data.projects[project].components_folder, folder)
        if not os.path.isdir(folder_path):
            raise click.UsageError(f"Folder not found: {folder_path}")

        # Find all files with the given extension
        ext = all_ext if all_ext.startswith('.') else '.' + all_ext
        matching_files = [f for f in os.listdir(folder_path)
                         if f.endswith(ext) and os.path.isfile(os.path.join(folder_path, f))]

        if not matching_files:
            click.echo(f"No files with extension '{ext}' found in {folder_path}")
            return

        click.echo(f"Found {len(matching_files)} file(s) with extension '{ext}':")
        for f in matching_files:
            click.echo(f"  - {f}")
        click.echo()

        for i, filename in enumerate(matching_files, 1):
            component = os.path.join(folder, filename)
            click.echo(f"[{i}/{len(matching_files)}] Processing: {component}")
            agent_action_single_component(workspace_data, action, project, component)
            click.echo()

        click.echo(f"Completed processing {len(matching_files)} file(s).")
        return

    if len(projcomps) == 0:
        raise click.UsageError(f"Need at least one project~component pair")
    elif len(projcomps) == 1:
        project, component = projcomps[0].split('~', 1)
        agent_action_single_component(workspace_data, action, project, component)
    elif len(projcomps) == 2:
        source_project, source_component = projcomps[0].split('~', 1)
        dest_project, dest_component = projcomps[1].split('~', 1)
        agent_action_source_and_dest_components(workspace_data, action, source_project, source_component, dest_project, dest_component)

        # print(f"{source_project=}, {source_component=}, {dest_project=}, {dest_component=}")
    else:
        raise click.UsageError("Currently supporting only 1 or 2 project~component pairs")

#################
# shalev config #
#################
@click.command()
@click.option('-w', '--workspace', help="Set workspace folder path")
def config(workspace):
    """View or set workspace configuration.

    Without options, displays the current workspace path. Use -w to set
    the workspace folder path.
    """
    config_func(workspace)

#################
# shalev status #
#################
@click.command()
@click.option('--show-shalev-log', is_flag=True, help="Show shalev internal log messages")
def status(show_shalev_log):
    """Display workspace status.

    Shows the workspace name, description, action prompts folder, and
    details of each project including folder paths.
    """
    if show_shalev_log:
        enable_verbose_logging()
    workspace_data = setup_workspace()
    logging.info("Displaying status")

    click.echo(f"Workspace: {workspace_data.name}")
    if workspace_data.description:
        click.echo(f"  {workspace_data.description.strip()}")
    click.echo(f"Action prompts: {workspace_data.action_prompts_folder}")
    if workspace_data.workspace_system_prompts:
        click.echo(f"System prompts: {workspace_data.workspace_system_prompts}")
    click.echo("")
    click.echo(f"Projects ({len(workspace_data.projects)}):")
    for handle, proj in workspace_data.projects.items():
        click.echo(f"  [{handle}] {proj.name}")
        if proj.description:
            click.echo(f"    {proj.description.strip()}")
        click.echo(f"    project_folder:        {proj.project_folder}")
        click.echo(f"    components_folder:      {proj.components_folder}")
        click.echo(f"    root_component:         {proj.root_component}")
        click.echo(f"    supporting_files_folder: {proj.supporting_files_folder}")
        click.echo(f"    results_folder:         {proj.results_folder}")
        click.echo(f"    build_folder:           {proj.build_folder}")

################
# shalev alias #
################
@click.command()
@click.argument('short_name', required=False)
@click.argument('full_component', required=False)
@click.option('--list', '-l', 'list_aliases', is_flag=True, help="List all aliases")
def alias(short_name, full_component, list_aliases):
    """Create or list component aliases.

    Aliases let you refer to frequently used project~component pairs
    by a short name in agent and split commands.

    \b
    Examples:
      shalev alias ch1 myproject~chapter1.tex
      shalev alias --list
    """
    if list_aliases:
        aliases = get_aliases()
        if not aliases:
            click.echo("No aliases configured.")
        else:
            click.echo("Configured aliases:")
            for name, component in aliases.items():
                click.echo(f"  {name} -> {component}")
        return

    if short_name is None or full_component is None:
        raise click.UsageError("Both short_name and full_component are required. Use --list to see aliases.")

    if '~' not in full_component:
        raise click.UsageError(f"full_component must contain '~' (format: project~component)")

    save_alias(short_name, full_component)
    click.echo(f"Alias saved: {short_name} -> {full_component}")
    # if long:
    #     pprint(workspace_data)
    #     pprint(action_prompt_templates)
    # else:
    #     workspace_status(workspace_data, action_prompt_templates)


##########################
# shalev default-project #
##########################
@click.command('default-project')
@click.argument('project', required=False, default=None)
@click.option('--show-shalev-log', is_flag=True, help="Show shalev internal log messages")
def default_project(project, show_shalev_log):
    """View or set the default project.

    When set, the default project is used by commands that accept a
    PROJECT argument when none is provided, and allows omitting the
    project~ prefix in component references.

    \b
    Examples:
      shalev default-project              Show current default
      shalev default-project myproject    Set default to myproject
    """
    if project is None:
        default = get_default_project()
        if default is None:
            click.echo("No default project set.")
        else:
            click.echo(f"Default project: {default}")
        return

    if show_shalev_log:
        enable_verbose_logging()
    workspace_data = setup_workspace()
    available = list(workspace_data.projects.keys())
    if project not in workspace_data.projects:
        click.echo(f"Error: project '{project}' not found. Available projects: {', '.join(available)}")
        sys.exit(1)

    save_default_project(project)
    click.echo(f"Default project set to: {project}")

###############
# shalev view #
###############
@click.command()
@click.argument('project', required=False, default=None)
@click.option('--show-shalev-log', is_flag=True, help="Show shalev internal log messages")
def view(project, show_shalev_log):
    """Open the composed PDF for a project.

    Opens the compiled PDF from the build folder using the system default
    PDF viewer. Run 'shalev compose' first to generate the PDF.

    PROJECT is optional; auto-selects when there is a single project or
    uses the default project.
    """
    if show_shalev_log:
        enable_verbose_logging()
    workspace_data = setup_workspace()
    project = resolve_project(workspace_data, project)
    pdf_path = os.path.join(workspace_data.projects[project].build_folder, 'composed_project.pdf')
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} does not exist. Run 'shalev compose {project}' first.")
        sys.exit(1)
    subprocess.run(['open', pdf_path])

###############
# shalev tree #
###############
def build_tree(file_path, components_folder, processed_files=None):
    """Parse include statements and return list of (name, subtree) tuples."""
    if processed_files is None:
        processed_files = set()
    if file_path in processed_files:
        return []
    processed_files.add(file_path)

    children = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith('!!!>include(') and line.rstrip().endswith(')'):
                    included = line[len('!!!>include('):line.rstrip().rindex(')')].strip()
                    included_path = os.path.join(components_folder, included)
                    subtree = build_tree(included_path, components_folder, processed_files)
                    children.append((included, subtree))
    except FileNotFoundError:
        pass
    processed_files.discard(file_path)
    return children


def print_tree(name, children, prefix="", is_last=True):
    connector = "└── " if is_last else "├── "
    if prefix == "":
        click.echo(name)
    else:
        click.echo(prefix + connector + name)

    child_prefix = prefix + ("    " if is_last else "│   ")
    for i, (child_name, subtree) in enumerate(children):
        print_tree(child_name, subtree, child_prefix, i == len(children) - 1)


@click.command()
@click.argument('project', required=False, default=None)
@click.option('--show-shalev-log', is_flag=True, help="Show shalev internal log messages")
def tree(project, show_shalev_log):
    """Display the component include tree for a project.

    Recursively follows !!!>include() directives from the root component
    and prints the tree structure.

    PROJECT is optional; auto-selects when there is a single project or
    uses the default project.
    """
    if show_shalev_log:
        enable_verbose_logging()
    workspace_data = setup_workspace()
    project = resolve_project(workspace_data, project)
    proj = workspace_data.projects[project]
    root_path = proj.root_component
    root_name = os.path.basename(root_path)
    children = build_tree(root_path, proj.components_folder)
    print_tree(root_name, children)


################
# shalev setup #
################
@click.command()
@click.option('--project', '-p', 'projects', multiple=True, help="Project handle (repeatable)")
@click.argument('directory', default='.')
def setup(projects, directory):
    """Set up a new Shalev workspace with one or more projects.

    Creates workspace_config.yaml, action_prompts folder, and project
    directories with components, supporting_files, results, and build
    subfolders.

    DIRECTORY defaults to the current directory.

    \b
    Example:
      shalev setup -p mybook -p mybook2 ./my_workspace
    """
    if not projects:
        click.echo("Error: at least one --project/-p is required.")
        click.echo("Usage: shalev setup --project <handle> [--project <handle2> ...] [<directory>]")
        sys.exit(1)

    directory = os.path.abspath(directory)
    config_path = os.path.join(directory, 'workspace_config.yaml')

    if os.path.exists(config_path):
        click.echo(f"Error: {config_path} already exists. Aborting.")
        sys.exit(1)

    workspace_name = os.path.basename(directory)

    project_entries = []
    for handle in projects:
        project_entries.append({
            'name': handle.capitalize(),
            'project_handle': handle,
            'description': '',
            'project_folder': f'{handle}_project',
            'components_folder': 'components',
            'root_component': 'root.tex',
            'supporting_files_folder': 'supporting_files',
            'results_folder': 'results',
            'build_folder': 'build',
        })

    config_data = {
        'workspace': {
            'name': workspace_name,
            'description': '',
            'action_prompts_folder': './action_prompts',
            'projects': project_entries,
            'workspace_system_prompts': {},
        }
    }

    os.makedirs(directory, exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    click.echo(f"Created {config_path}")

    # Create action_prompts folder
    action_prompts_dir = os.path.join(directory, 'action_prompts')
    os.makedirs(action_prompts_dir, exist_ok=True)
    click.echo(f"Created {action_prompts_dir}")

    # Create project directories and root.tex
    build_folders = []
    for entry in project_entries:
        handle = entry['project_handle']
        project_dir = os.path.join(directory, entry['project_folder'])
        for subfolder in ['components', 'supporting_files', 'results', 'build']:
            path = os.path.join(project_dir, subfolder)
            os.makedirs(path, exist_ok=True)
            click.echo(f"Created {path}")
        # Create empty root.tex
        root_tex = os.path.join(project_dir, 'components', 'root.tex')
        if not os.path.exists(root_tex):
            open(root_tex, 'w').close()
            click.echo(f"Created {root_tex}")
        build_folders.append(f"{entry['project_folder']}/build")

    # Check .gitignore for build folders
    gitignore_path = os.path.join(directory, '.gitignore')
    missing_entries = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
        for bf in build_folders:
            if bf not in gitignore_content:
                missing_entries.append(bf)
    else:
        missing_entries = build_folders

    if missing_entries:
        click.echo("")
        click.echo("Warning: The following build folders are not in .gitignore:")
        for bf in missing_entries:
            click.echo(f"  {bf}")
        if click.confirm("Add them to .gitignore?"):
            with open(gitignore_path, 'a') as f:
                for bf in missing_entries:
                    f.write(bf + "\n")
            click.echo("Updated .gitignore.")

    click.echo("")
    click.echo(f"Workspace '{workspace_name}' set up with {len(projects)} project(s): {', '.join(projects)}")


################
# shalev flush #
################
@click.command()
@click.argument('project', required=False, default=None)
@click.option('--show-shalev-log', is_flag=True, help="Show shalev internal log messages")
def flush(project, show_shalev_log):
    """Delete all files in the build folder for a project.

    Lists files before deleting and prompts for confirmation. Warns if
    any files in the build folder are tracked by git.

    PROJECT is optional; auto-selects when there is a single project or
    uses the default project.
    """
    if show_shalev_log:
        enable_verbose_logging()
    workspace_data = setup_workspace()
    project = resolve_project(workspace_data, project)
    build_folder = workspace_data.projects[project].build_folder

    if not os.path.isdir(build_folder) or not os.listdir(build_folder):
        click.echo("Build folder is already empty.")
        return

    # List files that will be deleted
    click.echo(f"Files in {build_folder}:")
    for entry in sorted(os.listdir(build_folder)):
        click.echo(f"  {entry}")

    # Check for git-tracked files
    try:
        result = subprocess.run(
            ['git', 'ls-files', build_folder],
            capture_output=True, text=True
        )
        tracked = result.stdout.strip()
        if tracked:
            click.echo("")
            click.echo("Warning: Some files in the build folder are tracked by git:")
            for f in tracked.splitlines():
                click.echo(f"  {f}")
            click.echo(f"\nTo untrack them, run:\n  git rm -r --cached {build_folder}")
            click.echo("")
    except FileNotFoundError:
        pass  # git not available

    if not click.confirm(f"Delete all files in {build_folder}?"):
        click.echo("Aborted.")
        return

    shutil.rmtree(build_folder)
    os.makedirs(build_folder)
    click.echo(f"Build folder flushed: {build_folder}")


################
# shalev split #
################
@click.command()
@click.argument('component')
@click.option('--split-type', required=True, help="LaTeX command to split on, e.g. \\\\section")
@click.option('--target', default=None, help="Subdirectory for sub-component files (relative to components folder)")
@click.option('--numbered', is_flag=False, flag_value='', default=None, help="Prefix filenames with a number. Optionally pass a parent prefix, e.g. --numbered c2")
@click.option('--show-shalev-log', is_flag=True, help="Show shalev internal log messages")
def split(component, split_type, target, numbered, show_shalev_log):
    """Split a component at LaTeX commands into sub-components.

    COMPONENT is a component reference in project~component format, or
    just a component name if a default project is set. Aliases are resolved.

    The split-type line (e.g. \\section{Title}) stays in the parent component.
    The body below each split point is extracted into a new sub-component file,
    and an !!!>include() directive is inserted in the parent.

    \b
    Examples:
      shalev split chapter.tex --split-type \\\\section
      shalev split myproj~chapter.tex --split-type \\\\subsection --target sections
      shalev split chapter.tex --split-type \\\\section --numbered c2
    """
    if show_shalev_log:
        enable_verbose_logging()
    workspace_data = setup_workspace()

    # Resolve aliases
    aliases = get_aliases()
    if component in aliases:
        resolved = aliases[component]
        click.echo(f"Using alias '{component}' -> '{resolved}'")
        component = resolved

    # Resolve bare component (no ~) using default project
    if '~' not in component:
        project = resolve_project(workspace_data, None)
        projcomp = f"{project}~{component}"
    else:
        projcomp = component

    project, comp = projcomp.split('~', 1)
    if project not in workspace_data.projects:
        click.echo(f"Error: project '{project}' not found.")
        sys.exit(1)

    component_path = os.path.join(workspace_data.projects[project].components_folder, comp)
    if not os.path.isfile(component_path):
        click.echo(f"Error: component file not found: {component_path}")
        sys.exit(1)

    logging.info(f"Splitting '{comp}' on '{split_type}'")
    split_component(component_path, split_type, target=target, numbered=numbered,
                    components_folder=workspace_data.projects[project].components_folder)
    click.echo("Done.")


###########################
# putting it all together #
###########################
cli.add_command(compose)
cli.add_command(agent)
cli.add_command(status)
cli.add_command(config)
cli.add_command(alias)
cli.add_command(default_project)
cli.add_command(view)
cli.add_command(tree)
cli.add_command(setup)
cli.add_command(split)
cli.add_command(flush)

def main():
    setup_logging()
    logging.info("Shalev CLI started")
    cli()

if __name__ == '__main__':
    main()