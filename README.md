# Dream Palace

Telegram-first private dream journal running on Azure. The FastAPI/Telegram edge
uses Azure Functions Flex Consumption, structured data lives in Cosmos DB
serverless, media lives in Blob Storage, and dream analysis runs as a Microsoft
Foundry hosted agent.

## Architecture

| Previous GCP service | Azure target |
| --- | --- |
| Cloud Run | Azure Functions Flex Consumption |
| Firestore | Azure Cosmos DB for NoSQL (serverless) |
| Google Cloud Storage | Azure Blob Storage |
| Google ADK/Gemini | Microsoft Foundry hosted agent |
| Secret Manager | Azure Key Vault |
| Workload Identity Federation | GitHub OIDC + user-assigned managed identities |
| Cloud logging | Application Insights + Log Analytics |

The Function authenticates the Telegram update, derives the tenant from the
signed Telegram ID, and retrieves only that user's dreams. It sends that
already-filtered journal to the hosted analyst. The agent has no Cosmos DB or
Blob Storage credentials, so model output cannot widen the tenant boundary.

## Repository structure

- `function_app.py`, `host.json`: Azure Functions ASGI entry point
- `src/dream_palace`: Telegram bot, Mini App, services, and Azure adapters
- `hosted_agent`: source-deployed Foundry Responses agent
- `azure.yaml`: hosted-agent deployment definition
- `infra`: Terraform for Azure resources, identities, and RBAC
- `scripts/migrate_gcp_to_azure.py`: idempotent Firestore/GCS data transfer
- `docs/AZURE_MIGRATION.md`: cutover and rollback runbook

## Local development

Python 3.12 and [uv](https://docs.astral.sh/uv/) are required. Sign in with the
Azure CLI so `DefaultAzureCredential` can reach a development deployment.

```bash
az login
cp .env.example .env
make install
make test
make lint
make run
```

Set the Azure endpoints and container names in `.env`. Leave `AZURE_CLIENT_ID`
empty locally; production sets it to the Function's user-assigned identity.

Telegram permits one webhook URL per bot. Use a separate development bot and
an HTTPS tunnel for local testing:

```bash
cloudflared tunnel --url http://localhost:8080
curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://<tunnel-host>/webhooks/telegram" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d 'allowed_updates=["message"]'
```

## Provision Azure

The default region is Sweden Central, which supports the selected Flex
Consumption and hosted-agent architecture. Confirm model quota and feature
availability for your subscription before applying.

```bash
terraform -chdir=infra init
terraform -chdir=infra plan \
  -var 'admin_telegram_ids=123456789' \
  -out dream-palace.tfplan
terraform -chdir=infra apply dream-palace.tfplan
```

Terraform creates:

- a Flex Consumption Function App and deployment container;
- Cosmos DB serverless with `users` and `dreams` containers;
- private Blob containers for deployment packages and dream media;
- a Key Vault, Application Insights, and Log Analytics workspace;
- a Foundry account, project, and model deployment;
- separate runtime and GitHub OIDC identities with least-privilege RBAC.

The identity that runs the initial Terraform apply also receives Key Vault
secret-write and destination data-plane roles so it can seed secrets and run
the migration. Use a dedicated deployment identity if you do not want those
operator permissions attached to a personal account.

Bot credentials are deliberately not accepted as Terraform variables, which
keeps secret values out of Terraform state. Seed the two Key Vault entries:

```bash
az keyvault secret set \
  --vault-name "$(terraform -chdir=infra output -raw key_vault_name)" \
  --name bot-token \
  --value "$BOT_TOKEN"
az keyvault secret set \
  --vault-name "$(terraform -chdir=infra output -raw key_vault_name)" \
  --name telegram-webhook-secret \
  --value "$WEBHOOK_SECRET"
```

## Deploy

The `production` GitHub environment must define these repository variables:

| Variable | Terraform output |
| --- | --- |
| `AZURE_CLIENT_ID` | `github_actions_client_id` |
| `AZURE_TENANT_ID` | `azure_tenant_id` |
| `AZURE_SUBSCRIPTION_ID` | `azure_subscription_id` |
| `AZURE_FUNCTION_APP_NAME` | `function_app_name` |
| `FOUNDRY_PROJECT_ENDPOINT` | `foundry_project_endpoint` |
| `FOUNDRY_MODEL_DEPLOYMENT_NAME` | `foundry_model_deployment_name` |

Merges to `main` use OIDC to deploy the Function with One Deploy and upload the
analyst from `hosted_agent/` to Foundry Agent Service. No long-lived Azure
credential is stored in GitHub.

For a first manual hosted-agent deployment:

```bash
azd ext install microsoft.foundry
azd env new dev
azd env set FOUNDRY_PROJECT_ENDPOINT \
  "$(terraform -chdir=infra output -raw foundry_project_endpoint)"
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME \
  "$(terraform -chdir=infra output -raw foundry_model_deployment_name)"
azd deploy --service dream-analyst
```

Register the production webhook after deployment:

```bash
FUNCTION_URL="$(terraform -chdir=infra output -raw function_base_url)"
curl -fsS "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=${FUNCTION_URL}/webhooks/telegram" \
  -d "secret_token=${WEBHOOK_SECRET}" \
  -d 'allowed_updates=["message"]'
```

## Move existing data

Follow `docs/AZURE_MIGRATION.md`. The migration command defaults to a dry run
and requires `--apply` before it writes to Azure:

```bash
gcloud auth application-default login
uv sync --group migration
uv run --group migration python scripts/migrate_gcp_to_azure.py
uv run --group migration python scripts/migrate_gcp_to_azure.py --apply
```

Run the transfer before webhook cutover, pause writes briefly, run it again,
compare source and destination counts, then point Telegram at Azure. The
transfer is resumable because Cosmos documents are upserted and existing blobs
are skipped.

## Operational notes

- The webhook is public because Telegram must reach it, but every update must
  include the configured Telegram webhook secret.
- Mini App API calls verify Telegram `initData` HMAC before deriving the tenant.
- Cosmos DB local authentication and Storage shared keys are disabled; runtime
  access uses the Function's managed identity.
- Hosted agents and source-code deployment are preview features. Review current
  region, quota, pricing, and service-level constraints before production use.
- If the hosted agent is unavailable, analysis falls back to a deterministic
  per-user summary; dream capture and retrieval remain available.
