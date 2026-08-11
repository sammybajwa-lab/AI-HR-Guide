from core.tool_impl import create_mock_hr_ticket_impl


def test_ticket_requires_confirmation():
    result = create_mock_hr_ticket_impl("E101", "workplace_conduct", "Synthetic test", confirmed=False)
    assert result["created"] is False
    assert result["requires_confirmation"] is True


def test_unknown_employee_does_not_create_ticket():
    result = create_mock_hr_ticket_impl("E999", "general", "Synthetic test", confirmed=True)
    assert result["created"] is False
