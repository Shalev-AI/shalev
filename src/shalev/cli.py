import click
import logging
import os
from pprint import pprint
from datetime import datetime
import json
import sys
import subprocess

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

def setup_logging(log_file="shalev_log.jsonl"):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    stream = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S")
    stream.setFormatter(formatter)

    file_handler = JSONFileHandler(log_file)
    print(file_handler.path)
    logger.handlers.clear()
    logger.addHandler(stream)
    logger.addHandler(file_handler)


from shalev.agent_actions import *
from shalev.compose_actions import *
from shalev.shalev_eachrun_setup import *
from shalev.shalev_config import get_aliases, save_alias, config as config_func

# workspace_data is lazily loaded by commands that need it
# action_prompt_templates = setup_action_prompt_templates(workspace_data["action_prompts_path"])

@click.group()
def cli():
    """Shalev - AI-powered document composition tool.

    Manage projects, compose documents from components, and run LLM agent actions.
    """
    pass


##################
# shalev compose #
##################
@click.command()
@click.argument('project')
# @click.option('--project', default=".", help="Project name or path (default: current directory)")
def compose(project):
    workspace_data = setup_workspace()
    logging.info(f"Running compose on project: {project}")
    compose_action(workspace_data.projects[project])
    print(f"To view the output, run: shalev view {project}")

################
# shalev agent #
################
@click.command()
@click.argument('action')
@click.argument('projcomps', nargs=-1)
@click.option('--all', 'all_ext', default=None, help="Run action on all files with given extension (e.g., .jl) in the folder")
def agent(action, projcomps, all_ext):
    workspace_data = setup_workspace()

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

    logging.info(f"Agent action '{action}' on: {projcomps}")

    for projcomp in projcomps:
        if projcomp.count('~') != 1:
            raise click.UsageError(f"'{projcomp}' is missing '~'. Format should be project~component")

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
    config_func(workspace)

#################
# shalev status #
#################
@click.command()
# @click.option('--long', is_flag=True, help="Show full status.")
def status():
    workspace_data = setup_workspace()
    print("QQQQQQQQQ")
    logging.info("Displaying status")

    pprint(workspace_data)

################
# shalev alias #
################
@click.command()
@click.argument('short_name', required=False)
@click.argument('full_component', required=False)
@click.option('--list', '-l', 'list_aliases', is_flag=True, help="List all aliases")
def alias(short_name, full_component, list_aliases):
    """Create or list component aliases.

    Usage:
      shalev alias <short_name> <full_component>  - Create an alias
      shalev alias --list                         - List all aliases
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


###############
# shalev view #
###############
@click.command()
@click.argument('project')
def view(project):
    workspace_data = setup_workspace()
    pdf_path = os.path.join(workspace_data.projects[project].build_folder, 'composed_project.pdf')
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} does not exist. Run 'shalev compose {project}' first.")
        sys.exit(1)
    subprocess.run(['open', pdf_path])

###########################
# putting it all together #
###########################
cli.add_command(compose)
cli.add_command(agent)
cli.add_command(status)
cli.add_command(config)
cli.add_command(alias)
cli.add_command(view)

def main():
    setup_logging()
    logging.info("Shalev CLI started")
    cli()

if __name__ == '__main__':
    main()