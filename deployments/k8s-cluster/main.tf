terraform {
  required_version = ">= 1.6"
}

resource "null_resource" "juju_add_k8s" {
  provisioner "local-exec" {
    command = <<-EOT
      TMPFILE=$(mktemp --tmpdir=./)
      sudo k8s kubectl config view --raw > $TMPFILE
      KUBECONFIG=$TMPFILE juju add-k8s --client  ${var.cluster_name} --storage=csi-rawfile-default
    EOT
  }
}

resource "null_resource" "juju_bootstrap_k8s" {
  provisioner "local-exec" {
    command = <<-EOT
      set -x
      juju show-controller ${var.cluster_name} || juju bootstrap  ${var.cluster_name}
    EOT
  }
}
