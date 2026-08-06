from functools import cached_property

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.llms.base_llm import BaseLLM
from crewai.project import CrewBase, agent, crew, task

from email_assistant.models import EmailClassification
from email_assistant.service import LLMSettings, create_llm


@CrewBase
class EmailAssistant:
    """EmailAssistant crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    agents_config = "../config/agents.yaml"
    tasks_config = "../config/tasks.yaml"

    @cached_property
    def configured_llm(self) -> BaseLLM:
        """Create one provider-configured LLM for this crew instance."""
        return create_llm(LLMSettings.from_env())

    @agent
    def classifier(self) -> Agent:
        return Agent(
            config=self.agents_config["classifier"],  # type: ignore[index]
            llm=self.configured_llm,
            verbose=True,
        )

    @agent
    def drafter(self) -> Agent:
        return Agent(
            config=self.agents_config["drafter"],  # type: ignore[index]
            llm=self.configured_llm,
            verbose=True,
        )

    @task
    def classify_email_task(self) -> Task:
        return Task(
            config=self.tasks_config["classify_email_task"],  # type: ignore[index]
            output_pydantic=EmailClassification,
        )

    @task
    def draft_reply_task(self) -> Task:
        return Task(
            config=self.tasks_config["draft_reply_task"],  # type: ignore[index]
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
