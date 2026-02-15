"""Tests for agent functions."""
import os
import pytest
from unittest.mock import patch, MagicMock

from shalev.agent_actions.agent import (
    make_LLM_messages_single_component,
    make_LLM_messages_source_and_dest_components,
    make_LLM_messages_multi_input_components,
    load_agent_configs_from_folder,
    SIZE_LIMIT,
)


class TestMessageBuilders:
    """Tests for LLM message building functions."""

    def test_single_component_message(self, test_workspace_data):
        """Test message building for single component."""
        configs = load_agent_configs_from_folder(test_workspace_data.action_prompts_folder)
        action_prompt = configs['echo']

        messages = make_LLM_messages_single_component(action_prompt, "Hello world")

        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert messages[1]['content'] == "Hello world"

    def test_source_and_dest_message(self, test_workspace_data):
        """Test message building for source and dest components."""
        configs = load_agent_configs_from_folder(test_workspace_data.action_prompts_folder)
        action_prompt = configs['echo']

        messages = make_LLM_messages_source_and_dest_components(
            action_prompt, "Source text", "Dest text"
        )

        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert '**INPUT**' in messages[1]['content']
        assert 'Source text' in messages[1]['content']
        assert '**TARGET**' in messages[1]['content']
        assert 'Dest text' in messages[1]['content']

    def test_multi_input_message_single_input(self, test_workspace_data):
        """Test message building with a single input."""
        configs = load_agent_configs_from_folder(test_workspace_data.action_prompts_folder)
        action_prompt = configs['stm']

        messages = make_LLM_messages_multi_input_components(
            action_prompt, ["Example 1"], "Target text"
        )

        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert '**INPUT 1**' in messages[1]['content']
        assert 'Example 1' in messages[1]['content']
        assert '**TARGET**' in messages[1]['content']
        assert 'Target text' in messages[1]['content']

    def test_multi_input_message_multiple_inputs(self, test_workspace_data):
        """Test message building with multiple inputs."""
        configs = load_agent_configs_from_folder(test_workspace_data.action_prompts_folder)
        action_prompt = configs['stm']

        messages = make_LLM_messages_multi_input_components(
            action_prompt,
            ["First example", "Second example", "Third example"],
            "Target text"
        )

        content = messages[1]['content']
        assert '**INPUT 1**' in content
        assert 'First example' in content
        assert '**INPUT 2**' in content
        assert 'Second example' in content
        assert '**INPUT 3**' in content
        assert 'Third example' in content
        assert '**TARGET**' in content
        assert 'Target text' in content

    def test_multi_input_message_order(self, test_workspace_data):
        """Test that inputs appear before target in the message."""
        configs = load_agent_configs_from_folder(test_workspace_data.action_prompts_folder)
        action_prompt = configs['stm']

        messages = make_LLM_messages_multi_input_components(
            action_prompt, ["Input A", "Input B"], "Target C"
        )

        content = messages[1]['content']
        input1_pos = content.index('**INPUT 1**')
        input2_pos = content.index('**INPUT 2**')
        target_pos = content.index('**TARGET**')

        assert input1_pos < input2_pos < target_pos


class TestActionPromptLoading:
    """Tests for action prompt loading."""

    def test_load_echo_action(self, test_workspace_data):
        """Test loading the echo action."""
        configs = load_agent_configs_from_folder(test_workspace_data.action_prompts_folder)
        assert 'echo' in configs
        assert configs['echo'].agent_command_name == 'echo'

    def test_load_stm_action(self, test_workspace_data):
        """Test loading the style transfer multi action."""
        configs = load_agent_configs_from_folder(test_workspace_data.action_prompts_folder)
        assert 'stm' in configs
        assert configs['stm'].agent_command_name == 'stm'


class TestSizeLimit:
    """Tests for size limit constant."""

    def test_size_limit_value(self):
        """Test that SIZE_LIMIT is set to expected value."""
        assert SIZE_LIMIT == 30000

    def test_components_under_size_limit(self, components_folder):
        """Test that all test components are under the size limit."""
        for filename in os.listdir(components_folder):
            if filename.endswith('.tex'):
                filepath = os.path.join(components_folder, filename)
                size = os.path.getsize(filepath)
                assert size < SIZE_LIMIT, f"{filename} exceeds size limit"


class TestFindSimilarComponents:
    """Tests for component suggestion when file not found."""

    def test_suggests_with_tex_extension(self, components_folder):
        """Test that missing .tex extension is suggested."""
        from shalev.agent_actions.agent import find_similar_components
        # Looking for 'root' should suggest 'root.tex'
        suggestions = find_similar_components(components_folder, 'root')
        assert 'root.tex' in suggestions

    def test_suggests_similar_names(self, components_folder):
        """Test fuzzy matching on similar names."""
        from shalev.agent_actions.agent import find_similar_components
        # Looking for 'ch1' should suggest 'ch1.tex'
        suggestions = find_similar_components(components_folder, 'ch1')
        assert 'ch1.tex' in suggestions

    def test_no_suggestions_for_completely_wrong(self, components_folder):
        """Test that completely wrong names return empty or limited suggestions."""
        from shalev.agent_actions.agent import find_similar_components
        suggestions = find_similar_components(components_folder, 'xyznonexistent123')
        # Should be empty or very few suggestions
        assert len(suggestions) <= 2
