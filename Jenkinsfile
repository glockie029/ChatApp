pipeline {
    agent any

    environment {
        VENV_PATH = "venv"
        APP_PORT  = "8000"
    }

    stages {
        stage('Checkout & Check Files') {
            steps {
                echo '检查当前工作区文件...'
                // 打印当前目录下的所有文件，确认 main.py 是否存在
                sh "ls -R"
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
                sh "./${VENV_PATH}/bin/pip install fastapi uvicorn"
                sh "pip install -r requirements.txt"
            }
        }

        stage('Run Server') {
            steps {
                echo "正在启动服务..."
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
                sh "netstat -tuln | grep ${APP_PORT} || echo '错误：服务未能在端口 ${APP_PORT} 启动'"
            }
        }
    }
}
