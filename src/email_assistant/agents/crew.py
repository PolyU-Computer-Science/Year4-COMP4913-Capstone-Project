from functools import cached_property

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.llms.base_llm import BaseLLM
from crewai.project import CrewBase, agent, crew, task

from email_assistant.models import EmailClassification
from email_assistant.service import LLMSettings, create_llm, load_llm_settings


@CrewBase
class EmailAssistant:
    """EmailAssistant crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "../config/agents.yaml"
    tasks_config = "../config/tasks.yaml"

    @cached_property
    def base_settings(self) -> LLMSettings:
        """The active AI config (or env fallback) as LLM settings."""
        return load_llm_settings()

    def _stage_settings(self, stage: str) -> dict:
        from email_assistant.core.settings_store import SettingsStore

        return SettingsStore().get_stage_settings(stage)

    def _stage_llm(self, stage: str) -> BaseLLM:
        """Build an LLM with per-stage temperature / max_tokens overrides."""
        stage_settings = self._stage_settings(stage)
        updates: dict = {}
        if stage_settings.get("temperature") is not None:
            updates["temperature"] = float(stage_settings["temperature"])
        if stage_settings.get("max_tokens") is not None:
            updates["max_tokens"] = int(stage_settings["max_tokens"])
        return create_llm(self.base_settings.model_copy(update=updates))

    def _agent_config(self, agent_key: str, stage: str) -> dict:
        """Agent config from YAML, overridden by per-stage system settings."""
        config = dict(self.agents_config[agent_key])  # type: ignore[index]
        stage_settings = self._stage_settings(stage)
        for field in ("role", "goal", "backstory"):
            if stage_settings.get(field):
                config[field] = stage_settings[field]
        return config

    def _task_config(self, task_key: str, stage: str) -> dict:
        """Task config from YAML, overridden by the per-stage prompt."""
        config = dict(self.tasks_config[task_key])  # type: ignore[index]
        prompt = self._stage_settings(stage).get("prompt")
        if prompt:
            config["description"] = prompt
        return config

    @cached_property
    def classifier_llm(self) -> BaseLLM:
        return self._stage_llm("classification")

    @cached_property
    def drafter_llm(self) -> BaseLLM:
        return self._stage_llm("draft")

    @agent
    def classifier(self) -> Agent:
        return Agent(
            config=self._agent_config("classifier", "classification"),
            llm=self.classifier_llm,
            verbose=True,
        )

    @agent
    def drafter(self) -> Agent:
        return Agent(
            config=self._agent_config("drafter", "draft"),
            llm=self.drafter_llm,
            verbose=True,
        )

    @task
    def classify_email_task(self) -> Task:
        return Task(
            config=self._task_config("classify_email_task", "classification"),
            output_pydantic=EmailClassification,
        )

    @task
    def draft_reply_task(self) -> Task:
        return Task(
            config=self._task_config("draft_reply_task", "draft"),
            context=[self.classify_email_task()],  # type: ignore[arg-type]
            output_file="draft_reply.txt",
        )

    @crew
    def crew(self) -> Crew:
        """Creates the EmailAssistant crew"""
        return Crew(  # type: ignore[call-arg]
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
