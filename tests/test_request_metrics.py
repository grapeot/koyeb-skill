"""Offline tests for preserving metric nulls, labels, and transport boundaries."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import request_metrics as metrics


class MetricsTests(unittest.TestCase):
    args = ["--service-id", "example-service-id", "--start", "2026-01-01T00:00:00Z", "--end", "2026-01-15T00:00:00Z"]

    def invoke(self, args=None, body=None, error=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        encoded = json.dumps(body if body is not None else {"metrics": []}).encode()
        with patch.object(metrics, "read_env", return_value={"KOYEB_API_KEY": "example-management-token"}), \
             patch.object(metrics, "resolve_token", return_value="example-management-token"), \
             patch.object(metrics.urllib.request, "urlopen") as opened, \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            if error:
                opened.side_effect = error
            else:
                opened.return_value.__enter__.return_value.read.return_value = encoded
            code = metrics.main(self.args if args is None else args)
        return code, stdout.getvalue(), stderr.getvalue(), opened

    def test_null_zero_positive_and_series_labels_are_preserved(self):
        body = {"metrics": [{"labels": {"code": "2xx", "service_id": "example-service-id"},
                             "samples": [{"timestamp": "2026-01-01T00:00:00Z", "value": None},
                                         {"timestamp": "2026-01-01T01:00:00Z", "value": 0},
                                         {"timestamp": "2026-01-01T02:00:00Z", "value": 3}]}]}
        code, out, err, opened = self.invoke(body=body)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out), body)
        request = opened.call_args.args[0]
        parsed = urllib.parse.urlparse(request.full_url)
        self.assertEqual(parsed.scheme + "://" + parsed.netloc + parsed.path, "https://app.koyeb.com/v1/streams/metrics")
        self.assertEqual(urllib.parse.parse_qs(parsed.query)["name"], ["HTTP_THROUGHPUT"])
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Bearer example-management-token")
        self.assertNotIn("example-management-token", out + err + request.full_url)

    def test_duration_step_forwarded_without_numeric_coercion(self):
        code, _, err, opened = self.invoke(args=self.args + ["--step", "5m"])
        self.assertEqual(code, 0, err)
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlparse(opened.call_args.args[0].full_url).query)["step"], ["5m"])

    def test_invalid_time_and_range_stop_before_network(self):
        for args in [self.args[:-1] + ["2025-12-31T00:00:00Z"],
                     ["--service-id", "example-service-id", "--start", "2026-01-01", "--end", "2026-01-15T00:00:00Z"]]:
            code, out, _, opened = self.invoke(args=args)
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            opened.assert_not_called()

    def test_http_error_reports_status_not_sensitive_body(self):
        error = urllib.error.HTTPError("https://example.com", 503, "example-management-token", {}, io.BytesIO(b"example-management-token"))
        code, out, err, _ = self.invoke(error=error)
        self.assertEqual(code, 1)
        self.assertIn("503", err)
        self.assertEqual(out, "")
        self.assertNotIn("example-management-token", err)

    def test_missing_metric_schema_is_not_fabricated_zero(self):
        code, out, err, _ = self.invoke(body={"unexpected": []})
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("unexpected JSON response", err)


if __name__ == "__main__":
    unittest.main()
