"""Tests for component tree building."""
import os
import pytest
from shalev.cli import build_tree


class TestBuildTree:
    """Tests for the build_tree function."""

    def test_root_has_two_children(self, test_project):
        """Test that root includes ch1.tex and ch2.tex."""
        children = build_tree(test_project.root_component, test_project.components_folder)
        child_names = [name for name, _ in children]
        assert len(children) == 2
        assert 'ch1.tex' in child_names
        assert 'ch2.tex' in child_names

    def test_ch1_has_two_children(self, test_project):
        """Test that ch1 includes sec1_1.tex and sec1_2.tex."""
        ch1_path = os.path.join(test_project.components_folder, 'ch1.tex')
        children = build_tree(ch1_path, test_project.components_folder)
        child_names = [name for name, _ in children]
        assert len(children) == 2
        assert 'sec1_1.tex' in child_names
        assert 'sec1_2.tex' in child_names

    def test_ch2_has_one_child(self, test_project):
        """Test that ch2 includes sec2_1.tex."""
        ch2_path = os.path.join(test_project.components_folder, 'ch2.tex')
        children = build_tree(ch2_path, test_project.components_folder)
        child_names = [name for name, _ in children]
        assert len(children) == 1
        assert 'sec2_1.tex' in child_names

    def test_sec1_2_has_subsection(self, test_project):
        """Test that sec1_2 includes subsec1_2_1.tex."""
        sec_path = os.path.join(test_project.components_folder, 'sec1_2.tex')
        children = build_tree(sec_path, test_project.components_folder)
        child_names = [name for name, _ in children]
        assert len(children) == 1
        assert 'subsec1_2_1.tex' in child_names

    def test_leaf_has_no_children(self, test_project):
        """Test that leaf components have no children."""
        leaf_path = os.path.join(test_project.components_folder, 'sec1_1.tex')
        children = build_tree(leaf_path, test_project.components_folder)
        assert len(children) == 0

    def test_standalone_has_no_children(self, test_project):
        """Test that standalone.tex has no children."""
        standalone_path = os.path.join(test_project.components_folder, 'standalone.tex')
        children = build_tree(standalone_path, test_project.components_folder)
        assert len(children) == 0

    def test_tree_depth(self, test_project):
        """Test that the tree has depth 3 (root -> ch1 -> sec1_2 -> subsec)."""
        def get_max_depth(children, current_depth=1):
            if not children:
                return current_depth
            max_child_depth = current_depth
            for _, subtree in children:
                child_depth = get_max_depth(subtree, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
            return max_child_depth

        children = build_tree(test_project.root_component, test_project.components_folder)
        depth = get_max_depth(children)
        assert depth == 4  # root(1) -> ch1(2) -> sec1_2(3) -> subsec(4)

    def test_total_nodes_in_tree(self, test_project):
        """Test total number of nodes reachable from root."""
        def count_nodes(children):
            count = len(children)
            for _, subtree in children:
                count += count_nodes(subtree)
            return count

        children = build_tree(test_project.root_component, test_project.components_folder)
        # ch1, ch2, sec1_1, sec1_2, sec2_1, subsec1_2_1 = 6 nodes
        assert count_nodes(children) == 6
