pipeline {
    agent any
    environment {
        PIP_NO_CACHE_DIR = "off"
    }
    stages {
        stage('Matrix Batch 1') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.12.5', '3.12.4'
                    }
                    axis {
                        name 'PSYCOPG_VERSION'
                        values '3.2.1', '3.1.20'
                    }
                    axis {
                        name 'PSYCOPG_POOL_VERSION'
                        values '3.2.2', '3.1.9'
                    }
                    axis {
                        name 'PYAML_VERSION'
                        values '6.0.2', '5.4.1'
                    }
                }
                stages {
                    stage('Setup Python Environment') {
                        steps {
                            script {
                                sh """
                                    # Set up pyenv
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install the specific Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Create and activate a virtual environment
                                    python -m venv venv
                                    . venv/bin/activate

                                    # Install the specific versions of dependencies
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION}

                                    # Ensure pytest is installed
                                    pip install pytest

                                    # Run tests
                                    pytest tests/

                                    # Clean up
                                    deactivate
                                    rm -rf venv
                                """
                            }
                        }
                    }
                }
            }
        }
        // Other stages remain the same...
    }
    post {
        always {
            // Archive the CSV file
            archiveArtifacts artifacts: 'test_results.csv', allowEmptyArchive: true
        }
    }
}
