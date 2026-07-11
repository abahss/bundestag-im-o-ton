# Outputs

# Network outputs
output "chromadb_internal_ip" {
  value       = google_compute_instance.chromadb.network_interface[0].network_ip
  description = "Internal IP address of ChromaDB VM"
}

output "vpc_connector_name" {
  value       = google_vpc_access_connector.connector.name
  description = "VPC connector name for Cloud Run"
}

# Cloud Run service outputs
output "rag_service_url" {
  value       = google_cloud_run_v2_service.rag_service.uri
  description = "URL of the deployed RAG service (external ChromaDB)"
}

output "rag_service_dev_url" {
  value       = google_cloud_run_v2_service.rag_service_dev.uri
  description = "URL of the deployed RAG dev service (external ChromaDB)"
}
