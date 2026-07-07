// Jenkinsfile — pipeline as code do monorepo Vectora.
//
// Dois fluxos independentes:
//   1. CI (job normal, dispara em todo push/PR): scons lint && scons tests.
//      Jenkins é o CI contínuo do repo — .github/workflows/vectora.yml só
//      roda de verdade com "[up-release]" na mensagem do commit ou
//      workflow_dispatch manual, pra não gastar minutos do plano billado.
//   2. Release (job parametrizado, disparo MANUAL): scons up-version, build
//      dos instaladores por SO (precisa de um agente por SO — Windows/macOS/
//      Linux não cross-compilam entre si no electron-builder) e publish no
//      vectora-services (R2 + KV via services/scripts/release.ts).
//
// Pré-requisito de infra (fora deste arquivo): controller Jenkins rodando +
// pelo menos 1 agente por SO com label windows/macos/linux, uv/pnpm/scons
// instalados, e `wrangler login` já autenticado no agente que publica.

pipeline {
    agent any

    parameters {
        booleanParam(
            name: 'RELEASE',
            defaultValue: false,
            description: 'Marcar pra rodar o fluxo de release em vez do CI normal.'
        )
        choice(
            name: 'BUMP',
            choices: ['patch', 'minor', 'major'],
            description: 'Só usado quando RELEASE=true — repassado pra scons up-version bump=...'
        )
        booleanParam(name: 'RELEASE_WIN', defaultValue: true, description: 'Buildar/publicar Windows')
        booleanParam(name: 'RELEASE_MAC', defaultValue: true, description: 'Buildar/publicar macOS')
        booleanParam(name: 'RELEASE_LINUX', defaultValue: true, description: 'Buildar/publicar Linux')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        // ── CI — todo push/PR ────────────────────────────────────────────
        stage('CI: lint + tests') {
            when { expression { !params.RELEASE } }
            steps {
                sh 'scons lint'
                sh 'scons tests'
            }
        }

        // ── Release — manual, um job separado por plataforma ─────────────
        stage('Release: bump de versão') {
            when { expression { params.RELEASE } }
            steps {
                sh "scons up-version bump=${params.BUMP}"
                script {
                    // Lê de volta o semver recém-gravado em pyproject.toml (fonte
                    // única — scons up-version já escreveu lá) em vez de tentar
                    // parsear a saída do scons.
                    env.VECTORA_VERSION = sh(
                        script: "grep -m1 '^version' vectora/pyproject.toml | sed -E 's/version = \"(.*)\"/\\1/'",
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Release: build por SO') {
            when { expression { params.RELEASE } }
            parallel {
                stage('Windows') {
                    when { expression { params.RELEASE_WIN } }
                    agent { label 'windows' }
                    steps {
                        sh 'scons release'
                    }
                }
                stage('macOS') {
                    when { expression { params.RELEASE_MAC } }
                    agent { label 'macos' }
                    steps {
                        sh 'scons release'
                    }
                }
                stage('Linux') {
                    when { expression { params.RELEASE_LINUX } }
                    agent { label 'linux' }
                    steps {
                        sh 'scons release'
                    }
                }
            }
        }

        stage('Release: publicar no vectora-services (R2 + KV)') {
            when { expression { params.RELEASE } }
            steps {
                dir('services') {
                    sh 'pnpm install --frozen-lockfile'
                    sh "pnpm run release -- --version=\${VECTORA_VERSION}"
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
    }
}
