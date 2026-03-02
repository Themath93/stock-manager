from tests.slack_bot.test_formatters import TestFormatConfig as _TestFormatConfig
from tests.slack_bot.test_formatters import TestFormatError as _TestFormatError
from tests.slack_bot.test_formatters import TestFormatHelp as _TestFormatHelp
from tests.slack_bot.test_formatters import TestFormatStarted as _TestFormatStarted
from tests.slack_bot.test_formatters import TestFormatStatus as _TestFormatStatus
from tests.slack_bot.test_formatters import TestFormatStopped as _TestFormatStopped
from tests.slack_bot.test_formatters import TestFormatUptime as _TestFormatUptime


class TestFormatUptime(_TestFormatUptime):
    pass


class TestFormatStarted(_TestFormatStarted):
    pass


class TestFormatError(_TestFormatError):
    pass


class TestFormatStatus(_TestFormatStatus):
    pass


class TestFormatHelp(_TestFormatHelp):
    pass


class TestFormatStopped(_TestFormatStopped):
    pass


class TestFormatConfig(_TestFormatConfig):
    pass
