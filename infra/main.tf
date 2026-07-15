provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "services" {
  for_each = toset(["aiplatform.googleapis.com", "firestore.googleapis.com", "run.googleapis.com", "storage.googleapis.com"])
  project  = var.project_id
  service  = each.value
}

resource "google_storage_bucket" "dream_media" {
  name                        = "${var.project_id}-dream-media"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
}

resource "google_service_account" "app" {
  account_id   = "dream-palace-app"
  display_name = "Dream Palace runtime"
}

resource "google_project_iam_member" "app_roles" {
  for_each = toset(["roles/datastore.user", "roles/storage.objectUser", "roles/aiplatform.user"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.app.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == '${var.github_repository}'"
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}
