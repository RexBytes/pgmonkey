pipeline {
    agent any
    environment {
        PIP_NO_CACHE_DIR = "off"
        PYTHONPATH = "${WORKSPACE}:$PYTHONPATH" // Add the workspace root to PYTHONPATH
    }
    stages {
        // Checkout the code from the repository
        stage('Checkout Code') {
            steps {
                script {
                    checkout scm
                }
            }
        }
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
                                // Define the virtual environment name in Groovy
                                def VENV_NAME = "pgmonkey_venv_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}"

                                sh """
                                    # Generate a unique virtual environment name based on the matrix parameters
                                    export VENV_NAME=${VENV_NAME}

                                    # Ensure pyenv is initialized properly
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Check if the virtual environment already exists
                                    if pyenv virtualenvs | grep -q "${VENV_NAME}"; then
                                        echo "${VENV_NAME} already exists. Activating..."
                                        pyenv activate ${VENV_NAME}
                                    else
                                        # Create a new virtual environment if it doesn't exist
                                        echo "Creating new virtual environment: ${VENV_NAME}..."
                                        pyenv virtualenv ${PYTHON_VERSION} ${VENV_NAME}
                                        pyenv activate ${VENV_NAME}

                                        # Upgrade pip, setuptools, and wheel
                                        python -m pip install --upgrade pip setuptools wheel

                                        # Install dependencies
                                        pip install psycopg[binary]==${PSYCOPG_VERSION}
                                        pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                        pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                        # Install pytest and testing dependencies
                                        pip install pytest==8.3.3 pytest-asyncio==0.17.0

                                        # Install the project itself (editable mode)
                                        pip install -e .
                                    fi

                                    # Run tests
                                    pytest src/tests/integration/ 2>&1 | tee pytest_output.log
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

                                    # Deactivate the virtual environment
                                    pyenv deactivate
                                """
                            } catch (Exception err) {
                            echo "Error in ${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: ${err.message}"
                            sh "echo '${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: ERROR - ${err.message}' >> test_results.csv"
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
                                // Define the virtual environment name in Groovy
                                def VENV_NAME = "pgmonkey_venv_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}"

                                sh """
                                    # Generate a unique virtual environment name based on the matrix parameters
                                    export VENV_NAME=${VENV_NAME}

                                    # Ensure pyenv is initialized properly
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Check if the virtual environment already exists
                                    if pyenv virtualenvs | grep -q "${VENV_NAME}"; then
                                        echo "${VENV_NAME} already exists. Activating..."
                                        pyenv activate ${VENV_NAME}
                                    else
                                        # Create a new virtual environment if it doesn't exist
                                        echo "Creating new virtual environment: ${VENV_NAME}..."
                                        pyenv virtualenv ${PYTHON_VERSION} ${VENV_NAME}
                                        pyenv activate ${VENV_NAME}

                                        # Upgrade pip, setuptools, and wheel
                                        python -m pip install --upgrade pip setuptools wheel

                                        # Install dependencies
                                        pip install psycopg[binary]==${PSYCOPG_VERSION}
                                        pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                        pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                        # Install pytest and testing dependencies
                                        pip install pytest==8.3.3 pytest-asyncio==0.17.0

                                        # Install the project itself (editable mode)
                                        pip install -e .
                                    fi

                                    # Run tests
                                    pytest src/tests/integration/ 2>&1 | tee pytest_output.log
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

                                    # Deactivate the virtual environment
                                    pyenv deactivate
                                """
                            } catch (Exception err) {
                            echo "Error in ${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: ${err.message}"
                            sh "echo '${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: ERROR - ${err.message}' >> test_results.csv"
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
                                // Define the virtual environment name in Groovy
                                def VENV_NAME = "pgmonkey_venv_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}"

                                sh """
                                    # Generate a unique virtual environment name based on the matrix parameters
                                    export VENV_NAME=${VENV_NAME}

                                    # Ensure pyenv is initialized properly
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Check if the virtual environment already exists
                                    if pyenv virtualenvs | grep -q "${VENV_NAME}"; then
                                        echo "${VENV_NAME} already exists. Activating..."
                                        pyenv activate ${VENV_NAME}
                                    else
                                        # Create a new virtual environment if it doesn't exist
                                        echo "Creating new virtual environment: ${VENV_NAME}..."
                                        pyenv virtualenv ${PYTHON_VERSION} ${VENV_NAME}
                                        pyenv activate ${VENV_NAME}

                                        # Upgrade pip, setuptools, and wheel
                                        python -m pip install --upgrade pip setuptools wheel

                                        # Install dependencies
                                        pip install psycopg[binary]==${PSYCOPG_VERSION}
                                        pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                        pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                        # Install pytest and testing dependencies
                                        pip install pytest==8.3.3 pytest-asyncio==0.17.0

                                        # Install the project itself (editable mode)
                                        pip install -e .
                                    fi

                                    # Run tests
                                    pytest src/tests/integration/ 2>&1 | tee pytest_output.log
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

                                    # Deactivate the virtual environment
                                    pyenv deactivate
                                """
                            } catch (Exception err) {
                            echo "Error in ${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: ${err.message}"
                            sh "echo '${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: ERROR - ${err.message}' >> test_results.csv"
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




