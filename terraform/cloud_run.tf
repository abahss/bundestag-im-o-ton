# Cloud Run services

locals {
  registry_host = "${local.location}-docker.pkg.dev"
  image_repo    = "${data.google_project.project.project_id}/${data.google_project.project.project_id}"
  image_name    = "rag:${var.rag_image_tag}"
  rag_image     = "${local.registry_host}/${local.image_repo}/${local.image_name}"

  env_vars = {
    LOG_LEVEL     = "INFO"
    CHROMADB_HOST = google_compute_instance.chromadb.network_interface[0].network_ip
    CHROMADB_PORT = "8000"
  }

  env_vars_dev = {
    LOG_LEVEL     = "DEBUG"
    CHROMADB_HOST = google_compute_instance.chromadb.network_interface[0].network_ip
    CHROMADB_PORT = "8000"
  }
}

# Prod RAG service
resource "google_cloud_run_v2_service" "rag_service" {
  name     = "rag-service"
  location = local.location
  project  = data.google_project.project.project_id

  template {
    containers {
      image = local.rag_image

      dynamic "env" {
        for_each = local.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "8Gi"
        }
        startup_cpu_boost = true
      }

      # Secrets
      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      ports {
        container_port = 8000
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    service_account = google_service_account.project_sa.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # Initial setup. COMMENT OUT TEMPORARILY for changes (env vars, CPU, VPC, etc.)
  lifecycle {
    ignore_changes = [template, traffic]
  }

  depends_on = [google_project_service.cloud_run, google_vpc_access_connector.connector]
}

# Service publicly accessible (i.e. anyone can curl)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.rag_service.project
  location = google_cloud_run_v2_service.rag_service.location
  name     = google_cloud_run_v2_service.rag_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Dev RAG service
resource "google_cloud_run_v2_service" "rag_service_dev" {
  name     = "rag-service-dev"
  location = local.location
  project  = data.google_project.project.project_id

  template {
    containers {
      image = "${local.registry_host}/${local.image_repo}/rag:dev"

      dynamic "env" {
        for_each = local.env_vars_dev
        content {
          name  = env.key
          value = env.value
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "8Gi"
        }
        startup_cpu_boost = true
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }

      ports {
        container_port = 8000
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    service_account = google_service_account.project_sa.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    ignore_changes = [template, traffic]
  }

  depends_on = [google_project_service.cloud_run, google_vpc_access_connector.connector]
}

# Dev service publicly accessible
resource "google_cloud_run_v2_service_iam_member" "public_access_dev" {
  project  = google_cloud_run_v2_service.rag_service_dev.project
  location = google_cloud_run_v2_service.rag_service_dev.location
  name     = google_cloud_run_v2_service.rag_service_dev.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
