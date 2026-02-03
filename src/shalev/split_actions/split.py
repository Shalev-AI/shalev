import os
import re
import logging


def slugify(title):
    """Convert a section title to a filename-safe slug.

    E.g. "Counting Techniques and Combinatorics" -> "counting_techniques_and_combinatorics"
    """
    slug = title.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug


def extract_title(line, split_type):
    """Extract the title from a LaTeX command line.

    E.g. for split_type='\\section' and line='\\section{My Title}\\label{foo}',
    returns 'My Title'.
    """
    # Match \command{...} and capture the first brace group
    pattern = re.escape(split_type) + r'\{([^}]*)\}'
    m = re.search(pattern, line)
    if m:
        return m.group(1)
    return None


def split_component(component_path, split_type, target=None, numbered=False):
    """Split a component file at LaTeX commands (e.g. \\section) into sub-components.

    The split-type command line (e.g. \\section{Title}) stays in the parent.
    Everything after it until the next split-type command becomes a sub-component,
    with an !!!>include() directive inserted in the parent.

    Args:
        component_path: Absolute path to the component file.
        split_type: The LaTeX command to split on, e.g. '\\section'.
        target: Optional subdirectory (relative to component's directory) for sub-components.
                If None, sub-components are placed alongside the parent.
        numbered: If set, prefix filenames with a number. Can be True for plain
                  numbering (1_, 2_) or a string prefix (e.g. 'c2' -> c2_1_, c2_2_).
    """
    # Ensure split_type starts with backslash (shell may strip it)
    if not split_type.startswith('\\'):
        split_type = '\\' + split_type

    with open(component_path, 'r') as f:
        content = f.read()

    lines = content.splitlines(keepends=True)

    # Detect the split command pattern (e.g. \section{)
    cmd_pattern = re.escape(split_type) + r'\{'

    # Find indices of lines that start with the split command
    split_indices = []
    for i, line in enumerate(lines):
        if re.match(r'\s*' + cmd_pattern, line):
            split_indices.append(i)

    if not split_indices:
        logging.info(f"No '{split_type}' commands found in {component_path}. Nothing to split.")
        return

    # Determine output directory
    component_dir = os.path.dirname(component_path)
    component_ext = os.path.splitext(component_path)[1] or '.tex'

    if target:
        output_dir = os.path.join(component_dir, target)
    else:
        output_dir = component_dir

    os.makedirs(output_dir, exist_ok=True)

    # Build segments: each segment is (split_line_index, title, body_lines)
    segments = []
    for idx, start in enumerate(split_indices):
        title = extract_title(lines[start], split_type)
        if title is None:
            title = f"untitled_{idx}"

        # Body is everything after the split line until the next split line (or EOF)
        body_start = start + 1
        if idx + 1 < len(split_indices):
            body_end = split_indices[idx + 1]
        else:
            body_end = len(lines)

        body_lines = lines[body_start:body_end]
        segments.append((start, title, body_lines))

    # Determine total segment count for zero-padding
    pad_width = len(str(len(segments)))

    # Create sub-component files and build the new parent content
    new_parent_lines = []
    segment_idx = 0
    line_idx = 0

    while line_idx < len(lines):
        if segment_idx < len(segments) and line_idx == segments[segment_idx][0]:
            start, title, body_lines = segments[segment_idx]

            # Generate filename
            slug = slugify(title)
            if numbered is not None:
                num = str(segment_idx + 1).zfill(pad_width)
                if isinstance(numbered, str) and numbered:
                    filename = f"{numbered}_{num}_{slug}{component_ext}"
                else:
                    filename = f"{num}_{slug}{component_ext}"
            else:
                filename = f"{slug}{component_ext}"

            # Write the sub-component file
            sub_path = os.path.join(output_dir, filename)
            with open(sub_path, 'w') as f:
                f.write(''.join(body_lines))
            logging.info(f"Created sub-component: {sub_path}")

            # In parent: keep the split line, add include directive
            new_parent_lines.append(lines[start])

            # Build include path relative to parent's directory
            if target:
                include_ref = os.path.join(target, filename)
            else:
                include_ref = filename

            new_parent_lines.append(f'!!!>include({include_ref})\n')

            # Skip body lines (they've been moved to the sub-component)
            line_idx = start + 1 + len(body_lines)
            segment_idx += 1
        else:
            new_parent_lines.append(lines[line_idx])
            line_idx += 1

    # Overwrite the parent component
    with open(component_path, 'w') as f:
        f.write(''.join(new_parent_lines))
    logging.info(f"Updated parent component: {component_path}")

    logging.info(f"Split '{os.path.basename(component_path)}' into {len(segments)} sub-component(s).")
