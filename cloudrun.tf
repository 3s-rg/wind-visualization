provider "google" {
  project = var.gcloud_project
  region  = var.gcloud_region
}

variable "gcloud_project" {
  type = string
}

variable "gcloud_region" {
  type        = string
  description = "region where everything is deployed"
}

variable "data_processed" {
  type        = string
  description = "the path to the processed data"
}

output "url" {
  value = google_cloud_run_v2_service.ocw.uri
}

locals {
  project_shortname       = "ocw"
  frontend_source         = "./dist"
  backend_source          = "./server"
  frontend_dockerfile     = "frontend.Dockerfile"
  backend_dockerfile      = "Dockerfile"
  frontend_image_platform = "linux/amd64"
  backend_image_platform  = "linux/amd64"
  frontend_image_name     = "ocw-frontend"
  backend_image_name      = "ocw-backend"
  frontend_image_tag      = "latest"
  backend_image_tag       = "latest"
  frontend_image          = "${var.gcloud_region}-docker.pkg.dev/${var.gcloud_project}/${google_artifact_registry_repository.ocw_repository.repository_id}/${local.frontend_image_name}:${local.frontend_image_tag}"
  backend_image           = "${var.gcloud_region}-docker.pkg.dev/${var.gcloud_project}/${google_artifact_registry_repository.ocw_repository.repository_id}/${local.backend_image_name}:${local.backend_image_tag}"
}

resource "google_storage_bucket" "ocw-data" {
  name          = "${local.project_shortname}-data"
  location      = var.gcloud_region
  storage_class = "STANDARD"
  force_destroy = true

  uniform_bucket_level_access = true
}

resource "terraform_data" "init_upload_data" {
  depends_on = [google_storage_bucket.ocw-data]

  triggers_replace = [
    sha1(join("", [for f in fileset("${var.data_processed}/", "*/meta.json") : filesha1("${var.data_processed}/${f}")])),
  ]

  provisioner "local-exec" {
    command = "gsutil -m rsync -d -J -r ${var.data_processed} gs://${google_storage_bucket.ocw-data.name}"
  }
}

resource "google_cloud_run_service_iam_member" "ocw-public-run" {
  service  = google_cloud_run_v2_service.ocw.name
  location = google_cloud_run_v2_service.ocw.location
  lifecycle {
    replace_triggered_by = [
      google_cloud_run_v2_service.ocw
    ]
  } # hack to make sure the service is created before the member is added
  role   = "roles/run.invoker"
  member = "allUsers"
}

resource "google_cloud_run_v2_service" "ocw" {
  #   provider     = google-beta
  name         = "${local.project_shortname}-cloudrun-service"
  location     = var.gcloud_region
  launch_stage = "BETA" # this is necessary to mount a GCS bucket
  ingress      = "INGRESS_TRAFFIC_ALL"

  lifecycle {
    replace_triggered_by = [
      terraform_data.init_push_frontend,
      terraform_data.init_push_backend
    ]
  }

  depends_on = [
    terraform_data.init_push_frontend,
    terraform_data.init_push_backend,
    terraform_data.init_upload_data
  ]

  template {
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2" # this is necessary to mount a GCS bucket
    timeout               = "10s"                        # backend service can be slow
    scaling {
      max_instance_count = 3
    }

    containers {
      name = "ocw-frontend"
      ports {
        container_port = 80
      }
      env {
        name  = "NGINX_BACKEND_SERVICE"
        value = "http://localhost:8081"
      }
      image      = local.frontend_image
      depends_on = ["${local.project_shortname}-backend"]
    }
    containers {
      name  = "${local.project_shortname}-backend"
      image = local.backend_image

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }

      startup_probe {
        http_get {
          path = "/health_check"
          port = 8081
        }
      }
      env {
        name  = "SERVER_PORT"
        value = "8081"
      }
      env {
        name  = "DATA_DIR"
        value = "/data"
      }
      volume_mounts {
        name       = "${local.project_shortname}-data-bucket"
        mount_path = "/data"
      }
    }

    volumes {
      name = "${local.project_shortname}-data-bucket"
      gcs {
        bucket    = google_storage_bucket.ocw-data.name
        read_only = true
      }
    }
  }
}

resource "terraform_data" "init_push_frontend" {
  depends_on = [google_artifact_registry_repository.ocw_repository]

  triggers_replace = [
    google_artifact_registry_repository.ocw_repository.create_time,
    filesha1(local.frontend_dockerfile),
    sha1(join("", [for f in fileset("${local.frontend_source}", "**") : filesha1("${local.frontend_source}/${f}")])),
  ]

  provisioner "local-exec" {
    command = "docker buildx build --platform ${local.frontend_image_platform} --push -t ${local.frontend_image} -f ${local.frontend_dockerfile} ."
  }
}

resource "terraform_data" "init_push_backend" {
  depends_on = [google_artifact_registry_repository.ocw_repository]

  triggers_replace = [
    google_artifact_registry_repository.ocw_repository.create_time,
    filesha1(local.backend_dockerfile),
    sha1(join("", [for f in fileset("${local.backend_source}", "**") : filesha1("${local.backend_source}/${f}")]))
  ]

  provisioner "local-exec" {
    command = "docker buildx build --platform ${local.backend_image_platform} --push -t ${local.backend_image} -f ${local.backend_dockerfile} ."
  }
}

resource "google_artifact_registry_repository" "ocw_repository" {
  location      = var.gcloud_region
  format        = "DOCKER"
  repository_id = local.project_shortname
}
