import {
  Html,
  Head,
  Preview,
  Body,
  Container,
  Heading,
  Text,
  Link,
  Hr,
  Section,
} from '@react-email/components'

interface Props {
  name: string
  amount: string
  plan: string
  periodEnd: string
  invoiceUrl: string
}

export default function InvoicePaid({
  name,
  amount,
  plan,
  periodEnd,
  invoiceUrl,
}: Props) {
  return (
    <Html lang="pt">
      <Head />
      <Preview>Pagamento confirmado — {amount}</Preview>
      <Body
        style={{
          backgroundColor: '#0a0e1a',
          fontFamily: 'ui-monospace, monospace',
        }}
      >
        <Container
          style={{ maxWidth: '560px', margin: '0 auto', padding: '32px 24px' }}
        >
          <Heading
            style={{ color: '#ffffff', fontSize: '22px', fontWeight: '700' }}
          >
            Vectora
          </Heading>
          <Text
            style={{ color: '#4ade80', fontSize: '14px', fontWeight: '600' }}
          >
            ✓ Pagamento confirmado
          </Text>
          <Text
            style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.6' }}
          >
            Olá, {name}! Recebemos seu pagamento de <strong>{amount}</strong>{' '}
            para o plano <strong>{plan}</strong>. Acesso ativo até {periodEnd}.
          </Text>
          <Section
            style={{
              backgroundColor: '#0f172a',
              borderRadius: '12px',
              padding: '16px 20px',
              margin: '20px 0',
            }}
          >
            <Text
              style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0' }}
            >
              Valor: <strong style={{ color: '#fff' }}>{amount}</strong>
            </Text>
            <Text
              style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0' }}
            >
              Plano: <strong style={{ color: '#fff' }}>{plan}</strong>
            </Text>
            <Text
              style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0' }}
            >
              Próxima renovação:{' '}
              <strong style={{ color: '#fff' }}>{periodEnd}</strong>
            </Text>
          </Section>
          <Link
            href={invoiceUrl}
            style={{ color: '#3b82f6', fontSize: '13px' }}
          >
            Ver fatura →
          </Link>
          <Hr style={{ borderColor: '#1e293b', margin: '24px 0' }} />
          <Text style={{ color: '#475569', fontSize: '12px' }}>
            Vectora · vectora.company
          </Text>
        </Container>
      </Body>
    </Html>
  )
}
