import subprocess
import os
import re
from ..shalev_eachrun_setup import *


def build_file_index(components_folder):
    """Walk components_folder and build {filename: full_path} dict.

    Raises ValueError if two files share the same filename.
    """
    index = {}
    for dirpath, _dirnames, filenames in os.walk(components_folder):
        for fname in filenames:
            full_path = os.path.join(dirpath, fname)
            if fname in index:
                raise ValueError(
                    f"Duplicate component filename '{fname}' found in:\n"
                    f"  {index[fname]}\n"
                    f"  {full_path}"
                )
            index[fname] = full_path
    return index


def resolve_include(include_ref, components_folder, file_index=None):
    """Resolve an include reference to a full path.

    If include_ref contains '/', resolve relative to components_folder (backward compat).
    Otherwise, look up the bare filename in file_index.
    Falls back to os.path.join if file_index is None.
    """
    if '/' in include_ref:
        return os.path.join(components_folder, include_ref)
    if file_index is not None:
        if include_ref not in file_index:
            raise FileNotFoundError(
                f"Component '{include_ref}' not found in any subdirectory of components folder"
            )
        return file_index[include_ref]
    return os.path.join(components_folder, include_ref)


def extract_chapter_number(target_name, target_component):
    """Extract chapter number from target name (e.g. 'chap5' → 5) or component filename (e.g. '5_foo.tex' → 5)."""
    m = re.match(r'chap(\d+)', target_name)
    if m:
        return int(m.group(1))
    basename = os.path.basename(target_component)
    m = re.match(r'^(\d+)_', basename)
    if m:
        return int(m.group(1))
    return None


def extract_chapter_pages(build_folder):
    """Parse composed_project.aux to get chapter → start page mapping.

    Returns dict[int, int] mapping chapter number to its start page.
    Returns empty dict if aux file doesn't exist.
    """
    aux_path = os.path.join(build_folder, 'composed_project.aux')
    if not os.path.isfile(aux_path):
        return {}
    chapter_pages = {}
    pattern = re.compile(
        r'\\contentsline\s*\{chapter\}\{\\numberline\s*\{(\d+)\}.*?\}\{(\d+)\}'
    )
    with open(aux_path, 'r') as f:
        for line in f:
            m = pattern.search(line)
            if m:
                chapter_pages[int(m.group(1))] = int(m.group(2))
    return chapter_pages


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

            pdf_path = os.path.join('.', 'composed_project.pdf')
            pdf_produced = os.path.exists(pdf_path)

            if pdf_produced and result.returncode == 0:
                print("Compose successful.")
            elif pdf_produced:
                print("Compose successful (with warnings). Run with --show-log to see details.")
            else:
                print("Compose failed. Run with --show-log to see full output.")

            if show_log:
                print(result.stdout)

            return pdf_produced
        finally:
            os.chdir(previous_dir)
    except Exception as e:
        print(f"Error: {e}")
        return False


 
    
def process_file(file_path, components_folder, processed_files=None, file_index=None):
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

                # Resolve the include path (supports bare filenames via file_index)
                included_file_path = resolve_include(included_file, components_folder, file_index)

                # Recursively process the included file
                included_text = process_file(included_file_path, components_folder, processed_files, file_index)

                # Add the included text to the body
                complete_text.append(included_text)
            else:
                # Otherwise, just add the current line
                complete_text.append(line)

    # Remove from chain so the same file can be included from other branches
    processed_files.discard(file_path)

    return ''.join(complete_text)

def process_file_with_target(file_path, components_folder, target_content, processed_files=None, file_index=None, target_preamble=""):
    """Like process_file but also replaces !!!>include_target with target_content
    and !!!>target_preamble with target_preamble."""
    if processed_files is None:
        processed_files = set()

    if file_path in processed_files:
        raise ValueError(f"Circular include detected with file: {file_path}")

    processed_files.add(file_path)
    complete_text = []

    with open(file_path, 'r') as f:
        for line in f:
            stripped = line.rstrip()
            if stripped == '!!!>include_target':
                complete_text.append(target_content)
                if not target_content.endswith('\n'):
                    complete_text.append('\n')
            elif stripped == '!!!>target_preamble':
                if target_preamble:
                    complete_text.append(target_preamble)
                    if not target_preamble.endswith('\n'):
                        complete_text.append('\n')
            elif stripped.startswith('!!!>include(') and stripped.endswith(')'):
                included_file = stripped[len('!!!>include('):-1].strip()
                included_file_path = resolve_include(included_file, components_folder, file_index)
                included_text = process_file(included_file_path, components_folder, processed_files, file_index)
                complete_text.append(included_text)
            else:
                complete_text.append(line)

    processed_files.discard(file_path)
    return ''.join(complete_text)


def create_complete_text(root_file, components_folder):
    try:
        file_index = build_file_index(components_folder)
        complete_text = process_file(root_file, components_folder, file_index=file_index)
        return complete_text
    except Exception as e:
        print(f"Error: {e}")
        return None


def compose_target_action(shalev_project, target_name, show_log=False):
    """Compose a single target (e.g. a chapter) using the compose wrapper."""
    if not shalev_project.compose_targets:
        print("Error: No compose_targets defined for this project.")
        return (False, None)

    if target_name not in shalev_project.compose_targets:
        available = ', '.join(sorted(shalev_project.compose_targets.keys()))
        print(f"Error: Target '{target_name}' not found. Available targets: {available}")
        return (False, None)

    if not shalev_project.compose_wrapper:
        print("Error: No compose_wrapper defined for this project.")
        return (False, None)

    if not os.path.isfile(shalev_project.compose_wrapper):
        print(f"Error: Wrapper file not found: {shalev_project.compose_wrapper}")
        return (False, None)

    try:
        file_index = build_file_index(shalev_project.components_folder)
    except ValueError as e:
        print(f"Error: {e}")
        return (False, None)

    target_component = shalev_project.compose_targets[target_name]
    target_path = resolve_include(target_component, shalev_project.components_folder, file_index)

    if not os.path.isfile(target_path):
        print(f"Error: Target component not found: {target_path}")
        return (False, None)

    try:
        # Build target preamble for chapter/page numbering
        target_preamble = ""
        chapter_num = extract_chapter_number(target_name, target_component)
        if chapter_num is not None:
            preamble_lines = [f"\\setcounter{{chapter}}{{{chapter_num - 1}}}"]
            chapter_pages = extract_chapter_pages(shalev_project.build_folder)
            if chapter_num in chapter_pages:
                preamble_lines.append(f"\\setcounter{{page}}{{{chapter_pages[chapter_num]}}}")
            target_preamble = '\n'.join(preamble_lines) + '\n'

        # Resolve the target component content
        target_content = process_file(target_path, shalev_project.components_folder, file_index=file_index)

        # Process the wrapper, substituting !!!>include_target with target content
        complete_text = process_file_with_target(
            shalev_project.compose_wrapper,
            shalev_project.components_folder,
            target_content,
            file_index=file_index,
            target_preamble=target_preamble
        )

        tex_filename = f'composed_{target_name}.tex'
        pdf_filename = f'composed_{target_name}.pdf'
        composed_path = os.path.join(shalev_project.build_folder, tex_filename)

        with open(composed_path, 'w') as f:
            f.write(complete_text)

        try:
            previous_dir = os.getcwd()
            os.chdir(shalev_project.build_folder)
            result = subprocess.run(
                ['pdflatex',
                 '-interaction=nonstopmode',
                 '-output-directory=.',
                 tex_filename],
                capture_output=True,
                text=True
            )

            pdf_produced = os.path.exists(pdf_filename)

            if pdf_produced and result.returncode == 0:
                print("Compose successful.")
            elif pdf_produced:
                print("Compose successful (with warnings). Run with --show-log to see details.")
            else:
                print("Compose failed. Run with --show-log to see full output.")

            if show_log:
                print(result.stdout)

            return (pdf_produced, pdf_filename)
        finally:
            os.chdir(previous_dir)
    except Exception as e:
        print(f"Error: {e}")
        return (False, None)
