from tests.slack_bot.test_session_manager import TestGetSessionInfo as _TestGetSessionInfo
from tests.slack_bot.test_session_manager import (
    TestSessionManagerDoubleStart as _TestSessionManagerDoubleStart,
)
from tests.slack_bot.test_session_manager import TestSessionManagerInit as _TestSessionManagerInit
from tests.slack_bot.test_session_manager import TestSessionManagerStop as _TestSessionManagerStop
from tests.slack_bot.test_session_manager import (
    TestSessionManagerWithMockEngine as _TestSessionManagerWithMockEngine,
)


class TestSessionManagerInit(_TestSessionManagerInit):
    pass


class TestSessionManagerDoubleStart(_TestSessionManagerDoubleStart):
    pass


class TestSessionManagerStop(_TestSessionManagerStop):
    pass


class TestGetSessionInfo(_TestGetSessionInfo):
    pass


class TestSessionManagerWithMockEngine(_TestSessionManagerWithMockEngine):
    pass
