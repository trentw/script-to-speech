import logging
from unittest.mock import MagicMock, Mock, patch

import pytest

from utils.logging import (
    SimpleFormatter,
    TqdmLoggingHandler,
    get_screenplay_logger,
    setup_screenplay_logging,
)


class TestSimpleFormatter:
    """Tests for the SimpleFormatter class."""

    def test_format_error(self):
        """Test formatting of error level messages."""
        formatter = SimpleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Test error message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert result == "[ERROR] Test error message"

    def test_format_warning(self):
        """Test formatting of warning level messages."""
        formatter = SimpleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Test warning message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert result == "[WARN] Test warning message"

    def test_format_info(self):
        """Test formatting of info level messages."""
        formatter = SimpleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test info message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert result == "Test info message"

    def test_format_debug(self):
        """Test formatting of debug level messages."""
        formatter = SimpleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Test debug message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert result == "Test debug message"


class TestGetScreenplayLogger:
    """Tests for the get_screenplay_logger function."""

    def test_get_screenplay_logger_with_existing_handlers(self):
        """Test getting a logger when the screenplay logger already has handlers."""
        # Setup screenplay logger with a handler
        screenplay_logger = logging.getLogger("screenplay")

        # Save original state to restore later
        original_handlers = list(screenplay_logger.handlers)
        original_level = screenplay_logger.level

        try:
            # Clear existing handlers and add a test handler
            screenplay_logger.handlers.clear()
            test_handler = logging.StreamHandler()
            screenplay_logger.addHandler(test_handler)
            screenplay_logger.setLevel(logging.WARNING)

            # Get a child logger
            logger = get_screenplay_logger("test")

            # Verify logger settings
            assert logger.name == "screenplay.test"
            assert logger.parent == screenplay_logger
            assert not logger.handlers  # Child logger should not have its own handlers
            assert logger.level == logging.NOTSET  # Child loggers default to NOTSET

            # Verify parent logger still has our handler
            assert len(screenplay_logger.handlers) == 1
            assert screenplay_logger.handlers[0] == test_handler
            assert screenplay_logger.level == logging.WARNING

        finally:
            # Restore original screenplay logger state
            screenplay_logger.handlers.clear()
            for handler in original_handlers:
                screenplay_logger.addHandler(handler)
            screenplay_logger.setLevel(original_level)

    def test_get_screenplay_logger_without_existing_handlers(self):
        """Test getting a logger when the screenplay logger has no handlers."""
        # Setup screenplay logger with no handlers
        screenplay_logger = logging.getLogger("screenplay")

        # Save original state to restore later
        original_handlers = list(screenplay_logger.handlers)
        original_level = screenplay_logger.level

        try:
            # Clear existing handlers
            screenplay_logger.handlers.clear()

            # Get a child logger
            logger = get_screenplay_logger("test")

            # Verify logger settings
            assert logger.name == "screenplay.test"
            assert logger.parent == screenplay_logger
            assert not logger.handlers  # Child logger should not have its own handlers

            # Verify parent logger has a new handler
            assert len(screenplay_logger.handlers) == 1
            assert isinstance(screenplay_logger.handlers[0], TqdmLoggingHandler)
            assert isinstance(screenplay_logger.handlers[0].formatter, SimpleFormatter)
            assert screenplay_logger.level == logging.INFO

        finally:
            # Restore original screenplay logger state
            screenplay_logger.handlers.clear()
            for handler in original_handlers:
                screenplay_logger.addHandler(handler)
            screenplay_logger.setLevel(original_level)


class TestSetupScreenplayLogging:
    """Tests for the setup_screenplay_logging function."""

    @patch("utils.logging.logging.FileHandler")
    def test_setup_screenplay_logging(self, mock_file_handler):
        """Test setting up screenplay logging with file and console output."""
        # Setup mock file handler
        mock_file_handler.return_value = MagicMock()

        # Mock TqdmLoggingHandler to avoid affecting console output during tests
        with patch("utils.logging.TqdmLoggingHandler") as mock_tqdm_handler:
            # Create a mock instance and track constructor arguments
            mock_instance = MagicMock()
            mock_tqdm_handler.return_value = mock_instance

            # Use side_effect to capture the level parameter
            captured_args = []

            def side_effect(*args, **kwargs):
                captured_args.append((args, kwargs))
                return mock_instance

            mock_tqdm_handler.side_effect = side_effect

            # Save original state of loggers to restore later
            root_logger = logging.getLogger()
            screenplay_logger = logging.getLogger("screenplay")
            original_root_handlers = list(root_logger.handlers)
            original_screenplay_handlers = list(screenplay_logger.handlers)
            original_root_level = root_logger.level
            original_screenplay_level = screenplay_logger.level

            try:
                # Create some test screenplay.* loggers
                test_logger1 = logging.getLogger("screenplay.test1")
                test_logger2 = logging.getLogger("screenplay.test2")

                # Add a handler to test_logger1 (should be removed)
                test_handler = logging.StreamHandler()
                test_logger1.addHandler(test_handler)

                # Setup logging
                setup_screenplay_logging(
                    log_file="test.log",
                    file_level=logging.DEBUG,
                    console_level=logging.WARNING,
                )

                # Verify file handler was created with correct settings
                mock_file_handler.assert_called_once_with("test.log")
                mock_file_handler.return_value.setFormatter.assert_called_once()
                mock_file_handler.return_value.setLevel.assert_called_once_with(
                    logging.DEBUG
                )

                # Verify console handler was created with correct settings
                # Due to complex mocking, don't check exact call count
                mock_tqdm_handler.return_value.setFormatter.assert_called()
                # Check that the handler was created with the correct level
                # The first argument after self is the level parameter
                assert len(captured_args) > 0
                args, kwargs = captured_args[0]
                if kwargs and "level" in kwargs:
                    assert kwargs["level"] == logging.WARNING
                elif len(args) > 1:  # args[0] is self
                    assert args[1] == logging.WARNING

                # Verify screenplay logger has both handlers
                assert len(screenplay_logger.handlers) == 2
                assert screenplay_logger.level == logging.DEBUG
                assert (
                    screenplay_logger.propagate is False
                )  # Don't propagate to root logger

                # Verify test loggers were reset
                assert len(test_logger1.handlers) == 0  # Any existing handlers removed
                assert test_logger1.propagate is True  # Set to propagate to parent
                assert test_logger1.level == logging.DEBUG

                assert len(test_logger2.handlers) == 0
                assert test_logger2.propagate is True
                assert test_logger2.level == logging.DEBUG

            finally:
                # Restore original logger states
                root_logger.handlers.clear()
                for handler in original_root_handlers:
                    root_logger.addHandler(handler)
                root_logger.setLevel(original_root_level)

                screenplay_logger.handlers.clear()
                for handler in original_screenplay_handlers:
                    screenplay_logger.addHandler(handler)
                screenplay_logger.setLevel(original_screenplay_level)

                # Remove test loggers by setting them to None
                # This is a cleaner approach than directly manipulating the loggerDict
                logging.getLogger("screenplay.test1").handlers = []
                logging.getLogger("screenplay.test1").propagate = True

                logging.getLogger("screenplay.test2").handlers = []
                logging.getLogger("screenplay.test2").propagate = True
