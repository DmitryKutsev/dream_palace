output "storage_bucket" { value = google_storage_bucket.dream_media.name }
output "service_account" { value = google_service_account.app.email }
output "workload_identity_provider" { value = google_iam_workload_identity_pool_provider.github.name }
