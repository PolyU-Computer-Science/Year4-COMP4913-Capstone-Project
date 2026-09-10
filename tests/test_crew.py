from crewai.llms.providers.openai.completion import OpenAICompletion

from email_assistant.agents import EmailAssistant


def test_agents_use_separate_llm_instances_with_same_model(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("SQLITE_SETTINGS_DB", str(tmp_path / "settings.db"))
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_MODEL", "test-local-model")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_TIMEOUT", "120")
    monkeypatch.setenv("LLM_MAX_TOKENS", "2000")

    email_assistant = EmailAssistant()
    classifier = email_assistant.classifier()
    drafter = email_assistant.drafter()

    assert classifier.llm is not drafter.llm
    assert type(classifier.llm) is OpenAICompletion
    assert classifier.llm.model == "test-local-model"
    assert drafter.llm.model == "test-local-model"


def test_stage_settings_apply_per_agent_max_tokens(
    monkeypatch, tmp_path
) -> None:
    from email_assistant.core.settings_store import SettingsStore

    monkeypatch.setenv("SQLITE_SETTINGS_DB", str(tmp_path / "settings.db"))
    monkeypatch.delenv("SETTINGS_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_MODEL", "test-local-model")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://localhost:11434/v1")

    store = SettingsStore()
    store.set_stage_settings(
        "classification", {"max_tokens": 111, "temperature": 0.1}
    )
    store.set_stage_settings("draft", {"max_tokens": 222, "temperature": 0.9})

    email_assistant = EmailAssistant()
    classifier = email_assistant.classifier()
    drafter = email_assistant.drafter()

    assert classifier.llm.max_tokens == 111
    assert classifier.llm.temperature == 0.1
    assert drafter.llm.max_tokens == 222
    assert drafter.llm.temperature == 0.9
