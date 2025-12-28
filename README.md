# 🏗️ FogNode Infrastructure

Infraestructura como Código (IaC) con **Pulumi** para el proyecto FogNode Audiobooks.

## 📁 Estructura

```
fognode-infrastructure/
├── pulumi/                    # Infraestructura con Pulumi (Python)
│   ├── Pulumi.yaml           # Configuración del proyecto
│   ├── Pulumi.dev.yaml       # Stack de desarrollo
│   ├── __main__.py           # Definición de infraestructura
│   └── requirements.txt      # Dependencias Python
├── cloud-functions/          # Código de Cloud Functions
│   ├── cleanup/              # Limpieza de archivos huérfanos
│   └── notification/         # Estadísticas y reportes
└── docs/
    └── ARCHITECTURE.md       # Documentación de arquitectura
```

## 🚀 Despliegue Rápido

### Prerrequisitos

1. **Google Cloud SDK** configurado con tu proyecto
2. **Pulumi CLI** instalado
3. **Python 3.11+**

### Pasos

```bash
# 1. Autenticarse en GCP
gcloud auth application-default login

# 2. Instalar Pulumi (si no lo tienes)
curl -fsSL https://get.pulumi.com | sh

# 3. Ir a la carpeta de Pulumi
cd pulumi

# 4. Crear entorno virtual e instalar dependencias
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 5. Inicializar stack (primera vez)
pulumi stack init dev

# 6. Configurar proyecto GCP (si no editaste Pulumi.dev.yaml)
pulumi config set gcp:project TU_PROJECT_ID
pulumi config set gcp:region us-central1

# 7. Vista previa de cambios
pulumi preview

# 8. Desplegar infraestructura
pulumi up
```

## ⚙️ Configuración

Edita `pulumi/Pulumi.dev.yaml`:

```yaml
config:
  gcp:project: mycloud-jhuamaniv        # Tu proyecto GCP
  gcp:region: us-central1               # Región
  fognode:environment: dev              # Ambiente
  fognode:bucket_name: fognode-audiobooks  # Nombre del bucket
  fognode:cleanup_schedule: "0 2 * * *" # Limpieza: 2 AM diario
  fognode:stats_schedule: "0 8 * * *"   # Stats: 8 AM diario
```

## 🛠️ Recursos Desplegados

| Servicio | Recurso | Descripción |
|----------|---------|-------------|
| **Cloud Storage** | `fognode-audiobooks-*` | Almacena archivos de audio generados |
| **Firestore** | `(default)` | Base de datos de jobs de procesamiento |
| **Cloud Functions** | `fognode-cleanup` | Limpia archivos huérfanos |
| **Cloud Functions** | `fognode-stats` | Genera estadísticas |
| **Cloud Scheduler** | `fognode-cleanup-daily` | Ejecuta limpieza diaria |
| **Cloud Scheduler** | `fognode-stats-daily` | Genera reporte diario |
| **Service Accounts** | 2 cuentas | Para functions y scheduler |

## 📊 Comandos Útiles

```bash
# Ver estado actual
pulumi stack

# Ver outputs
pulumi stack output

# Ver cambios sin aplicar
pulumi preview

# Aplicar cambios
pulumi up

# Destruir infraestructura
pulumi destroy

# Ver logs de Cloud Functions
gcloud functions logs read fognode-cleanup --region=us-central1
gcloud functions logs read fognode-stats --region=us-central1
```

## 🔗 Repositorios Relacionados

| Repositorio | Descripción |
|-------------|-------------|
| [fog_node](https://github.com/tu-usuario/fog_node) | Backend - API REST + TTS Processing |
| [audiobooks-frontend](https://github.com/tu-usuario/audiobooks-frontend) | Frontend - React + Vite |

## 🆚 ¿Por qué Pulumi en lugar de Terraform?

| Característica | Pulumi | Terraform |
|---------------|--------|-----------|
| Lenguaje | Python, TS, Go | HCL (DSL propio) |
| Tipado | ✅ Completo | ❌ Limitado |
| Lógica condicional | ✅ Nativo | ⚠️ Limitado |
| Testing | ✅ Unit tests nativos | ⚠️ Terraform test |
| IDE Support | ✅ Autocompletado | ⚠️ Básico |

## 📝 Licencia

MIT License
