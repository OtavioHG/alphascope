"""Automation primitives for scheduled and continuous AlphaScope execution."""

from alphascope.automation.continuous_pipeline import ContinuousCycleResult, ContinuousPipeline, ContinuousPipelineConfig
from alphascope.automation.daemon_runner import DaemonRunner, DaemonRunnerConfig
from alphascope.automation.heartbeat import HeartbeatConfig, HeartbeatService
from alphascope.automation.job_registry import JobDefinition, JobExecutionResult, JobRegistry
from alphascope.automation.scheduler import AutomationScheduler

__all__ = [
    "AutomationScheduler",
    "ContinuousCycleResult",
    "ContinuousPipeline",
    "ContinuousPipelineConfig",
    "DaemonRunner",
    "DaemonRunnerConfig",
    "HeartbeatConfig",
    "HeartbeatService",
    "JobDefinition",
    "JobExecutionResult",
    "JobRegistry",
]
