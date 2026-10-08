"""Tests for Chrome downloader companion."""
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bridge"))
import server

class TestBridge(unittest.TestCase):
    def test_url_validation(self):
        self.assertEqual(server.check_url("https://example.com/media"), "https://example.com/media")
        for value in ["file:///tmp/a", "javascript:alert(1)", "ftp://example.com/a",
                      "http://localhost/a", "http://127.0.0.1/a", "", 123]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                server.check_url(value)

    def test_inspect(self):
        raw = json.dumps({"title":"Sample", "extractor_key":"Generic", "formats":[
            {"height":1080,"vcodec":"avc1"}, {"height":720,"vcodec":"avc1"},
            {"height":1080,"vcodec":"avc1"}, {"height":None,"vcodec":"none"}]})
        fake = type("Result",(),{"returncode":0,"stdout":raw,"stderr":""})()
        with patch.object(server.subprocess,"run",return_value=fake):
            data = server.inspect("https://example.com/a")
        self.assertEqual(data["heights"],[1080,720])
        self.assertEqual(data["title"],"Sample")

    def test_inspect_failure(self):
        fake = type("Result",(),{"returncode":1,"stdout":"","stderr":"unsupported"})()
        with patch.object(server.subprocess,"run",return_value=fake):
            with self.assertRaisesRegex(ValueError,"unsupported"):
                server.inspect("https://example.com/a")

    def test_origin(self):
        self.assertTrue(server.ORIGIN.fullmatch("chrome-extension://" + "a"*32))
        self.assertFalse(server.ORIGIN.fullmatch("https://example.com"))
        self.assertFalse(server.ORIGIN.fullmatch("chrome-extension://" + "z"*32))

if __name__ == "__main__":
    unittest.main()
