## ADDED Requirements

### Requirement: Workspace commands cover model and file management operations
The CLI SHALL provide commands for `get_available_models`, `get_model_providers`, `get_model_provider_models`, `validate_model_provider_credentials`, `get_file_info`, `get_file_download_url`, and `delete_file`, with one canonical command for duplicate workspace methods.

#### Scenario: Model discovery is grouped by provider and model type
- **WHEN** a user queries available models or providers
- **THEN** the CLI exposes commands and flags that distinguish model type lookups from provider-specific model listings

#### Scenario: Provider credential validation accepts structured JSON
- **WHEN** a user validates model provider credentials
- **THEN** the CLI accepts the credential payload through JSON input and returns the API validation result unchanged in JSON mode

### Requirement: Knowledge-base dataset commands cover lifecycle management
The CLI SHALL provide commands for dataset creation, listing, retrieval, update, deletion, creation from template, duplication, and batch document status changes.

#### Scenario: Dataset-scoped commands accept explicit dataset identifiers
- **WHEN** a knowledge-base command operates on an existing dataset
- **THEN** the CLI requires `--dataset-id` or an equivalent explicit identifier rather than relying on hidden process state

#### Scenario: Dataset update sends only requested fields
- **WHEN** a user updates a dataset with a subset of editable properties
- **THEN** the CLI constructs a partial update payload without forcing unrelated fields into the request

### Requirement: Knowledge-base document commands support text and file ingestion
The CLI SHALL provide commands for `create_document_by_text`, `update_document_by_text`, `create_document_by_file`, `update_document_by_file`, `list_documents`, `delete_document`, and `batch_indexing_status`, including support for extra JSON parameters used by indexing and processing rules.

#### Scenario: Text document creation merges extra JSON parameters
- **WHEN** a user creates or updates a text-backed document with extra processing parameters
- **THEN** the CLI merges the provided JSON into the request payload alongside the required text fields

#### Scenario: File document creation sends multipart data correctly
- **WHEN** a user creates or updates a file-backed document
- **THEN** the CLI opens the file path, sends multipart upload data through the SDK helper, and preserves optional original-document replacement fields when provided

### Requirement: Knowledge-base segment commands cover full segment lifecycle
The CLI SHALL provide commands for `add_segments`, `query_segments`, `update_document_segment`, and `delete_document_segment`.

#### Scenario: Segment add accepts structured segment lists
- **WHEN** a user adds segments to a document
- **THEN** the CLI accepts a JSON array of segment objects and passes it unchanged to the SDK

#### Scenario: Segment query supports filtering
- **WHEN** a user queries document segments with keyword, status, or extra query parameters
- **THEN** the CLI exposes flags or JSON parameter input that map to the underlying filter options without dropping unknown passthrough params

### Requirement: Knowledge-base metadata and tag commands cover advanced dataset operations
The CLI SHALL provide commands for `hit_testing`, dataset metadata CRUD, built-in metadata management, document metadata updates, dataset tag listing, tag binding, tag unbinding, and dataset tag retrieval.

#### Scenario: Built-in metadata management supports arbitrary action names
- **WHEN** a user invokes built-in metadata management
- **THEN** the CLI accepts the action name explicitly and forwards any accompanying JSON payload through the SDK method

#### Scenario: Bulk document metadata updates accept operation lists
- **WHEN** a user performs a metadata update across multiple documents
- **THEN** the CLI accepts a JSON array of operation objects and sends it as `operation_data`

### Requirement: Knowledge-base pipeline commands cover datasource and RAG execution
The CLI SHALL provide commands for `get_datasource_plugins`, `run_datasource_node`, `run_rag_pipeline`, and `upload_pipeline_file`, with support for streaming where the SDK supports it.

#### Scenario: Datasource node run preserves datasource configuration
- **WHEN** a user runs a datasource node with inputs, datasource type, and optional credential ID
- **THEN** the CLI sends those values unchanged and emits streaming output as line-delimited JSON events when requested

#### Scenario: RAG pipeline run supports blocking and streaming responses
- **WHEN** a user executes a RAG pipeline run command
- **THEN** the CLI accepts datasource info lists and response mode, and maps them directly to the SDK request contract
