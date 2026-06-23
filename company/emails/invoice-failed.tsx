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
} from "@react-email/components";

interface Props {
  name: string;
  amount: string;
  retryDate: string;
}

export default function InvoiceFailed({ name, amount, retryDate }: Props) {
  return (
    <Html lang="pt">
      <Head />
      <Preview>Falha no pagamento — ação necessária</Preview>
      <Body
        style={{
          backgroundColor: "#0a0e1a",
          fontFamily: "ui-monospace, monospace",
        }}
      >
        <Container
          style={{ maxWidth: "560px", margin: "0 auto", padding: "32px 24px" }}
        >
          <Heading
            style={{ color: "#ffffff", fontSize: "22px", fontWeight: "700" }}
          >
            Vectora
          </Heading>
          <Text
            style={{ color: "#f87171", fontSize: "14px", fontWeight: "600" }}
          >
            ⚠ Falha no pagamento
          </Text>
          <Text
            style={{ color: "#94a3b8", fontSize: "14px", lineHeight: "1.6" }}
          >
            Olá, {name}! Não conseguimos processar o pagamento de{" "}
            <strong>{amount}</strong>. Próxima tentativa: {retryDate}.
          </Text>
          <Text
            style={{ color: "#94a3b8", fontSize: "14px", lineHeight: "1.6" }}
          >
            Atualize seu método de pagamento para evitar a suspensão do acesso.
          </Text>
          <Link
            href="https://app.vectora.company/dashboard/billing"
            style={{
              display: "inline-block",
              backgroundColor: "#f87171",
              color: "#ffffff",
              padding: "12px 24px",
              borderRadius: "12px",
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: "600",
              margin: "16px 0",
            }}
          >
            Atualizar pagamento →
          </Link>
          <Hr style={{ borderColor: "#1e293b", margin: "24px 0" }} />
          <Text style={{ color: "#475569", fontSize: "12px" }}>
            Vectora · vectora.company
          </Text>
        </Container>
      </Body>
    </Html>
  );
}
