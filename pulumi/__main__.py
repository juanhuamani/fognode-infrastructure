"""
FogNode Audiobooks - Infrastructure as Code con Pulumi
======================================================

Este script define toda la infraestructura serverless en GCP:
- Cloud Storage (almacenamiento de audios)
- Firestore (base de datos NoSQL)
- Cloud Functions (procesamiento serverless)
- Cloud Scheduler (tareas programadas)
"""

import pulumi
import pulumi_gcp as gcp
import pulumi_docker as docker
from pulumi import Config, export, Output

# =============================================================================
# Configuración
# =============================================================================

config = Config("fognode")
gcp_config = Config("gcp")

PROJECT_ID = gcp_config.require("project")
REGION = gcp_config.require("region")
ENVIRONMENT = config.get("environment") or "dev"
BUCKET_NAME = config.get("bucket_name") or "fognode-audiobooks"
CLEANUP_SCHEDULE = config.get("cleanup_schedule") or "0 2 * * *"
STATS_SCHEDULE = config.get("stats_schedule") or "0 8 * * *"

# =============================================================================
# Habilitar APIs necesarias
# =============================================================================

apis = [
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "eventarc.googleapis.com",
    "artifactregistry.googleapis.com",  # Requerido para Cloud Functions v2 y Docker images
]

enabled_apis = []
for api in apis:
    service = gcp.projects.Service(
        f"enable-{api.replace('.', '-')}",
        service=api,
        disable_on_destroy=False,
    )
    enabled_apis.append(service)

# =============================================================================
# Cloud Storage - Bucket para archivos de audio
# =============================================================================

audio_bucket = gcp.storage.Bucket(
    "audiobooks-bucket",
    name=f"{BUCKET_NAME}-{PROJECT_ID}",
    location=REGION,
    force_destroy=False,
    uniform_bucket_level_access=True,
    versioning=gcp.storage.BucketVersioningArgs(enabled=False),
    lifecycle_rules=[
        gcp.storage.BucketLifecycleRuleArgs(
            condition=gcp.storage.BucketLifecycleRuleConditionArgs(age=90),
            action=gcp.storage.BucketLifecycleRuleActionArgs(type="Delete"),
        )
    ],
    labels={
        "environment": ENVIRONMENT,
        "project": "fognode-audiobooks",
    },
)

# =============================================================================
# Firestore - Base de datos NoSQL
# =============================================================================

# NOTA: La base de datos Firestore "(default)" ya existe en el proyecto.
# No la recreamos aquí para evitar conflictos.
# Si necesitas crearla desde cero, descomenta el siguiente bloque:
#
# firestore_db = gcp.firestore.Database(
#     "audiobooks-db",
#     name="(default)",
#     location_id=REGION,
#     type="FIRESTORE_NATIVE",
#     opts=pulumi.ResourceOptions(depends_on=enabled_apis),
# )

# =============================================================================
# Service Account - Para Cloud Functions
# =============================================================================

functions_sa = gcp.serviceaccount.Account(
    "functions-service-account",
    account_id="fognode-functions",
    display_name="FogNode Cloud Functions Service Account",
)

# IAM: Storage Admin
storage_iam = gcp.projects.IAMMember(
    "functions-storage-iam",
    project=PROJECT_ID,
    role="roles/storage.objectAdmin",
    member=functions_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

# IAM: Firestore User
firestore_iam = gcp.projects.IAMMember(
    "functions-firestore-iam",
    project=PROJECT_ID,
    role="roles/datastore.user",
    member=functions_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

# IAM: Artifact Registry Reader para Cloud Functions Service Agent
# El service agent tiene formato: service-PROJECT_NUMBER@gcf-admin-robot.iam.gserviceaccount.com
artifact_registry_iam = gcp.projects.IAMMember(
    "cloudfunctions-artifact-registry-iam",
    project=PROJECT_ID,
    role="roles/artifactregistry.reader",
    member=f"serviceAccount:service-{gcp.organizations.get_project(project_id=PROJECT_ID).number}@gcf-admin-robot.iam.gserviceaccount.com",
)

# =============================================================================
# Service Account - Para Cloud Scheduler
# =============================================================================

scheduler_sa = gcp.serviceaccount.Account(
    "scheduler-service-account",
    account_id="fognode-scheduler",
    display_name="FogNode Cloud Scheduler Service Account",
)

# =============================================================================
# Cloud Function - Cleanup (Limpieza de archivos huérfanos)
# =============================================================================

# Subir código de la función al bucket
cleanup_code = gcp.storage.BucketObject(
    "cleanup-function-code",
    bucket=audio_bucket.name,
    name="cloud-functions/cleanup.zip",
    source=pulumi.FileArchive("../cloud-functions/cleanup"),
)

cleanup_function = gcp.cloudfunctionsv2.Function(
    "cleanup-function",
    name="fognode-cleanup",
    location=REGION,
    description="Limpieza automática de archivos huérfanos en Storage",
    build_config=gcp.cloudfunctionsv2.FunctionBuildConfigArgs(
        runtime="python311",
        entry_point="cleanup_orphaned_files",
        source=gcp.cloudfunctionsv2.FunctionBuildConfigSourceArgs(
            storage_source=gcp.cloudfunctionsv2.FunctionBuildConfigSourceStorageSourceArgs(
                bucket=audio_bucket.name,
                object=cleanup_code.name,
            ),
        ),
    ),
    service_config=gcp.cloudfunctionsv2.FunctionServiceConfigArgs(
        max_instance_count=1,
        available_memory="256M",
        timeout_seconds=300,
        service_account_email=functions_sa.email,
        environment_variables={
            "BUCKET_NAME": audio_bucket.name,
            "FIRESTORE_COLLECTION": "audiobook_jobs",
        },
    ),
    opts=pulumi.ResourceOptions(depends_on=enabled_apis),
)

# =============================================================================
# Cloud Function - Stats (Estadísticas)
# =============================================================================

stats_code = gcp.storage.BucketObject(
    "stats-function-code",
    bucket=audio_bucket.name,
    name="cloud-functions/notification.zip",
    source=pulumi.FileArchive("../cloud-functions/notification"),
)

stats_function = gcp.cloudfunctionsv2.Function(
    "stats-function",
    name="fognode-stats",
    location=REGION,
    description="Estadísticas de procesamiento de audiobooks",
    build_config=gcp.cloudfunctionsv2.FunctionBuildConfigArgs(
        runtime="python311",
        entry_point="get_stats",
        source=gcp.cloudfunctionsv2.FunctionBuildConfigSourceArgs(
            storage_source=gcp.cloudfunctionsv2.FunctionBuildConfigSourceStorageSourceArgs(
                bucket=audio_bucket.name,
                object=stats_code.name,
            ),
        ),
    ),
    service_config=gcp.cloudfunctionsv2.FunctionServiceConfigArgs(
        max_instance_count=1,
        available_memory="256M",
        timeout_seconds=60,
        service_account_email=functions_sa.email,
    ),
    opts=pulumi.ResourceOptions(depends_on=enabled_apis),
)

# =============================================================================
# IAM - Permitir que Scheduler invoque las funciones
# =============================================================================

cleanup_invoker = gcp.cloudrun.IamMember(
    "cleanup-invoker",
    location=REGION,
    service=cleanup_function.name,
    role="roles/run.invoker",
    member=scheduler_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

stats_invoker = gcp.cloudrun.IamMember(
    "stats-invoker",
    location=REGION,
    service=stats_function.name,
    role="roles/run.invoker",
    member=scheduler_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

# =============================================================================
# Cloud Scheduler - Limpieza diaria
# =============================================================================

cleanup_scheduler = gcp.cloudscheduler.Job(
    "cleanup-scheduler",
    name="fognode-cleanup-daily",
    description="Limpieza diaria de archivos huérfanos",
    schedule=CLEANUP_SCHEDULE,
    time_zone="America/Lima",
    region=REGION,
    http_target=gcp.cloudscheduler.JobHttpTargetArgs(
        http_method="POST",
        uri=cleanup_function.service_config.uri,
        oidc_token=gcp.cloudscheduler.JobHttpTargetOidcTokenArgs(
            service_account_email=scheduler_sa.email,
        ),
    ),
    retry_config=gcp.cloudscheduler.JobRetryConfigArgs(
        retry_count=3,
    ),
    opts=pulumi.ResourceOptions(depends_on=[cleanup_invoker]),
)

# =============================================================================
# Cloud Scheduler - Estadísticas diarias
# =============================================================================

stats_scheduler = gcp.cloudscheduler.Job(
    "stats-scheduler",
    name="fognode-stats-daily",
    description="Reporte diario de estadísticas",
    schedule=STATS_SCHEDULE,
    time_zone="America/Lima",
    region=REGION,
    http_target=gcp.cloudscheduler.JobHttpTargetArgs(
        http_method="GET",
        uri=stats_function.service_config.uri,
        oidc_token=gcp.cloudscheduler.JobHttpTargetOidcTokenArgs(
            service_account_email=scheduler_sa.email,
        ),
    ),
    retry_config=gcp.cloudscheduler.JobRetryConfigArgs(
        retry_count=3,
    ),
    opts=pulumi.ResourceOptions(depends_on=[stats_invoker]),
)

# =============================================================================
# Artifact Registry - Repository para imágenes Docker del Fog Node
# =============================================================================

docker_repo = gcp.artifactregistry.Repository(
    "fognode-docker-repo",
    repository_id="fognode",
    location=REGION,
    format="DOCKER",
    description="Docker images for FogNode API",
    opts=pulumi.ResourceOptions(depends_on=enabled_apis),
)

# =============================================================================
# Service Account - Para Fog Node API en Cloud Run
# =============================================================================

fognode_api_sa = gcp.serviceaccount.Account(
    "fognode-api-service-account",
    account_id="fognode-api",
    display_name="FogNode API Service Account",
    description="Service account for FogNode Cloud Run API service",
)

# IAM: Storage Object Admin para el bucket
fognode_storage_iam = gcp.storage.BucketIAMBinding(
    "fognode-api-storage-iam",
    bucket=audio_bucket.name,
    role="roles/storage.objectAdmin",
    members=[fognode_api_sa.email.apply(lambda email: f"serviceAccount:{email}")],
)

# IAM: Firestore User
fognode_firestore_iam = gcp.projects.IAMMember(
    "fognode-api-firestore-iam",
    project=PROJECT_ID,
    role="roles/datastore.user",
    member=fognode_api_sa.email.apply(lambda email: f"serviceAccount:{email}"),
)

# =============================================================================
# Build & Push Docker Image del Fog Node
# =============================================================================

# Docker image name en Artifact Registry
fognode_image_name = Output.concat(
    REGION,
    "-docker.pkg.dev/",
    PROJECT_ID,
    "/",
    docker_repo.repository_id,
    "/fognode-api:latest",
)

# Construir y subir imagen Docker
# Nota: Requiere Docker instalado y autenticado con gcloud
fognode_app_image = docker.Image(
    "fognode-api-image",
    image_name=fognode_image_name,
    build=docker.DockerBuildArgs(
        context="../../fog_node",  # Ruta relativa desde pulumi/ al directorio fog_node
        dockerfile="../../fog_node/Dockerfile",
        platform="linux/amd64",
    ),
    registry=docker.RegistryArgs(
        server=Output.concat(REGION, "-docker.pkg.dev"),
    ),
    opts=pulumi.ResourceOptions(depends_on=[docker_repo]),
)

# =============================================================================
# Cloud Run Service - Fog Node API
# =============================================================================

fognode_api_service = gcp.cloudrunv2.Service(
    "fognode-api-service",
    name="fognode-api",
    location=REGION,
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        service_account=fognode_api_sa.email,
        containers=[
            gcp.cloudrunv2.ServiceTemplateContainerArgs(
                image=fognode_app_image.image_name,
                ports=[
                    gcp.cloudrunv2.ServiceTemplateContainerPortArgs(
                        container_port=8000,
                    ),
                ],
                resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                    limits={
                        "cpu": "2",
                        "memory": "2Gi",
                    },
                ),
                envs=[
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="GCP_PROJECT_ID",
                        value=PROJECT_ID,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="BUCKET_NAME",
                        value=audio_bucket.name,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="ENV_MODE",
                        value="production",
                    ),
                    # Sobrescribir GOOGLE_APPLICATION_CREDENTIALS para que use Application Default Credentials
                    # En Cloud Run, las credenciales se obtienen automáticamente del Service Account asignado
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="GOOGLE_APPLICATION_CREDENTIALS",
                        value="",  # Vacío para forzar uso de ADC del Service Account
                    ),
                ],
            ),
        ],
        scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
            min_instance_count=0,
            max_instance_count=10,
        ),
    ),
    opts=pulumi.ResourceOptions(
        depends_on=[
            fognode_api_sa,
            fognode_storage_iam,
            fognode_firestore_iam,
            fognode_app_image,
        ]
    ),
)

# Hacer el servicio Cloud Run público
fognode_api_iam = gcp.cloudrunv2.ServiceIamBinding(
    "fognode-api-public-access",
    name=fognode_api_service.name,
    location=REGION,
    role="roles/run.invoker",
    members=["allUsers"],  # Hacerlo público
)

# =============================================================================
# Exports - Valores de salida
# =============================================================================

export("bucket_name", audio_bucket.name)
export("bucket_url", audio_bucket.url)
export("cleanup_function_url", cleanup_function.service_config.uri)
export("stats_function_url", stats_function.service_config.uri)
export("cleanup_scheduler", cleanup_scheduler.name)
export("stats_scheduler", stats_scheduler.name)
export("functions_service_account", functions_sa.email)
export("fognode_api_url", fognode_api_service.uri)
export("fognode_api_service_account", fognode_api_sa.email)

# Resumen de arquitectura
export("architecture_summary", Output.concat(
    "\n",
    "╔══════════════════════════════════════════════════════════════════╗\n",
    "║         FogNode Audiobooks - Infraestructura Desplegada          ║\n",
    "╠══════════════════════════════════════════════════════════════════╣\n",
    "║                                                                  ║\n",
    "║  ☁️  SERVERLESS (GCP)                                            ║\n",
    "║  ├── Cloud Storage: ", audio_bucket.name, "\n",
    "║  ├── Firestore: audiobook_jobs                                   ║\n",
    "║  ├── Cloud Function: fognode-cleanup                             ║\n",
    "║  ├── Cloud Function: fognode-stats                               ║\n",
    "║  ├── Cloud Scheduler: cleanup-daily                              ║\n",
    "║  └── Cloud Scheduler: stats-daily                                ║\n",
    "║                                                                  ║\n",
    "║  🌫️  FOG COMPUTING                                               ║\n",
    "║  └── Cloud Run: fognode-api (", fognode_api_service.uri, ")  ║\n",
    "║                                                                  ║\n",
    "╚══════════════════════════════════════════════════════════════════╝\n",
))

