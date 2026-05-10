{{/*
Expand the name of the chart.
*/}}
{{- define "mem0-mcp-server.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "mem0-mcp-server.fullname" -}}
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
Common labels
*/}}
{{- define "mem0-mcp-server.labels" -}}
helm.sh/chart: {{ include "mem0-mcp-server.chart" . }}
{{ include "mem0-mcp-server.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mem0-mcp-server.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mem0-mcp-server.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create chart version
*/}}
{{- define "mem0-mcp-server.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
ServiceAccount name
*/}}
{{- define "mem0-mcp-server.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- include "mem0-mcp-server.fullname" . -}}
{{- else }}
{{- .Values.serviceAccount.name | default "default" }}
{{- end }}
{{- end }}
