from legal_preprocessing.cli import completion_message


def test_completion_message_is_safe_for_legacy_windows_console():
    message = completion_message(824, 8)
    assert message.encode("cp1252")
    assert "824" in message and "8" in message
