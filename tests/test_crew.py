from crewai.llms.providers.openai.completion import OpenAICompletion

from email_assistant.crew import EmailAssistant


def test_agents_share_the_configured_llm_instance(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_MODEL", "test-local-model")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_TIMEOUT", "120")
    monkeypatch.setenv("LLM_MAX_TOKENS", "2000")

    email_assistant = EmailAssistant()
    classifier = email_assistant.classifier()
    drafter = email_assistant.drafter()

    assert classifier.llm is drafter.llm
    assert type(classifier.llm) is OpenAICompletion
    assert classifier.llm.model == "test-local-model"
