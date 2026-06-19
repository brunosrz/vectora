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
  name: string
  deletionDate: string
}

export default function AccountDeleted({ name, deletionDate }: Props) {
  return (
    <Html lang="pt">
      <Head />
      <Preview>Sua conta Vectora será excluída em 30 dias</Preview>
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
            Olá, {name}. Recebemos sua solicitação de exclusão de conta.
          </Text>
          <Text
            style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.6' }}
          >
            Sua conta será permanentemente excluída em{' '}
            <strong>{deletionDate}</strong> (30 dias a partir de hoje). Se mudar
            de ideia, entre em contato com{' '}
            <Link
              href="mailto:support@vectora.company"
              style={{ color: '#3b82f6' }}
            >
              support@vectora.company
            </Link>{' '}
            antes dessa data.
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
