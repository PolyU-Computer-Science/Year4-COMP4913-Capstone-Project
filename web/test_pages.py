import pytest
from nicegui.testing import User


@pytest.mark.anyio
async def test_dashboard(user: User) -> None:
    await user.open("/")
    await user.should_see("Dashboard")
    await user.should_see("Total Emails")


@pytest.mark.anyio
async def test_inbox(user: User) -> None:
    await user.open("/inbox")
    await user.should_see("Inbox")
    await user.should_see("Fetch Emails")


@pytest.mark.anyio
async def test_cases(user: User) -> None:
    await user.open("/cases")
    await user.should_see("Cases")
    await user.should_see("No processed cases yet")
