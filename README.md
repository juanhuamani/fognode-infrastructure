# 🏗️ FogNode Infrastructure

> Infrastructure as Code (IaC) y servicios Serverless para el proyecto FogNode Audiobooks.

[![GCP](https://img.shields.io/badge/GCP-Serverless-blue?logo=google-cloud)](https://cloud.google.com/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform)](https://terraform.io/)

---

## 📁 Repositorios del Proyecto

Este proyecto está dividido en 3 repositorios:

| Repositorio | Descripción | Tecnología |
|-------------|-------------|------------|
| **[fog_node](../fog_node)** | 🌫️ Fog Computing Backend | FastAPI + Piper TTS + Docker |
| **[audiobooks-frontend](../audiobooks-frontend)** | 📱 Frontend Web | React + Vite + Tailwind |
| **fognode-infrastructure** (este) | ☁️ IaC + Serverless | Terraform + Cloud Functions |

---

## 📐 Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                     ☁️  CLOUD (GCP Serverless)                   │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Firestore  │  │   Cloud     │  │    Cloud Functions      │  │
│  │   (NoSQL)   │  │  Storage    │  │  • cleanup (scheduled)  │  │
│  └──────┬──────┘  └──────┬──────┘  │  • stats (scheduled)    │  │
│         │                │         └───────────┬─────────────┘  │
│         └────────────────┼─────────────────────┘                │
│                          │                                       │
│  Este repositorio gestiona toda esta capa ☝️                    │
└──────────────────────────┼──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                 🌫️  FOG NODE (Docker)                            │
│  ┌───────────────────────┴───────────────────────────────────┐  │
│  │  FastAPI + Piper TTS + BookProcessor                      │  │
│  │  📦 Repositorio: fog_node                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                    📱 EDGE (Frontend)                            │
│  ┌───────────────────────┴───────────────────────────────────┐  │
│  │  React + Vite + Tailwind CSS                              │  │
│  │  📦 Repositorio: audiobooks-frontend                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Estructura de este Repositorio

```
fognode-infrastructure/
├── terraform/                   # 🏗️ Infrastructure as Code
│   ├── main.tf                  # Recursos principales
│   ├── variables.tf             # Variables configurables
│   └── outputs.tf               # Valores de salida
│
├── cloud-functions/             # ☁️ Serverless Functions
│   ├── cleanup/                 # Limpieza de archivos huérfanos
│   │   ├── main.py
│   │   └── requirements.txt
│   └── notification/            # Estadísticas y notificaciones
│       ├── main.py
│       └── requirements.txt
│
├── docs/                        # 📚 Documentación
│   └── ARCHITECTURE.md          # Arquitectura detallada
│
└── README.md                    # Este archivo
```

---

## ☁️ Servicios GCP Gestionados

| Servicio | Tipo | Propósito |
|----------|------|-----------|
| **Firestore** | Serverless DB | Persistir metadata de jobs |
| **Cloud Storage** | Serverless Storage | Almacenar audios WAV |
| **Cloud Functions** | Serverless Compute | Limpieza y estadísticas |
| **Cloud Scheduler** | Serverless Cron | Tareas programadas |

---

## 🚀 Despliegue

### Prerrequisitos

1. [Terraform](https://terraform.io/downloads) instalado
2. [gcloud CLI](https://cloud.google.com/sdk/docs/install) configurado
3. Proyecto de GCP con billing habilitado

### Paso 1: Configurar variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con tu project_id
```

### Paso 2: Inicializar Terraform

```bash
terraform init
```

### Paso 3: Revisar plan

```bash
terraform plan
```

### Paso 4: Aplicar infraestructura

```bash
terraform apply
```

### Paso 5: Ver outputs

```bash
terraform output
```

---

## 📊 Cloud Functions

### 1. Cleanup Function (`cleanup/`)

**Propósito**: Elimina archivos de audio huérfanos en Cloud Storage que no tienen un job correspondiente en Firestore.

| Propiedad | Valor |
|-----------|-------|
| Runtime | Python 3.11 |
| Trigger | Cloud Scheduler |
| Schedule | `0 2 * * *` (2 AM diario) |
| Timeout | 300 segundos |

### 2. Stats Function (`notification/`)

**Propósito**: Genera estadísticas de procesamiento de audiobooks.

| Propiedad | Valor |
|-----------|-------|
| Runtime | Python 3.11 |
| Trigger | Cloud Scheduler |
| Schedule | `0 8 * * *` (8 AM diario) |
| Timeout | 60 segundos |

---

## 🔧 Recursos Terraform Creados

```hcl
# Almacenamiento
google_storage_bucket.audiobooks

# Base de datos
google_firestore_database.audiobooks_db

# Serverless Functions
google_cloudfunctions2_function.cleanup
google_cloudfunctions2_function.notification

# Scheduler Jobs
google_cloud_scheduler_job.cleanup_daily
google_cloud_scheduler_job.stats_daily

# IAM & Service Accounts
google_service_account.cloud_functions
google_service_account.scheduler
google_project_iam_member.functions_storage
google_project_iam_member.functions_firestore
```

---

## 🔗 Integración con otros Repositorios

### fog_node (Backend)

El Fog Node usa las credenciales de GCP para:
- Subir audios a Cloud Storage
- Persistir jobs en Firestore

```bash
# En fog_node/, configurar:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
export BUCKET_NAME=fognode-audiobooks-xxx
export GCP_PROJECT_ID=mycloud-jhuamaniv
```

### audiobooks-frontend (Frontend)

El Frontend se conecta al Fog Node que a su vez usa los servicios de GCP:

```
Frontend → Fog Node → GCP (Storage + Firestore)
```

---

## 💰 Costos Estimados

| Servicio | Tier Gratuito | Uso Típico |
|----------|---------------|------------|
| Cloud Storage | 5 GB | ~50 audiobooks |
| Firestore | 1 GB, 50K lecturas/día | Suficiente |
| Cloud Functions | 2M invocaciones/mes | Suficiente |
| Cloud Scheduler | 3 jobs gratuitos | Suficiente |

**Costo estimado para uso educativo: $0/mes** ✅

---

## 📚 Documentación Adicional

- [Arquitectura Detallada](docs/ARCHITECTURE.md)
- [Configuración de GCP](../fog_node/docs/GCP_SETUP.md) (en fog_node)

---

## 🛠️ Comandos Útiles

```bash
# Ver estado de Terraform
terraform show

# Destruir infraestructura
terraform destroy

# Formatear archivos Terraform
terraform fmt

# Validar configuración
terraform validate

# Ejecutar Cloud Function manualmente
gcloud functions call fognode-cleanup --region=us-central1
```

---

## 👥 Equipo

Proyecto de Cloud Computing - UNSA

---

## 📄 Licencia

MIT License
