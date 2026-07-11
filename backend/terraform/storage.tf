# Main bucket for everything (project data, etc.)
resource "google_storage_bucket" "project-bucket" {
  name    = "batch-2170-political-reality-check"
  project = data.google_project.project.name

  location = local.location

  force_destroy = true

  hierarchical_namespace {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }
}

resource "google_storage_bucket_iam_member" "project_sa_bucket_access" {
  bucket = google_storage_bucket.project-bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.project_sa.email}"
}
