from __future__ import annotations

from marshmallow import Schema, fields, validate


class ErrorSchema(Schema):
    """Default error schema."""
    code = fields.Int(description="Error code")
    status = fields.Str(description="Error name")
    message = fields.Str(description="Error message")
    errors = fields.Dict(keys=fields.Str(), values=fields.Raw(), description="Errors")


class RunRequestSchema(Schema):
    """Request payload for starting a run."""
    suite = fields.Str(required=False, load_default="default", description="Name of the suite to run")
    parameters = fields.Dict(keys=fields.Str(), values=fields.Raw(), required=False, load_default=dict, description="Optional parameters")


class RunResponseSchema(Schema):
    """Response for a run start request."""
    session_id = fields.Str(required=True, description="Session identifier")
    status = fields.Str(required=True, description="Current status of the session")
    created_at = fields.Float(required=True, description="Creation timestamp (epoch seconds)")
    updated_at = fields.Float(required=True, description="Last update timestamp (epoch seconds)")


class ProgressQuerySchema(Schema):
    """Progress query params."""
    session_id = fields.Str(required=True, metadata={"description": "Session identifier"})


class ProgressSchema(Schema):
    """Progress response payload."""
    total_steps = fields.Int(required=True, description="Total steps")
    current_step = fields.Int(required=True, description="Current step")
    percent = fields.Float(required=True, description="Progress percent 0..100")


class StatsQuerySchema(Schema):
    """Stats query params."""
    session_id = fields.Str(required=True, metadata={"description": "Session identifier"})


class StatsSchema(Schema):
    """Stats response payload."""
    duration_seconds = fields.Float(required=True, description="Execution duration in seconds")
    steps_completed = fields.Int(required=True, description="Number of steps completed")
    success = fields.Bool(required=True, description="Whether the session completed successfully")
    artifacts = fields.Dict(keys=fields.Str(), values=fields.Str(), required=True, description="Artifact map such as URLs")


class LogsQuerySchema(Schema):
    """Logs query params."""
    session_id = fields.Str(required=True, metadata={"description": "Session identifier"})
    level = fields.Str(required=False, validate=validate.OneOf(["DEBUG", "INFO", "WARN", "ERROR"]), metadata={"description": "Optional log level filter"})
    limit = fields.Int(required=False, metadata={"description": "Optional limit for last N entries"})


class LogEntrySchema(Schema):
    """Single log entry schema."""
    timestamp = fields.Float(required=True, description="Epoch seconds")
    level = fields.Str(required=True, description="Log level")
    message = fields.Str(required=True, description="Log message")
