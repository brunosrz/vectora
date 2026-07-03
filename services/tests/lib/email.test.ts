import { describe, expect, it, vi, afterEach } from "vitest";
import {
  sendEmail,
  verifyEmailHtml,
  magicLinkHtml,
  invoicePaidHtml,
  invoiceFailedHtml,
  waitlistJoinedHtml,
  accountDeletedHtml,
  FROM_EMAIL,
} from "../../src/lib/email";

describe("sendEmail", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("chama o Resend com os campos certos, usando FROM_EMAIL por padrão", async () => {
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const body = JSON.parse(init.body as string);
      expect(body).toEqual({
        from: FROM_EMAIL,
        to: "user@example.com",
        subject: "Assunto",
        html: "<p>oi</p>",
      });
      return new Response(null, { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await sendEmail("api-key", {
      to: "user@example.com",
      subject: "Assunto",
      html: "<p>oi</p>",
    });

    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("loga e não lança quando o Resend responde não-ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("bad request", { status: 400 })),
    );
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    await expect(
      sendEmail("api-key", { to: "a@b.com", subject: "s", html: "h" }),
    ).resolves.toBeUndefined();
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("loga e não lança quando o fetch falha (rede/timeout)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    await expect(
      sendEmail("api-key", { to: "a@b.com", subject: "s", html: "h" }),
    ).resolves.toBeUndefined();
    expect(errorSpy).toHaveBeenCalledWith(
      "sendEmail failed",
      expect.any(Error),
    );
    errorSpy.mockRestore();
  });
});

describe("HTML templates", () => {
  it("geram HTML contendo os dados interpolados", () => {
    expect(verifyEmailHtml("Ada", "https://x/verify")).toContain(
      "https://x/verify",
    );
    expect(magicLinkHtml("https://x/login")).toContain("https://x/login");
    expect(invoicePaidHtml("Ada", "$9", "pro", "01/01/2027")).toContain("$9");
    expect(invoiceFailedHtml("Ada", "$9")).toContain("$9");
    expect(waitlistJoinedHtml()).toContain("lista de espera");
    expect(accountDeletedHtml("Ada", "01/01/2027")).toContain("01/01/2027");
  });
});
