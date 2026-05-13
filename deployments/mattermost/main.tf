terraform {
  required_version = ">= 1.6"
  required_providers {
    juju = {
      source  = "juju/juju"
      version = "~> 0.14"
    }
  }
}

provider "juju" {}

resource "juju_model" "mattermost" {
  name = var.model_name

  cloud {
    name = var.k8s_cloud_name
  }

  config = {
    logging-config              = "<root>=INFO"
    update-status-hook-interval = "5m"
  }
}

resource "juju_application" "postgresql" {
  name = "postgresql"

  model = juju_model.mattermost.name

  charm {
    name    = "postgresql-k8s"
    channel = "14/stable"
  }

  trust = true
  units = 1
}

resource "juju_application" "mattermost" {
  name = "mattermost"

  model = juju_model.mattermost.name

  charm {
    name    = "mattermost-k8s"
    channel = "latest/stable"
  }

  units = 1

  config = {
    site_url             = var.site_url
    tls_secret_name      = var.tls_secret_name
    s3_enabled           = var.s3_enabled
    s3_bucket            = var.s3_bucket
    s3_access_key_id     = var.s3_access_key_id
    s3_secret_access_key = var.s3_secret_access_key
    s3_endpoint          = var.s3_endpoint
    s3_region            = var.s3_region
    debug                = var.mattermost_debug
  }
}

resource "juju_integration" "mattermost_db" {
  model = juju_model.mattermost.name

  application {
    name     = juju_application.mattermost.name
    endpoint = "db"
  }

  application {
    name     = juju_application.postgresql.name
    endpoint = "database"
  }

  lifecycle {
    replace_triggered_by = [
      juju_application.mattermost.charm,
      juju_application.postgresql.charm,
    ]
  }
}
