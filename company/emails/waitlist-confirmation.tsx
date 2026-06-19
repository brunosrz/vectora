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
} from '@react-email/components'

interface Props {
  email: string
}

export default function WaitlistConfirmation({ email }: Props) {
  return (
    <Html lang="pt">
      <Head />
      <Preview>Você está na lista — Vectora</Preview>
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
            ✓ Você está na lista!
          </Text>
          <Text
            style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.6' }}
          >
            Registramos <strong>{email}</strong> na lista de espera do Vectora.
            Você será um dos primeiros a receber acesso — com trial grátis de 30
            dias.
          </Text>
          <Text
            style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.6' }}
          >
            Enquanto isso, conheça a documentação:
          </Text>
          <Link
            href="https://docs.vectora.company"
            style={{
              display: 'inline-block',
              color: '#3b82f6',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: '500',
            }}
          >
            docs.vectora.company →
          </Link>
          <Hr style={{ borderColor: '#1e293b', margin: '24px 0' }} />
          <Text style={{ color: '#475569', fontSize: '12px' }}>
            Vectora · Sem spam. Apenas o aviso de lançamento.
          </Text>
        </Container>
      </Body>
    </Html>
  )
}
