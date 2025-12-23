pipeline {
    agent any // 在任何可用的 Jenkins 节点上运行

    stages {
        stage('Hello') {
            steps {
                echo 'Hello, Jenkins! 这是一个基础测试。'
            }
        }
        stage('Check Environment') {
            steps {
                sh 'python3 --version' // 检查服务器是否安装了 Python
                sh 'pip3 --version'
            }
        }
    }
}