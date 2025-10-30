"""
Test to verify that Airflow DAGs are loading without errors.

This test module validates that all dynamically generated DAGs from YAML
configuration files can be imported and instantiated without raising
exceptions, ensuring the DAG loading mechanism works correctly.
"""

import os
import sys
import importlib
import pytest
from unittest.mock import patch, Mock
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dou_dag_generator import DouDigestDagGenerator
from airflow import DAG
from airflow.models import Variable, DagBag


class TestDAGLoading:
    """Test suite for DAG loading functionality."""

    def setup_method(self):
        """Setup method called before each test."""
        self.dag_generator = DouDigestDagGenerator()

    @patch('dou_dag_generator.Variable')
    @patch('airflow.hooks.base.BaseHook.get_connection')
    def test_all_dags_load_without_errors(self, mock_get_connection, mock_variable):
        """
        Test that all DAGs defined in YAML config files can be loaded without errors.
        
        This test:
        1. Mocks external dependencies (Airflow Variables, DB connections)
        2. Attempts to generate all DAGs from YAML configs
        3. Verifies that DAGs are created successfully
        4. Ensures no exceptions are raised during DAG generation
        """
        # Mock Airflow Variable.get to return dummy data
        mock_variable.get.return_value = '["test_term_1", "test_term_2"]'
        
        # Mock database connection for external DB queries
        mock_conn = Mock()
        mock_conn.conn_type = 'postgresql'
        mock_get_connection.return_value = mock_conn

        original_globals = dict(globals())
        
        # Carregar todas as DAGs
        dag_bag = DagBag()

        try:
            self.dag_generator.generate_dags()
            
            dag_count = 0
            for dag_id, dag in dag_bag.dags.items():
                if isinstance(dag, DAG) and dag_id not in original_globals:
                    dag_count += 1
                    # Verifique as propriedades básicas do DAG
                    assert dag.dag_id is not None
                    assert dag.description is not None

            assert dag_count > 0, "Nenhuma DAG foi gerada a partir dos arquivos de configuração YAML"

        finally:
            for name in list(globals().keys()):
                if name not in original_globals and isinstance(globals().get(name), DAG):
                    del globals()[name]

    def test_yaml_config_files_exist(self):
        """Test that YAML configuration files exist in expected directories."""
        yaml_files_found = []
        
        for directory in self.dag_generator.YAMLS_DIR_LIST:
            if os.path.exists(directory):
                for dirpath, _, filenames in os.walk(directory):
                    for filename in filenames:
                        if any(ext in filename for ext in [".yaml", ".yml"]):
                            yaml_files_found.append(os.path.join(dirpath, filename))
        
        assert len(yaml_files_found) > 0, f"Nenhum arquivo de configuração YAML encontrado nos diretórios: {self.dag_generator.YAMLS_DIR_LIST}"

    @patch('dou_dag_generator.Variable')
    @patch('airflow.hooks.base.BaseHook.get_connection')
    def test_individual_dag_creation(self, mock_get_connection, mock_variable):
        """
        Test that individual DAGs can be created from valid YAML configs.
        
        This test picks a specific YAML config file and verifies it can
        create a valid DAG object.
        """
        mock_variable.get.return_value = '["test_term"]'
        mock_conn = Mock()
        mock_conn.conn_type = 'postgresql'
        mock_get_connection.return_value = mock_conn

        test_yaml_file = None
        for directory in self.dag_generator.YAMLS_DIR_LIST:
            if os.path.exists(directory):
                for dirpath, _, filenames in os.walk(directory):
                    for filename in filenames:
                        if filename.endswith(('.yaml', '.yml')) and 'basic_example' in filename:
                            test_yaml_file = os.path.join(dirpath, filename)
                            break
                    if test_yaml_file:
                        break
                if test_yaml_file:
                    break

        if test_yaml_file and os.path.exists(test_yaml_file):
            dag_specs = self.dag_generator.parser(test_yaml_file).parse()
            dag = self.dag_generator.create_dag(dag_specs, test_yaml_file)
            
            assert isinstance(dag, DAG)
            assert dag.dag_id == dag_specs.id
            assert dag.description == dag_specs.description
            assert len(dag.tasks) > 0, "A DAG deve ter pelo menos uma tarefa"
        else:
            pytest.skip("Nenhum arquivo YAML de teste adequado encontrado")

    def test_dag_generator_initialization(self):
        """Test that the DAG generator initializes correctly."""
        assert self.dag_generator is not None
        assert hasattr(self.dag_generator, 'YAMLS_DIR_LIST')
        assert hasattr(self.dag_generator, 'generate_dags')
        assert hasattr(self.dag_generator, 'create_dag')

    @patch('dou_dag_generator.Variable')
    def test_dag_generation_handles_missing_variables(self, mock_variable):
        """
        Test that DAG generation handles missing Airflow variables.
        
        Some DAGs may reference Airflow variables that don't exist during testing.
        This test ensures the system handles such cases appropriately.
        """
        # Mock Variable.get to raise KeyError (variable not found)
        mock_variable.get.side_effect = KeyError("Variable not found")
        
        # Find YAML files that might use variables
        variable_yaml_files = []
        for directory in self.dag_generator.YAMLS_DIR_LIST:
            if os.path.exists(directory):
                for dirpath, _, filenames in os.walk(directory):
                    for filename in filenames:
                        if 'variable' in filename.lower() and filename.endswith(('.yaml', '.yml')):
                            variable_yaml_files.append(os.path.join(dirpath, filename))
        
        if variable_yaml_files:
            for yaml_file in variable_yaml_files[:1]:
                try:
                    dag_specs = self.dag_generator.parser(yaml_file).parse()
                    dag = self.dag_generator.create_dag(dag_specs, yaml_file)
                    assert isinstance(dag, DAG)
                except (KeyError, Exception) as e:
                    assert "Não encontrado" in str(e).lower() or "variável" in str(e).lower()
        else:
            pytest.skip("Nenhum arquivo YAML baseado em variáveis encontrado para teste")