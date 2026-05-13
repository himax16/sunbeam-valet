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
