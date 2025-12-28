# 📐 Arquitectura del Sistema - FogNode Audiobooks

## Resumen Ejecutivo

FogNode Audiobooks es una solución híbrida que combina **Fog Computing** y **Serverless Computing** para convertir libros digitales (PDF, EPUB, TXT) en audiobooks usando síntesis de voz (TTS).

## 📁 Repositorios del Proyecto

| Repositorio | Capa | Descripción |
|-------------|------|-------------|
| `fog_node` | Fog Computing | Backend con FastAPI + Piper TTS |
| `audiobooks-frontend` | Edge | Frontend React + Vite |
| `fognode-infrastructure` | Cloud/Serverless | Terraform + Cloud Functions |

---

## 🏗️ Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD LAYER (GCP)                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         SERVERLESS COMPUTING                            │ │
│  │                                                                         │ │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐ │ │
│  │   │   Cloud      │    │   Cloud      │    │      Cloud Scheduler     │ │ │
│  │   │  Functions   │    │  Storage     │    │                          │ │ │
│  │   │              │    │              │    │  ┌────────────────────┐  │ │ │
│  │   │ ┌──────────┐ │    │  ┌────────┐  │    │  │ cleanup-daily      │  │ │ │
│  │   │ │ cleanup  │─┼────┼─▶│ audios │  │    │  │ (0 2 * * *)        │  │ │ │
│  │   │ └──────────┘ │    │  └────────┘  │    │  └─────────┬──────────┘  │ │ │
│  │   │ ┌──────────┐ │    │              │    │            │             │ │ │
│  │   │ │  stats   │◀┼────┼──────────────┼────┼────────────┘             │ │ │
│  │   │ └──────────┘ │    │              │    │  ┌────────────────────┐  │ │ │
│  │   └──────────────┘    └──────────────┘    │  │ stats-daily        │  │ │ │
│  │          │                   ▲            │  │ (0 8 * * *)        │  │ │ │
│  │          │                   │            │  └────────────────────┘  │ │ │
│  │          ▼                   │            └──────────────────────────┘ │ │
│  │   ┌──────────────┐           │                                         │ │
│  │   │  Firestore   │───────────┘                                         │ │
│  │   │  (NoSQL DB)  │                                                     │ │
│  │   │              │                                                     │ │
│  │   │ ┌──────────┐ │                                                     │ │
│  │   │ │  jobs    │ │                                                     │ │
│  │   │ └──────────┘ │                                                     │ │
│  │   └──────────────┘                                                     │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        │ HTTPS API
                                        │
┌───────────────────────────────────────┼─────────────────────────────────────┐
│                              FOG LAYER │                                     │
│  ┌────────────────────────────────────┴────────────────────────────────────┐ │
│  │                         FOG NODE (Docker)                               │ │
│  │                                                                         │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │                      FastAPI Application                        │  │ │
│  │   │                                                                 │  │ │
│  │   │  POST /api/v1/upload    ──▶  BookProcessor  ──▶  Piper TTS     │  │ │
│  │   │  GET  /api/v1/jobs      ◀──  JobManager     ◀──  StorageService│  │ │
│  │   │  GET  /api/v1/status                                           │  │ │
│  │   │  DELETE /api/v1/jobs/:id                                       │  │ │
│  │   │                                                                 │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │ │
│  │   │  Piper TTS   │  │   Models     │  │  Generated   │                 │ │
│  │   │   Engine     │  │   (ONNX)     │  │    Audio     │                 │ │
│  │   └──────────────┘  └──────────────┘  └──────────────┘                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        │ HTTP localhost:8000
                                        │
┌───────────────────────────────────────┼─────────────────────────────────────┐
│                              EDGE LAYER                                      │
│  ┌────────────────────────────────────┴────────────────────────────────────┐ │
│  │                       Frontend (React + Vite)                           │ │
│  │                                                                         │ │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │ │
│  │   │   Upload     │  │     Job      │  │    Audio     │                 │ │
│  │   │    Form      │  │  Dashboard   │  │   Player     │                 │ │
│  │   └──────────────┘  └──────────────┘  └──────────────┘                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│                            👤 Usuario Final                                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Datos

### 1. Procesamiento de Audiobook

```
Usuario ──▶ Frontend ──▶ Fog Node ──▶ Piper TTS ──▶ Cloud Storage
                              │                           │
                              └──▶ Firestore ◀────────────┘
```

1. **Usuario** sube un archivo PDF/EPUB/TXT
2. **Frontend** envía el archivo al Fog Node
3. **Fog Node** extrae texto y genera audio con Piper TTS
4. **Audio** se guarda localmente y se sube a Cloud Storage
5. **Metadata** del job se guarda en Firestore

### 2. Limpieza Automática (Cloud Scheduler)

```
Cloud Scheduler ──▶ Cloud Function ──▶ Firestore (check jobs)
      (2 AM)              │                    │
                          │                    ▼
                          └──▶ Cloud Storage (delete orphans)
```

1. **Cloud Scheduler** ejecuta diariamente a las 2 AM
2. **Cloud Function** lista jobs en Firestore
3. Compara con archivos en Cloud Storage
4. Elimina archivos huérfanos (sin job asociado)

---

## 📦 Componentes del Sistema

### Serverless Computing (GCP)

| Componente | Servicio GCP | Propósito |
|------------|--------------|-----------|
| Base de datos | Firestore | Persistir metadata de jobs |
| Almacenamiento | Cloud Storage | Almacenar archivos de audio |
| Funciones | Cloud Functions | Limpieza y estadísticas |
| Programador | Cloud Scheduler | Tareas automáticas |

### Fog Computing (Docker)

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| API REST | FastAPI | Endpoints HTTP |
| TTS Engine | Piper | Síntesis de voz |
| Modelo | ONNX | Modelo de voz español |
| Container | Docker | Empaquetado y despliegue |

### Edge Computing (Frontend)

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| Framework | React 18 | UI reactiva |
| Router | React Router 7 | Navegación SPA |
| Build | Vite | Bundling rápido |
| Estilos | Tailwind CSS | UI moderna |

---

## 🔧 Infrastructure as Code (IaC)

### Terraform

```
infrastructure/
├── terraform/
│   ├── main.tf          # Recursos principales
│   ├── variables.tf     # Variables configurables
│   └── outputs.tf       # Valores de salida
└── cloud-functions/
    ├── cleanup/         # Función de limpieza
    └── notification/    # Función de estadísticas
```

### Recursos Terraform

```hcl
# Servicios creados automáticamente:
- google_storage_bucket          # Bucket para audios
- google_firestore_database      # Base de datos
- google_cloudfunctions2_function # x2 funciones
- google_cloud_scheduler_job     # x2 jobs programados
- google_service_account         # x2 cuentas de servicio
- google_project_service         # APIs habilitadas
```

---

## 🚀 Despliegue

### Fog Node (Docker)

```bash
cd fog_node
docker build -t fog_node .
docker run -d --name fog_node -p 8000:8000 fog_node
```

### Infraestructura (Terraform)

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### Frontend

```bash
cd audiobooks-frontend
npm install
npm run dev
```

---

## 📊 Escalabilidad

### Horizontal Scaling

```
                    ┌─────────────┐
                    │ Load        │
Usuario ───────────▶│ Balancer    │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ Fog Node 1 │  │ Fog Node 2 │  │ Fog Node N │
    └────────────┘  └────────────┘  └────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌─────────────┐
                    │   GCP       │
                    │ (Serverless)│
                    └─────────────┘
```

El frontend soporta múltiples nodos Fog, permitiendo escalar horizontalmente agregando más contenedores Docker.

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

## 🔒 Seguridad

- **IAM**: Cuentas de servicio con permisos mínimos
- **CORS**: Configurado para dominios específicos
- **Credenciales**: Excluidas de Git (.gitignore)
- **Docker**: Usuario no-root en contenedor

---

## 📚 Referencias

- [Google Cloud Functions](https://cloud.google.com/functions)
- [Cloud Scheduler](https://cloud.google.com/scheduler)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google)
- [Piper TTS](https://github.com/rhasspy/piper)
- [Fog Computing - Wikipedia](https://en.wikipedia.org/wiki/Fog_computing)

