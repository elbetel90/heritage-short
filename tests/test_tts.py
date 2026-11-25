import unittest

from pipeline.http import HTTPError
from pipeline.tts import _retry_after


class RetryAfterTests(unittest.TestCase):
    def test_minute_limit_waits_the_stated_seconds(self):
        error = HTTPError(429, "Rate limit exceeded. Please retry in 45s.")
        self.assertEqual(_retry_after(error), 46.0)

    def test_daily_limit_is_not_retried(self):
        error = HTTPError(429, "limit: 10 requests per day. Please retry in 11h20m59s.")
        self.assertIsNone(_retry_after(error))
