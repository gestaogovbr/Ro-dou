# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ro-DOU is a tool that performs clipping of the Diário Oficial da União (D.O.U.) and municipal official gazettes through Querido Diário. It enables receiving notifications (via email, Slack, Discord, or other channels) for all publications containing specified keywords.

The system is built on Apache Airflow and uses dynamic DAG generation based on YAML configuration files. Each DAG configuration file in `dag_confs/` automatically generates an Airflow DAG that:
1. Searches for terms in official publications
2. Processes and formats results
3. Sends notifications through configured channels

## Architecture

- **Core Engine**: `src/dou_dag_generator.py` - Dynamic DAG generator that creates Airflow DAGs from YAML configs
- **Search Systems**: 
  - `src/searchers.py` - Base searcher classes and implementations (DOUSearcher, QDSearcher, INLABSSearcher)
  - `src/hooks/` - Custom Airflow hooks for DOU and INLabs integration
- **Notification System**: `src/notification/` - Multi-channel notification system (email, Slack, Discord)
- **Configuration**: `src/parsers.py` and `src/schemas.py` - YAML config parsing and validation
- **DAG Configs**: `dag_confs/` - YAML files that define search parameters and notification settings

## Development Commands

### Environment Setup
```bash
make run  # Full setup: creates containers, variables, connections, and activates DAGs
make down # Stop all containers
```

### Testing
```bash
make tests  # Run pytest inside the airflow-webserver container
```

### Container Management
```bash
docker compose up -d --force-recreate --remove-orphans  # Start containers
docker exec airflow-webserver sh -c "command"  # Execute commands in webserver
```

### Airflow Access
- Web UI: http://localhost:8080 (airflow/airflow)
- SMTP Debug UI: http://localhost:5001
- PostgreSQL: localhost:5432 (airflow/airflow)

## YAML Configuration System

DAG configurations are stored in `dag_confs/` and automatically generate Airflow DAGs. Key structure:
- `dag.id` - Unique DAG identifier
- `dag.search.terms` - List of search terms
- `dag.report.emails` - Notification email addresses
- `dag.search.sources` - Publication sources (DOU sections, QD territories, INLabs)

Examples available in `dag_confs/examples_and_tests/`.

## Key Dependencies

- **Apache Airflow 2.10.0** with Python 3.10
- **pandas** for data processing
- **requests** for API calls
- **html2text** and **markdown** for content formatting
- **jsonschema** and **PyYAML** for configuration validation

## Database Integration

- **PostgreSQL**: Primary database for Airflow metadata and INLabs data storage
- **INLabs Integration**: Separate database schema for storing publication data
- Connection setup handled automatically by `make run`

## Testing Framework

Uses pytest with comprehensive test coverage:
- DAG generation tests
- Searcher functionality tests  
- Notification system tests
- YAML schema validation tests

Run tests with `make tests` or directly via pytest in the container.