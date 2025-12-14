import click
import logging
from pprint import pprint
from datetime import datetime
import json
import sys

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

# workspace_data is lazily loaded by commands that need it
# action_prompt_templates = setup_action_prompt_templates(workspace_data["action_prompts_path"])

@click.group()
def cli():
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

################
# shalev agent #
################
@click.command()
@click.argument('action')
@click.argument('projcomps', nargs=-1)
def agent(action, projcomps):
    workspace_data = setup_workspace()
    logging.info(f"Agent action '{action}' on: {projcomps}")

    for projcomp in projcomps:
        if projcomp.count('~') != 1:
            raise click.UsageError(f"'{projcomp}' is missing '~'. Format should be project~component")
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
    from shalev.shalev_config import config as config_func
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
    # if long:
    #     pprint(workspace_data)
    #     pprint(action_prompt_templates)
    # else:
    #     workspace_status(workspace_data, action_prompt_templates)


###########################
# putting it all together #
###########################
cli.add_command(compose)
cli.add_command(agent)
cli.add_command(status)
cli.add_command(config)

def main():
    setup_logging()
    logging.info("Shalev CLI started")
    cli()

if __name__ == '__main__':
    main()