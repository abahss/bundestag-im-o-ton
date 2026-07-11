resource "google_project_service" "iam" {
  project            = data.google_project.project.project_id
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

# Generic service account for all tasks/services
resource "google_service_account" "project_sa" {
  project      = data.google_project.project.project_id
  account_id   = "batch-2170-project"
  display_name = "General-purpose service account for the project"
}

# Grant Vertex AI User role
resource "google_project_iam_member" "project_sa_ai_user" {
  project = data.google_project.project.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.project_sa.email}"
}
