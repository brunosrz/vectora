// Jenkinsfile — pipeline as code do monorepo Vectora.
//
// CI contínuo (lint + tests em todo push/PR). O fluxo de release — bump de
// versão, build dos instaladores por SO e publicação no canal de update —
// roda inteiramente no GitHub Actions (.github/workflows/vectora.yml),
// disparado por "[up-release]" na mensagem do commit ou workflow_dispatch
// manual.
//
// Pré-requisito de infra (fora deste arquivo): controller Jenkins rodando +
// pelo menos 1 agente com uv/pnpm/scons instalados.

pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('CI: lint + tests') {
            steps {
                sh 'scons lint'
                sh 'scons tests'
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
