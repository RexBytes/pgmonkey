pipeline {
    agent any
    environment {
        PIP_NO_CACHE_DIR = "off"
    }
    stages {
        // Matrix for Python 3.12.x (newer versions of dependencies)
        stage('Matrix Python 3.12') {
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
                        values '6.0.2'
                    }
                }
                stages {
                    stage('Setup Python Environment') {
                        steps {
                            script {
                                sh """
                                    # Clean up any existing venv
                                    rm -rf venv

                                    # Set up pyenv
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Set up venv and install dependencies
                                    python -m venv venv
                                    . venv/bin/activate
                                    pip install --upgrade pip setuptools wheel Cython

                                    # Install specific versions
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                    # Run tests
                                    pytest tests/

                                    # Clean up venv
                                    deactivate
                                    rm -rf venv
                                """
                            }
                        }
                    }
                }
            }
        }

        // Matrix for Python 3.11.x (compatible with slightly older dependencies)
        stage('Matrix Python 3.11') {
            matrix {
                axes {
                    axis {
                        name 'PYTHON_VERSION'
                        values '3.11.9'
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
                                    # Clean up any existing venv
                                    rm -rf venv

                                    # Set up pyenv
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Set up venv and install dependencies
                                    python -m venv venv
                                    . venv/bin/activate
                                    pip install --upgrade pip setuptools wheel Cython

                                    # Install specific versions
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                    # Run tests
                                    pytest tests/

                                    # Clean up venv
                                    deactivate
                                    rm -rf venv
                                """
                            }
                        }
                    }
                }
            }
        }

        // Matrix for Python 3.10.x and 3.9.x (older and newer dependencies allowed)
        stage('Matrix Python 3.10 and 3.9') {
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
                                    # Clean up any existing venv
                                    rm -rf venv

                                    # Set up pyenv
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Set up venv and install dependencies
                                    python -m venv venv
                                    . venv/bin/activate
                                    pip install --upgrade pip setuptools wheel Cython

                                    # Install specific versions
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                    # Run tests
                                    pytest tests/

                                    # Clean up venv
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
            archiveArtifacts artifacts: 'test_results.csv', allowEmptyArchive: true
        }
    }
}




