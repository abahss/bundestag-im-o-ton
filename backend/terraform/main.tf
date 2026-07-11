data "google_billing_account" "account" {
  billing_account = "01BE33-F9A3D8-3BBA0B" # foudil
}

data "google_project" "project" {
  project_id = "lw-speech-preach"
}


locals {
  region   = "EU"
  location = "europe-west10"
}

provider "google" {
  project = "lw-speech-preach"
  region  = local.location

  user_project_override = true
  billing_project       = "lw-speech-preach"
}

terraform {
  backend "gcs" {
    bucket = "lw-speech-preach-terraform-state"
  }
}

resource "google_project" "project" {
  name            = data.google_project.project.name
  project_id      = data.google_project.project.name
  billing_account = data.google_billing_account.account.id
}
