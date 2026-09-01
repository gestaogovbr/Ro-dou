{{/*
Expand the name of the chart.
*/}}
{{- define "ro-dou.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ro-dou.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ro-dou.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ro-dou.labels" -}}
helm.sh/chart: {{ include "ro-dou.chart" . }}
{{ include "ro-dou.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ro-dou.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ro-dou.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Name of the PVC shared by git-rsync and the Airflow workloads.
*/}}
{{- define "ro-dou.gitRsync.claimName" -}}
{{- default (printf "%s-dag-confs-pvc" (include "ro-dou.fullname" .)) .Values.gitRsync.persistence.existingClaim -}}
{{- end }}

{{/*
Shell snippet that blocks until the Postgres service is accepting TCP connections.
Hooks only guarantee Postgres has been created, not that it is ready, so jobs that
talk to it must wait themselves.
*/}}
{{- define "ro-dou.waitForPostgres" -}}
until (exec 3<>/dev/tcp/{{ include "ro-dou.fullname" . }}-postgres/{{ .Values.postgres.service.port }}) 2>/dev/null; do
  echo "Waiting for PostgreSQL to be reachable..."
  sleep 3
done
{{- end }}
