import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from dify_client.cli import EXIT_VALIDATION, app
from dify_client.cli_mapping import METHOD_TO_COMMAND
from dify_client.client import (
    ChatClient,
    CompletionClient,
    DifyClient,
    KnowledgeBaseClient,
    WorkspaceClient,
    WorkflowClient,
)


def make_response(payload=None, *, text=None, headers=None, lines=None, content=None):
    response = MagicMock()
    response.headers = headers or {"content-type": "application/json"}
    response.json.return_value = payload if payload is not None else {}
    response.text = text if text is not None else json.dumps(payload or {})
    response.content = content if content is not None else response.text.encode("utf-8")
    response.iter_lines.return_value = lines or []
    return response


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_root_help_lists_command_groups(self):
        result = self.runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        for group in ["app", "files", "completion", "chat", "workflow", "workspace", "kb"]:
            self.assertIn(group, result.stdout)

    @patch("dify_client.cli.DifyClient")
    def test_config_precedence_prefers_flag_over_env_and_config(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.get_app_info.return_value = make_response({"name": "demo"})
        mock_client_cls.return_value = mock_client

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "api_key": "config-key",
                        "base_url": "https://config.example/v1",
                        "timeout": 11,
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["DIFY_API_KEY"] = "env-key"
            result = self.runner.invoke(
                app,
                [
                    "--config",
                    str(config_path),
                    "--api-key",
                    "flag-key",
                    "app",
                    "info",
                ],
                env=env,
            )

        self.assertEqual(result.exit_code, 0)
        mock_client_cls.assert_called_once()
        self.assertEqual(mock_client_cls.call_args.kwargs["api_key"], "flag-key")
        self.assertEqual(
            mock_client_cls.call_args.kwargs["base_url"], "https://config.example/v1"
        )
        self.assertEqual(mock_client_cls.call_args.kwargs["timeout"], 11.0)

    @patch("dify_client.cli.ChatClient")
    def test_chat_send_uses_string_inputs_and_explicit_conversation_id(
        self, mock_chat_cls
    ):
        mock_chat = MagicMock()
        mock_chat.__enter__.return_value = mock_chat
        mock_chat.__exit__.return_value = False
        mock_chat.create_chat_message.return_value = make_response(
            {"answer": "ok", "conversation_id": "conv-123"}
        )
        mock_chat_cls.return_value = mock_chat

        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "--json",
                "chat",
                "send",
                "--user",
                "demo-user",
                "--conversation-id",
                "conv-123",
                "--query",
                "hello",
                "--input",
                "days=3",
                "--input",
                "budget=low",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["conversation_id"], "conv-123")
        kwargs = mock_chat.create_chat_message.call_args.kwargs
        self.assertEqual(kwargs["inputs"], {"days": "3", "budget": "low"})
        self.assertEqual(kwargs["conversation_id"], "conv-123")

    @patch("dify_client.cli.ChatClient")
    @patch("dify_client.cli.DifyClient")
    def test_chat_send_attach_uploads_then_sends(self, mock_dify_cls, mock_chat_cls):
        mock_uploader = MagicMock()
        mock_uploader.__enter__.return_value = mock_uploader
        mock_uploader.__exit__.return_value = False
        mock_uploader.file_upload.return_value = make_response({"id": "file-123"})
        mock_dify_cls.return_value = mock_uploader

        mock_chat = MagicMock()
        mock_chat.__enter__.return_value = mock_chat
        mock_chat.__exit__.return_value = False
        mock_chat.create_chat_message.return_value = make_response({"answer": "ok"})
        mock_chat_cls.return_value = mock_chat

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "photo.png"
            file_path.write_bytes(b"fake-image")
            result = self.runner.invoke(
                app,
                [
                    "--api-key",
                    "test-key",
                    "chat",
                    "send",
                    "--user",
                    "demo-user",
                    "--query",
                    "describe",
                    "--attach",
                    str(file_path),
                ],
            )

        self.assertEqual(result.exit_code, 0)
        files = mock_chat.create_chat_message.call_args.kwargs["files"]
        self.assertEqual(files[0]["upload_file_id"], "file-123")
        self.assertEqual(files[0]["type"], "image")

    @patch("dify_client.cli.ChatClient")
    def test_chat_send_streaming_json_emits_one_event_per_line(self, mock_chat_cls):
        mock_chat = MagicMock()
        mock_chat.__enter__.return_value = mock_chat
        mock_chat.__exit__.return_value = False
        mock_chat.create_chat_message.return_value = make_response(
            {"ignored": True},
            lines=[b'data: {"answer":"hi"}', b'data: {"answer":"there"}'],
        )
        mock_chat_cls.return_value = mock_chat

        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "--json",
                "chat",
                "send",
                "--user",
                "demo-user",
                "--query",
                "hello",
                "--response-mode",
                "streaming",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        lines = [json.loads(line) for line in result.stdout.strip().splitlines()]
        self.assertEqual(lines, [{"answer": "hi"}, {"answer": "there"}])

    def test_invalid_inputs_json_exits_with_validation_code(self):
        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "chat",
                "send",
                "--user",
                "demo-user",
                "--query",
                "hello",
                "--inputs-json",
                "{bad-json",
            ],
        )

        self.assertEqual(result.exit_code, EXIT_VALIDATION)
        self.assertIn("Validation error", result.stderr)

    @patch("dify_client.cli.DifyClient")
    def test_app_inspect_json_includes_normalized_schema(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.get_application_parameters.return_value = make_response(
            {
                "user_input_form": [
                    {"variable": "destination", "label": "Destination", "required": True}
                ],
                "file_upload": {"enabled": True},
            }
        )
        mock_client_cls.return_value = mock_client

        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "--json",
                "app",
                "inspect",
                "--user",
                "demo-user",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["normalized"]["file_upload_enabled"])
        self.assertEqual(payload["normalized"]["fields"][0]["name"], "destination")

    @patch("dify_client.cli.WorkflowClient")
    def test_workflow_run_passes_typed_inputs_json(self, mock_workflow_cls):
        mock_workflow = MagicMock()
        mock_workflow.__enter__.return_value = mock_workflow
        mock_workflow.__exit__.return_value = False
        mock_workflow.run.return_value = make_response({"data": {"outputs": {"ok": True}}})
        mock_workflow_cls.return_value = mock_workflow

        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "--json",
                "workflow",
                "run",
                "--user",
                "demo-user",
                "--inputs-json",
                '{"days":3,"family":true}',
            ],
        )

        self.assertEqual(result.exit_code, 0)
        kwargs = mock_workflow.run.call_args.kwargs
        self.assertEqual(kwargs["inputs"], {"days": 3, "family": True})

    @patch("dify_client.cli.WorkspaceClient")
    def test_workspace_validate_credentials_accepts_json(self, mock_workspace_cls):
        mock_workspace = MagicMock()
        mock_workspace.__enter__.return_value = mock_workspace
        mock_workspace.__exit__.return_value = False
        mock_workspace.validate_model_provider_credentials.return_value = make_response(
            {"valid": True}
        )
        mock_workspace_cls.return_value = mock_workspace

        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "--json",
                "workspace",
                "validate-credentials",
                "--provider-name",
                "openai",
                "--credentials-json",
                '{"api_key":"secret"}',
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            mock_workspace.validate_model_provider_credentials.call_args.args[1],
            {"api_key": "secret"},
        )

    @patch("dify_client.cli.KnowledgeBaseClient")
    def test_kb_dataset_update_merges_retrieval_and_extra_json(self, mock_kb_cls):
        mock_kb = MagicMock()
        mock_kb.__enter__.return_value = mock_kb
        mock_kb.__exit__.return_value = False
        mock_kb.update_dataset.return_value = make_response({"ok": True})
        mock_kb_cls.return_value = mock_kb

        result = self.runner.invoke(
            app,
            [
                "--api-key",
                "test-key",
                "kb",
                "dataset",
                "update",
                "--dataset-id",
                "ds-1",
                "--name",
                "Updated",
                "--retrieval-model-json",
                '{"top_k": 5}',
                "--extra-json",
                '{"permission":"only_me"}',
            ],
        )

        self.assertEqual(result.exit_code, 0)
        kwargs = mock_kb.update_dataset.call_args.kwargs
        self.assertEqual(kwargs["retrieval_model"], {"top_k": 5})
        self.assertEqual(kwargs["permission"], "only_me")

    def test_method_to_command_mapping_covers_public_sync_methods(self):
        classes = [
            DifyClient,
            CompletionClient,
            ChatClient,
            WorkflowClient,
            WorkspaceClient,
            KnowledgeBaseClient,
        ]
        missing = []
        for cls in classes:
            for name, value in cls.__dict__.items():
                if name.startswith("_") or name == "close" or not callable(value):
                    continue
                key = f"{cls.__name__}.{name}"
                if key not in METHOD_TO_COMMAND:
                    missing.append(key)
        self.assertEqual(missing, [])
