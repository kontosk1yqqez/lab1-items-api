{{- define "items-app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "items-app.fullname" -}}
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

{{- define "items-app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "items-app.labels" -}}
helm.sh/chart: {{ include "items-app.chart" . }}
app.kubernetes.io/part-of: {{ include "items-app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Селектор компонента: include "items-app.selector" (dict "ctx" $ "component" "api") */}}
{{- define "items-app.selector" -}}
app.kubernetes.io/name: {{ include "items-app.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/* Повне ім'я образу: include "items-app.image" (dict "ctx" $ "image" .Values.api.image) */}}
{{- define "items-app.image" -}}
{{- $repo := .image.repository -}}
{{- if and .ctx.Values.imageRegistry (not (contains "/" $repo)) -}}
{{- $repo = printf "%s/%s" .ctx.Values.imageRegistry $repo -}}
{{- end -}}
{{- printf "%s:%s" $repo (toString .image.tag) -}}
{{- end }}

{{- define "items-app.api.fullname" -}}{{ include "items-app.fullname" . }}-{{ .Values.api.name }}{{- end }}
{{- define "items-app.frontend.fullname" -}}{{ include "items-app.fullname" . }}-{{ .Values.frontend.name }}{{- end }}
{{- define "items-app.db.fullname" -}}{{ include "items-app.fullname" . }}-{{ .Values.db.name }}{{- end }}

{{- define "items-app.db.secretName" -}}
{{- default (printf "%s-secret" (include "items-app.db.fullname" .)) .Values.db.existingSecret }}
{{- end }}

{{- define "items-app.storageClassName" -}}
{{- if .Values.db.persistence.createStorageClass -}}
{{ include "items-app.fullname" . }}-sc
{{- else -}}
{{ .Values.db.persistence.storageClassName }}
{{- end -}}
{{- end }}
