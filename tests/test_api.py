import json
import socket
import pytest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient

# conftest.py adds api/ to sys.path so `import api` loads api/api.py
import api as api_module
from api import app, send_msg

client = TestClient(app)


def _mock_socket():
    mock_sock = MagicMock()
    return mock_sock


# ---------------------------------------------------------------------------
# send_msg unit tests
# ---------------------------------------------------------------------------


class TestSendMsg:
    def test_default_decoder_is_wazuh_aws(self):
        with patch("api.socket.socket") as MockSocket:
            MockSocket.return_value = _mock_socket()
            result = send_msg({"event": "test"})

        assert result == {"reply": "saved"}
        sent = MockSocket.return_value.send.call_args[0][0].decode()
        assert sent.startswith("1:Wazuh-AWS:")

    def test_custom_decoder_field_overrides_header(self):
        with patch("api.socket.socket") as MockSocket:
            MockSocket.return_value = _mock_socket()
            result = send_msg({"decoder": "my-app", "event": "test"})

        assert result == {"reply": "saved"}
        sent = MockSocket.return_value.send.call_args[0][0].decode()
        assert sent.startswith("1:my-app:")

    def test_ingest_field_is_added_to_payload(self):
        with patch("api.socket.socket") as MockSocket:
            MockSocket.return_value = _mock_socket()
            send_msg({"event": "test"})

        sent = MockSocket.return_value.send.call_args[0][0].decode()
        # wire format: "1:HEADER:{json}"
        payload = json.loads(sent.split(":", 2)[2])
        assert payload["ingest"] == "api"

    def test_connects_to_wazuh_unix_socket_path(self):
        with patch("api.socket.socket") as MockSocket:
            MockSocket.return_value = _mock_socket()
            send_msg({"event": "test"})

        MockSocket.return_value.connect.assert_called_once_with(
            "/var/ossec/queue/sockets/queue"
        )

    def test_wazuh_not_running_errno_111(self):
        with patch("api.socket.socket") as MockSocket:
            mock_sock = _mock_socket()
            MockSocket.return_value = mock_sock
            err = socket.error()
            err.errno = 111
            mock_sock.connect.side_effect = err

            result = send_msg({"event": "test"})

        assert result == {"reply": "Wazuh must be running."}

    def test_message_too_long_errno_90_returns_none(self):
        with patch("api.socket.socket") as MockSocket:
            mock_sock = _mock_socket()
            MockSocket.return_value = mock_sock
            err = socket.error()
            err.errno = 90
            mock_sock.send.side_effect = err

            result = send_msg({"event": "test"})

        assert result is None

    def test_other_socket_error_returns_error_reply(self):
        with patch("api.socket.socket") as MockSocket:
            mock_sock = _mock_socket()
            MockSocket.return_value = mock_sock
            err = socket.error()
            err.errno = 99  # some other error
            mock_sock.connect.side_effect = err

            result = send_msg({"event": "test"})

        assert result == {"reply": "Error sending message to wazuh"}

    def test_non_socket_exception_returns_error_reply(self):
        with patch("api.socket.socket") as MockSocket:
            mock_sock = _mock_socket()
            MockSocket.return_value = mock_sock
            mock_sock.connect.side_effect = RuntimeError("unexpected")

            result = send_msg({"event": "test"})

        assert result == {"reply": "Error sending message to wazuh"}

    def test_socket_is_closed_after_send(self):
        with patch("api.socket.socket") as MockSocket:
            mock_sock = _mock_socket()
            MockSocket.return_value = mock_sock
            send_msg({"event": "test"})

        mock_sock.close.assert_called_once()

    def test_message_body_is_valid_json(self):
        with patch("api.socket.socket") as MockSocket:
            MockSocket.return_value = _mock_socket()
            send_msg({"key": "value", "num": 42})

        sent = MockSocket.return_value.send.call_args[0][0].decode()
        raw_json = sent.split(":", 2)[2]
        parsed = json.loads(raw_json)
        assert parsed["key"] == "value"
        assert parsed["num"] == 42


# ---------------------------------------------------------------------------
# PUT / endpoint tests
# ---------------------------------------------------------------------------


class TestSingleEventEndpoint:
    def test_valid_json_is_forwarded_to_send_msg(self):
        payload = {"event": "login", "user": "admin"}
        with patch("api.send_msg", return_value={"reply": "saved"}) as mock_send:
            response = client.put("/", json=payload)

        assert response.status_code == 200
        assert response.json() == {"reply": "saved"}
        mock_send.assert_called_once_with(payload)

    def test_invalid_json_returns_error_message(self):
        response = client.put(
            "/",
            content=b"not { valid } json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert "not valid json" in response.json()["reply"].lower()

    def test_empty_object_is_accepted(self):
        with patch("api.send_msg", return_value={"reply": "saved"}):
            response = client.put("/", json={})

        assert response.status_code == 200

    def test_wazuh_not_running_propagates_reply(self):
        with patch("api.send_msg", return_value={"reply": "Wazuh must be running."}):
            response = client.put("/", json={"event": "x"})

        assert response.status_code == 200
        assert response.json() == {"reply": "Wazuh must be running."}


# ---------------------------------------------------------------------------
# PUT /batch endpoint tests
# ---------------------------------------------------------------------------


class TestBatchEndpoint:
    def test_each_event_in_array_is_sent_individually(self):
        events = [{"event": "a"}, {"event": "b"}, {"event": "c"}]
        with patch("api.send_msg", return_value={"reply": "saved"}) as mock_send:
            response = client.put("/batch", json=events)

        assert response.status_code == 200
        assert response.json() == {"reply": "batch data has bean added"}
        assert mock_send.call_count == 3

    def test_send_msg_called_with_correct_items(self):
        events = [{"event": "x", "id": 1}, {"event": "y", "id": 2}]
        with patch("api.send_msg", return_value={"reply": "saved"}) as mock_send:
            client.put("/batch", json=events)

        mock_send.assert_any_call({"event": "x", "id": 1})
        mock_send.assert_any_call({"event": "y", "id": 2})

    def test_invalid_json_returns_error_message(self):
        response = client.put(
            "/batch",
            content=b"not { valid } json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert "not valid json" in response.json()["reply"].lower()

    def test_empty_array_sends_nothing(self):
        with patch("api.send_msg") as mock_send:
            response = client.put("/batch", json=[])

        assert response.status_code == 200
        mock_send.assert_not_called()

    def test_single_item_batch(self):
        with patch("api.send_msg", return_value={"reply": "saved"}) as mock_send:
            response = client.put("/batch", json=[{"event": "solo"}])

        assert response.status_code == 200
        mock_send.assert_called_once_with({"event": "solo"})
