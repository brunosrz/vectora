import {
  Html,
  Head,
  Preview,
  Body,
  Container,
  Section,
  Heading,
  Text,
  Link,
  Hr,
} from '@react-email/components'

interface WelcomeEmailProps {
  name: string
  trialEndsAt: string
}

export default function WelcomeEmail({ name, trialEndsAt }: WelcomeEmailProps) {
  return (
    <Html lang="pt">
      <Head />
      <Preview>Bem-vindo ao Vectora — seu trial de 30 dias começou</Preview>
      <Body style={body}>
        <Container style={container}>
          <Heading style={h1}>Vectora</Heading>
          <Text style={text}>Olá, {name}!</Text>
          <Text style={text}>
            Seu trial de 30 dias começou. Você tem acesso completo ao plano{' '}
            <strong>Plus</strong> até <strong>{trialEndsAt}</strong>.
          </Text>
          <Section style={card}>
            <Text style={cardText}>
              <strong>Próximos passos:</strong>
            </Text>
            <Text style={cardText}>
              1. Acesse o painel e revele seu <code>VECTORA_TOKEN</code>
            </Text>
            <Text style={cardText}>
              2. <code>pip install vectora</code>
            </Text>
            <Text style={cardText}>
              3. <code>vectora setup</code>
            </Text>
            <Text style={cardText}>
              4. <code>vectora chat</code>
            </Text>
          </Section>
          <Link href="https://app.vectora.company/dashboard" style={button}>
            Ir para o painel →
          </Link>
          <Hr style={hr} />
          <Text style={footer}>
            Vectora ·{' '}
            <Link href="https://vectora.company" style={footerLink}>
              vectora.company
            </Link>
          </Text>
        </Container>
      </Body>
    </Html>
  )
}

const body = {
  backgroundColor: '#0a0e1a',
  fontFamily: 'ui-monospace, monospace',
}
const container = { maxWidth: '560px', margin: '0 auto', padding: '32px 24px' }
const h1 = {
  color: '#ffffff',
  fontSize: '24px',
  fontWeight: '700',
  marginBottom: '24px',
}
const text = {
  color: '#94a3b8',
  fontSize: '14px',
  lineHeight: '1.6',
  margin: '8px 0',
}
const card = {
  backgroundColor: '#0f172a',
  borderRadius: '12px',
  padding: '16px 20px',
  margin: '20px 0',
}
const cardText = {
  color: '#cbd5e1',
  fontSize: '13px',
  lineHeight: '1.8',
  margin: '4px 0',
}
const button = {
  display: 'inline-block',
  backgroundColor: '#3b82f6',
  color: '#ffffff',
  padding: '12px 24px',
  borderRadius: '12px',
  textDecoration: 'none',
  fontSize: '14px',
  fontWeight: '600',
  margin: '16px 0',
}
const hr = { borderColor: '#1e293b', margin: '24px 0' }
const footer = { color: '#475569', fontSize: '12px' }
const footerLink = { color: '#3b82f6' }
