# VPC Network and Networking Resources

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "project-vpc"
  auto_create_subnetworks = false
  project                 = data.google_project.project.project_id
}

# Subnet
resource "google_compute_subnetwork" "subnet" {
  name          = "project-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = local.location
  network       = google_compute_network.vpc.id
  project       = data.google_project.project.project_id
}

# Cloud Router for NAT
resource "google_compute_router" "router" {
  name    = "project-router"
  region  = local.location
  network = google_compute_network.vpc.id
  project = data.google_project.project.project_id
}

# Cloud NAT for outbound internet access
resource "google_compute_router_nat" "nat" {
  name    = "project-nat"
  router  = google_compute_router.router.name
  region  = local.location
  project = data.google_project.project.project_id

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Serverless VPC Access Connector (for Cloud Run to reach VM)
resource "google_vpc_access_connector" "connector" {
  name          = "project-connector"
  region        = local.location
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28" # Must be /28 and not overlap with subnet
  project       = data.google_project.project.project_id
  min_instances = 2
  max_instances = 3
}

# Firewall rule to allow Cloud Run -> ChromaDB
resource "google_compute_firewall" "chromadb_internal" {
  name    = "allow-chromadb-internal"
  network = google_compute_network.vpc.name
  project = data.google_project.project.project_id

  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }

  # Allow from VPC connector range
  source_ranges = ["10.8.0.0/28"]
  target_tags   = ["chromadb"]
}

# Firewall rule to allow SSH via IAP
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-iap-ssh"
  network = google_compute_network.vpc.name
  project = data.google_project.project.project_id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # IAP's IP range for SSH tunneling
  source_ranges = ["35.235.240.0/20"]
}
