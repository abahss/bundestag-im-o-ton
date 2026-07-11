# Enable required Google Cloud APIs

# Compute Engine API
resource "google_project_service" "compute" {
  project            = data.google_project.project.project_id
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

# VPC Access API (for serverless VPC connector)
resource "google_project_service" "vpcaccess" {
  project            = data.google_project.project.project_id
  service            = "vpcaccess.googleapis.com"
  disable_on_destroy = false
}

# Identity-Aware Proxy API (for SSH tunneling)
resource "google_project_service" "iap" {
  project            = data.google_project.project.project_id
  service            = "iap.googleapis.com"
  disable_on_destroy = false
}

# Network Management API
resource "google_project_service" "networkmanagement" {
  project            = data.google_project.project.project_id
  service            = "networkmanagement.googleapis.com"
  disable_on_destroy = false
}

# Cloud Monitoring API
resource "google_project_service" "monitoring" {
  project            = data.google_project.project.project_id
  service            = "monitoring.googleapis.com"
  disable_on_destroy = false
}

# Cloud Run API
resource "google_project_service" "cloud_run" {
  project            = data.google_project.project.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry API
resource "google_project_service" "artifact_registry" {
  project            = data.google_project.project.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

# Secret Manager API
resource "google_project_service" "secret_manager" {
  project            = data.google_project.project.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}
