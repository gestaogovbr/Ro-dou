# Ro-dou Helm Chart

This Helm chart deploys the Ro-dou project on Kubernetes, including Airflow, PostgreSQL, and SMTP4Dev.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+

## Installing the Chart

To install the chart with the release name `my-release`:

```bash
helm install my-release ./helm/ro-dou
```

## Uninstalling the Chart

To uninstall the chart:

```bash
helm uninstall my-release
```

## Configuration

The following table lists the configurable parameters of the Ro-dou chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `airflow.image.repository` | Airflow image repository | `ghcr.io/gestaogovbr/ro-dou` |
| `airflow.image.tag` | Airflow image tag | `latest` |
| `airflow.apiServer.replicas` | Number of API server replicas | `1` |
| `airflow.scheduler.replicas` | Number of scheduler replicas | `1` |
| `airflow.dagProcessor.replicas` | Number of DAG processor replicas | `1` |
| `postgres.image.repository` | PostgreSQL image repository | `postgres` |
| `postgres.image.tag` | PostgreSQL image tag | `"15"` |
| `smtp4dev.image.repository` | SMTP4Dev image repository | `rnwood/smtp4dev` |
| `smtp4dev.image.tag` | SMTP4Dev image tag | `v3` |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`.

Alternatively, a YAML file that specifies the values for the parameters can be provided while installing the chart.

```bash
helm install my-release ./helm/ro-dou -f ./helm/ro-dou/values.yaml
```

## Services

- **Airflow API Server**: Accessible on port 8080 (Airflow 3 UI/API, formerly the webserver)
- **PostgreSQL**: Accessible on port 5432
- **SMTP4Dev**: Web UI on port 5001, SMTP on port 25, IMAP on port 143

This chart deploys Airflow 3, which requires a separate DAG Processor component (`airflow.dagProcessor`) in addition to the scheduler and API server.

## Persistence

The chart uses Persistent Volume Claims for storing Airflow logs and PostgreSQL data.

## Secrets

Update the `airflow.secrets` and `postgres.secrets` in `values.yaml` with your actual credentials before deployment.