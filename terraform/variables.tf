# =============================================================================
# Variables de configuración para la infraestructura
# =============================================================================

variable "project_id" {
  description = "ID del proyecto de GCP"
  type        = string
  default     = "mycloud-jhuamaniv"
}

variable "region" {
  description = "Región principal de GCP"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Ambiente de despliegue (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "bucket_name" {
  description = "Nombre del bucket para almacenar audiobooks"
  type        = string
  default     = "fognode-audiobooks"
}

variable "cleanup_schedule" {
  description = "Cron schedule para limpieza de archivos huérfanos"
  type        = string
  default     = "0 2 * * *"  # Todos los días a las 2 AM
}

variable "stats_schedule" {
  description = "Cron schedule para generar estadísticas"
  type        = string
  default     = "0 8 * * *"  # Todos los días a las 8 AM
}

