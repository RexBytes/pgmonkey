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
        stage('Prepare Environment') {
            steps {
                script {
                    // Delete test_results.csv if it exists
                    sh """
                        if [ -f test_results.csv ]; then
                            rm test_results.csv
                        fi
                        touch test_results.csv
                    """
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
                                try {
                                    // Define the virtual environment name in Groovy
                                    def VENV_NAME = "pgmonkey_venv_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}"

                                    sh """
                                        set +e
                                        export PATH="\$HOME/.pyenv/bin:\$PATH"
                                        eval "\$(pyenv init --path)"
                                        eval "\$(pyenv init -)"
                                        eval "\$(pyenv virtualenv-init -)"

                                        if pyenv virtualenvs | grep -q "${VENV_NAME}"; then
                                            pyenv activate ${VENV_NAME}
                                        else
                                            pyenv virtualenv ${PYTHON_VERSION} ${VENV_NAME}
                                            pyenv activate ${VENV_NAME}
                                            pip install --upgrade pip setuptools wheel
                                            pip install psycopg[binary]==${PSYCOPG_VERSION} psycopg_pool==${PSYCOPG_POOL_VERSION} PyYAML==${PYAML_VERSION} pytest==8.3.3 pytest-asyncio==0.17.0
                                            pip install -e .
                                        fi

                                        # Run pytest and save logs uniquely per combination to avoid overwriting
                                        pytest src/tests/integration/ 2>&1 | tee pytest_output_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}.log || \
                                        echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv

                                        pyenv deactivate
                                        pyenv uninstall -f ${VENV_NAME}
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
                                try {
                                    def VENV_NAME = "pgmonkey_venv_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}"

                                    sh """
                                        set +e
                                        export PATH="\$HOME/.pyenv/bin:\$PATH"
                                        eval "\$(pyenv init --path)"
                                        eval "\$(pyenv init -)"
                                        eval "\$(pyenv virtualenv-init -)"

                                        if pyenv virtualenvs | grep -q "${VENV_NAME}"; then
                                            pyenv activate ${VENV_NAME}
                                        else
                                            pyenv virtualenv ${PYTHON_VERSION} ${VENV_NAME}
                                            pyenv activate ${VENV_NAME}
                                            pip install --upgrade pip setuptools wheel
                                            pip install psycopg[binary]==${PSYCOPG_VERSION} psycopg_pool==${PSYCOPG_POOL_VERSION} PyYAML==${PYAML_VERSION} pytest==8.3.3 pytest-asyncio==0.17.0
                                            pip install -e .
                                        fi

                                        # Run pytest and save logs uniquely per combination to avoid overwriting
                                        pytest src/tests/integration/ 2>&1 | tee pytest_output_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}.log || \
                                        echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv

                                        pyenv deactivate
                                        pyenv uninstall -f ${VENV_NAME}
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

        // Matrix for Python 3.10.x and 3.9.x
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
                                try {
                                    def VENV_NAME = "pgmonkey_venv_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}"

                                    sh """
                                        set +e
                                        export PATH="\$HOME/.pyenv/bin:\$PATH"
                                        eval "\$(pyenv init --path)"
                                        eval "\$(pyenv init -)"
                                        eval "\$(pyenv virtualenv-init -)"

                                        if pyenv virtualenvs | grep -q "${VENV_NAME}"; then
                                            pyenv activate ${VENV_NAME}
                                        else
                                            pyenv virtualenv ${PYTHON_VERSION} ${VENV_NAME}
                                            pyenv activate ${VENV_NAME}
                                            pip install --upgrade pip setuptools wheel
                                            pip install psycopg[binary]==${PSYCOPG_VERSION} psycopg_pool==${PSYCOPG_POOL_VERSION} PyYAML==${PYAML_VERSION} pytest==8.3.3 pytest-asyncio==0.17.0
                                            pip install -e .
                                        fi

                                        # Run pytest and save logs uniquely per combination to avoid overwriting
                                        pytest src/tests/integration/ 2>&1 | tee pytest_output_${PYTHON_VERSION}_${PSYCOPG_VERSION}_${PSYCOPG_POOL_VERSION}_${PYAML_VERSION}.log || \
                                        echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv

                                        pyenv deactivate
                                        pyenv uninstall -f ${VENV_NAME}
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
    }
    post {
        always {
        archiveArtifacts artifacts: 'test_results.csv', allowEmptyArchive: true
        junit 'pytest_output.xml'  // This will allow Jenkins to display test results in the UI
    }
    }
}
