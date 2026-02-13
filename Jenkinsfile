pipeline {
    agent any

    environment {
        VENV_PATH = "venv"
        APP_PORT  = "8000"
        // 强制设置语言环境，避免 Python 工具报编码错误
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
                // 尝试杀掉占用 8000 端口的进程，防止冲突
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
                // 使用虚拟环境中的 pip 安装
                sh "./${VENV_PATH}/bin/pip install --upgrade pip"
                sh "./${VENV_PATH}/bin/pip install -r requirements.txt"
            }
        }

        stage('Unit Test') {
            steps {
                echo '正在执行单元测试 (Pytest)...'
                echo '检查pytest'
                sh "./${VENV_PATH}/bin/pytest --version" || true
                // 运行 pytest 并生成简单的结果
                sh "./${VENV_PATH}/bin/pytest -v test_main.py > test_result.log"
            }
        }

        stage('Security: SAST') {
            steps {
                echo '正在执行静态代码安全分析 (Bandit)...'
                // 扫描当前目录, 排除 venv, 输出为 JSON 格式以便后续处理
                // || true 表示即使发现漏洞也不阻断流水线
                sh "./${VENV_PATH}/bin/bandit -r . -x ./venv -f json -o bandit_report.json || true"
            }
        }

        stage('Security: SCA') {
            steps {
                echo '正在执行依赖组件安全分析 (Safety)...'
                // 扫描 requirements.txt 中的已知漏洞
                sh "./${VENV_PATH}/bin/safety check -r requirements.txt --json > safety_report.json || true"
            }
        }

        stage('Run Server') {
            steps {
                echo "正在启动服务..."
                // 使用 nohup 后台运行 uvicorn
                // 注意：如果 ls -R 显示 main.py 在子目录下，请修改这里的 main:app
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
                
                echo '执行健康检查...'
                // 访问根路径，如果失败则退出非 0 状态
                sh "curl -s http://localhost:${APP_PORT}/ || (echo '错误：服务未能在端口 ${APP_PORT} 响应'; exit 1)"
            }
        }
    }
    
    post {
        always {
            echo '归档测试报告与安全扫描报告...'
            // 归档所有 JSON 报告和日志文件
            archiveArtifacts artifacts: '*.json, *.log', allowEmptyArchive: true
            
            // 可选：清理工作空间 (生产环境建议开启)
            // cleanWs()
        }
        success {
            echo 'DevSecOps 流水线执行成功！应用已启动。'
        }
        failure {
            echo '流水线执行失败，请检查控制台输出。'
        }
    }
}