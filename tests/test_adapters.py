# Test suite for Dream Palace


import pytest

from dream_palace.adapters.database.base import DatabaseAdapter, DatabaseConfig, DreamEntry
from dream_palace.adapters.llm.base import LLMAdapter, LLMConfig


class TestLLMAdapter:
    """Test LLM adapter base class."""

    def test_abstract_methods(self):
        """Test that LLMAdapter has required abstract methods."""
        config = LLMConfig(model_name="test", api_key="test")

        # Should not be able to instantiate abstract class
        with pytest.raises(TypeError):
            LLMAdapter(config)


class TestDatabaseAdapter:
    """Test database adapter base class."""

    def test_abstract_methods(self):
        """Test that DatabaseAdapter has required abstract methods."""
        config = DatabaseConfig(connection_string="test")

        # Should not be able to instantiate abstract class
        with pytest.raises(TypeError):
            DatabaseAdapter(config)


class TestDreamEntry:
    """Test DreamEntry model."""

    def test_dream_entry_creation(self):
        """Test creating a dream entry."""
        dream = DreamEntry(
            user_id=123,
            content="I dreamed of flying",
            title="Flying Dream",
            tags=["flying", "freedom"],
        )

        assert dream.user_id == 123
        assert dream.content == "I dreamed of flying"
        assert dream.title == "Flying Dream"
        assert dream.tags == ["flying", "freedom"]
        assert dream.id is None  # Not set yet
