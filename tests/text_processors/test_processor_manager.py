import builtins
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import yaml

from text_processors.processor_manager import TextProcessorManager
from text_processors.text_preprocessor_base import TextPreProcessor
from text_processors.text_processor_base import TextProcessor


class TestTextProcessorManager:
    """Tests for the TextProcessorManager class."""

    def test_initialization_with_single_config(self):
        """Test initialization with a single config file."""
        mock_config = """
        preprocessors:
          - name: skip_and_merge
            config: {}
        processors:
          - name: skip_empty
            config: {}
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = MagicMock()

                # Create mock preprocessor and processor classes
                mock_preprocessor = Mock(spec=TextPreProcessor)
                mock_preprocessor.return_value.validate_config.return_value = True
                mock_preprocessor.return_value.multi_config_mode = "chain"

                mock_processor = Mock(spec=TextProcessor)
                mock_processor.return_value.validate_config.return_value = True
                mock_processor.return_value.multi_config_mode = "chain"

                # Set up module attributes
                mock_import.return_value.SkipAndMergePreProcessor = mock_preprocessor
                mock_import.return_value.SkipEmptyProcessor = mock_processor

                # Initialize manager
                manager = TextProcessorManager(["fake_config.yaml"])

                # Verify the correct modules were imported
                mock_import.assert_any_call(
                    "text_processors.preprocessors.skip_and_merge_preprocessor"
                )
                mock_import.assert_any_call(
                    "text_processors.processors.skip_empty_processor"
                )

                # Verify preprocessors and processors were initialized
                assert len(manager.preprocessors) == 1
                assert len(manager.processors) == 1

                # Verify validate_config was called
                mock_preprocessor.return_value.validate_config.assert_called_once()
                mock_processor.return_value.validate_config.assert_called_once()

    def test_initialization_with_multiple_configs(self):
        """Test initialization with multiple config files."""
        # Create two different configurations
        config1 = """
        preprocessors:
          - name: skip_and_merge
            config: {}
        processors:
          - name: skip_empty
            config: {}
        """

        config2 = """
        preprocessors:
          - name: dual_dialog
            config: {}
        processors:
          - name: pattern_replace
            config: {}
        """

        # Mock open to return different content based on filename
        def mock_open_func(filename, *args, **kwargs):
            if filename == "config1.yaml":
                return mock_open(read_data=config1)()
            elif filename == "config2.yaml":
                return mock_open(read_data=config2)()
            raise FileNotFoundError(f"Mock file not found: {filename}")

        with patch("builtins.open", side_effect=mock_open_func):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = MagicMock()

                # Mock preprocessors and processors
                preprocessors = {
                    "skip_and_merge": Mock(spec=TextPreProcessor),
                    "dual_dialog": Mock(spec=TextPreProcessor),
                }
                processors = {
                    "skip_empty": Mock(spec=TextProcessor),
                    "pattern_replace": Mock(spec=TextProcessor),
                }

                # Configure mocks
                for name, mock_obj in {**preprocessors, **processors}.items():
                    mock_obj.return_value.validate_config.return_value = True
                    mock_obj.return_value.multi_config_mode = "chain"

                # Set module attributes
                mock_module = mock_import.return_value
                mock_module.SkipAndMergePreProcessor = preprocessors["skip_and_merge"]
                mock_module.DualDialogPreProcessor = preprocessors["dual_dialog"]
                mock_module.SkipEmptyProcessor = processors["skip_empty"]
                mock_module.PatternReplaceProcessor = processors["pattern_replace"]

                # Initialize manager
                manager = TextProcessorManager(["config1.yaml", "config2.yaml"])

                # Verify the right number of processors are initialized
                assert len(manager.preprocessors) == 2
                assert len(manager.processors) == 2

    def test_multi_config_mode_chain(self):
        """Test chaining multiple configs with the same processor (chain mode)."""
        # Create two configurations with the same processor
        config1 = """
        processors:
          - name: skip_empty
            config:
              skip_types: ["type1"]
        """

        config2 = """
        processors:
          - name: skip_empty
            config:
              skip_types: ["type2"]
        """

        # Mock open to return different content based on filename
        def mock_open_func(filename, *args, **kwargs):
            if filename == "config1.yaml":
                return mock_open(read_data=config1)()
            elif filename == "config2.yaml":
                return mock_open(read_data=config2)()
            raise FileNotFoundError(f"Mock file not found: {filename}")

        with patch("builtins.open", side_effect=mock_open_func):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = MagicMock()

                # Create mock processor that uses chain mode
                mock_processor = Mock(spec=TextProcessor)
                mock_processor.return_value.validate_config.return_value = True
                mock_processor.return_value.multi_config_mode = "chain"

                # Set module attributes
                mock_import.return_value.SkipEmptyProcessor = mock_processor

                # Initialize manager
                manager = TextProcessorManager(["config1.yaml", "config2.yaml"])

                # Verify we have two processor instances (chain mode)
                assert len(manager.processors) == 2

    def test_multi_config_mode_override(self):
        """Test overriding configs with the same processor (override mode)."""
        # Create two configurations with the same processor
        config1 = """
        processors:
          - name: skip_empty
            config:
              skip_types: ["type1"]
        """

        config2 = """
        processors:
          - name: skip_empty
            config:
              skip_types: ["type2"]
        """

        # Mock open to return different content based on filename
        def mock_open_func(filename, *args, **kwargs):
            if filename == "config1.yaml":
                return mock_open(read_data=config1)()
            elif filename == "config2.yaml":
                return mock_open(read_data=config2)()
            raise FileNotFoundError(f"Mock file not found: {filename}")

        with patch("builtins.open", side_effect=mock_open_func):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = MagicMock()

                # Create mock processor that uses override mode
                mock_processor = Mock(spec=TextProcessor)
                mock_processor.return_value.validate_config.return_value = True
                mock_processor.return_value.multi_config_mode = "override"

                # Set module attributes
                mock_import.return_value.SkipEmptyProcessor = mock_processor

                # Initialize manager
                manager = TextProcessorManager(["config1.yaml", "config2.yaml"])

                # Verify we only have one processor instance (override mode)
                assert len(manager.processors) == 1

    def test_process_chunks(self):
        """Test the process_chunks method's overall behavior."""
        # Setup input chunks
        chunks = [
            {"type": "dialog", "text": "Hello world"},
            {"type": "action", "text": "Character walks away"},
        ]

        # Mock basic config
        mock_config = """
        preprocessors: []
        processors: []
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            # Mock preprocessor that adds a new chunk
            mock_preprocessor = Mock(spec=TextPreProcessor)
            mock_preprocessor.process.return_value = (
                chunks + [{"type": "scene_heading", "text": "INT. ROOM - DAY"}],
                True,
            )

            # Mock processor that changes text to uppercase
            mock_processor = Mock(spec=TextProcessor)

            def mock_process(chunk):
                result = chunk.copy()
                result["text"] = result["text"].upper()
                return result, True

            mock_processor.process.side_effect = mock_process

            # Create manager with mocked components
            with patch.object(
                TextProcessorManager, "_initialize_preprocessors"
            ) as mock_init_pre:
                with patch.object(
                    TextProcessorManager, "_initialize_processors"
                ) as mock_init_proc:
                    mock_init_pre.return_value = [mock_preprocessor]
                    mock_init_proc.return_value = [mock_processor]

                    manager = TextProcessorManager(["config.yaml"])

                    # Process chunks
                    result = manager.process_chunks(chunks)

                    # Verify preprocessor was called
                    mock_preprocessor.process.assert_called_once_with(chunks)

                    # Verify processor was called for each chunk
                    assert mock_processor.process.call_count == 3

                    # Verify results
                    assert len(result) == 3
                    assert all(chunk["text"].isupper() for chunk in result)
                    assert result[2]["type"] == "scene_heading"

    def test_preprocess_chunks(self):
        """Test the preprocess_chunks method."""
        # Setup
        chunks = [{"type": "dialog", "text": "Hello"}]

        # Mock basic config
        mock_config = """
        preprocessors: []
        processors: []
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            # Mock preprocessor that adds a chunk
            mock_preprocessor = Mock(spec=TextPreProcessor)
            enhanced_chunks = [
                {"type": "dialog", "text": "Hello"},
                {"type": "dialog", "text": "World"},
            ]
            mock_preprocessor.process.return_value = (enhanced_chunks, True)

            # Create manager with mocked components
            with patch.object(
                TextProcessorManager, "_initialize_preprocessors"
            ) as mock_init:
                mock_init.return_value = [mock_preprocessor]

                manager = TextProcessorManager(["config.yaml"])

                # Run preprocess_chunks
                result = manager.preprocess_chunks(chunks)

                # Verify preprocessor was called
                mock_preprocessor.process.assert_called_once_with(chunks)

                # Verify results
                assert result == enhanced_chunks
                assert manager.preprocessed_chunks == enhanced_chunks

    def test_process_chunk(self):
        """Test the process_chunk method with mocked processors."""
        # Setup
        chunk = {"type": "dialog", "text": "Hello world"}

        # Mock basic config
        mock_config = """
        preprocessors: []
        processors: []
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            # Mock processor that changes text to uppercase
            mock_processor1 = Mock(spec=TextProcessor)

            def mock_process1(input_chunk):
                result = input_chunk.copy()
                result["text"] = result["text"].upper()
                return result, True

            mock_processor1.process.side_effect = mock_process1

            # Mock processor that adds exclamation point
            mock_processor2 = Mock(spec=TextProcessor)

            def mock_process2(input_chunk):
                result = input_chunk.copy()
                result["text"] = result["text"] + "!"
                return result, True

            mock_processor2.process.side_effect = mock_process2

            # Create manager with mocked components
            with patch.object(
                TextProcessorManager, "_initialize_processors"
            ) as mock_init:
                mock_init.return_value = [mock_processor1, mock_processor2]

                manager = TextProcessorManager(["config.yaml"])
                manager.preprocessed_chunks = (
                    []
                )  # Set preprocessed_chunks to avoid error

                # Process chunk
                result, modified = manager.process_chunk(chunk)

                # Verify processors were called in sequence
                mock_processor1.process.assert_called_once()
                mock_processor2.process.assert_called_once()

                # Verify result has changes from both processors
                assert result["text"] == "HELLO WORLD!"
                assert modified is True

    def test_process_chunk_error_if_preprocess_not_called(self):
        """Test that process_chunk raises error if preprocess_chunks wasn't called."""
        # Setup
        chunk = {"type": "dialog", "text": "Hello world"}

        # Mock basic config
        mock_config = """
        preprocessors: []
        processors: []
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            # Create manager with mocked components
            with patch.object(
                TextProcessorManager, "_initialize_processors"
            ) as mock_init:
                mock_init.return_value = []

                manager = TextProcessorManager(["config.yaml"])

                # Process chunk without calling preprocess_chunks first
                with pytest.raises(ValueError):
                    result, modified = manager.process_chunk(chunk)

    def test_error_handling_invalid_config(self):
        """Test error handling with invalid preprocessor or processor configuration."""
        mock_config = """
        preprocessors:
          - name: skip_and_merge
            config: {}
        processors:
          - name: skip_empty
            config: {}
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = MagicMock()

                # Create mocks
                mock_preprocessor = Mock(spec=TextPreProcessor)
                mock_preprocessor.return_value.validate_config.return_value = (
                    False  # Invalid config
                )

                mock_processor = Mock(spec=TextProcessor)
                mock_processor.return_value.validate_config.return_value = True

                # Set module attributes
                mock_import.return_value.SkipAndMergePreProcessor = mock_preprocessor
                mock_import.return_value.SkipEmptyProcessor = mock_processor

                # Initialize manager should raise exception for invalid config
                with pytest.raises(ValueError):
                    manager = TextProcessorManager(["fake_config.yaml"])

    def test_error_handling_module_import_failure(self):
        """Test error handling when a processor module cannot be imported."""
        mock_config = """
        preprocessors:
          - name: nonexistent
            config: {}
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError("Module not found")

                # Initialize manager should raise ValueError for import failure
                with pytest.raises(ValueError):
                    manager = TextProcessorManager(["fake_config.yaml"])

    def test_multi_config_modes_complex_ordering(self):
        """Test complex combinations of chain and override configs with multiple processors."""
        # Create three configurations with various processors
        config1 = """
        preprocessors:
          - name: skip_and_merge
            config: {"skip_types": ["type1"]}
          - name: dual_dialog
            config: {"min_speaker_spacing": 3}
        processors:
          - name: skip_empty
            config: {"skip_types": ["type1"]}
          - name: pattern_replace
            config: {"replacements": [{"match_field": "text", "match_pattern": "test1"}]}
        """

        config2 = """
        preprocessors:
          - name: skip_and_merge
            config: {"skip_types": ["type2"]}
          - name: extract_dialog_parentheticals
            config: {"max_words": 5}
        processors:
          - name: skip_empty
            config: {"skip_types": ["type2"]}
          - name: text_substitution
            config: {"substitutions": [{"from": "INT.", "to": "INTERIOR"}]}
        """

        config3 = """
        preprocessors:
          - name: skip_and_merge
            config: {"skip_types": ["type3"]}
          - name: speaker_merge
            config: {"speakers_to_merge": {"BOB": ["B_OB"]}}
        processors:
          - name: skip_empty
            config: {"skip_types": ["type3"]}
          - name: capitalization_transform
            config: {"transformations": [{"chunk_type": "dialog", "case": "lower_case"}]}
        """

        # Mock open to return different content based on filename
        def mock_open_func(filename, *args, **kwargs):
            if filename == "config1.yaml":
                return mock_open(read_data=config1)()
            elif filename == "config2.yaml":
                return mock_open(read_data=config2)()
            elif filename == "config3.yaml":
                return mock_open(read_data=config3)()
            raise FileNotFoundError(f"Mock file not found: {filename}")

        with patch("builtins.open", side_effect=mock_open_func):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = MagicMock()

                # Setup preprocessors with different multi_config_modes
                preprocessors = {
                    "skip_and_merge": Mock(spec=TextPreProcessor),
                    "dual_dialog": Mock(spec=TextPreProcessor),
                    "extract_dialog_parentheticals": Mock(spec=TextPreProcessor),
                    "speaker_merge": Mock(spec=TextPreProcessor),
                }

                # Skip and merge uses override mode
                preprocessors["skip_and_merge"].return_value.multi_config_mode = (
                    "override"
                )
                # The rest use chain mode
                for name in [
                    "dual_dialog",
                    "extract_dialog_parentheticals",
                    "speaker_merge",
                ]:
                    preprocessors[name].return_value.multi_config_mode = "chain"

                # All preprocessors have valid configs
                for mock_obj in preprocessors.values():
                    mock_obj.return_value.validate_config.return_value = True

                # Setup processors with different multi_config_modes
                processors = {
                    "skip_empty": Mock(spec=TextProcessor),
                    "pattern_replace": Mock(spec=TextProcessor),
                    "text_substitution": Mock(spec=TextProcessor),
                    "capitalization_transform": Mock(spec=TextProcessor),
                }

                # Skip empty uses override mode
                processors["skip_empty"].return_value.multi_config_mode = "override"
                # The rest use chain mode
                for name in [
                    "pattern_replace",
                    "text_substitution",
                    "capitalization_transform",
                ]:
                    processors[name].return_value.multi_config_mode = "chain"

                # All processors have valid configs
                for mock_obj in processors.values():
                    mock_obj.return_value.validate_config.return_value = True

                # Set module attributes for importlib to find
                mock_module = mock_import.return_value
                class_names = {
                    "skip_and_merge": "SkipAndMergePreProcessor",
                    "dual_dialog": "DualDialogPreProcessor",
                    "extract_dialog_parentheticals": "ExtractDialogParentheticalsPreProcessor",
                    "speaker_merge": "SpeakerMergePreProcessor",
                    "skip_empty": "SkipEmptyProcessor",
                    "pattern_replace": "PatternReplaceProcessor",
                    "text_substitution": "TextSubstitutionProcessor",
                    "capitalization_transform": "CapitalizationTransformProcessor",
                }

                for name, mock_obj in {**preprocessors, **processors}.items():
                    setattr(mock_module, class_names[name], mock_obj)

                # Initialize manager
                manager = TextProcessorManager(
                    ["config1.yaml", "config2.yaml", "config3.yaml"]
                )

                # Verify preprocessor counts and ordering
                # Should have 4 preprocessors:
                # - 1 skip_and_merge (override mode keeps last one)
                # - 1 dual_dialog (from config1)
                # - 1 extract_dialog_parentheticals (from config2)
                # - 1 speaker_merge (from config3)
                assert len(manager.preprocessors) == 4

                # Check that the correct preprocessors are present
                preprocessor_types = [p.__class__ for p in manager.preprocessors]
                assert (
                    preprocessors["skip_and_merge"].return_value.__class__
                    in preprocessor_types
                )
                assert (
                    preprocessors["dual_dialog"].return_value.__class__
                    in preprocessor_types
                )
                assert (
                    preprocessors[
                        "extract_dialog_parentheticals"
                    ].return_value.__class__
                    in preprocessor_types
                )
                assert (
                    preprocessors["speaker_merge"].return_value.__class__
                    in preprocessor_types
                )

                # For the override mode preprocessor (skip_and_merge), ensure it has the last config
                skip_merge_instances = [
                    (i, p)
                    for i, p in enumerate(manager.preprocessors)
                    if p.__class__
                    == preprocessors["skip_and_merge"].return_value.__class__
                ]
                assert (
                    len(skip_merge_instances) == 1
                )  # Only one instance due to override mode

                # Verify the skip_and_merge instance got the config from config3
                skip_merge_calls = preprocessors["skip_and_merge"].call_args_list
                assert (
                    len(skip_merge_calls) == 3
                )  # Called 3 times (once per config file)
                # Check the last call had the config from config3
                last_config = skip_merge_calls[-1][0][0]
                assert last_config == {"skip_types": ["type3"]}

                # Verify processor counts and ordering
                # Should have 4 processors:
                # - 1 skip_empty (override mode keeps last one)
                # - 1 pattern_replace (from config1)
                # - 1 text_substitution (from config2)
                # - 1 capitalization_transform (from config3)
                assert len(manager.processors) == 4

                # Check that the correct processors are present
                processor_types = [p.__class__ for p in manager.processors]
                assert (
                    processors["skip_empty"].return_value.__class__ in processor_types
                )
                assert (
                    processors["pattern_replace"].return_value.__class__
                    in processor_types
                )
                assert (
                    processors["text_substitution"].return_value.__class__
                    in processor_types
                )
                assert (
                    processors["capitalization_transform"].return_value.__class__
                    in processor_types
                )

                # For the override mode processor (skip_empty), ensure it has the last config
                skip_empty_instances = [
                    (i, p)
                    for i, p in enumerate(manager.processors)
                    if p.__class__ == processors["skip_empty"].return_value.__class__
                ]
                assert (
                    len(skip_empty_instances) == 1
                )  # Only one instance due to override mode

                # Verify the skip_empty instance got the config from config3
                skip_empty_calls = processors["skip_empty"].call_args_list
                assert (
                    len(skip_empty_calls) == 3
                )  # Called 3 times (once per config file)
                # Check the last call had the config from config3
                last_config = skip_empty_calls[-1][0][0]
                assert last_config == {"skip_types": ["type3"]}

    def test_preprocessor_execution_order(self):
        """Test that preprocessors are executed in the correct order."""
        # Setup input chunks
        initial_chunks = [{"type": "test", "text": "Original"}]

        # Mock basic config
        mock_config = """
        preprocessors:
          - name: skip_and_merge
            config: {}
          - name: dual_dialog
            config: {}
          - name: extract_dialog_parentheticals
            config: {}
        processors: []
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            # Create mock preprocessors that modify chunks in a detectable way
            mock_preprocessor1 = Mock(spec=TextPreProcessor)

            def mock_process1(chunks):
                modified = [{"type": "test", "text": "After preprocessor 1"}]
                return modified, True

            mock_preprocessor1.process.side_effect = mock_process1

            mock_preprocessor2 = Mock(spec=TextPreProcessor)

            def mock_process2(chunks):
                # We should get the output from preprocessor 1
                assert chunks[0]["text"] == "After preprocessor 1"
                modified = [{"type": "test", "text": "After preprocessor 2"}]
                return modified, True

            mock_preprocessor2.process.side_effect = mock_process2

            mock_preprocessor3 = Mock(spec=TextPreProcessor)

            def mock_process3(chunks):
                # We should get the output from preprocessor 2
                assert chunks[0]["text"] == "After preprocessor 2"
                modified = [{"type": "test", "text": "After preprocessor 3"}]
                return modified, True

            mock_preprocessor3.process.side_effect = mock_process3

            # Create manager with ordered mock preprocessors
            with patch.object(
                TextProcessorManager, "_initialize_preprocessors"
            ) as mock_init_pre:
                with patch.object(
                    TextProcessorManager, "_initialize_processors"
                ) as mock_init_proc:
                    mock_init_pre.return_value = [
                        mock_preprocessor1,
                        mock_preprocessor2,
                        mock_preprocessor3,
                    ]
                    mock_init_proc.return_value = []

                    manager = TextProcessorManager(["config.yaml"])

                    # Process chunks
                    result = manager.preprocess_chunks(initial_chunks)

                    # Verify preprocessors were called in order
                    assert mock_preprocessor1.process.call_count == 1
                    assert mock_preprocessor1.process.call_args[0][0] == initial_chunks

                    assert mock_preprocessor2.process.call_count == 1
                    assert mock_preprocessor3.process.call_count == 1

                    # Verify final result
                    assert len(result) == 1
                    assert result[0]["text"] == "After preprocessor 3"

    def test_processor_execution_order(self):
        """Test that processors are executed in the correct order."""
        # Setup input chunk
        chunk = {"type": "test", "text": "Original"}

        # Mock basic config
        mock_config = """
        preprocessors: []
        processors:
          - name: skip_empty
            config: {}
          - name: pattern_replace
            config: {}
          - name: text_substitution
            config: {}
        """

        with patch("builtins.open", mock_open(read_data=mock_config)):
            # Create mock processors that modify chunk in a detectable way
            mock_processor1 = Mock(spec=TextProcessor)

            def mock_process1(input_chunk):
                modified = input_chunk.copy()
                modified["text"] = "After processor 1"
                return modified, True

            mock_processor1.process.side_effect = mock_process1

            mock_processor2 = Mock(spec=TextProcessor)

            def mock_process2(input_chunk):
                # We should get the output from processor 1
                assert input_chunk["text"] == "After processor 1"
                modified = input_chunk.copy()
                modified["text"] = "After processor 2"
                return modified, True

            mock_processor2.process.side_effect = mock_process2

            mock_processor3 = Mock(spec=TextProcessor)

            def mock_process3(input_chunk):
                # We should get the output from processor 2
                assert input_chunk["text"] == "After processor 2"
                modified = input_chunk.copy()
                modified["text"] = "After processor 3"
                return modified, True

            mock_processor3.process.side_effect = mock_process3

            # Create manager with ordered mock processors
            with patch.object(
                TextProcessorManager, "_initialize_preprocessors"
            ) as mock_init_pre:
                with patch.object(
                    TextProcessorManager, "_initialize_processors"
                ) as mock_init_proc:
                    mock_init_pre.return_value = []
                    mock_init_proc.return_value = [
                        mock_processor1,
                        mock_processor2,
                        mock_processor3,
                    ]

                    manager = TextProcessorManager(["config.yaml"])
                    manager.preprocessed_chunks = (
                        []
                    )  # Set preprocessed_chunks to avoid error

                    # Process chunk
                    result, modified = manager.process_chunk(chunk)

                    # Verify processors were called in order
                    assert mock_processor1.process.call_count == 1
                    assert mock_processor1.process.call_args[0][0] == chunk

                    assert mock_processor2.process.call_count == 1
                    assert mock_processor3.process.call_count == 1

                    # Verify final result
                    assert result["text"] == "After processor 3"
                    assert modified is True

    def test_multiple_override_preserves_first_occurrence_order(self):
        """Test that when multiple processors use override mode, their relative order is preserved."""
        # Create three configurations with the same processors
        config1 = """
        processors:
          - name: skip_empty
            config: {"skip_types": ["type1"]}
          - name: pattern_replace
            config: {"replacements": [{"match_field": "text", "match_pattern": "test1"}]}
        """

        config2 = """
        processors:
          - name: pattern_replace
            config: {"replacements": [{"match_field": "text", "match_pattern": "test2"}]}
          - name: skip_empty
            config: {"skip_types": ["type2"]}
        """

        config3 = """
        processors:
          - name: skip_empty
            config: {"skip_types": ["type3"]}
          - name: pattern_replace
            config: {"replacements": [{"match_field": "text", "match_pattern": "test3"}]}
        """

        # Mock open to return different content based on filename
        def mock_open_func(filename, *args, **kwargs):
            if filename == "config1.yaml":
                return mock_open(read_data=config1)()
            elif filename == "config2.yaml":
                return mock_open(read_data=config2)()
            elif filename == "config3.yaml":
                return mock_open(read_data=config3)()
            raise FileNotFoundError(f"Mock file not found: {filename}")

        with patch("builtins.open", side_effect=mock_open_func):
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = MagicMock()

                # Setup processors with override mode
                processors = {
                    "skip_empty": Mock(spec=TextProcessor),
                    "pattern_replace": Mock(spec=TextProcessor),
                }

                # Both use override mode
                processors["skip_empty"].return_value.multi_config_mode = "override"
                processors["pattern_replace"].return_value.multi_config_mode = (
                    "override"
                )

                # All processors have valid configs
                for mock_obj in processors.values():
                    mock_obj.return_value.validate_config.return_value = True

                # Set module attributes for importlib to find
                mock_module = mock_import.return_value
                class_names = {
                    "skip_empty": "SkipEmptyProcessor",
                    "pattern_replace": "PatternReplaceProcessor",
                }

                for name, mock_obj in processors.items():
                    setattr(mock_module, class_names[name], mock_obj)

                # Initialize manager
                manager = TextProcessorManager(
                    ["config1.yaml", "config2.yaml", "config3.yaml"]
                )

                # Verify processor counts - should have one of each type
                assert len(manager.processors) == 2

                # For the override mode, the processor ordering should match the first config file
                # Even though we keep the latest config for each processor, the order is based on first appearance
                processor_classes = [p.__class__ for p in manager.processors]

                # Assert the correct ordering (should match config1)
                skip_empty_class = processors["skip_empty"].return_value.__class__
                pattern_replace_class = processors[
                    "pattern_replace"
                ].return_value.__class__

                assert processor_classes.index(
                    skip_empty_class
                ) < processor_classes.index(pattern_replace_class)

                # Verify the skip_empty instance got the config from config3 (latest)
                skip_empty_calls = processors["skip_empty"].call_args_list
                last_config = skip_empty_calls[-1][0][0]
                assert last_config == {"skip_types": ["type3"]}

                # Verify the pattern_replace instance got the config from config3 (latest)
                pattern_replace_calls = processors["pattern_replace"].call_args_list
                last_config = pattern_replace_calls[-1][0][0]
                assert last_config["replacements"][0]["match_pattern"] == "test3"
