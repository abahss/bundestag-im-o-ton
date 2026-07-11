# Secret Manager resources

# Create API key in https://console.cloud.google.com/apis/credentials. Then
# `printf "YOUR_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-`
#
# Make sure the secret doesn't have a trailing \n:
# `gcloud secrets versions access 2 --secret=gemini-api-key --out-file=/tmp/secret`
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secret_manager]
}

# Grant Cloud Run access to the secret
resource "google_secret_manager_secret_iam_member" "cloud_run_secret_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.project_sa.email}"
}
