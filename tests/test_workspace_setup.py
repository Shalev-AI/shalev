"""Tests for workspace setup and loading."""
import os
import pytest


class TestWorkspaceLoading:
    """Tests for loading workspace configuration."""

    def test_workspace_loads(self, test_workspace_data):
        """Test that the workspace loads without errors."""
        assert test_workspace_data is not None
        assert test_workspace_data.name == "Test Workspace"

    def test_workspace_has_project(self, test_workspace_data):
        """Test that the workspace contains the test project."""
        assert 'testproj' in test_workspace_data.projects
        assert len(test_workspace_data.projects) == 1

    def test_workspace_action_prompts_folder(self, test_workspace_data, test_workspace_path):
        """Test that action prompts folder is correctly set."""
        expected = os.path.join(test_workspace_path, 'action_prompts')
        # Normalize paths for comparison (handles ./action_prompts vs action_prompts)
        assert os.path.normpath(test_workspace_data.action_prompts_folder) == os.path.normpath(expected)
        assert os.path.isdir(test_workspace_data.action_prompts_folder)


class TestProjectLoading:
    """Tests for project configuration."""

    def test_project_name(self, test_project):
        """Test project name is correct."""
        assert test_project.name == "Test Project"
        assert test_project.project_handle == "testproj"

    def test_project_folders_exist(self, test_project):
        """Test that all project folders exist."""
        assert os.path.isdir(test_project.project_folder)
        assert os.path.isdir(test_project.components_folder)
        assert os.path.isdir(test_project.supporting_files_folder)
        assert os.path.isdir(test_project.results_folder)
        assert os.path.isdir(test_project.build_folder)

    def test_root_component_exists(self, test_project):
        """Test that root component file exists."""
        assert os.path.isfile(test_project.root_component)

    def test_components_count(self, components_folder):
        """Test that we have 10 components."""
        components = [f for f in os.listdir(components_folder) if f.endswith('.tex')]
        assert len(components) == 10


class TestActionPrompts:
    """Tests for action prompt loading."""

    def test_action_prompts_exist(self, test_workspace_data):
        """Test that action prompt files exist."""
        folder = test_workspace_data.action_prompts_folder
        files = os.listdir(folder)
        assert 'echo.yaml' in files
        assert 'stm.yaml' in files

    def test_load_action_configs(self, test_workspace_data):
        """Test loading action configurations."""
        from shalev.agent_actions.agent import load_agent_configs_from_folder
        configs = load_agent_configs_from_folder(test_workspace_data.action_prompts_folder)
        assert 'echo' in configs
        assert 'stm' in configs
        assert configs['echo'].agent_command_name == 'echo'
        assert configs['stm'].agent_command_name == 'stm'
