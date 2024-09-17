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
                                    # Clean up any existing venv
                                    rm -rf venv

                                    # Unset PYTHONPATH to avoid conflicts
                                    export PYTHONPATH=""

                                    # Clean up any existing packages in pyenv
                                    rm -rf ~/.pyenv/versions/${PYTHON_VERSION}/lib/python*/site-packages/*

                                    # Set up pyenv
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Set up venv and ensure pip is available
                                    python -m venv venv
                                    . venv/bin/activate

                                    # Remove any existing pip that might be broken
                                    # First remove files, then directory
                                    rm -rf venv/lib/python*/site-packages/pip/*
                                    rm -rf venv/lib/python*/site-packages/pip-*.dist-info/*
                                    rm -rf venv/lib/python*/site-packages/pip
                                    rm -rf venv/lib/python*/site-packages/pip-*.dist-info


                                    # Download and reinstall pip using get-pip.py
                                    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
                                    python get-pip.py --force-reinstall

                                    # Ensure pip, setuptools, and wheel are updated
                                    pip install --no-cache-dir --upgrade pip setuptools wheel Cython

                                    # Log the setuptools version to trace any issues
                                    pip show setuptools

                                    # Install specific versions
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                    # Ensure pytest is installed
                                    pip install pytest==8.3.3 pytest-asyncio==0.17.0

                                    # Install the checked-out pgmonkey package in editable mode
                                    pip install -e .

                                    # Run tests and capture result
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

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

                                    # Unset PYTHONPATH to avoid conflicts
                                    export PYTHONPATH=""

                                    # Clean up any existing packages in pyenv
                                    rm -rf ~/.pyenv/versions/${PYTHON_VERSION}/lib/python*/site-packages/*

                                    # Set up pyenv
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Set up venv and ensure pip is available
                                    python -m venv venv
                                    . venv/bin/activate

                                    # Remove any existing pip that might be broken
                                    # First remove files, then directory
                                    rm -rf venv/lib/python*/site-packages/pip/*
                                    rm -rf venv/lib/python*/site-packages/pip-*.dist-info/*
                                    rm -rf venv/lib/python*/site-packages/pip
                                    rm -rf venv/lib/python*/site-packages/pip-*.dist-info


                                    # Download and reinstall pip using get-pip.py
                                    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
                                    python get-pip.py --force-reinstall

                                    # Ensure pip, setuptools, and wheel are updated
                                    pip install --no-cache-dir --upgrade pip setuptools wheel Cython

                                    # Log the setuptools version to trace any issues
                                    pip show setuptools

                                    # Install specific versions
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                    # Ensure pytest is installed
                                    pip install pytest==8.3.3 pytest-asyncio==0.17.0

                                    # Install the checked-out pgmonkey package in editable mode
                                    pip install -e .

                                    # Run tests and capture result
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

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

                                    # Unset PYTHONPATH to avoid conflicts
                                    export PYTHONPATH=""

                                    # Clean up any existing packages in pyenv
                                    rm -rf ~/.pyenv/versions/${PYTHON_VERSION}/lib/python*/site-packages/*

                                    # Set up pyenv
                                    export PATH="\$HOME/.pyenv/bin:\$PATH"
                                    eval "\$(pyenv init --path)"
                                    eval "\$(pyenv init -)"
                                    eval "\$(pyenv virtualenv-init -)"

                                    # Install Python version
                                    pyenv install -s ${PYTHON_VERSION}
                                    pyenv global ${PYTHON_VERSION}

                                    # Set up venv and ensure pip is available
                                    python -m venv venv
                                    . venv/bin/activate

                                    # Remove any existing pip that might be broken
                                    # First remove files, then directory
                                    rm -rf venv/lib/python*/site-packages/pip/*
                                    rm -rf venv/lib/python*/site-packages/pip-*.dist-info/*
                                    rm -rf venv/lib/python*/site-packages/pip
                                    rm -rf venv/lib/python*/site-packages/pip-*.dist-info


                                    # Download and reinstall pip using get-pip.py
                                    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
                                    python get-pip.py --force-reinstall

                                    # Ensure pip, setuptools, and wheel are updated
                                    pip install --no-cache-dir --upgrade pip setuptools wheel Cython

                                    # Log the setuptools version to trace any issues
                                    pip show setuptools

                                    # Install specific versions
                                    pip install psycopg[binary]==${PSYCOPG_VERSION}
                                    pip install psycopg_pool==${PSYCOPG_POOL_VERSION}
                                    pip install PyYAML==${PYAML_VERSION} --use-deprecated=legacy-resolver

                                    # Ensure pytest is installed
                                    pip install pytest==8.3.3 pytest-asyncio==0.17.0

                                    # Install the checked-out pgmonkey package in editable mode
                                    pip install -e .

                                    # Run tests and capture result
                                    set +e
                                    pytest src/tests/integration/ || echo "${PYTHON_VERSION}, ${PSYCOPG_VERSION}, ${PSYCOPG_POOL_VERSION}, ${PYAML_VERSION}: FAILED" >> test_results.csv
                                    set -e

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




