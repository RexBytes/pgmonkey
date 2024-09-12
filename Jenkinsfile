pipeline {
    agent any
    environment {
        PIP_NO_CACHE_DIR = "off"
    }
    stages {
        // First batch of combinations (2 Python, 2 psycopg, 2 psycopg_pool, 2 PyYAML)
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

        // Second batch of combinations
        stage('Matrix Batch 2') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.12.3', '3.11.9'
                    }
                    axis {
                        name 'PSYCOPG_VERSION'
                        values '3.0.18', '3.1.20'
                    }
                    axis {
                        name 'PSYCOPG_POOL_VERSION'
                        values '3.0.3', '3.2.2'
                    }
                    axis {
                        name 'PYAML_VERSION'
                        values '5.3.1', '6.0.2'
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

        // Third batch of combinations
        stage('Matrix Batch 3') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.10.14', '3.9.19'
                    }
                    axis {
                        name 'PSYCOPG_VERSION'
                        values '3.2.1', '3.1.20'
                    }
                    axis {
                        name 'PSYCOPG_POOL_VERSION'
                        values '3.1.9', '3.0.3'
                    }
                    axis {
                        name 'PYAML_VERSION'
                        values '6.0.2', '5.3.1'
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

        // Fourth batch of combinations
        stage('Matrix Batch 4') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.8.19', '3.7.9'
                    }
                    axis {
                        name 'PSYCOPG_VERSION'
                        values '3.0.18', '3.1.20'
                    }
                    axis {
                        name 'PSYCOPG_POOL_VERSION'
                        values '3.2.2', '3.1.9'
                    }
                    axis {
                        name 'PYAML_VERSION'
                        values '5.4.1', '6.0.2'
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
    }
    post {
        always {
            // Archive the CSV file
            archiveArtifacts artifacts: 'test_results.csv', allowEmptyArchive: true
        }
    }
}
