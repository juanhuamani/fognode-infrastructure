# =============================================================================
# Terraform Configuration for FogNode Audiobooks
# Infrastructure as Code (IaC) for GCP Serverless + Fog Computing
# =============================================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

# -----------------------------------------------------------------------------
# Provider Configuration
# -----------------------------------------------------------------------------
provider "google" {
  project = var.project_id
  region  = var.region
}

# -----------------------------------------------------------------------------
# Enable Required APIs
# -----------------------------------------------------------------------------
resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "eventarc.googleapis.com",
  ])
  
  project = var.project_id
  service = each.value
  
  disable_on_destroy = false
}

# -----------------------------------------------------------------------------
# Cloud Storage Bucket for Audio Files
# -----------------------------------------------------------------------------
resource "google_storage_bucket" "audiobooks" {
  name          = "${var.bucket_name}-${var.project_id}"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = false
  }
  
  lifecycle_rule {
    condition {
      age = 90  # Eliminar archivos después de 90 días
    }
    action {
      type = "Delete"
    }
  }
  
  labels = {
    environment = var.environment
    project     = "fognode-audiobooks"
  }
}

# -----------------------------------------------------------------------------
# Firestore Database
# -----------------------------------------------------------------------------
resource "google_firestore_database" "audiobooks_db" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  
  depends_on = [google_project_service.required_apis]
}

# -----------------------------------------------------------------------------
# Service Account for Cloud Functions
# -----------------------------------------------------------------------------
resource "google_service_account" "cloud_functions" {
  account_id   = "fognode-functions"
  display_name = "FogNode Cloud Functions Service Account"
  project      = var.project_id
}

# IAM: Storage Admin
resource "google_project_iam_member" "functions_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_functions.email}"
}

# IAM: Firestore User
resource "google_project_iam_member" "functions_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.cloud_functions.email}"
}

# -----------------------------------------------------------------------------
# Pub/Sub Topic for Scheduler
# -----------------------------------------------------------------------------
resource "google_pubsub_topic" "cleanup_trigger" {
  name    = "fognode-cleanup-trigger"
  project = var.project_id
  
  depends_on = [google_project_service.required_apis]
}

resource "google_pubsub_topic" "stats_trigger" {
  name    = "fognode-stats-trigger"
  project = var.project_id
  
  depends_on = [google_project_service.required_apis]
}

# -----------------------------------------------------------------------------
# Cloud Function: Cleanup Orphaned Files
# -----------------------------------------------------------------------------
data "archive_file" "cleanup_function" {
  type        = "zip"
  source_dir  = "${path.module}/../cloud-functions/cleanup"
  output_path = "${path.module}/tmp/cleanup_function.zip"
}

resource "google_storage_bucket_object" "cleanup_function_zip" {
  name   = "cloud-functions/cleanup-${data.archive_file.cleanup_function.output_md5}.zip"
  bucket = google_storage_bucket.audiobooks.name
  source = data.archive_file.cleanup_function.output_path
}

resource "google_cloudfunctions2_function" "cleanup" {
  name        = "fognode-cleanup"
  location    = var.region
  description = "Clean up orphaned audio files from Storage"
  
  build_config {
    runtime     = "python311"
    entry_point = "cleanup_orphaned_files"
    source {
      storage_source {
        bucket = google_storage_bucket.audiobooks.name
        object = google_storage_bucket_object.cleanup_function_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count    = 1
    available_memory      = "256M"
    timeout_seconds       = 300
    service_account_email = google_service_account.cloud_functions.email
    
    environment_variables = {
      BUCKET_NAME           = google_storage_bucket.audiobooks.name
      FIRESTORE_COLLECTION  = "audiobook_jobs"
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Allow Cloud Scheduler to invoke the function
resource "google_cloud_run_service_iam_member" "cleanup_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.cleanup.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

# -----------------------------------------------------------------------------
# Cloud Function: Notification (Stats)
# -----------------------------------------------------------------------------
data "archive_file" "notification_function" {
  type        = "zip"
  source_dir  = "${path.module}/../cloud-functions/notification"
  output_path = "${path.module}/tmp/notification_function.zip"
}

resource "google_storage_bucket_object" "notification_function_zip" {
  name   = "cloud-functions/notification-${data.archive_file.notification_function.output_md5}.zip"
  bucket = google_storage_bucket.audiobooks.name
  source = data.archive_file.notification_function.output_path
}

resource "google_cloudfunctions2_function" "notification" {
  name        = "fognode-stats"
  location    = var.region
  description = "Get audiobook processing statistics"
  
  build_config {
    runtime     = "python311"
    entry_point = "get_stats"
    source {
      storage_source {
        bucket = google_storage_bucket.audiobooks.name
        object = google_storage_bucket_object.notification_function_zip.name
      }
    }
  }
  
  service_config {
    max_instance_count    = 1
    available_memory      = "256M"
    timeout_seconds       = 60
    service_account_email = google_service_account.cloud_functions.email
  }
  
  depends_on = [google_project_service.required_apis]
}

# -----------------------------------------------------------------------------
# Cloud Scheduler Service Account
# -----------------------------------------------------------------------------
resource "google_service_account" "scheduler" {
  account_id   = "fognode-scheduler"
  display_name = "FogNode Cloud Scheduler Service Account"
  project      = var.project_id
}

# -----------------------------------------------------------------------------
# Cloud Scheduler: Daily Cleanup Job
# -----------------------------------------------------------------------------
resource "google_cloud_scheduler_job" "cleanup_daily" {
  name        = "fognode-cleanup-daily"
  description = "Daily cleanup of orphaned audio files"
  schedule    = var.cleanup_schedule
  time_zone   = "America/Lima"
  project     = var.project_id
  region      = var.region
  
  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.cleanup.service_config[0].uri
    
    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
  
  retry_config {
    retry_count = 3
  }
  
  depends_on = [google_project_service.required_apis]
}

# -----------------------------------------------------------------------------
# Cloud Scheduler: Daily Stats Job
# -----------------------------------------------------------------------------
resource "google_cloud_scheduler_job" "stats_daily" {
  name        = "fognode-stats-daily"
  description = "Daily statistics report"
  schedule    = var.stats_schedule
  time_zone   = "America/Lima"
  project     = var.project_id
  region      = var.region
  
  http_target {
    http_method = "GET"
    uri         = google_cloudfunctions2_function.notification.service_config[0].uri
    
    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
  
  retry_config {
    retry_count = 3
  }
  
  depends_on = [google_project_service.required_apis]
}

# Allow scheduler to invoke stats function
resource "google_cloud_run_service_iam_member" "stats_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloudfunctions2_function.notification.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

