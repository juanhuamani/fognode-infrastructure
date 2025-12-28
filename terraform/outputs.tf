# =============================================================================
# Outputs - Valores exportados después del despliegue
# =============================================================================

output "bucket_name" {
  description = "Nombre del bucket de Cloud Storage"
  value       = google_storage_bucket.audiobooks.name
}

output "bucket_url" {
  description = "URL del bucket"
  value       = "gs://${google_storage_bucket.audiobooks.name}"
}

output "cleanup_function_url" {
  description = "URL de la Cloud Function de limpieza"
  value       = google_cloudfunctions2_function.cleanup.service_config[0].uri
}

output "stats_function_url" {
  description = "URL de la Cloud Function de estadísticas"
  value       = google_cloudfunctions2_function.notification.service_config[0].uri
}

output "cleanup_scheduler_name" {
  description = "Nombre del job de Cloud Scheduler para limpieza"
  value       = google_cloud_scheduler_job.cleanup_daily.name
}

output "stats_scheduler_name" {
  description = "Nombre del job de Cloud Scheduler para estadísticas"
  value       = google_cloud_scheduler_job.stats_daily.name
}

output "service_account_email" {
  description = "Email de la cuenta de servicio de Cloud Functions"
  value       = google_service_account.cloud_functions.email
}

output "firestore_database" {
  description = "Nombre de la base de datos Firestore"
  value       = google_firestore_database.audiobooks_db.name
}

# Resumen de la arquitectura desplegada
output "architecture_summary" {
  description = "Resumen de la arquitectura desplegada"
  value = <<-EOT
    
    ╔══════════════════════════════════════════════════════════════════╗
    ║         FogNode Audiobooks - Arquitectura Desplegada             ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║                                                                  ║
    ║  ☁️  SERVERLESS (GCP)                                            ║
    ║  ├── Cloud Storage: ${google_storage_bucket.audiobooks.name}
    ║  ├── Firestore: audiobook_jobs                                   ║
    ║  ├── Cloud Function: fognode-cleanup                             ║
    ║  ├── Cloud Function: fognode-stats                               ║
    ║  ├── Cloud Scheduler: cleanup-daily (${var.cleanup_schedule})
    ║  └── Cloud Scheduler: stats-daily (${var.stats_schedule})
    ║                                                                  ║
    ║  🌫️  FOG COMPUTING                                               ║
    ║  └── Docker Container: fog_node (localhost:8000)                 ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    
  EOT
}

