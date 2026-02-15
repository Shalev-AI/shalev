"""Pytest fixtures for shalev tests."""
import os
import pytest
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shalev.shalev_eachrun_setup import workspace_from_dict
import yaml


@pytest.fixture
def test_workspace_path():
    """Return the path to the test workspace fixture."""
    return os.path.join(os.path.dirname(__file__), 'fixtures', 'test_workspace')


@pytest.fixture
def test_workspace_data(test_workspace_path):
    """Load and return the test workspace data."""
    config_path = os.path.join(test_workspace_path, 'workspace_config.yaml')
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
    return workspace_from_dict(config_dict, test_workspace_path)


@pytest.fixture
def test_project(test_workspace_data):
    """Return the test project from the workspace."""
    return test_workspace_data.projects['testproj']


@pytest.fixture
def components_folder(test_project):
    """Return the path to the components folder."""
    return test_project.components_folder
