# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""
Command Validator Decorator for AIC Applications.

This module provides the @command_validator decorator that allows AIC applications
to define optional validation logic for commands before they are sent to network nodes.

Command validators are OPTIONAL - if no validator is defined for a command, the command
passes through unchanged (backward compatible). This feature is primarily useful when
using the FastAPI REST API or MCP tools to send manual control commands.

Usage:
    from ai_nn_controller import command_validator

    @aic_app(name="MyApp")
    class MyApp(AicApp):
        control_functions = {8: ["SET_GAIN", "SET_VOA"]}

        # Optional: Add validation for SET_GAIN commands
        # IMPORTANT: @classmethod must be ABOVE @command_validator
        @classmethod
        @command_validator("SET_GAIN")
        def validate_set_gain(cls, params: dict) -> Tuple[bool, Optional[str]]:
            '''Validate SET_GAIN command parameters.'''
            target_gain = params.get("target_gain", 0)
            if target_gain > 25:
                return False, f"Gain {target_gain} exceeds maximum of 25 dB"
            if target_gain < 0:
                return False, "Gain cannot be negative"
            return True, None

        # SET_VOA has no validator - passes through unchanged
"""

from typing import Callable, Dict, Optional, Tuple, Any
from ..config import vprint


# Storage for command validators per app class
# Structure: {app_class_name: {command_name: validator_func}}
_app_command_validators: Dict[str, Dict[str, Callable]] = {}


def command_validator(command_name: str):
    """
    Decorator to register a validator function for a specific command.

    The validator function should be a classmethod that takes a params dict
    and returns a tuple of (is_valid: bool, error_message: Optional[str]).

    If is_valid is True, the command proceeds. If False, the command is
    rejected with the provided error message.

    Args:
        command_name: The name of the command to validate (e.g., "SET_GAIN")

    Returns:
        Decorator function that registers the validator

    Example:
        # IMPORTANT: @classmethod must be ABOVE @command_validator
        @classmethod
        @command_validator("SET_GAIN")
        def validate_set_gain(cls, params: dict) -> Tuple[bool, Optional[str]]:
            if params.get("target_gain", 0) > 25:
                return False, "Gain exceeds maximum"
            return True, None
    """
    def decorator(func: Callable) -> Callable:
        # Mark the function as a command validator
        # This metadata will be read when the class is processed by @aic_app
        if not hasattr(func, '_command_validators'):
            func._command_validators = {}
        func._command_validators[command_name] = func

        vprint(f"[CommandValidator] Registered validator for '{command_name}'")
        return func

    return decorator


def register_app_validators(app_class: type, app_name: str) -> None:
    """
    Scan an app class for @command_validator decorated methods and register them.

    This is called by the @aic_app decorator during class registration.

    Args:
        app_class: The AIC application class to scan
        app_name: The unique name of the application
    """
    validators = {}

    # Scan all class attributes for validator decorations
    # We need to check multiple locations because decorator order affects where
    # the _command_validators attribute ends up
    for attr_name in dir(app_class):
        try:
            attr = getattr(app_class, attr_name)

            # Check if this method has validator metadata directly
            if hasattr(attr, '_command_validators'):
                for cmd_name, validator_func in attr._command_validators.items():
                    validators[cmd_name] = attr  # Store the bound method
                    vprint(f"[CommandValidator] App '{app_name}': registered validator for '{cmd_name}' (direct)")

            # Check the underlying function for classmethods (__func__)
            elif hasattr(attr, '__func__') and hasattr(attr.__func__, '_command_validators'):
                for cmd_name, validator_func in attr.__func__._command_validators.items():
                    validators[cmd_name] = attr  # Store the bound classmethod
                    vprint(f"[CommandValidator] App '{app_name}': registered validator for '{cmd_name}' (__func__)")

        except Exception as e:
            # Skip any attributes that can't be accessed
            vprint(f"[CommandValidator] Warning: Could not inspect '{attr_name}': {e}")
            pass

    # Also check __dict__ directly for any validators that might have been missed
    for attr_name, attr in app_class.__dict__.items():
        try:
            # Check classmethod wrapper
            if isinstance(attr, classmethod):
                func = attr.__func__
                if hasattr(func, '_command_validators'):
                    for cmd_name, validator_func in func._command_validators.items():
                        if cmd_name not in validators:
                            validators[cmd_name] = getattr(app_class, attr_name)
                            vprint(f"[CommandValidator] App '{app_name}': registered validator for '{cmd_name}' (__dict__)")
            # Check regular function
            elif callable(attr) and hasattr(attr, '_command_validators'):
                for cmd_name, validator_func in attr._command_validators.items():
                    if cmd_name not in validators:
                        validators[cmd_name] = attr
                        vprint(f"[CommandValidator] App '{app_name}': registered validator for '{cmd_name}' (callable)")
        except Exception as e:
            pass

    if validators:
        _app_command_validators[app_name] = validators
        vprint(f"[CommandValidator] App '{app_name}': {len(validators)} validator(s) registered")
    else:
        vprint(f"[CommandValidator] App '{app_name}': no validators found")


def validate_command(
    app_name: str,
    app_class: type,
    command_name: str,
    params: dict
) -> Tuple[bool, Optional[str]]:
    """
    Validate a command using the app's registered validator (if any).

    If no validator is registered for this command, returns (True, None)
    allowing the command to proceed.

    Args:
        app_name: Name of the AIC application
        app_class: The AIC application class
        command_name: Name of the command to validate
        params: Command parameters dict (includes node_id and command-specific params)

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if command is valid or no validator exists
        - error_message: None if valid, error string if invalid
    """
    vprint(f"[CommandValidator] Validating command '{command_name}' for app '{app_name}'")
    vprint(f"[CommandValidator] Registered apps with validators: {list(_app_command_validators.keys())}")

    # Check if app has any validators registered
    if app_name not in _app_command_validators:
        vprint(f"[CommandValidator] No validators registered for app '{app_name}'")
        return True, None  # No validators for this app

    app_validators = _app_command_validators[app_name]
    vprint(f"[CommandValidator] App '{app_name}' has validators for: {list(app_validators.keys())}")

    # Check if there's a validator for this specific command
    if command_name not in app_validators:
        vprint(f"[CommandValidator] No validator for command '{command_name}'")
        return True, None  # No validator for this command

    validator = app_validators[command_name]
    vprint(f"[CommandValidator] Found validator: {validator}")

    try:
        # Call the validator - it's stored as a bound method or classmethod
        # For bound methods/classmethods, we just call with params (class is already bound)
        if callable(validator):
            result = validator(params)
        else:
            vprint(f"[CommandValidator] Validator is not callable: {type(validator)}")
            return True, None

        vprint(f"[CommandValidator] Validator result: {result}")

        # Validate return format
        if isinstance(result, tuple) and len(result) == 2:
            is_valid, error_msg = result
            return bool(is_valid), error_msg if not is_valid else None
        elif isinstance(result, bool):
            # Allow simple bool return for convenience
            return result, None if result else "Validation failed"
        else:
            vprint(f"[CommandValidator] Warning: validator for '{command_name}' returned invalid format: {result}")
            return True, None  # Default to allowing if format is wrong

    except Exception as e:
        vprint(f"[CommandValidator] Error in validator for '{command_name}': {e}")
        import traceback
        traceback.print_exc()
        # On error, reject the command for safety
        return False, f"Validation error: {str(e)}"


def get_app_validators(app_name: str) -> Dict[str, Callable]:
    """
    Get all registered validators for an application.

    Args:
        app_name: Name of the AIC application

    Returns:
        Dictionary mapping command names to validator functions
    """
    return _app_command_validators.get(app_name, {})


def has_validator(app_name: str, command_name: str) -> bool:
    """
    Check if a validator exists for a specific command in an app.

    Args:
        app_name: Name of the AIC application
        command_name: Name of the command

    Returns:
        True if a validator exists, False otherwise
    """
    if app_name not in _app_command_validators:
        return False
    return command_name in _app_command_validators[app_name]


def clear_validators() -> None:
    """Clear all registered validators. Mainly for testing."""
    _app_command_validators.clear()
