pipeline {
    agent any
    environment {
        PIP_NO_CACHE_DIR = "off"
    }
    stages {
        // Cleanup workspace
        stage('Cleanup Workspace') {
            steps {
                deleteDir() // Clean the workspace entirely before each build
            }
        }

        // Checkout the latest code from SCM
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }

        // Matrix for Python 3.12.5
        stage('Matrix Python 3.12.5') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.12.5'
                    }
                    axis {
                        name 'PSYCOPG_VERSION'
                        values '3.2.1', '3.1.20', '3.0.18'
                    }
                    axis {
                        name 'PSYCOPG_POOL_VERSION'
                        values '3.2.2', '3.1.9', '3.0.3'
                    }
                    axis {
                        name 'PYAML_VERSION'
                        values '6.0.2', '5.4.1', '5.3.1'
                    }
                }
                stages {
                    stage('Setup Python Environment') {
                        steps {
                            script {
                                sh """
                                    # Ensure clean environment
                                    rm -rf venv

                                    # Set up pyenv and install the specific Python version
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install the specified Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}
                                    pyenv rehash

                                    # Create and activate a virtual environment
                                    python -m venv venv
                                    . venv/bin/activate

                                    # Install the specific versions of dependencies
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION}
                                """
                            }
                        }
                    }

                    // Run unit tests
                    stage('Run Unit Tests') {
                        steps {
                            script {
                                sh """
                                    . venv/bin/activate
                                    pytest tests/
                                """
                            }
                        }
                    }

                    // Run integration tests
                    stage('Run Integration Tests') {
                        steps {
                            script {
                                sh """
                                    . venv/bin/activate
                                    pytest src/tests/integration/test_pgconnection_manager_integration.py
                                """
                            }
                        }
                    }

                    // Clean up virtual environment after testing
                    stage('Clean Up Virtual Environment') {
                        steps {
                            sh """
                                deactivate
                                rm -rf venv
                            """
                        }
                    }
                }
            }
        }

        // Matrix for Python 3.11.9
        stage('Matrix Python 3.11.9') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.11.9'
                    }
                    axis {
                        name 'PSYCOPG_VERSION'
                        values '3.2.1', '3.1.20', '3.0.18'
                    }
                    axis {
                        name 'PSYCOPG_POOL_VERSION'
                        values '3.2.2', '3.1.9', '3.0.3'
                    }
                    axis {
                        name 'PYAML_VERSION'
                        values '6.0.2', '5.4.1', '5.3.1'
                    }
                }
                stages {
                    stage('Setup Python Environment') {
                        steps {
                            script {
                                sh """
                                    # Ensure clean environment
                                    rm -rf venv

                                    # Set up pyenv and install the specific Python version
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install the specified Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}
                                    pyenv rehash

                                    # Create and activate a virtual environment
                                    python -m venv venv
                                    . venv/bin/activate

                                    # Install the specific versions of dependencies
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION}
                                """
                            }
                        }
                    }

                    // Run unit tests
                    stage('Run Unit Tests') {
                        steps {
                            script {
                                sh """
                                    . venv/bin/activate
                                    pytest tests/
                                """
                            }
                        }
                    }

                    // Run integration tests
                    stage('Run Integration Tests') {
                        steps {
                            script {
                                sh """
                                    . venv/bin/activate
                                    pytest src/tests/integration/test_pgconnection_manager_integration.py
                                """
                            }
                        }
                    }

                    // Clean up virtual environment after testing
                    stage('Clean Up Virtual Environment') {
                        steps {
                            sh """
                                deactivate
                                rm -rf venv
                            """
                        }
                    }
                }
            }
        }

        // Matrix for Python 3.10.14
        stage('Matrix Python 3.10.14') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.10.14'
                    }
                    axis {
                        name 'PSYCOPG_VERSION'
                        values '3.2.1', '3.1.20', '3.0.18'
                    }
                    axis {
                        name 'PSYCOPG_POOL_VERSION'
                        values '3.2.2', '3.1.9', '3.0.3'
                    }
                    axis {
                        name 'PYAML_VERSION'
                        values '6.0.2', '5.4.1', '5.3.1'
                    }
                }
                stages {
                    stage('Setup Python Environment') {
                        steps {
                            script {
                                sh """
                                    # Ensure clean environment
                                    rm -rf venv

                                    # Set up pyenv and install the specific Python version
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install the specified Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}
                                    pyenv rehash

                                    # Create and activate a virtual environment
                                    python -m venv venv
                                    . venv/bin/activate

                                    # Install the specific versions of dependencies
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION}
                                """
                            }
                        }
                    }

                    // Run unit tests
                    stage('Run Unit Tests') {
                        steps {
                            script {
                                sh """
                                    . venv/bin/activate
                                    pytest tests/
                                """
                            }
                        }
                    }

                    // Run integration tests
                    stage('Run Integration Tests') {
                        steps {
                            script {
                                sh """
                                    . venv/bin/activate
                                    pytest src/tests/integration/test_pgconnection_manager_integration.py
                                """
                            }
                        }
                    }

                    // Clean up virtual environment after testing
                    stage('Clean Up Virtual Environment') {
                        steps {
                            sh """
                                deactivate
                                rm -rf venv
                            """
                        }
                    }
                }
            }
        }

        // Matrix for Python 3.9.19
        stage('Matrix Python 3.9.19') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.9.19'
                    }
                    axis {
                        name 'PSYCOPG_VERSION'
                        values '3.2.1', '3.1.20', '3.0.18'
                    }
                    axis {
                        name 'PSYCOPG_POOL_VERSION'
                        values '3.2.2', '3.1.9', '3.0.3'
                    }
                    axis {
                        name 'PYAML_VERSION'
                        values '6.0.2', '5.4.1', '5.3.1'
                    }
                }
                stages {
                    stage('Setup Python Environment') {
                        steps {
                            script {
                                sh """
                                    # Ensure clean environment
                                    rm -rf venv

                                    # Set up pyenv and install the specific Python version
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install the specified Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}
                                    pyenv rehash

                                    # Create and activate a virtual environment
                                    python -m venv venv
                                    . venv/bin/activate

                                    # Install the specific versions of dependencies
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION}
                                """
                            }
                        }
                    }

                    // Run unit tests
                    stage('Run Unit Tests') {
                        steps {
                            script {
                                sh """
                                    . venv/bin/activate
                                    pytest tests/
                                """
                            }
                        }
                    }

                    // Run integration tests
                    stage('Run Integration Tests') {
                        steps {
                            script {
                                sh """
                                    . venv/bin/activate
                                    pytest src/tests/integration/test_pgconnection_manager_integration.py
                                """
                            }
                        }
                    }

                    // Clean up virtual environment after testing
                    stage('Clean Up Virtual Environment') {
                        steps {
                            sh """
                                deactivate
                                rm -rf venv
                            """
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            // Archive the test result artifacts
            archiveArtifacts artifacts: 'test_results.csv', allowEmptyArchive: true
        }
    }
}



