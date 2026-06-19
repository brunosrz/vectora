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
  magicLink: string
}

export default function MagicLinkEmail({ magicLink }: Props) {
  return (
    <Html lang="pt">
      <Head />
      <Preview>Seu link de acesso ao Vectora</Preview>
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
            style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.6' }}
          >
            Clique no botão abaixo para acessar sua conta. O link expira em 1
            hora.
          </Text>
          <Link
            href={magicLink}
            style={{
              display: 'inline-block',
              backgroundColor: '#3b82f6',
              color: '#ffffff',
              padding: '12px 24px',
              borderRadius: '12px',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: '600',
              margin: '16px 0',
            }}
          >
            Entrar na conta →
          </Link>
          <Text style={{ color: '#64748b', fontSize: '12px' }}>
            Se você não solicitou este link, ignore este email.
          </Text>
          <Hr style={{ borderColor: '#1e293b', margin: '24px 0' }} />
          <Text style={{ color: '#475569', fontSize: '12px' }}>
            Vectora · vectora.company
          </Text>
        </Container>
      </Body>
    </Html>
  )
}
