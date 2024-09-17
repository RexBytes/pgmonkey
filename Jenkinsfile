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
                                sh """
                                    # Ensure pyenv is initialized properly
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Forcefully remove any existing symbolic links and environments
                                    if [ -L ~/.pyenv/versions/pgmonkey_venv ]; then
                                        echo "Removing symbolic link for pgmonkey_venv..."
                                        rm ~/.pyenv/versions/pgmonkey_venv
                                    fi

                                    # Delete the virtual environment directory manually if it exists
                                    if [ -d ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv ]; then
                                        echo "Removing existing pgmonkey_venv environment directory..."
                                        rm -rf ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv
                                    fi

                                    # Remove symlinks pointing to other versions
                                    if [ -L ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv ]; then
                                        echo "Removing symbolic link in ${PYTHON_VERSION} pointing to another environment..."
                                        rm ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv
                                    fi

                                    # Recheck and force removal if necessary
                                    if pyenv virtualenvs | grep -q 'pgmonkey_venv'; then
                                        echo "pgmonkey_venv still found, forcing uninstall through pyenv..."
                                        pyenv uninstall -f pgmonkey_venv
                                    fi

                                    # Install the specific Python version via pyenv if not installed
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Create a new virtual environment
                                    pyenv virtualenv ${PYTHON_VERSION} pgmonkey_venv

                                    # Activate the new environment
                                    pyenv activate pgmonkey_venv

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

                                    # Run tests
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

                                    # Deactivate the virtual environment
                                    pyenv deactivate
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
                                    # Ensure pyenv is initialized properly
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Forcefully remove any existing symbolic links and environments
                                    if [ -L ~/.pyenv/versions/pgmonkey_venv ]; then
                                        echo "Removing symbolic link for pgmonkey_venv..."
                                        rm ~/.pyenv/versions/pgmonkey_venv
                                    fi

                                    # Delete the virtual environment directory manually if it exists
                                    if [ -d ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv ]; then
                                        echo "Removing existing pgmonkey_venv environment directory..."
                                        rm -rf ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv
                                    fi

                                    # Remove symlinks pointing to other versions
                                    if [ -L ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv ]; then
                                        echo "Removing symbolic link in ${PYTHON_VERSION} pointing to another environment..."
                                        rm ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv
                                    fi

                                    # Recheck and force removal if necessary
                                    if pyenv virtualenvs | grep -q 'pgmonkey_venv'; then
                                        echo "pgmonkey_venv still found, forcing uninstall through pyenv..."
                                        pyenv uninstall -f pgmonkey_venv
                                    fi

                                    # Install the specific Python version via pyenv if not installed
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Create a new virtual environment
                                    pyenv virtualenv ${PYTHON_VERSION} pgmonkey_venv

                                    # Activate the new environment
                                    pyenv activate pgmonkey_venv

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

                                    # Run tests
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

                                    # Deactivate the virtual environment
                                    pyenv deactivate
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
                                    # Ensure pyenv is initialized properly
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Forcefully remove any existing symbolic links and environments
                                    if [ -L ~/.pyenv/versions/pgmonkey_venv ]; then
                                        echo "Removing symbolic link for pgmonkey_venv..."
                                        rm ~/.pyenv/versions/pgmonkey_venv
                                    fi

                                    # Delete the virtual environment directory manually if it exists
                                    if [ -d ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv ]; then
                                        echo "Removing existing pgmonkey_venv environment directory..."
                                        rm -rf ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv
                                    fi

                                    # Remove symlinks pointing to other versions
                                    if [ -L ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv ]; then
                                        echo "Removing symbolic link in ${PYTHON_VERSION} pointing to another environment..."
                                        rm ~/.pyenv/versions/${PYTHON_VERSION}/envs/pgmonkey_venv
                                    fi

                                    # Recheck and force removal if necessary
                                    if pyenv virtualenvs | grep -q 'pgmonkey_venv'; then
                                        echo "pgmonkey_venv still found, forcing uninstall through pyenv..."
                                        pyenv uninstall -f pgmonkey_venv
                                    fi

                                    # Install the specific Python version via pyenv if not installed
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Create a new virtual environment
                                    pyenv virtualenv ${PYTHON_VERSION} pgmonkey_venv

                                    # Activate the new environment
                                    pyenv activate pgmonkey_venv

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

                                    # Run tests
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

                                    # Deactivate the virtual environment
                                    pyenv deactivate
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




