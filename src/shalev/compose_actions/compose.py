import subprocess
import os
from pprint import pprint
from ..shalev_eachrun_setup import *


def compose_action(shalev_project: ShalevProject, show_log=False):
    try:
        complete_text = create_complete_text(shalev_project.root_component, shalev_project.components_folder)
        if complete_text is None:
            return False
        composed_project_path = os.path.join(shalev_project.build_folder, 'composed_project.tex')
        with open(composed_project_path, 'w') as file:
            file.write(complete_text)
        try:
            previous_dir = os.getcwd()
            os.chdir(shalev_project.build_folder)
            result = subprocess.run(['pdflatex',
                                    '-interaction=nonstopmode',
                                    '-output-directory=.',
                                    'composed_project.tex'],
                                    capture_output=True,
                                    text=True)

            if result.returncode == 0:
                print("Compose successful.")
                if show_log:
                    print(result.stdout)
                return True
            else:
                print("Compose failed. Run with --show-log to see full output.")
                if show_log:
                    print(result.stdout)
                return False
        finally:
            os.chdir(previous_dir)
    except Exception as e:
        print(f"Error: {e}")
        return False


 
    
def process_file(file_path, components_folder, processed_files=None):
    # Initialize the set to track the current inclusion chain (to detect circular includes)
    if processed_files is None:
        processed_files = set()

    # Check if the file is already in the current inclusion chain
    if file_path in processed_files:
        raise ValueError(f"Circular include detected with file: {file_path}")

    # Add the current file to the chain
    processed_files.add(file_path)

    complete_text = []

    with open(file_path, 'r') as f:
        for line in f:
            # Check for the include statement
            stripped = line.rstrip()
            if stripped.startswith('!!!>include(') and stripped.endswith(')'):

                # Extract the file to be included
                included_file = stripped[len('!!!>include('):-1].strip()

                # Generate the full path relative to the components folder
                included_file_path = os.path.join(components_folder, included_file)

                # Recursively process the included file
                included_text = process_file(included_file_path, components_folder, processed_files)

                # Add the included text to the body
                complete_text.append(included_text)
            else:
                # Otherwise, just add the current line
                complete_text.append(line)

    # Remove from chain so the same file can be included from other branches
    processed_files.discard(file_path)

    return ''.join(complete_text)

def create_complete_text(root_file, components_folder):
    try:
        complete_text = process_file(root_file, components_folder)
        return complete_text
    except Exception as e:
        print(f"Error: {e}")
        return None
