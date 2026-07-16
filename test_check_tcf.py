import unittest
from unittest.mock import Mock, patch

import requests

from check_tcf import ERROR_EXIT_CODE, fetch_page_html, find_available_exam_rows, main


def exam_row(status_html: str) -> str:
    return f"""
    <table>
      <tr class="tableRow">
        <td><span class="es-exam-title">TCF Canada - July 15</span></td>
        <td>{status_html}</td>
      </tr>
    </table>
    """


class TcfMonitorTests(unittest.TestCase):
    def test_sold_out_and_closed_rows_do_not_alert(self) -> None:
        html = exam_row(
            '<span class="es-sold-out">SOLD OUT!</span>'
            '<span class="es-status es-status-closed">Closed</span>'
        )
        self.assertEqual(find_available_exam_rows(html), [])

    def test_available_status_alerts_for_that_row(self) -> None:
        html = exam_row(
            '<span class="es-status es-status-available">Available</span>'
        )
        self.assertEqual(
            find_available_exam_rows(html),
            ["TCF Canada - July 15 — status: Available"],
        )

    def test_register_control_alerts_for_that_row(self) -> None:
        html = exam_row('<a href="/register">Register now</a>')
        self.assertEqual(
            find_available_exam_rows(html),
            ["TCF Canada - July 15 — booking action: Register now"],
        )

    def test_static_page_help_text_does_not_alert(self) -> None:
        html = "<p>Register online when new dates become available.</p>"
        self.assertEqual(find_available_exam_rows(html), [])

    def test_fetch_error_uses_distinct_exit_code(self) -> None:
        with patch(
            "check_tcf.fetch_page_html",
            side_effect=requests.Timeout("test timeout"),
        ):
            self.assertEqual(main(), ERROR_EXIT_CODE)

    @patch("check_tcf.time.sleep")
    @patch("check_tcf.requests.get")
    def test_fetch_retries_transient_connection_error(
        self,
        mock_get: Mock,
        mock_sleep: Mock,
    ) -> None:
        response = Mock(status_code=200, text="<html>ok</html>")
        mock_get.side_effect = [requests.ConnectionError("connection refused"), response]

        self.assertEqual(fetch_page_html("https://example.com"), "<html>ok</html>")
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
