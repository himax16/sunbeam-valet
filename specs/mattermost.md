# Mattermost on Canonical Kubernetes — Deployment Spec

Deploy Mattermost on [Canonical K8s](https://snapcraft.io/k8s) (snap) using the [`mattermost-k8s`](https://charmhub.io/mattermost-k8s) Juju charm, orchestrated end-to-end with Terraform and Terragrunt via the [Terraform Juju provider](https://github.com/juju/terraform-provider-juju).

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Juju Controller (existing)                  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            Juju Model (mattermost)                       │ │
│  │                                                          │ │
│  │  ┌──────────────┐    pgsql    ┌──────────────────┐      │ │
│  │  │ mattermost   │◄────────────│  postgresql-k8s  │      │ │
│  │  │ (k8s charm)  │    db:int   │  (14/stable)     │      │ │
│  │  └──────┬───────┘             └──────────────────┘      │ │
│  │         │                                                 │ │
│  │    config: site_url, s3_*, tls_secret_name                │ │
│  └─────────┼─────────────────────────────────────────────────┘ │
└────────────┼───────────────────────────────────────────────────┘
             │ cloud: canonical
     ┌───────▼────────┐
     │ Canonical K8s  │
     │ (snap k8s)     │
     └────────────────┘
```

- **mattermost-k8s**: single k8s charm, listens on port `8065` (HTTP). Talks to PostgreSQL and an optional S3-compatible filestore.
- **postgresql-k8s** (`14/stable`): the only **required** Juju relation (`db`, interface `pgsql`). Deploy with `--trust`.
- **S3 storage**: configured via charm config keys — **not** a Juju relation. No separate S3 charm required.
- **Ingress / TLS**: configured via `site_url` and `tls_secret_name` config keys — **not** a Juju relation. The charm manages its own Kubernetes Ingress and expects the TLS secret to already exist in the namespace.

## Prerequisites

| Component               | Version / Source                                     |
|-------------------------|------------------------------------------------------|
| Juju controller         | **must already exist** (bootstrapped and accessible) |
| Juju                    | ≥ 3.6                                                |
| Terraform               | ≥ 1.6                                                |
| Terragrunt              | latest                                               |
| Terraform Juju provider | `juju/juju` ~> 0.14                                  |
| `kubectl`               | latest                                               |

### Terraform Juju provider authentication

The provider auto-detects credentials from the `juju` CLI client's current context. Static credentials or env vars (`JUJU_CONTROLLER_ADDRESSES`, `JUJU_USERNAME`, `JUJU_PASSWORD`, `JUJU_CA_CERT`) are alternatives — see the [provider docs](https://registry.terraform.io/providers/juju/juju/latest/docs).

## Module layout

```
deployments/
├── k8s-cluster/
│   ├── terragrunt.hcl
│   ├── main.tf                  # juju add-k8s
│   ├── variables.tf
│   ├── outputs.tf
└── mattermost/
    ├── terragrunt.hcl
    ├── main.tf                  # juju_model, juju_application × 2, juju_integration
    ├── variables.tf
    ├── outputs.tf
    └── terraform.tfvars
```

Apply order: `k8s-cluster` → `mattermost`. Each module uses a **local** state file (`terraform.tfstate`) co-located in its directory — no external services required.

---

## Module 1: Juju cloud registration

Registers the pre-existing Canonical K8s cluster as a Juju k8s cloud via `juju add-k8s`.


### Register Canonical K8s cluster as a Juju cloud

```
resource "null_resource" "juju_add_k8s" {
  provisioner "local-exec" {
    command = <<-EOT
      TMPFILE=$(mktemp --tmpdir=./)
      k8s kubectl config view --raw > $TMPFILE
      KUBECONFIG=$TMPFILE juju add-k8s ${var.cluster_name} --storage=hostpath || true
    EOT
  }
}
```


---

## Module 2: Mattermost on Juju

Deploys `mattermost-k8s` + `postgresql-k8s` into a Juju model on the Canonical K8s cloud registered by Module 1.

### `deployments/mattermost/main.tf`

```hcl
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
```

### `deployments/mattermost/variables.tf`

```hcl
variable "model_name" {
  type    = string
  default = "mattermost"
}

variable "k8s_cloud_name" {
  type        = string
  description = "Name of the K8s cloud registered in Juju (matches cluster_name from Module 1)"
}

variable "site_url" {
  type        = string
  description = "Public URL for Mattermost (e.g. https://chat.example.com)"
}

variable "tls_secret_name" {
  type        = string
  default     = ""
  description = "Kubernetes TLS secret name (only used when site_url starts with https)"
}

variable "s3_enabled" {
  type    = bool
  default = false
}
variable "s3_bucket" {
  type    = string
  default = ""
}
variable "s3_access_key_id" {
  type      = string
  default   = ""
  sensitive = true
}
variable "s3_secret_access_key" {
  type      = string
  default   = ""
  sensitive = true
}
variable "s3_endpoint" {
  type    = string
  default = "s3.amazonaws.com"
}
variable "s3_region" {
  type    = string
  default = ""
}
variable "mattermost_debug" {
  type    = bool
  default = false
}
```

### `deployments/mattermost/terragrunt.hcl`

```hcl
terraform {
  source = "."
}

inputs = {
  k8s_cloud_name  = "canonical"
  site_url        = "https://chat.example.com"
  tls_secret_name = "mattermost-tls"
  s3_enabled      = true
  s3_bucket       = "mattermost-files"
  s3_endpoint     = "https://s3.example.com"
  s3_region       = "us-east-1"
}
```

### `deployments/mattermost/outputs.tf`

```hcl
output "model_name" {
  value = juju_model.mattermost.name
}

output "site_url" {
  value = var.site_url
}
```

## Deployment order

1. **Register K8s cluster**:
   ```bash
   cd deployments/k8s-cluster
   terragrunt init
   terragrunt apply
   ```

2. **Verify cluster is registered in Juju:**
   ```bash
   juju clouds | grep canonical
   kubectl get nodes
   ```

3. **TLS secret** (if using HTTPS) — create before deploying Mattermost:
   ```bash
   kubectl create secret tls mattermost-tls \
     --cert=path/to/tls.crt --key=path/to/tls.key \
     -n mattermost
   ```
   > The `mattermost` namespace will be created by Juju when the model is created. If creating the secret before the model exists, pre-create the namespace.

4. **Deploy Mattermost:**
   ```bash
   cd deployments/mattermost
   terragrunt init
   terragrunt plan
   terragrunt apply
   ```

5. **Post-deploy** — grant the initial admin user:
   ```bash
   juju run mattermost/0 grant-admin-role user=admin
   ```

## Verification

```bash
juju status --model mattermost --watch 5s
# wait for all units "active" / "idle"

juju status --model mattermost --relations
# verify db relation is "joined" or "active"

curl -I https://chat.example.com
# expect HTTP 200
```

## Key gotchas

### Mattermost / Juju module
- **No ingress/Traefik charm needed.** The charm creates its own Kubernetes Ingress. `tls_secret_name` must reference a secret that *already exists* in the model namespace. The charm does not provision TLS certs.
- **S3 is config-only.** `s3_enabled = true` with valid credentials is sufficient — no Juju S3 charm or relation required.
- **Only one database relation.** The `db` endpoint has `limit: 1` — you cannot relate to multiple PostgreSQL backends.
- **`postgresql-k8s` requires `--trust`.** Set `trust = true` on the `juju_application` resource or the charm will fail.
- **`units` vs `machines` are mutually exclusive** on `juju_application`. For k8s charms, use `units` only.
- **Juju controller must already exist.** The Terraform Juju provider cannot bootstrap a controller.
- **Sensitive values.** Mark S3 keys and passwords as `sensitive = true` in variables to avoid them appearing in plan output.
- **State files are local and co-located.** Each module stores `terraform.tfstate` in its own directory. For team workflows, commit them to version control or place on a shared filesystem.

## References

- [mattermost-k8s Charmhub](https://charmhub.io/mattermost-k8s)
- [Terraform Juju Provider](https://github.com/juju/terraform-provider-juju)
- [Canonical K8s snap](https://snapcraft.io/k8s)
- [postgresql-k8s Charmhub](https://charmhub.io/postgresql-k8s)
