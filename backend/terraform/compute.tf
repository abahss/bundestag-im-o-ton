# Compute resources (VMs and disks)

# Persistent disk for ChromaDB data
resource "google_compute_disk" "chromadb_data" {
  name    = "chromadb-data"
  type    = "pd-ssd" # SSD for faster vector search with 250K+ vectors
  zone    = "${local.location}-a"
  size    = 20 # GB - adjust based on your needs
  project = data.google_project.project.project_id
}

# ChromaDB VM Instance
#
# $(gcloud info --format="value(basic.python_location)") -m pip install numpy
# gcloud compute ssh chromadb-vm --zone=europe-west10-a --tunnel-through-iap # --troubleshoot
# curl http://localhost:8000/api/v1/heartbeat
# curl http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections
resource "google_compute_instance" "chromadb" {
  name         = "chromadb-vm"
  machine_type = "e2-standard-2" # 2 vCPU, 8GB RAM. Or n2-standard-2
  zone         = "${local.location}-a"
  project      = data.google_project.project.project_id

  tags = ["chromadb"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 10 # GB for OS
    }
  }

  attached_disk {
    source      = google_compute_disk.chromadb_data.self_link
    device_name = "chromadb-data"
  }

  network_interface {
    network    = google_compute_network.vpc.name
    subnetwork = google_compute_subnetwork.subnet.name

    # No external IP - internal only
    # Uncomment if you need external access for debugging:
    # access_config {}
  }

  service_account {
    email  = google_service_account.project_sa.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = templatefile("${path.module}/files/chromadb-startup.sh", {
    disk_device = "/dev/disk/by-id/google-chromadb-data"
  })

  # Ensure disk exists first
  depends_on = [google_compute_disk.chromadb_data]
}
