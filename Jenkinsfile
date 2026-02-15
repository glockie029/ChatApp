pipeline {
    agent any

    environment {
        VENV_PATH = "venv"
        APP_PORT  = "8000"
        LC_ALL    = "C.UTF-8"
        LANG      = "C.UTF-8"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Cleanup') {
            steps {
                echo '清理旧进程...'
                sh "pkill -f uvicorn || true"
                sh "fuser -k ${APP_PORT}/tcp || true"
            }
        }

        stage('Prepare Environment') {
            steps {
                echo '正在初始化虚拟环境...'
                sh "python3 -m venv ${VENV_PATH}"
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
                // 使用推荐的模块调用方式
                sh "PYTHONPATH=. ./${VENV_PATH}/bin/python3 -m pytest -v -W ignore::DeprecationWarning test_main.py > test_result.log"
            }
        }

        stage('Security: SAST (Code)') {
            steps {
                echo '正在执行静态代码安全分析 (Bandit)...'
                // 1. 生成报告 (|| true 确保即使发现漏洞，shell 也不报错，交由 python 脚本判断)
                sh "./${VENV_PATH}/bin/bandit -r . -x ./venv -f json -o bandit_report.json || true"
                
                // 2. 执行安全门禁检查
                script {
                    // 调用我们编写的 python 脚本检查 bandit 报告
                    // returnStatus: true 让 sh 返回退出码而不是抛出异常
                    def exitCode = sh(script: "python3 security_gate.py bandit", returnStatus: true)
                    
                    if (exitCode == 1) {
                        error("⛔ [Security Gate] 检测到高危代码漏洞，流水线阻断！请查看日志中的详细报告。")
                    } else if (exitCode == 2) {
                        currentBuild.result = 'UNSTABLE'
                        echo "⚠️ [Security Gate] 检测到中危漏洞，流水线标记为不稳定。"
                    } else {
                        echo "✅ [Security Gate] 代码安全检查通过。"
                    }
                }
            }
        }

        stage('Security: SCA (Deps)') {
            steps {
                echo '正在执行依赖组件安全分析 (Safety)...'
                // 1. 生成报告
                sh "./${VENV_PATH}/bin/safety check -r requirements.txt --json > safety_report.json || true"
                
                // 2. 执行安全门禁检查
                script {
                    def exitCode = sh(script: "python3 security_gate.py safety", returnStatus: true)
                    
                    if (exitCode == 1) {
                        error("⛔ [Security Gate] 检测到依赖组件存在 CVE 漏洞，流水线阻断！请升级依赖包。")
                    } else {
                        echo "✅ [Security Gate] 依赖安全检查通过。"
                    }
                }
            }
        }

        stage('Run Server') {
            steps {
                echo "正在启动服务..."
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
    }
}