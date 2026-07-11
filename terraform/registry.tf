# Artifact Registry for Docker images

resource "google_artifact_registry_repository" "project-registry" {
  location      = local.location
  repository_id = data.google_project.project.name
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry]
}
