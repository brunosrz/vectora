import { Resend } from "resend";

export const resend = new Resend(process.env.RESEND_API_KEY);

export const FROM_EMAIL = "noreply@vectora.company";
export const SUPPORT_EMAIL = "support@vectora.company";
export const BILLING_EMAIL = "billing@vectora.company";
