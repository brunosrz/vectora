import { createFileRoute } from '@tanstack/react-router'
import LegalPage from '#/components/shared/LegalPage'

export const Route = createFileRoute('/terms')({
  head: () => ({
    meta: [
      { title: 'Termos de Uso — Vectora' },
      {
        property: 'og:image',
        content: `/api/og?title=${encodeURIComponent('Termos de Uso')}&desc=${encodeURIComponent('Licença de uso, cancelamento, trial e limitações do Vectora.')}`,
      },
    ],
  }),
  component: TermsPage,
})

function TermsPage() {
  return (
    <LegalPage title="Termos de Uso" lastUpdated="2025-01-01">
      <h2>1. Aceitação</h2>
      <p>
        Ao criar uma conta ou usar o Vectora, você concorda com estes Termos de
        Uso. Se não concordar, não use o serviço.
      </p>

      <h2>2. Licença</h2>
      <p>
        A Vectora concede uma licença não-exclusiva, intransferível e revogável
        para usar o software conforme o plano contratado. Redistribuição ou
        sublicenciamento são proibidos.
      </p>

      <h2>3. Responsabilidades do cliente</h2>
      <ul>
        <li>Manter a segurança do servidor e das credenciais de acesso</li>
        <li>
          Não usar o Vectora para atividades ilegais ou que violem direitos de
          terceiros
        </li>
        <li>Respeitar os limites de uso da API conforme o plano</li>
      </ul>

      <h2>4. Pagamentos e cancelamento</h2>
      <p>
        O trial de 30 dias é gratuito e não exige cartão. Após o trial, é
        necessário assinar um plano para continuar usando. O cancelamento pode
        ser feito a qualquer momento pelo painel.
      </p>

      <h2>5. Limitação de responsabilidade</h2>
      <p>
        O Vectora é fornecido "como está". Não nos responsabilizamos por perdas
        de dados, interrupções de serviço ou danos indiretos decorrentes do uso.
      </p>

      <h2>6. Contato</h2>
      <p>
        <a href="mailto:legal@vectora.company">legal@vectora.company</a>
      </p>
    </LegalPage>
  )
}
