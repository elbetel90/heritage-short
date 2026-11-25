import json
import pathlib
import tempfile
import unittest

from pipeline.log import append


class LogTests(unittest.TestCase):
    def test_redacts_planted_secret(self):
        secret = "super-secret-token"
        directory = tempfile.mkdtemp()
        path = pathlib.Path(directory) / "runs.jsonl"
        append(
            path,
            {
                "stage": "smoke",
                "model": "test",
                "parameters": {"api_key": secret, "note": "token is " + secret},
                "cost": 0,
                "status": "ok",
            },
            [secret],
        )
        text = path.read_text(encoding="utf-8")
        self.assertNotIn(secret, text)
        row = json.loads(text)
        self.assertEqual(row["parameters"]["api_key"], "[redacted]")
        self.assertIn("[redacted]", row["parameters"]["note"])
        self.assertEqual(row["cost"], 0)


if __name__ == "__main__":
    unittest.main()
