"""Tests for CLI commands."""
import os
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from shalev.cli import cli, build_tree, print_tree


class TestCliBasic:
    """Basic CLI tests."""

    def test_cli_help(self):
        """Test that CLI help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Shalev' in result.output

    def test_agent_help(self):
        """Test that agent help works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['agent', '--help'])
        assert result.exit_code == 0
        assert '--inputs' in result.output
        assert '--targets' in result.output


class TestAgentCommand:
    """Tests for the agent command."""

    def test_agent_missing_action(self):
        """Test that agent without action shows error."""
        runner = CliRunner()
        with patch('shalev.cli.setup_workspace'):
            result = runner.invoke(cli, ['agent'])
        assert result.exit_code != 0
        assert 'ACTION' in result.output

    def test_agent_list_actions(self, test_workspace_path):
        """Test listing available actions."""
        runner = CliRunner()
        # Create a .shalev.yaml pointing to test workspace
        shalev_config = f"workspace_folder: {test_workspace_path}\n"
        with runner.isolated_filesystem():
            with open('.shalev.yaml', 'w') as f:
                f.write(shalev_config)
            result = runner.invoke(cli, ['agent', '--list'])
            assert result.exit_code == 0
            # Check actions are listed
            assert 'echo' in result.output
            assert 'stm' in result.output
            assert 'ltb' in result.output
            assert 'expand' in result.output
            # Check categories are shown
            assert '[global]' in result.output
            assert '[project]' in result.output
            assert '[component]' in result.output

    def test_agent_mixed_mode_error(self, test_workspace_path):
        """Test that mixing positional and flag modes fails."""
        runner = CliRunner()
        shalev_config = f"workspace_folder: {test_workspace_path}\n"
        with runner.isolated_filesystem():
            with open('.shalev.yaml', 'w') as f:
                f.write(shalev_config)
            result = runner.invoke(cli, [
                'agent', 'echo', 'testproj~root.tex',
                '--inputs', 'ch1.tex'
            ])
            assert result.exit_code != 0
            assert 'Cannot mix' in result.output

    def test_agent_flag_mode_missing_inputs(self, test_workspace_path):
        """Test that flag mode without inputs fails."""
        runner = CliRunner()
        shalev_config = f"workspace_folder: {test_workspace_path}\n"
        with runner.isolated_filesystem():
            with open('.shalev.yaml', 'w') as f:
                f.write(shalev_config)
            result = runner.invoke(cli, [
                'agent', 'stm', '--target', 'draft.tex'
            ])
            assert result.exit_code != 0
            assert 'input' in result.output.lower()

    def test_agent_flag_mode_missing_targets(self, test_workspace_path):
        """Test that flag mode without targets fails."""
        runner = CliRunner()
        shalev_config = f"workspace_folder: {test_workspace_path}\n"
        with runner.isolated_filesystem():
            with open('.shalev.yaml', 'w') as f:
                f.write(shalev_config)
            result = runner.invoke(cli, [
                'agent', 'stm', '--inputs', 'example_style.tex'
            ])
            assert result.exit_code != 0
            assert 'target' in result.output.lower()


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_shows_workspace(self, test_workspace_path):
        """Test that status shows workspace info."""
        runner = CliRunner()
        shalev_config = f"workspace_folder: {test_workspace_path}\n"
        with runner.isolated_filesystem():
            with open('.shalev.yaml', 'w') as f:
                f.write(shalev_config)
            result = runner.invoke(cli, ['status'])
            assert result.exit_code == 0
            assert 'Test Workspace' in result.output
            assert 'testproj' in result.output


class TestTreeCommand:
    """Tests for the tree command."""

    def test_tree_shows_hierarchy(self, test_workspace_path):
        """Test that tree shows component hierarchy."""
        runner = CliRunner()
        shalev_config = f"workspace_folder: {test_workspace_path}\n"
        with runner.isolated_filesystem():
            with open('.shalev.yaml', 'w') as f:
                f.write(shalev_config)
            result = runner.invoke(cli, ['tree'])
            assert result.exit_code == 0
            assert 'root.tex' in result.output
            assert 'ch1.tex' in result.output
            assert 'ch2.tex' in result.output


class TestConfigCommand:
    """Tests for the config command."""

    def test_config_init_actions(self, test_workspace_path, tmp_path):
        """Test that --init-actions creates folders and default actions."""
        import shutil

        # Create a temporary copy of the test workspace
        temp_workspace = tmp_path / "test_workspace"
        shutil.copytree(test_workspace_path, temp_workspace)

        # Remove existing default actions to test creation
        global_dir = temp_workspace / "action_prompts" / "global"
        for f in ['fix_grammar.yaml', 'remove_whitespace.yaml', 'style_transfer.yaml', 'style_transfer_multi.yaml']:
            (global_dir / f).unlink(missing_ok=True)

        runner = CliRunner()
        shalev_config = f"workspace_folder: {temp_workspace}\n"
        with runner.isolated_filesystem():
            with open('.shalev.yaml', 'w') as f:
                f.write(shalev_config)
            result = runner.invoke(cli, ['config', '--init-actions'])
            assert result.exit_code == 0
            assert 'fix_grammar.yaml' in result.output
            assert 'style_transfer.yaml' in result.output

        # Verify files were created
        assert (global_dir / 'fix_grammar.yaml').exists()
        assert (global_dir / 'style_transfer.yaml').exists()
