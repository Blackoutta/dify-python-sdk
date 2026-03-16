# Management Commands

Use this file for workspace-level and knowledge-base operations.

## Scope

- `workspace` commands for models, providers, and workspace file operations
- `kb` commands for datasets, documents, segments, metadata, tags, and pipelines

## Workspace Commands

- `workspace models`
  Purpose: list available models
  Key flags: `--model-type`
- `workspace providers`
  Purpose: list model providers
- `workspace provider-models`
  Purpose: list models for a provider
  Key flags: `--provider-name`
- `workspace validate-credentials`
  Purpose: validate provider credentials
  Key flags: `--provider-name`, `--credentials-json`
  Note: send structured JSON exactly as required by the provider
- `workspace file-info`
  Purpose: fetch workspace file metadata
  Key flags: `--file-id`
- `workspace file-download-url`
  Purpose: fetch a download URL for a file
  Key flags: `--file-id`
- `workspace file-delete`
  Purpose: delete a workspace file
  Key flags: `--file-id`

## Knowledge-Base Dataset Commands

- `kb dataset create`
  Purpose: create a dataset
  Key flags: `--name`
- `kb dataset list`
  Purpose: list datasets
  Key flags: optional `--page`, `--page-size`
- `kb dataset get`
  Purpose: fetch one dataset
  Key flags: `--dataset-id`
- `kb dataset update`
  Purpose: partially update a dataset
  Key flags: `--dataset-id`, optional `--name`, `--description`, `--indexing-technique`, `--embedding-model`, `--embedding-model-provider`, `--retrieval-model-json`, `--extra-json`
  Note: send only the fields you intend to change
- `kb dataset delete`
  Purpose: delete a dataset
  Key flags: `--dataset-id`
- `kb dataset create-from-template`
  Purpose: create a dataset from a template
  Key flags: `--template-name`, `--name`, optional `--description`
- `kb dataset duplicate`
  Purpose: duplicate an existing dataset
  Key flags: `--dataset-id`, `--name`
- `kb dataset batch-document-status`
  Purpose: batch-change document indexing status
  Key flags: `--dataset-id`, `--action`, `--document-ids-json`

## Knowledge-Base Document Commands

- `kb document create-text`
  Purpose: create a text-backed document
  Key flags: `--dataset-id`, `--name`, `--text`, optional `--extra-json`
- `kb document update-text`
  Purpose: update a text-backed document
  Key flags: `--dataset-id`, `--document-id`, `--name`, `--text`, optional `--extra-json`
- `kb document create-file`
  Purpose: create a file-backed document
  Key flags: `--dataset-id`, `--path`, optional `--original-document-id`, `--extra-json`
- `kb document update-file`
  Purpose: update a file-backed document
  Key flags: `--dataset-id`, `--document-id`, `--path`, optional `--extra-json`
- `kb document list`
  Purpose: list documents in a dataset
  Key flags: `--dataset-id`, optional `--page`, `--page-size`, `--keyword`
- `kb document delete`
  Purpose: delete a document
  Key flags: `--dataset-id`, `--document-id`
- `kb document indexing-status`
  Purpose: fetch indexing status for a batch
  Key flags: `--dataset-id`, `--batch-id`

## Knowledge-Base Segment Commands

- `kb segment add`
  Purpose: add segments to a document
  Key flags: `--dataset-id`, `--document-id`, `--segments-json`
- `kb segment query`
  Purpose: query document segments
  Key flags: `--dataset-id`, `--document-id`, optional `--keyword`, `--status`, `--params-json`
- `kb segment update`
  Purpose: update one segment
  Key flags: `--dataset-id`, `--document-id`, `--segment-id`, `--segment-json`
- `kb segment delete`
  Purpose: delete one segment
  Key flags: `--dataset-id`, `--document-id`, `--segment-id`

## Knowledge-Base Metadata Commands

- `kb metadata hit-test`
  Purpose: run retrieval hit testing
  Key flags: `--dataset-id`, `--query`, optional `--retrieval-model-json`, `--external-retrieval-model-json`
- `kb metadata get`
  Purpose: list metadata definitions for a dataset
  Key flags: `--dataset-id`
- `kb metadata create`
  Purpose: create dataset metadata
  Key flags: `--dataset-id`, `--metadata-json`
- `kb metadata update`
  Purpose: update dataset metadata
  Key flags: `--dataset-id`, `--metadata-id`, `--metadata-json`
- `kb metadata built-in-get`
  Purpose: fetch built-in metadata definitions
  Key flags: `--dataset-id`
- `kb metadata built-in-manage`
  Purpose: manage built-in metadata by action name
  Key flags: `--dataset-id`, `--action`, optional `--metadata-json`
- `kb metadata update-documents`
  Purpose: bulk-update document metadata
  Key flags: `--dataset-id`, `--operation-data-json`

## Knowledge-Base Tag Commands

- `kb tag list-all`
  Purpose: list all available tags, optionally filtered by dataset
  Key flags: optional `--dataset-id`
- `kb tag bind`
  Purpose: bind tags to a dataset
  Key flags: `--dataset-id`, `--tag-ids-json`
- `kb tag unbind`
  Purpose: unbind one tag from a dataset
  Key flags: `--dataset-id`, `--tag-id`
- `kb tag list`
  Purpose: list tags attached to a dataset
  Key flags: `--dataset-id`

## Knowledge-Base Pipeline Commands

- `kb pipeline datasource-plugins`
  Purpose: list datasource plugins
  Key flags: `--dataset-id`, optional `--is-published`
- `kb pipeline run-datasource-node`
  Purpose: run a datasource node
  Key flags: `--dataset-id`, `--node-id`, `--datasource-type`, `--inputs-json`, optional `--is-published`, `--credential-id`
- `kb pipeline run`
  Purpose: run the RAG pipeline
  Key flags: `--dataset-id`, `--datasource-type`, `--start-node-id`, `--inputs-json`, `--datasource-info-list-json`, optional `--is-published`, `--response-mode`
- `kb pipeline upload-file`
  Purpose: upload a file for pipeline use
  Key flags: `--path`

## Agent Notes

- Always preserve explicit dataset/document/segment identifiers; these commands do not rely on hidden local state.
- Prefer JSON-bearing flags such as `--credentials-json`, `--retrieval-model-json`, `--segments-json`, `--metadata-json`, `--operation-data-json`, and `--datasource-info-list-json` over trying to flatten complex payloads into scalar flags.
- For file-backed document commands, ensure the local path exists before invoking the CLI.
- For pipeline or hit-test commands, treat the JSON payload flags as authoritative request contracts and avoid guessing missing nested fields.

## Coverage

- OpenSpec capability:
  `python-cli-management`
