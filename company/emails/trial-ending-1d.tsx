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
  trialEndsAt: string;
}

export default function TrialEnding1d({ name, trialEndsAt }: Props) {
  return (
    <Html lang="pt">
      <Head />
      <Preview>Último dia do seu trial Vectora</Preview>
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
            style={{
              color: "#f59e0b",
              fontSize: "14px",
              lineHeight: "1.6",
              fontWeight: "600",
            }}
          >
            ⚠ Último dia do seu trial
          </Text>
          <Text
            style={{ color: "#94a3b8", fontSize: "14px", lineHeight: "1.6" }}
          >
            Olá, {name}! Seu trial termina amanhã ({trialEndsAt}). Assine agora
            para não perder o acesso.
          </Text>
          <Link
            href="https://app.vectora.company/dashboard/billing"
            style={{
              display: "inline-block",
              backgroundColor: "#3b82f6",
              color: "#ffffff",
              padding: "12px 24px",
              borderRadius: "12px",
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: "600",
              margin: "16px 0",
            }}
          >
            Assinar agora →
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
