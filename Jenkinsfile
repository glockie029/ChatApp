def isPullRequestBuild() {
    return env.CHANGE_ID?.trim()
}

def isMainBranch() {
    return (env.BRANCH_NAME ?: '') in ['main', 'master']
}

def isDevelopBranch() {
    return (env.BRANCH_NAME ?: '') in ['develop', 'dev']
}

def isFeatureLikeBranch() {
    def branchName = env.BRANCH_NAME ?: ''
    return isPullRequestBuild() ||
        branchName.startsWith('feature/') ||
        branchName.startsWith('bugfix/') ||
        branchName.startsWith('hotfix/')
}

def resolveSecurityProfile() {
    if (isMainBranch()) {
        return 'strict'
    }
    if (isDevelopBranch()) {
        return 'standard'
    }
    return 'relaxed'
}

def resolveAppPort() {
    def branchKey = isPullRequestBuild() ? "pr-${env.CHANGE_ID}" : (env.BRANCH_NAME ?: 'local')
    return (8200 + ((branchKey.hashCode() & 0x7fffffff) % 300)).toString()
}

def handleBanditGate(int exitCode) {
    if (exitCode == 0) {
        echo "✅ [Security Gate] Bandit 检查通过。"
        return
    }

    if (exitCode == 1) {
        error("⛔ [Security Gate] 检测到高危代码漏洞，流水线阻断！")
    }

    if (exitCode == 2) {
        if (env.SECURITY_PROFILE == 'relaxed') {
            currentBuild.result = 'UNSTABLE'
            echo "⚠️ [Security Gate] 当前为功能分支/PR，中危漏洞仅标记为不稳定。"
            return
        }

        error("⛔ [Security Gate] ${env.BRANCH_NAME} 分支不允许存在中危代码漏洞，流水线阻断！")
    }

    error("⛔ [Security Gate] Bandit 执行结果异常，流水线阻断！")
}

def handleSafetyGate(int exitCode) {
    if (exitCode == 0) {
        echo "✅ [Security Gate] Safety 检查通过。"
        return
    }

    if (exitCode == 1) {
        if (env.SECURITY_PROFILE == 'relaxed') {
            currentBuild.result = 'UNSTABLE'
            echo "⚠️ [Security Gate] 当前为功能分支/PR，依赖漏洞仅标记为不稳定。"
            return
        }

        error("⛔ [Security Gate] ${env.BRANCH_NAME} 分支检测到依赖漏洞，流水线阻断！")
    }

    if (exitCode == 2) {
        currentBuild.result = 'UNSTABLE'
        echo "⚠️ [Security Gate] 检测到低危/中危依赖漏洞，流水线标记为不稳定。"
        return
    }

    error("⛔ [Security Gate] Safety 执行结果异常，流水线阻断！")
}

pipeline {
    agent any

    environment {
        VENV_PATH = "venv"
        APP_PORT = "8000"
        LC_ALL = "C.UTF-8"
        LANG = "C.UTF-8"
        SECURITY_PROFILE = "relaxed"
        BRANCH_CATEGORY = "feature"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Branch Policy') {
            steps {
                script {
                    env.SECURITY_PROFILE = resolveSecurityProfile()
                    env.APP_PORT = resolveAppPort()

                    if (isMainBranch()) {
                        env.BRANCH_CATEGORY = 'main'
                    } else if (isDevelopBranch()) {
                        env.BRANCH_CATEGORY = 'develop'
                    } else if (isFeatureLikeBranch()) {
                        env.BRANCH_CATEGORY = 'feature-or-pr'
                    } else {
                        env.BRANCH_CATEGORY = 'other'
                    }

                    echo """
                    当前分支: ${env.BRANCH_NAME ?: 'unknown'}
                    分支类型: ${env.BRANCH_CATEGORY}
                    安全策略: ${env.SECURITY_PROFILE}
                    PR 编号: ${env.CHANGE_ID ?: 'N/A'}
                    当前校验端口: ${env.APP_PORT}
                    """
                }
            }
        }

        stage('Cleanup') {
            steps {
                echo "清理端口 ${APP_PORT} 上的旧进程..."
                sh "fuser -k ${APP_PORT}/tcp || true"
            }
        }

        stage('Prepare Environment') {
            steps {
                echo '正在初始化虚拟环境...'
                sh "python -m venv ${VENV_PATH}"
            }
        }

        stage('Install Dependencies') {
            steps {
                echo '安装依赖...'
                sh "./${VENV_PATH}/bin/pip install --upgrade pip"
                sh "./${VENV_PATH}/bin/pip install -r requirements.txt"
            }
        }

        stage('Unit Test') {
            steps {
                echo '正在执行单元测试...'
                sh "PYTHONPATH=. ./${VENV_PATH}/bin/python3 -m pytest -v -W ignore::DeprecationWarning > test_result.log"
            }
        }

        stage('Security: SAST (Code)') {
            steps {
                echo "正在执行静态代码安全分析 (Bandit)... [策略: ${SECURITY_PROFILE}]"
                sh "./${VENV_PATH}/bin/bandit -r . -x ./venv,./test_main.py -f json -o bandit_report.json || true"

                script {
                    def exitCode = sh(
                        script: "python3 security_gate.py bandit",
                        returnStatus: true
                    )
                    handleBanditGate(exitCode)
                }
            }
        }

        stage('Security: SCA (Deps)') {
            steps {
                echo "正在执行依赖组件安全分析 (Safety)... [策略: ${SECURITY_PROFILE}]"
                sh """
                    ./${VENV_PATH}/bin/safety check -r requirements.txt --json > safety_report.json 2>&1 || true
                """

                script {
                    def exitCode = sh(
                        script: "python3 security_gate.py safety",
                        returnStatus: true
                    )
                    handleSafetyGate(exitCode)
                }
            }
        }

        stage('Trivy Scan') {
            when {
                expression {
                    return env.BRANCH_CATEGORY in ['develop', 'main']
                }
            }
            steps {
                echo "Trivy 阶段预留给长期分支，当前仅保留占位。"
            }
        }

        stage('Run Server') {
            steps {
                echo "正在启动服务，端口 ${APP_PORT}..."
                sh """
                    export JENKINS_NODE_COOKIE=dontKillMe
                    PYTHONPATH=. nohup ./${VENV_PATH}/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port ${APP_PORT} > server.log 2>&1 &
                """
            }
        }

        stage('Verify') {
            steps {
                echo '检查启动日志...'
                sleep 5
                sh "cat server.log"
                sh "curl -s http://localhost:${APP_PORT}/ || (echo '错误：服务未能在端口 ${APP_PORT} 响应'; exit 1)"
            }
        }
    }

    post {
        always {
            echo '归档报告...'
            archiveArtifacts artifacts: '*.json, *.log', allowEmptyArchive: true
        }
        cleanup {
            sh "fuser -k ${APP_PORT}/tcp || true"
        }
    }
}
