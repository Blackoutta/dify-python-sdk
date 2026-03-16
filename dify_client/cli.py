"""Typer-based CLI for dify-client."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List

import typer
from httpx import Response
from typing_extensions import Annotated

from .client import (
    ChatClient,
    CompletionClient,
    DifyClient,
    KnowledgeBaseClient,
    WorkspaceClient,
    WorkflowClient,
)
from .exceptions import (
    APIError,
    AuthenticationError,
    DifyClientError,
    FileUploadError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

app = typer.Typer(help="CLI for the Dify Python SDK.")
app_app = typer.Typer(help="Inspect and manage application-level resources.")
files_app = typer.Typer(help="Upload files and fetch file previews.")
completion_app = typer.Typer(help="Send completion requests.")
chat_app = typer.Typer(help="Send chat requests and manage chat resources.")
workflow_app = typer.Typer(help="Run and inspect workflows.")
workspace_app = typer.Typer(help="Inspect workspace models and files.")
kb_app = typer.Typer(help="Manage datasets, documents, tags, metadata, and pipelines.")

app.add_typer(app_app, name="app")
app.add_typer(files_app, name="files")
app.add_typer(completion_app, name="completion")
app.add_typer(chat_app, name="chat")
app.add_typer(workflow_app, name="workflow")
app.add_typer(workspace_app, name="workspace")
app.add_typer(kb_app, name="kb")

site_config_app = typer.Typer(help="Read or update app site configuration.")
api_tokens_app = typer.Typer(help="Manage app API tokens.")
annotations_app = typer.Typer(help="Manage chat annotations.")
variables_app = typer.Typer(help="Manage chat conversation variables.")
draft_app = typer.Typer(help="Read or update workflow drafts.")
dataset_app = typer.Typer(help="Manage datasets.")
document_app = typer.Typer(help="Manage documents.")
segment_app = typer.Typer(help="Manage document segments.")
metadata_app = typer.Typer(help="Manage dataset metadata.")
tag_app = typer.Typer(help="Manage dataset tags.")
pipeline_app = typer.Typer(help="Run datasource and RAG pipeline operations.")

app_app.add_typer(site_config_app, name="site-config")
app_app.add_typer(api_tokens_app, name="api-tokens")
chat_app.add_typer(annotations_app, name="annotations")
chat_app.add_typer(variables_app, name="variables")
workflow_app.add_typer(draft_app, name="draft")
kb_app.add_typer(dataset_app, name="dataset")
kb_app.add_typer(document_app, name="document")
kb_app.add_typer(segment_app, name="segment")
kb_app.add_typer(metadata_app, name="metadata")
kb_app.add_typer(tag_app, name="tag")
kb_app.add_typer(pipeline_app, name="pipeline")

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "dify-client" / "config.json"

EXIT_VALIDATION = 2
EXIT_AUTH = 3
EXIT_API = 4
EXIT_NETWORK = 5
EXIT_INTERNAL = 10


@dataclass
class CLISettings:
    api_key: str
    base_url: str
    timeout: float
    enable_logging: bool
    default_user: str | None
    json_output: bool
    config_path: Path


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_config_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise typer.BadParameter("Config file must contain a JSON object.")
    return data


def _resolve_setting(
    flag_value: Any,
    env_name: str,
    config_data: Dict[str, Any],
    config_key: str,
    default: Any = None,
) -> Any:
    if flag_value is not None:
        return flag_value
    if env_name in os.environ:
        return os.environ[env_name]
    if config_key in config_data:
        return config_data[config_key]
    return default


def _require_user(settings: CLISettings, user: str | None) -> str:
    resolved = user or settings.default_user
    if resolved:
        return resolved
    raise typer.BadParameter(
        "A user is required. Pass --user or configure DIFY_USER/default_user."
    )


def _require_identifier(value: str | None, label: str) -> str:
    if value and value.strip():
        return value.strip()
    raise typer.BadParameter(f"{label} is required.")


def _parse_key_value_inputs(values: List[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise typer.BadParameter(
                f"Invalid --input value '{raw}'. Expected key=value format."
            )
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter(
                f"Invalid --input value '{raw}'. Key must not be empty."
            )
        parsed[key] = value
    return parsed


def _parse_json_object(value: str | None, option_name: str) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"{option_name} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise typer.BadParameter(f"{option_name} must decode to a JSON object.")
    return parsed


def _parse_json_array(value: str | None, option_name: str) -> List[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"{option_name} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise typer.BadParameter(f"{option_name} must decode to a JSON array.")
    return parsed


def _parse_json_value(value: str | None, option_name: str) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"{option_name} must be valid JSON: {exc}") from exc


def _build_inputs(input_values: List[str], inputs_json: str | None) -> Dict[str, Any]:
    if inputs_json:
        return _parse_json_object(inputs_json, "--inputs-json")
    return _parse_key_value_inputs(input_values)


def _guess_file_type(file_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith("image/"):
        return "image"
    if mime_type and mime_type.startswith("audio/"):
        return "audio"
    if mime_type and mime_type.startswith("video/"):
        return "video"
    return "document"


def _parse_attach_specs(values: List[str]) -> List[tuple[str, str]]:
    attachments: List[tuple[str, str]] = []
    for raw in values:
        if "=" in raw:
            file_type, path = raw.split("=", 1)
            file_type = file_type.strip()
            path = path.strip()
        else:
            path = raw.strip()
            file_type = _guess_file_type(path)
        if not path:
            raise typer.BadParameter(f"Invalid attachment '{raw}'.")
        attachments.append((file_type or _guess_file_type(path), path))
    return attachments


def _parse_file_refs(values: List[str]) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    for raw in values:
        if "=" not in raw:
            raise typer.BadParameter(
                f"Invalid --file-ref value '{raw}'. Expected type=file_id."
            )
        file_type, file_id = raw.split("=", 1)
        files.append(
            {
                "type": _require_identifier(file_type, "file type"),
                "transfer_method": "local_file",
                "upload_file_id": _require_identifier(file_id, "file id"),
            }
        )
    return files


def _parse_remote_files(values: List[str]) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    for raw in values:
        if "=" not in raw:
            raise typer.BadParameter(
                f"Invalid --remote-file-url value '{raw}'. Expected type=url."
            )
        file_type, url = raw.split("=", 1)
        files.append(
            {
                "type": _require_identifier(file_type, "file type"),
                "transfer_method": "remote_url",
                "url": _require_identifier(url, "remote file URL"),
            }
        )
    return files


def _normalize_user_input_form(
    user_input_form: Any, file_upload: Any
) -> Dict[str, Any]:
    normalized_fields = []
    if isinstance(user_input_form, list):
        for field in user_input_form:
            if not isinstance(field, dict):
                continue
            normalized_fields.append(
                {
                    "name": field.get("variable")
                    or field.get("name")
                    or field.get("field")
                    or field.get("id"),
                    "label": field.get("label") or field.get("text"),
                    "type": field.get("type"),
                    "required": bool(
                        field.get("required")
                        or field.get("is_required")
                        or field.get("required_for_user_input")
                    ),
                    "options": field.get("options") or field.get("choices"),
                    "raw": field,
                }
            )
    return {
        "fields": normalized_fields,
        "file_upload_enabled": bool(file_upload.get("enabled"))
        if isinstance(file_upload, dict)
        else False,
        "file_upload": file_upload,
    }


def _response_payload(response: Response) -> Any:
    try:
        return response.json()
    except Exception:
        text = response.text
        return {"text": text} if text else {}


def _render_data(settings: CLISettings, payload: Any) -> None:
    if settings.json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return
    if isinstance(payload, dict):
        if "answer" in payload:
            typer.echo(payload["answer"])
            return
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, list):
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo(str(payload))


def _render_binary_response(
    settings: CLISettings, response: Response, output: Path | None, label: str
) -> None:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.content)
        payload = {
            "output_path": str(output),
            "bytes_written": len(response.content),
            "content_type": response.headers.get("content-type"),
            "label": label,
        }
        _render_data(settings, payload)
        return
    payload = {
        "content_type": response.headers.get("content-type"),
        "content_base64": base64.b64encode(response.content).decode("ascii"),
        "label": label,
    }
    _render_data(settings, payload)


def _render_stream_response(settings: CLISettings, response: Response) -> None:
    for line in response.iter_lines():
        decoded = line.decode() if isinstance(line, bytes) else line
        if not decoded:
            continue
        chunk = decoded.split("data:", 1)[-1].strip()
        if not chunk:
            continue
        try:
            payload = json.loads(chunk)
        except json.JSONDecodeError:
            payload = {"event": chunk}
        if settings.json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False))
        elif isinstance(payload, dict) and "answer" in payload:
            typer.echo(payload["answer"])
        else:
            typer.echo(json.dumps(payload, ensure_ascii=False))


def _handle_cli_exception(exc: Exception) -> None:
    if isinstance(exc, typer.Exit):
        raise exc
    if isinstance(exc, typer.BadParameter):
        typer.echo(f"Validation error: {exc}", err=True)
        raise typer.Exit(EXIT_VALIDATION) from exc
    if isinstance(exc, AuthenticationError):
        typer.echo(f"Authentication error: {exc.message}", err=True)
        raise typer.Exit(EXIT_AUTH) from exc
    if isinstance(exc, (ValidationError, FileUploadError)):
        typer.echo(f"Validation error: {exc.message}", err=True)
        raise typer.Exit(EXIT_VALIDATION) from exc
    if isinstance(exc, RateLimitError):
        typer.echo(f"API error: {exc.message}", err=True)
        raise typer.Exit(EXIT_API) from exc
    if isinstance(exc, (APIError, DifyClientError)):
        typer.echo(f"API error: {getattr(exc, 'message', str(exc))}", err=True)
        raise typer.Exit(EXIT_API) from exc
    if isinstance(exc, (NetworkError, TimeoutError, OSError)):
        typer.echo(f"Network error: {exc}", err=True)
        raise typer.Exit(EXIT_NETWORK) from exc
    typer.echo(f"Internal error: {exc}", err=True)
    raise typer.Exit(EXIT_INTERNAL) from exc


def _with_error_handling(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - centralized path
            _handle_cli_exception(exc)

    return wrapper


def _settings(ctx: typer.Context) -> CLISettings:
    settings = ctx.obj
    if not isinstance(settings, CLISettings):
        raise RuntimeError("CLI context has not been initialized.")
    return settings


def _client_kwargs(settings: CLISettings) -> Dict[str, Any]:
    return {
        "api_key": settings.api_key,
        "base_url": settings.base_url,
        "timeout": settings.timeout,
        "enable_logging": settings.enable_logging,
    }


def _dify_client(settings: CLISettings) -> DifyClient:
    return DifyClient(**_client_kwargs(settings))


def _completion_client(settings: CLISettings) -> CompletionClient:
    return CompletionClient(**_client_kwargs(settings))


def _chat_client(settings: CLISettings) -> ChatClient:
    return ChatClient(**_client_kwargs(settings))


def _workflow_client(settings: CLISettings) -> WorkflowClient:
    return WorkflowClient(**_client_kwargs(settings))


def _workspace_client(settings: CLISettings) -> WorkspaceClient:
    return WorkspaceClient(**_client_kwargs(settings))


def _kb_client(settings: CLISettings, dataset_id: str | None = None) -> KnowledgeBaseClient:
    return KnowledgeBaseClient(**_client_kwargs(settings), dataset_id=dataset_id)


def _upload_inline_files(
    settings: CLISettings, user: str, attachments: List[str]
) -> List[Dict[str, Any]]:
    files = _parse_attach_specs(attachments)
    uploaded: List[Dict[str, Any]] = []
    with _dify_client(settings) as client:
        for file_type, file_path in files:
            path = Path(file_path)
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            with path.open("rb") as handle:
                response = client.file_upload(
                    user,
                    {"file": (path.name, handle, mime_type)},
                )
            payload = _response_payload(response)
            uploaded.append(
                {
                    "type": file_type,
                    "transfer_method": "local_file",
                    "upload_file_id": payload.get("id"),
                }
            )
    return uploaded


def _collect_request_files(
    settings: CLISettings,
    user: str,
    attach: List[str],
    file_refs: List[str],
    remote_file_urls: List[str],
) -> List[Dict[str, Any]]:
    files: List[Dict[str, Any]] = []
    files.extend(_parse_file_refs(file_refs))
    files.extend(_parse_remote_files(remote_file_urls))
    if attach:
        files.extend(_upload_inline_files(settings, user, attach))
    return files


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    api_key: Annotated[str | None, typer.Option("--api-key")] = None,
    base_url: Annotated[str | None, typer.Option("--base-url")] = None,
    timeout: Annotated[float | None, typer.Option("--timeout")] = None,
    enable_logging: Annotated[bool | None, typer.Option("--enable-logging")] = None,
    user: Annotated[str | None, typer.Option("--user")] = None,
    json_output: Annotated[bool | None, typer.Option("--json")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    config_path = config or Path(os.environ.get("DIFY_CONFIG", DEFAULT_CONFIG_PATH))
    config_data = _load_config_file(config_path)
    resolved_api_key = _resolve_setting(
        api_key, "DIFY_API_KEY", config_data, "api_key", None
    )
    if not resolved_api_key:
        resolved_api_key = ""
    settings = CLISettings(
        api_key=resolved_api_key,
        base_url=_resolve_setting(
            base_url, "DIFY_BASE_URL", config_data, "base_url", "https://api.dify.ai/v1"
        ),
        timeout=float(
            _resolve_setting(timeout, "DIFY_TIMEOUT", config_data, "timeout", 60.0)
        ),
        enable_logging=_coerce_bool(
            _resolve_setting(
                enable_logging, "DIFY_ENABLE_LOGGING", config_data, "enable_logging", False
            )
        ),
        default_user=_resolve_setting(user, "DIFY_USER", config_data, "default_user", None),
        json_output=_coerce_bool(
            _resolve_setting(json_output, "DIFY_OUTPUT_JSON", config_data, "json_output", False)
        ),
        config_path=config_path,
    )
    ctx.obj = settings
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("message-feedback")
@_with_error_handling
def message_feedback(
    ctx: typer.Context,
    message_id: Annotated[str, typer.Option("--message-id")],
    rating: Annotated[str, typer.Option("--rating")],
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.message_feedback(
            _require_identifier(message_id, "message_id"),
            rating,
            _require_user(settings, user),
        )
    _render_data(settings, _response_payload(response))


@app.command("audio-to-text")
@_with_error_handling
def audio_to_text(
    ctx: typer.Context,
    path: Annotated[Path, typer.Option("--path")],
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        with path.open("rb") as handle:
            response = client.audio_to_text(
                (path.name, handle), _require_user(settings, user)
            )
    _render_data(settings, _response_payload(response))


@app.command("text-to-audio")
@_with_error_handling
def text_to_audio(
    ctx: typer.Context,
    text: Annotated[str, typer.Option("--text")],
    user: Annotated[str | None, typer.Option("--user")] = None,
    streaming: Annotated[bool, typer.Option("--streaming")] = False,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.text_to_audio(text, _require_user(settings, user), streaming)
    content_type = response.headers.get("content-type", "")
    if output is not None or "audio" in content_type:
        _render_binary_response(settings, response, output, "text-to-audio")
        return
    _render_data(settings, _response_payload(response))


@app_app.command("info")
@_with_error_handling
def app_info(ctx: typer.Context) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.get_app_info()
    _render_data(settings, _response_payload(response))


@app_app.command("site-info")
@_with_error_handling
def app_site_info(ctx: typer.Context) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.get_app_site_info()
    _render_data(settings, _response_payload(response))


@app_app.command("parameters")
@_with_error_handling
def app_parameters(
    ctx: typer.Context,
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.get_application_parameters(_require_user(settings, user))
    _render_data(settings, _response_payload(response))


@app_app.command("inspect")
@_with_error_handling
def app_inspect(
    ctx: typer.Context,
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.get_application_parameters(_require_user(settings, user))
    payload = _response_payload(response)
    if isinstance(payload, dict):
        payload["normalized"] = _normalize_user_input_form(
            payload.get("user_input_form"), payload.get("file_upload")
        )
    _render_data(settings, payload)


@app_app.command("meta")
@_with_error_handling
def app_meta(
    ctx: typer.Context,
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.get_meta(_require_user(settings, user))
    _render_data(settings, _response_payload(response))


@site_config_app.command("get")
@_with_error_handling
def site_config_get(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.get_app_site_config(app_id)
    _render_data(settings, _response_payload(response))


@site_config_app.command("update")
@_with_error_handling
def site_config_update(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
    config_json: Annotated[str, typer.Option("--config-json")],
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.update_app_site_config(app_id, _parse_json_object(config_json, "--config-json"))
    _render_data(settings, _response_payload(response))


@api_tokens_app.command("list")
@_with_error_handling
def api_tokens_list(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.get_app_api_tokens(app_id)
    _render_data(settings, _response_payload(response))


@api_tokens_app.command("create")
@_with_error_handling
def api_tokens_create(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
    name: Annotated[str, typer.Option("--name")],
    description: Annotated[str | None, typer.Option("--description")] = None,
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.create_app_api_token(app_id, name, description)
    _render_data(settings, _response_payload(response))


@api_tokens_app.command("delete")
@_with_error_handling
def api_tokens_delete(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
    token_id: Annotated[str, typer.Option("--token-id")],
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.delete_app_api_token(app_id, token_id)
    _render_data(settings, _response_payload(response))


@files_app.command("upload")
@_with_error_handling
def files_upload(
    ctx: typer.Context,
    path: Annotated[Path, typer.Option("--path")],
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    resolved_user = _require_user(settings, user)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with _dify_client(settings) as client:
        with path.open("rb") as handle:
            response = client.file_upload(
                resolved_user,
                {"file": (path.name, handle, mime_type)},
            )
    _render_data(settings, _response_payload(response))


@files_app.command("preview")
@_with_error_handling
def files_preview(
    ctx: typer.Context,
    file_id: Annotated[str, typer.Option("--file-id")],
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    settings = _settings(ctx)
    with _dify_client(settings) as client:
        response = client.get_file_preview(file_id)
    content_type = response.headers.get("content-type", "")
    if output is not None or content_type.startswith(("image/", "audio/", "application/octet-stream")):
        _render_binary_response(settings, response, output, "file-preview")
        return
    _render_data(settings, _response_payload(response))


@completion_app.command("send")
@_with_error_handling
def completion_send(
    ctx: typer.Context,
    user: Annotated[str | None, typer.Option("--user")] = None,
    input_values: Annotated[List[str], typer.Option("--input")] = [],
    inputs_json: Annotated[str | None, typer.Option("--inputs-json")] = None,
    response_mode: Annotated[str, typer.Option("--response-mode")] = "blocking",
    attach: Annotated[List[str], typer.Option("--attach")] = [],
    file_refs: Annotated[List[str], typer.Option("--file-ref")] = [],
    remote_file_urls: Annotated[List[str], typer.Option("--remote-file-url")] = [],
) -> None:
    settings = _settings(ctx)
    resolved_user = _require_user(settings, user)
    inputs = _build_inputs(input_values, inputs_json)
    files = _collect_request_files(settings, resolved_user, attach, file_refs, remote_file_urls)
    with _completion_client(settings) as client:
        response = client.create_completion_message(
            inputs=inputs,
            response_mode=response_mode,
            user=resolved_user,
            files=files or None,
        )
    if response_mode == "streaming":
        _render_stream_response(settings, response)
        return
    _render_data(settings, _response_payload(response))


@chat_app.command("send")
@_with_error_handling
def chat_send(
    ctx: typer.Context,
    query: Annotated[str, typer.Option("--query")],
    user: Annotated[str | None, typer.Option("--user")] = None,
    conversation_id: Annotated[str | None, typer.Option("--conversation-id")] = None,
    input_values: Annotated[List[str], typer.Option("--input")] = [],
    inputs_json: Annotated[str | None, typer.Option("--inputs-json")] = None,
    response_mode: Annotated[str, typer.Option("--response-mode")] = "blocking",
    attach: Annotated[List[str], typer.Option("--attach")] = [],
    file_refs: Annotated[List[str], typer.Option("--file-ref")] = [],
    remote_file_urls: Annotated[List[str], typer.Option("--remote-file-url")] = [],
) -> None:
    settings = _settings(ctx)
    resolved_user = _require_user(settings, user)
    inputs = _build_inputs(input_values, inputs_json)
    files = _collect_request_files(settings, resolved_user, attach, file_refs, remote_file_urls)
    with _chat_client(settings) as client:
        response = client.create_chat_message(
            inputs=inputs,
            query=query,
            user=resolved_user,
            response_mode=response_mode,
            conversation_id=conversation_id,
            files=files or None,
        )
    if response_mode == "streaming":
        _render_stream_response(settings, response)
        return
    _render_data(settings, _response_payload(response))


@chat_app.command("suggested")
@_with_error_handling
def chat_suggested(
    ctx: typer.Context,
    message_id: Annotated[str, typer.Option("--message-id")],
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.get_suggested(message_id, _require_user(settings, user))
    _render_data(settings, _response_payload(response))


@chat_app.command("stop")
@_with_error_handling
def chat_stop(
    ctx: typer.Context,
    task_id: Annotated[str, typer.Option("--task-id")],
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.stop_message(task_id, _require_user(settings, user))
    _render_data(settings, _response_payload(response))


@chat_app.command("conversations")
@_with_error_handling
def chat_conversations(
    ctx: typer.Context,
    user: Annotated[str | None, typer.Option("--user")] = None,
    last_id: Annotated[str | None, typer.Option("--last-id")] = None,
    limit: Annotated[int | None, typer.Option("--limit")] = None,
    pinned: Annotated[bool | None, typer.Option("--pinned")] = None,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.get_conversations(
            _require_user(settings, user), last_id=last_id, limit=limit, pinned=pinned
        )
    _render_data(settings, _response_payload(response))


@chat_app.command("messages")
@_with_error_handling
def chat_messages(
    ctx: typer.Context,
    user: Annotated[str | None, typer.Option("--user")] = None,
    conversation_id: Annotated[str | None, typer.Option("--conversation-id")] = None,
    first_id: Annotated[str | None, typer.Option("--first-id")] = None,
    limit: Annotated[int | None, typer.Option("--limit")] = None,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.get_conversation_messages(
            _require_user(settings, user),
            conversation_id=conversation_id,
            first_id=first_id,
            limit=limit,
        )
    _render_data(settings, _response_payload(response))


@chat_app.command("rename-conversation")
@_with_error_handling
def chat_rename_conversation(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Option("--conversation-id")],
    name: Annotated[str, typer.Option("--name")],
    user: Annotated[str | None, typer.Option("--user")] = None,
    auto_generate: Annotated[bool, typer.Option("--auto-generate")] = False,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.rename_conversation(
            conversation_id, name, auto_generate, _require_user(settings, user)
        )
    _render_data(settings, _response_payload(response))


@chat_app.command("delete-conversation")
@_with_error_handling
def chat_delete_conversation(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Option("--conversation-id")],
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.delete_conversation(conversation_id, _require_user(settings, user))
    _render_data(settings, _response_payload(response))


@chat_app.command("annotation-reply-action")
@_with_error_handling
def chat_annotation_reply_action(
    ctx: typer.Context,
    action: Annotated[str, typer.Option("--action")],
    score_threshold: Annotated[float, typer.Option("--score-threshold")],
    embedding_provider_name: Annotated[str, typer.Option("--embedding-provider-name")],
    embedding_model_name: Annotated[str, typer.Option("--embedding-model-name")],
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.annotation_reply_action(
            action, score_threshold, embedding_provider_name, embedding_model_name
        )
    _render_data(settings, _response_payload(response))


@chat_app.command("annotation-reply-status")
@_with_error_handling
def chat_annotation_reply_status(
    ctx: typer.Context,
    action: Annotated[str, typer.Option("--action")],
    job_id: Annotated[str, typer.Option("--job-id")],
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.get_annotation_reply_status(action, job_id)
    _render_data(settings, _response_payload(response))


@annotations_app.command("list")
@_with_error_handling
def annotations_list(
    ctx: typer.Context,
    page: Annotated[int, typer.Option("--page")] = 1,
    limit: Annotated[int, typer.Option("--limit")] = 20,
    keyword: Annotated[str | None, typer.Option("--keyword")] = None,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.list_annotations(page=page, limit=limit, keyword=keyword)
    _render_data(settings, _response_payload(response))


@annotations_app.command("create")
@_with_error_handling
def annotations_create(
    ctx: typer.Context,
    question: Annotated[str, typer.Option("--question")],
    answer: Annotated[str, typer.Option("--answer")],
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.create_annotation(question, answer)
    _render_data(settings, _response_payload(response))


@annotations_app.command("update")
@_with_error_handling
def annotations_update(
    ctx: typer.Context,
    annotation_id: Annotated[str, typer.Option("--annotation-id")],
    question: Annotated[str, typer.Option("--question")],
    answer: Annotated[str, typer.Option("--answer")],
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.update_annotation(annotation_id, question, answer)
    _render_data(settings, _response_payload(response))


@annotations_app.command("delete")
@_with_error_handling
def annotations_delete(
    ctx: typer.Context,
    annotation_id: Annotated[str, typer.Option("--annotation-id")],
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.delete_annotation(annotation_id)
    _render_data(settings, _response_payload(response))


@variables_app.command("list")
@_with_error_handling
def variables_list(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Option("--conversation-id")],
    user: Annotated[str | None, typer.Option("--user")] = None,
    page: Annotated[int | None, typer.Option("--page")] = None,
    limit: Annotated[int | None, typer.Option("--limit")] = None,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        if page is not None or limit is not None:
            response = client.list_conversation_variables_with_pagination(
                conversation_id,
                _require_user(settings, user),
                page=page or 1,
                limit=limit or 20,
            )
        else:
            response = client.get_conversation_variables(
                conversation_id, _require_user(settings, user)
            )
    _render_data(settings, _response_payload(response))


@variables_app.command("update")
@_with_error_handling
def variables_update(
    ctx: typer.Context,
    conversation_id: Annotated[str, typer.Option("--conversation-id")],
    variable_id: Annotated[str, typer.Option("--variable-id")],
    user: Annotated[str | None, typer.Option("--user")] = None,
    value_json: Annotated[str, typer.Option("--value-json")] = ...,
) -> None:
    settings = _settings(ctx)
    with _chat_client(settings) as client:
        response = client.update_conversation_variable(
            conversation_id,
            variable_id,
            _parse_json_value(value_json, "--value-json"),
            _require_user(settings, user),
        )
    _render_data(settings, _response_payload(response))


@workflow_app.command("run")
@_with_error_handling
def workflow_run(
    ctx: typer.Context,
    user: Annotated[str | None, typer.Option("--user")] = None,
    input_values: Annotated[List[str], typer.Option("--input")] = [],
    inputs_json: Annotated[str | None, typer.Option("--inputs-json")] = None,
    response_mode: Annotated[str, typer.Option("--response-mode")] = "blocking",
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.run(
            inputs=_build_inputs(input_values, inputs_json),
            response_mode=response_mode,
            user=_require_user(settings, user),
        )
    if response_mode == "streaming":
        _render_stream_response(settings, response)
        return
    _render_data(settings, _response_payload(response))


@workflow_app.command("run-specific")
@_with_error_handling
def workflow_run_specific(
    ctx: typer.Context,
    workflow_id: Annotated[str, typer.Option("--workflow-id")],
    user: Annotated[str | None, typer.Option("--user")] = None,
    input_values: Annotated[List[str], typer.Option("--input")] = [],
    inputs_json: Annotated[str | None, typer.Option("--inputs-json")] = None,
    response_mode: Annotated[str, typer.Option("--response-mode")] = "blocking",
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.run_specific_workflow(
            workflow_id=workflow_id,
            inputs=_build_inputs(input_values, inputs_json),
            response_mode=response_mode,
            user=_require_user(settings, user),
        )
    if response_mode == "streaming":
        _render_stream_response(settings, response)
        return
    _render_data(settings, _response_payload(response))


@workflow_app.command("stop")
@_with_error_handling
def workflow_stop(
    ctx: typer.Context,
    task_id: Annotated[str, typer.Option("--task-id")],
    user: Annotated[str | None, typer.Option("--user")] = None,
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.stop(task_id, _require_user(settings, user))
    _render_data(settings, _response_payload(response))


@workflow_app.command("result")
@_with_error_handling
def workflow_result(
    ctx: typer.Context,
    workflow_run_id: Annotated[str, typer.Option("--workflow-run-id")],
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.get_result(workflow_run_id)
    _render_data(settings, _response_payload(response))


@workflow_app.command("logs")
@_with_error_handling
def workflow_logs(
    ctx: typer.Context,
    keyword: Annotated[str | None, typer.Option("--keyword")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    page: Annotated[int, typer.Option("--page")] = 1,
    limit: Annotated[int, typer.Option("--limit")] = 20,
    created_at_before: Annotated[str | None, typer.Option("--created-at-before")] = None,
    created_at_after: Annotated[str | None, typer.Option("--created-at-after")] = None,
    created_by_end_user_session_id: Annotated[
        str | None, typer.Option("--created-by-end-user-session-id")
    ] = None,
    created_by_account: Annotated[str | None, typer.Option("--created-by-account")] = None,
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.get_workflow_logs(
            keyword=keyword,
            status=status,
            page=page,
            limit=limit,
            created_at__before=created_at_before,
            created_at__after=created_at_after,
            created_by_end_user_session_id=created_by_end_user_session_id,
            created_by_account=created_by_account,
        )
    _render_data(settings, _response_payload(response))


@draft_app.command("get")
@_with_error_handling
def workflow_draft_get(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.get_workflow_draft(app_id)
    _render_data(settings, _response_payload(response))


@draft_app.command("update")
@_with_error_handling
def workflow_draft_update(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
    workflow_json: Annotated[str, typer.Option("--workflow-json")],
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.update_workflow_draft(
            app_id, _parse_json_object(workflow_json, "--workflow-json")
        )
    _render_data(settings, _response_payload(response))


@workflow_app.command("publish")
@_with_error_handling
def workflow_publish(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.publish_workflow(app_id)
    _render_data(settings, _response_payload(response))


@workflow_app.command("history")
@_with_error_handling
def workflow_history(
    ctx: typer.Context,
    app_id: Annotated[str, typer.Option("--app-id")],
    page: Annotated[int, typer.Option("--page")] = 1,
    limit: Annotated[int, typer.Option("--limit")] = 20,
    status: Annotated[str | None, typer.Option("--status")] = None,
) -> None:
    settings = _settings(ctx)
    with _workflow_client(settings) as client:
        response = client.get_workflow_run_history(
            app_id, page=page, limit=limit, status=status
        )
    _render_data(settings, _response_payload(response))


@workspace_app.command("models")
@_with_error_handling
def workspace_models(
    ctx: typer.Context,
    model_type: Annotated[str, typer.Option("--model-type")],
) -> None:
    settings = _settings(ctx)
    with _workspace_client(settings) as client:
        response = client.get_available_models(model_type)
    _render_data(settings, _response_payload(response))


@workspace_app.command("providers")
@_with_error_handling
def workspace_providers(ctx: typer.Context) -> None:
    settings = _settings(ctx)
    with _workspace_client(settings) as client:
        response = client.get_model_providers()
    _render_data(settings, _response_payload(response))


@workspace_app.command("provider-models")
@_with_error_handling
def workspace_provider_models(
    ctx: typer.Context,
    provider_name: Annotated[str, typer.Option("--provider-name")],
) -> None:
    settings = _settings(ctx)
    with _workspace_client(settings) as client:
        response = client.get_model_provider_models(provider_name)
    _render_data(settings, _response_payload(response))


@workspace_app.command("validate-credentials")
@_with_error_handling
def workspace_validate_credentials(
    ctx: typer.Context,
    provider_name: Annotated[str, typer.Option("--provider-name")],
    credentials_json: Annotated[str, typer.Option("--credentials-json")],
) -> None:
    settings = _settings(ctx)
    with _workspace_client(settings) as client:
        response = client.validate_model_provider_credentials(
            provider_name, _parse_json_object(credentials_json, "--credentials-json")
        )
    _render_data(settings, _response_payload(response))


@workspace_app.command("file-info")
@_with_error_handling
def workspace_file_info(
    ctx: typer.Context,
    file_id: Annotated[str, typer.Option("--file-id")],
) -> None:
    settings = _settings(ctx)
    with _workspace_client(settings) as client:
        response = client.get_file_info(file_id)
    _render_data(settings, _response_payload(response))


@workspace_app.command("file-download-url")
@_with_error_handling
def workspace_file_download_url(
    ctx: typer.Context,
    file_id: Annotated[str, typer.Option("--file-id")],
) -> None:
    settings = _settings(ctx)
    with _workspace_client(settings) as client:
        response = client.get_file_download_url(file_id)
    _render_data(settings, _response_payload(response))


@workspace_app.command("file-delete")
@_with_error_handling
def workspace_file_delete(
    ctx: typer.Context,
    file_id: Annotated[str, typer.Option("--file-id")],
) -> None:
    settings = _settings(ctx)
    with _workspace_client(settings) as client:
        response = client.delete_file(file_id)
    _render_data(settings, _response_payload(response))


@dataset_app.command("create")
@_with_error_handling
def kb_dataset_create(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings) as client:
        response = client.create_dataset(name=name)
    _render_data(settings, _response_payload(response))


@dataset_app.command("list")
@_with_error_handling
def kb_dataset_list(
    ctx: typer.Context,
    page: Annotated[int, typer.Option("--page")] = 1,
    page_size: Annotated[int, typer.Option("--page-size")] = 20,
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings) as client:
        response = client.list_datasets(page=page, page_size=page_size)
    _render_data(settings, _response_payload(response))


@dataset_app.command("get")
@_with_error_handling
def kb_dataset_get(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.get_dataset(dataset_id=dataset_id)
    _render_data(settings, _response_payload(response))


@dataset_app.command("update")
@_with_error_handling
def kb_dataset_update(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    name: Annotated[str | None, typer.Option("--name")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    indexing_technique: Annotated[str | None, typer.Option("--indexing-technique")] = None,
    embedding_model: Annotated[str | None, typer.Option("--embedding-model")] = None,
    embedding_model_provider: Annotated[
        str | None, typer.Option("--embedding-model-provider")
    ] = None,
    retrieval_model_json: Annotated[
        str | None, typer.Option("--retrieval-model-json")
    ] = None,
    extra_json: Annotated[str | None, typer.Option("--extra-json")] = None,
) -> None:
    settings = _settings(ctx)
    extra = _parse_json_object(extra_json, "--extra-json") if extra_json else {}
    retrieval_model = (
        _parse_json_object(retrieval_model_json, "--retrieval-model-json")
        if retrieval_model_json
        else None
    )
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.update_dataset(
            dataset_id=dataset_id,
            name=name,
            description=description,
            indexing_technique=indexing_technique,
            embedding_model=embedding_model,
            embedding_model_provider=embedding_model_provider,
            retrieval_model=retrieval_model,
            **extra,
        )
    _render_data(settings, _response_payload(response))


@dataset_app.command("delete")
@_with_error_handling
def kb_dataset_delete(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.delete_dataset()
    _render_data(settings, _response_payload(response))


@dataset_app.command("create-from-template")
@_with_error_handling
def kb_dataset_create_from_template(
    ctx: typer.Context,
    template_name: Annotated[str, typer.Option("--template-name")],
    name: Annotated[str, typer.Option("--name")],
    description: Annotated[str | None, typer.Option("--description")] = None,
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings) as client:
        response = client.create_dataset_from_template(template_name, name, description)
    _render_data(settings, _response_payload(response))


@dataset_app.command("duplicate")
@_with_error_handling
def kb_dataset_duplicate(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    name: Annotated[str, typer.Option("--name")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings) as client:
        response = client.duplicate_dataset(dataset_id, name)
    _render_data(settings, _response_payload(response))


@dataset_app.command("batch-document-status")
@_with_error_handling
def kb_dataset_batch_document_status(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    action: Annotated[str, typer.Option("--action")],
    document_ids_json: Annotated[str, typer.Option("--document-ids-json")],
) -> None:
    settings = _settings(ctx)
    document_ids = _parse_json_array(document_ids_json, "--document-ids-json")
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.batch_update_document_status(action, document_ids, dataset_id=dataset_id)
    _render_data(settings, _response_payload(response))


@document_app.command("create-text")
@_with_error_handling
def kb_document_create_text(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    name: Annotated[str, typer.Option("--name")],
    text: Annotated[str, typer.Option("--text")],
    extra_json: Annotated[str | None, typer.Option("--extra-json")] = None,
) -> None:
    settings = _settings(ctx)
    extra = _parse_json_object(extra_json, "--extra-json") if extra_json else None
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.create_document_by_text(name, text, extra_params=extra)
    _render_data(settings, _response_payload(response))


@document_app.command("update-text")
@_with_error_handling
def kb_document_update_text(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    document_id: Annotated[str, typer.Option("--document-id")],
    name: Annotated[str, typer.Option("--name")],
    text: Annotated[str, typer.Option("--text")],
    extra_json: Annotated[str | None, typer.Option("--extra-json")] = None,
) -> None:
    settings = _settings(ctx)
    extra = _parse_json_object(extra_json, "--extra-json") if extra_json else None
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.update_document_by_text(
            document_id, name, text, extra_params=extra
        )
    _render_data(settings, _response_payload(response))


@document_app.command("create-file")
@_with_error_handling
def kb_document_create_file(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    path: Annotated[Path, typer.Option("--path")],
    original_document_id: Annotated[
        str | None, typer.Option("--original-document-id")
    ] = None,
    extra_json: Annotated[str | None, typer.Option("--extra-json")] = None,
) -> None:
    settings = _settings(ctx)
    extra = _parse_json_object(extra_json, "--extra-json") if extra_json else None
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.create_document_by_file(
            str(path), original_document_id=original_document_id, extra_params=extra
        )
    _render_data(settings, _response_payload(response))


@document_app.command("update-file")
@_with_error_handling
def kb_document_update_file(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    document_id: Annotated[str, typer.Option("--document-id")],
    path: Annotated[Path, typer.Option("--path")],
    extra_json: Annotated[str | None, typer.Option("--extra-json")] = None,
) -> None:
    settings = _settings(ctx)
    extra = _parse_json_object(extra_json, "--extra-json") if extra_json else None
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.update_document_by_file(document_id, str(path), extra_params=extra)
    _render_data(settings, _response_payload(response))


@document_app.command("list")
@_with_error_handling
def kb_document_list(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    page: Annotated[int | None, typer.Option("--page")] = None,
    page_size: Annotated[int | None, typer.Option("--page-size")] = None,
    keyword: Annotated[str | None, typer.Option("--keyword")] = None,
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.list_documents(page=page, page_size=page_size, keyword=keyword)
    _render_data(settings, _response_payload(response))


@document_app.command("delete")
@_with_error_handling
def kb_document_delete(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    document_id: Annotated[str, typer.Option("--document-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.delete_document(document_id)
    _render_data(settings, _response_payload(response))


@document_app.command("indexing-status")
@_with_error_handling
def kb_document_indexing_status(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    batch_id: Annotated[str, typer.Option("--batch-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.batch_indexing_status(batch_id)
    _render_data(settings, _response_payload(response))


@segment_app.command("add")
@_with_error_handling
def kb_segment_add(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    document_id: Annotated[str, typer.Option("--document-id")],
    segments_json: Annotated[str, typer.Option("--segments-json")],
) -> None:
    settings = _settings(ctx)
    segments = _parse_json_array(segments_json, "--segments-json")
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.add_segments(document_id, segments)
    _render_data(settings, _response_payload(response))


@segment_app.command("query")
@_with_error_handling
def kb_segment_query(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    document_id: Annotated[str, typer.Option("--document-id")],
    keyword: Annotated[str | None, typer.Option("--keyword")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    params_json: Annotated[str | None, typer.Option("--params-json")] = None,
) -> None:
    settings = _settings(ctx)
    extra_params = _parse_json_object(params_json, "--params-json") if params_json else None
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.query_segments(
            document_id, keyword=keyword, status=status, params=extra_params or {}
        )
    _render_data(settings, _response_payload(response))


@segment_app.command("update")
@_with_error_handling
def kb_segment_update(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    document_id: Annotated[str, typer.Option("--document-id")],
    segment_id: Annotated[str, typer.Option("--segment-id")],
    segment_json: Annotated[str, typer.Option("--segment-json")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.update_document_segment(
            document_id, segment_id, _parse_json_object(segment_json, "--segment-json")
        )
    _render_data(settings, _response_payload(response))


@segment_app.command("delete")
@_with_error_handling
def kb_segment_delete(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    document_id: Annotated[str, typer.Option("--document-id")],
    segment_id: Annotated[str, typer.Option("--segment-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.delete_document_segment(document_id, segment_id)
    _render_data(settings, _response_payload(response))


@metadata_app.command("hit-test")
@_with_error_handling
def kb_metadata_hit_test(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    query: Annotated[str, typer.Option("--query")],
    retrieval_model_json: Annotated[
        str | None, typer.Option("--retrieval-model-json")
    ] = None,
    external_retrieval_model_json: Annotated[
        str | None, typer.Option("--external-retrieval-model-json")
    ] = None,
) -> None:
    settings = _settings(ctx)
    retrieval_model = (
        _parse_json_object(retrieval_model_json, "--retrieval-model-json")
        if retrieval_model_json
        else None
    )
    external_retrieval_model = (
        _parse_json_object(
            external_retrieval_model_json, "--external-retrieval-model-json"
        )
        if external_retrieval_model_json
        else None
    )
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.hit_testing(
            query,
            retrieval_model=retrieval_model,
            external_retrieval_model=external_retrieval_model,
        )
    _render_data(settings, _response_payload(response))


@metadata_app.command("get")
@_with_error_handling
def kb_metadata_get(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.get_dataset_metadata()
    _render_data(settings, _response_payload(response))


@metadata_app.command("create")
@_with_error_handling
def kb_metadata_create(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    metadata_json: Annotated[str, typer.Option("--metadata-json")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.create_dataset_metadata(
            _parse_json_object(metadata_json, "--metadata-json")
        )
    _render_data(settings, _response_payload(response))


@metadata_app.command("update")
@_with_error_handling
def kb_metadata_update(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    metadata_id: Annotated[str, typer.Option("--metadata-id")],
    metadata_json: Annotated[str, typer.Option("--metadata-json")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.update_dataset_metadata(
            metadata_id, _parse_json_object(metadata_json, "--metadata-json")
        )
    _render_data(settings, _response_payload(response))


@metadata_app.command("built-in-get")
@_with_error_handling
def kb_metadata_built_in_get(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.get_built_in_metadata()
    _render_data(settings, _response_payload(response))


@metadata_app.command("built-in-manage")
@_with_error_handling
def kb_metadata_built_in_manage(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    action: Annotated[str, typer.Option("--action")],
    metadata_json: Annotated[str | None, typer.Option("--metadata-json")] = None,
) -> None:
    settings = _settings(ctx)
    payload = _parse_json_object(metadata_json, "--metadata-json") if metadata_json else None
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.manage_built_in_metadata(action, payload)
    _render_data(settings, _response_payload(response))


@metadata_app.command("update-documents")
@_with_error_handling
def kb_metadata_update_documents(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    operation_data_json: Annotated[str, typer.Option("--operation-data-json")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.update_documents_metadata(
            _parse_json_array(operation_data_json, "--operation-data-json")
        )
    _render_data(settings, _response_payload(response))


@tag_app.command("list-all")
@_with_error_handling
def kb_tag_list_all(ctx: typer.Context, dataset_id: Annotated[str | None, typer.Option("--dataset-id")] = None) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.list_dataset_tags()
    _render_data(settings, _response_payload(response))


@tag_app.command("bind")
@_with_error_handling
def kb_tag_bind(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    tag_ids_json: Annotated[str, typer.Option("--tag-ids-json")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.bind_dataset_tags(_parse_json_array(tag_ids_json, "--tag-ids-json"))
    _render_data(settings, _response_payload(response))


@tag_app.command("unbind")
@_with_error_handling
def kb_tag_unbind(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    tag_id: Annotated[str, typer.Option("--tag-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.unbind_dataset_tag(tag_id)
    _render_data(settings, _response_payload(response))


@tag_app.command("list")
@_with_error_handling
def kb_tag_list(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.get_dataset_tags()
    _render_data(settings, _response_payload(response))


@pipeline_app.command("datasource-plugins")
@_with_error_handling
def kb_pipeline_datasource_plugins(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    is_published: Annotated[bool, typer.Option("--is-published")] = True,
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.get_datasource_plugins(is_published=is_published)
    _render_data(settings, _response_payload(response))


@pipeline_app.command("run-datasource-node")
@_with_error_handling
def kb_pipeline_run_datasource_node(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    node_id: Annotated[str, typer.Option("--node-id")],
    datasource_type: Annotated[str, typer.Option("--datasource-type")],
    inputs_json: Annotated[str, typer.Option("--inputs-json")],
    is_published: Annotated[bool, typer.Option("--is-published")] = True,
    credential_id: Annotated[str | None, typer.Option("--credential-id")] = None,
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.run_datasource_node(
            node_id=node_id,
            inputs=_parse_json_object(inputs_json, "--inputs-json"),
            datasource_type=datasource_type,
            is_published=is_published,
            credential_id=credential_id,
        )
    _render_stream_response(settings, response)


@pipeline_app.command("run")
@_with_error_handling
def kb_pipeline_run(
    ctx: typer.Context,
    dataset_id: Annotated[str, typer.Option("--dataset-id")],
    datasource_type: Annotated[str, typer.Option("--datasource-type")],
    start_node_id: Annotated[str, typer.Option("--start-node-id")],
    inputs_json: Annotated[str, typer.Option("--inputs-json")],
    datasource_info_list_json: Annotated[
        str, typer.Option("--datasource-info-list-json")
    ],
    is_published: Annotated[bool, typer.Option("--is-published")] = True,
    response_mode: Annotated[str, typer.Option("--response-mode")] = "blocking",
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings, dataset_id=dataset_id) as client:
        response = client.run_rag_pipeline(
            inputs=_parse_json_object(inputs_json, "--inputs-json"),
            datasource_type=datasource_type,
            datasource_info_list=_parse_json_array(
                datasource_info_list_json, "--datasource-info-list-json"
            ),
            start_node_id=start_node_id,
            is_published=is_published,
            response_mode=response_mode,
        )
    if response_mode == "streaming":
        _render_stream_response(settings, response)
        return
    _render_data(settings, _response_payload(response))


@pipeline_app.command("upload-file")
@_with_error_handling
def kb_pipeline_upload_file(
    ctx: typer.Context,
    path: Annotated[Path, typer.Option("--path")],
) -> None:
    settings = _settings(ctx)
    with _kb_client(settings) as client:
        response = client.upload_pipeline_file(str(path))
    _render_data(settings, _response_payload(response))


if __name__ == "__main__":  # pragma: no cover
    app()
