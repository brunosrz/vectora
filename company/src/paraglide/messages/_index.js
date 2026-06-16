/* eslint-disable */
import { getLocale, experimentalStaticLocale } from "../runtime.js";

/** @typedef {import('../runtime.js').LocalizedString} LocalizedString */
/** @typedef {{}} Language_LabelInputs */
/** @typedef {{ locale: NonNullable<unknown> }} Current_LocaleInputs */
/** @typedef {{}} Site_TitleInputs */
/** @typedef {{}} Site_DescriptionInputs */
/** @typedef {{}} Nav_PricingInputs */
/** @typedef {{}} Nav_DocsInputs */
/** @typedef {{}} Nav_FaqInputs */
/** @typedef {{}} Nav_LoginInputs */
/** @typedef {{}} Nav_SignupInputs */
/** @typedef {{}} Nav_SupportInputs */
/** @typedef {{}} Hero_EyebrowInputs */
/** @typedef {{}} Hero_TaglineInputs */
/** @typedef {{}} Hero_SubtitleInputs */
/** @typedef {{}} Hero_Gif_AltInputs */
/** @typedef {{}} Showcase_Chat_AltInputs */
/** @typedef {{}} Showcase_Rag_AltInputs */
/** @typedef {{}} Showcase_Code_AltInputs */
/** @typedef {{}} Showcase_Plan_AltInputs */
/** @typedef {{}} Hero_Cta_TrialInputs */
/** @typedef {{}} Hero_Cta_PricingInputs */
/** @typedef {{}} Showcase_TitleInputs */
/** @typedef {{}} Showcase_Chat_TitleInputs */
/** @typedef {{}} Showcase_Chat_DescInputs */
/** @typedef {{}} Showcase_Rag_TitleInputs */
/** @typedef {{}} Showcase_Rag_DescInputs */
/** @typedef {{}} Showcase_Code_TitleInputs */
/** @typedef {{}} Showcase_Code_DescInputs */
/** @typedef {{}} Showcase_Plan_TitleInputs */
/** @typedef {{}} Showcase_Plan_DescInputs */
/** @typedef {{}} Agentic_HeadingInputs */
/** @typedef {{}} Agentic_Docs_LinkInputs */
/** @typedef {{}} Agentic_Bullet_OrchestratorInputs */
/** @typedef {{}} Agentic_Bullet_CoderInputs */
/** @typedef {{}} Agentic_Bullet_SearchInputs */
/** @typedef {{}} Agentic_Bullet_RagInputs */
/** @typedef {{}} Agentic_Bullet_ParallelInputs */
/** @typedef {{}} Rag_HeadingInputs */
/** @typedef {{}} Team_HeadingInputs */
/** @typedef {{}} Team_Step1_TitleInputs */
/** @typedef {{}} Team_Step1_DescInputs */
/** @typedef {{}} Team_Step2_TitleInputs */
/** @typedef {{}} Team_Step2_DescInputs */
/** @typedef {{}} Team_Step3_TitleInputs */
/** @typedef {{}} Team_Step3_DescInputs */
/** @typedef {{}} Team_Step4_TitleInputs */
/** @typedef {{}} Team_Step4_DescInputs */
/** @typedef {{}} Team_CompatInputs */
/** @typedef {{}} Why_HeadingInputs */
/** @typedef {{}} Why_Privacy_TitleInputs */
/** @typedef {{}} Why_Privacy_DescInputs */
/** @typedef {{}} Why_Cost_TitleInputs */
/** @typedef {{}} Why_Cost_DescInputs */
/** @typedef {{}} Why_Custom_TitleInputs */
/** @typedef {{}} Why_Custom_DescInputs */
/** @typedef {{}} Why_Sovereign_TitleInputs */
/** @typedef {{}} Why_Sovereign_DescInputs */
/** @typedef {{}} Pricing_HeadingInputs */
/** @typedef {{}} Pricing_SubtitleInputs */
/** @typedef {{}} Pricing_Plus_BadgeInputs */
/** @typedef {{}} Pricing_Pro_BadgeInputs */
/** @typedef {{}} Pricing_CtaInputs */
/** @typedef {{}} Pricing_Compare_ToggleInputs */
/** @typedef {{}} Pricing_Toggle_BrlInputs */
/** @typedef {{}} Pricing_Toggle_UsdInputs */
/** @typedef {{}} Pricing_Per_MonthInputs */
/** @typedef {{}} Waitlist_HeadingInputs */
/** @typedef {{}} Waitlist_SubtitleInputs */
/** @typedef {{}} Waitlist_Email_PlaceholderInputs */
/** @typedef {{}} Waitlist_SubmitInputs */
/** @typedef {{}} Waitlist_SuccessInputs */
/** @typedef {{}} Waitlist_DuplicateInputs */
/** @typedef {{}} Waitlist_FooterInputs */
/** @typedef {{}} Footer_Made_InInputs */
/** @typedef {{}} Footer_ProductInputs */
/** @typedef {{}} Footer_LegalInputs */
/** @typedef {{}} Footer_PrivacyInputs */
/** @typedef {{}} Footer_TermsInputs */
/** @typedef {{}} Footer_CookiesInputs */
/** @typedef {{}} Footer_SlaInputs */
/** @typedef {{}} Footer_DpaInputs */
/** @typedef {{}} Footer_SupportInputs */
/** @typedef {{}} Footer_DocsInputs */
/** @typedef {{}} Footer_FaqInputs */
/** @typedef {{}} Footer_StatusInputs */
/** @typedef {{}} Signup_TitleInputs */
/** @typedef {{}} Signup_SubtitleInputs */
/** @typedef {{}} Signup_Already_Have_AccountInputs */
/** @typedef {{}} Signup_View_PricingInputs */
/** @typedef {{}} Login_TitleInputs */
/** @typedef {{}} Login_No_AccountInputs */
/** @typedef {{}} Login_Forgot_PasswordInputs */
/** @typedef {{}} Login_Magic_Link_SentInputs */
/** @typedef {{}} Form_Full_NameInputs */
/** @typedef {{}} Form_EmailInputs */
/** @typedef {{}} Form_PasswordInputs */
/** @typedef {{}} Form_CountryInputs */
/** @typedef {{}} Form_Country_BrInputs */
/** @typedef {{}} Form_Country_IntlInputs */
/** @typedef {{}} Form_Submit_SignupInputs */
/** @typedef {{}} Form_Submit_LoginInputs */
/** @typedef {{}} Form_LoadingInputs */
/** @typedef {{}} Dashboard_Token_TitleInputs */
/** @typedef {{}} Dashboard_Token_Reveal_BtnInputs */
/** @typedef {{}} Dashboard_Token_Copy_BtnInputs */
/** @typedef {{}} Dashboard_Token_CopiedInputs */
/** @typedef {{}} Dashboard_Token_WarningInputs */
/** @typedef {{}} Dashboard_Token_Revealed_BannerInputs */
/** @typedef {{}} Dashboard_Token_Rotate_BtnInputs */
/** @typedef {{}} Dashboard_Token_Rotate_ConfirmInputs */
/** @typedef {{}} Dashboard_Quickstart_TitleInputs */
/** @typedef {{}} Dashboard_License_TitleInputs */
/** @typedef {{}} Dashboard_License_PlanInputs */
/** @typedef {{}} Dashboard_License_StatusInputs */
/** @typedef {{}} Dashboard_License_Trial_ActiveInputs */
/** @typedef {{}} Dashboard_License_ActiveInputs */
/** @typedef {{}} Dashboard_License_Past_DueInputs */
/** @typedef {{}} Dashboard_License_CanceledInputs */
/** @typedef {{}} Dashboard_License_ExpiredInputs */
/** @typedef {{}} Dashboard_License_Trial_EndsInputs */
/** @typedef {{ days: NonNullable<unknown> }} Dashboard_License_Days_LeftInputs */
/** @typedef {{}} Dashboard_License_History_TitleInputs */
/** @typedef {{}} Dashboard_Billing_TitleInputs */
/** @typedef {{}} Dashboard_Billing_Subscribe_PlusInputs */
/** @typedef {{}} Dashboard_Billing_Subscribe_ProInputs */
/** @typedef {{}} Dashboard_Billing_Upgrade_ProInputs */
/** @typedef {{}} Dashboard_Billing_ManageInputs */
/** @typedef {{}} Dashboard_Billing_Update_PaymentInputs */
/** @typedef {{}} Dashboard_Billing_ReactivateInputs */
/** @typedef {{}} Dashboard_Apikeys_TitleInputs */
/** @typedef {{}} Dashboard_Apikeys_Create_BtnInputs */
/** @typedef {{}} Dashboard_Apikeys_NameInputs */
/** @typedef {{}} Dashboard_Apikeys_CreatedInputs */
/** @typedef {{}} Dashboard_Apikeys_ScopesInputs */
/** @typedef {{}} Dashboard_Apikeys_Last_UsedInputs */
/** @typedef {{}} Dashboard_Apikeys_RevokeInputs */
/** @typedef {{}} Dashboard_Apikeys_Secret_WarningInputs */
/** @typedef {{}} Dashboard_Apikeys_Revoke_ConfirmInputs */
/** @typedef {{}} Dashboard_Account_TitleInputs */
/** @typedef {{}} Dashboard_Account_SaveInputs */
/** @typedef {{}} Dashboard_Account_Security_TitleInputs */
/** @typedef {{}} Dashboard_Account_Change_PasswordInputs */
/** @typedef {{}} Dashboard_Account_Gdpr_TitleInputs */
/** @typedef {{}} Dashboard_Account_ExportInputs */
/** @typedef {{}} Dashboard_Account_DeleteInputs */
/** @typedef {{}} Dashboard_Account_Delete_ConfirmInputs */
/** @typedef {{}} Pricing_Page_TitleInputs */
/** @typedef {{}} Faq_Page_TitleInputs */
/** @typedef {{}} Faq_Search_PlaceholderInputs */
/** @typedef {{}} Support_Page_TitleInputs */
/** @typedef {{}} Issues_Page_TitleInputs */
/** @typedef {{}} Issues_Title_LabelInputs */
/** @typedef {{}} Issues_Category_LabelInputs */
/** @typedef {{}} Issues_Category_BugInputs */
/** @typedef {{}} Issues_List_TitleInputs */
/** @typedef {{}} Issues_List_EmptyInputs */
/** @typedef {{}} Issues_Category_FeedbackInputs */
/** @typedef {{}} Issues_Category_FeatureInputs */
/** @typedef {{}} Issues_Description_LabelInputs */
/** @typedef {{}} Issues_Email_LabelInputs */
/** @typedef {{}} Issues_SubmitInputs */
/** @typedef {{}} Issues_SuccessInputs */
/** @typedef {{}} Legal_Last_UpdatedInputs */
/** @typedef {{}} Error_GenericInputs */
/** @typedef {{}} Error_UnauthorizedInputs */
/** @typedef {{}} Error_Invalid_CredentialsInputs */
/** @typedef {{}} Error_Email_Already_UsedInputs */
/** @typedef {{}} Error_Weak_PasswordInputs */
/** @typedef {{}} Error_TurnstileInputs */
/** @typedef {{}} Error_Duplicate_WaitlistInputs */
/** @typedef {{}} Error_Email_Not_ConfirmedInputs */
/** @typedef {{}} Error_Email_TakenInputs */
/** @typedef {{}} Error_Password_WeakInputs */
/** @typedef {{}} Why_SubtitleInputs */
/** @typedef {{}} Pricing_TrialInputs */
/** @typedef {{}} Pricing_Cta_TrialInputs */
/** @typedef {{}} Pricing_CompareInputs */
/** @typedef {{}} Waitlist_CtaInputs */
/** @typedef {{}} Waitlist_No_SpamInputs */
/** @typedef {{}} Form_SubmittingInputs */
/** @typedef {{}} Form_CancelInputs */
/** @typedef {{}} Form_NameInputs */
/** @typedef {{}} Signup_HeadingInputs */
/** @typedef {{}} Signup_CtaInputs */
/** @typedef {{}} Signup_Have_AccountInputs */
/** @typedef {{}} Signup_See_PricingInputs */
/** @typedef {{}} Login_HeadingInputs */
/** @typedef {{}} Login_ForgotInputs */
/** @typedef {{}} Login_Magic_SentInputs */
/** @typedef {{}} Login_CtaInputs */
/** @typedef {{}} Nav_TokenInputs */
/** @typedef {{}} Nav_LicenseInputs */
/** @typedef {{}} Nav_BillingInputs */
/** @typedef {{}} Nav_Api_KeysInputs */
/** @typedef {{}} Nav_AccountInputs */
/** @typedef {{}} Page_Home_TitleInputs */
/** @typedef {{}} Page_Home_DescInputs */
/** @typedef {{}} Page_Pricing_TitleInputs */
/** @typedef {{}} Page_Pricing_DescInputs */
/** @typedef {{}} Page_Faq_TitleInputs */
/** @typedef {{}} Page_Faq_DescInputs */
/** @typedef {{}} Page_Support_TitleInputs */
/** @typedef {{}} Page_Login_TitleInputs */
/** @typedef {{}} Page_Signup_TitleInputs */
/** @typedef {{}} Page_Issues_TitleInputs */
/** @typedef {{}} Support_SubtitleInputs */
/** @typedef {{}} Issues_SubtitleInputs */
/** @typedef {{}} Issues_Desc_LabelInputs */
/** @typedef {{}} Token_HeadingInputs */
/** @typedef {{}} Token_DescInputs */
/** @typedef {{}} Token_Quickstart_HeadingInputs */
/** @typedef {{}} Token_Reveal_CtaInputs */
/** @typedef {{}} Token_CopiedInputs */
/** @typedef {{}} Token_Copy_CtaInputs */
/** @typedef {{}} Token_Show_Once_WarningInputs */
/** @typedef {{}} Token_Already_RevealedInputs */
/** @typedef {{}} Token_Rotate_CtaInputs */
/** @typedef {{}} Token_RotatedInputs */
/** @typedef {{}} License_PlanInputs */
/** @typedef {{}} License_StartedInputs */
/** @typedef {{}} License_Trial_EndsInputs */
/** @typedef {{}} License_Cta_Subscribe_PlusInputs */
/** @typedef {{}} License_Cta_Upgrade_ProInputs */
/** @typedef {{}} License_Cta_ManageInputs */
/** @typedef {{}} License_Cta_Update_PaymentInputs */
/** @typedef {{}} License_No_ChecksInputs */
/** @typedef {{}} License_Col_DateInputs */
/** @typedef {{}} License_Col_VersionInputs */
/** @typedef {{}} License_Col_ResultInputs */
/** @typedef {{}} License_History_HeadingInputs */
/** @typedef {{}} Billing_Inactive_DescInputs */
/** @typedef {{}} Billing_Upgrade_ProInputs */
/** @typedef {{}} Billing_ManageInputs */
/** @typedef {{}} Billing_FooterInputs */
/** @typedef {{}} Apikeys_Modal_HeadingInputs */
/** @typedef {{}} Apikeys_Modal_Secret_HeadingInputs */
/** @typedef {{}} Apikeys_Modal_DoneInputs */
/** @typedef {{}} Apikeys_Name_LabelInputs */
/** @typedef {{}} Apikeys_Scopes_LabelInputs */
/** @typedef {{}} Apikeys_Create_CtaInputs */
/** @typedef {{}} Apikeys_CountInputs */
/** @typedef {{}} Apikeys_EmptyInputs */
/** @typedef {{}} Apikeys_Col_NameInputs */
/** @typedef {{}} Apikeys_Col_ScopesInputs */
/** @typedef {{}} Apikeys_Col_CreatedInputs */
/** @typedef {{}} Apikeys_Col_Last_UsedInputs */
/** @typedef {{}} Apikeys_SubtitleInputs */
/** @typedef {{}} Account_Profile_HeadingInputs */
/** @typedef {{}} Account_Security_HeadingInputs */
/** @typedef {{}} Account_Password_DescInputs */
/** @typedef {{}} Account_Change_PasswordInputs */
/** @typedef {{}} Account_Gdpr_HeadingInputs */
/** @typedef {{}} Account_Export_DescInputs */
/** @typedef {{}} Account_Export_CtaInputs */
/** @typedef {{}} Account_Delete_DescInputs */
/** @typedef {{}} Account_Delete_CtaInputs */
/** @typedef {{}} Account_Delete_Confirm_DescInputs */
/** @typedef {{}} Account_Delete_Confirm_CtaInputs */
/** @typedef {{}} Footer_RoadmapInputs */
/** @typedef {{}} Page_Roadmap_TitleInputs */
/** @typedef {{}} Page_Roadmap_DescInputs */
/** @typedef {{}} Form_SaveInputs */
/** @typedef {{}} Account_LanguageInputs */
/** @typedef {{}} Account_Profile_SavedInputs */
/** @typedef {{}} Theme_LightInputs */
/** @typedef {{}} Theme_DarkInputs */
/** @typedef {{}} Nav_MenuInputs */
/** @typedef {{}} Pricing_Feat_Workspace1Inputs */
/** @typedef {{}} Pricing_Feat_McpInputs */
/** @typedef {{}} Pricing_Feat_Api60Inputs */
/** @typedef {{}} Pricing_Feat_Api600Inputs */
/** @typedef {{}} Pricing_Feat_SdksInputs */
/** @typedef {{}} Pricing_Feat_WebhooksInputs */
/** @typedef {{}} Pricing_Feat_AcpInputs */
/** @typedef {{}} Pricing_Feat_SsoInputs */
/** @typedef {{}} Pricing_Cmp_Api_KeysInputs */
/** @typedef {{}} Pricing_Cmp_AuditInputs */
/** @typedef {{}} Pricing_Cmp_SlaInputs */
/** @typedef {{}} Pricing_Feat_Members5Inputs */
/** @typedef {{}} Pricing_Feat_Rag_UnlimitedInputs */
/** @typedef {{}} Pricing_Feat_Email_SupportInputs */
/** @typedef {{}} Pricing_Feat_Priority_SupportInputs */
/** @typedef {{}} Pricing_Feat_Priority_SlaInputs */
/** @typedef {{}} Pricing_Feat_Sso_SoonInputs */
/** @typedef {{}} Pricing_Feat_Workspaces_UnlimitedInputs */
/** @typedef {{}} Pricing_Feat_Members_UnlimitedInputs */
/** @typedef {{}} Pricing_Feat_Workspace5Inputs */
/** @typedef {{}} Pricing_Feat_Mcp_AcpInputs */
/** @typedef {{}} Pricing_Feat_Support_SlaInputs */
/** @typedef {{}} Pricing_Feat_Everything_PlusInputs */
/** @typedef {{}} Pricing_Feat_Rest_ApiInputs */
/** @typedef {{}} Pricing_Cmp_FeatureInputs */
/** @typedef {{}} Pricing_Cmp_StorageInputs */
/** @typedef {{}} Pricing_Cmp_ProjectsInputs */
/** @typedef {{}} Pricing_Cmp_UnlimitedInputs */
/** @typedef {{}} Pricing_Cmp_Days7Inputs */
/** @typedef {{}} Pricing_Cmp_Days90Inputs */
/** @typedef {{}} Pricing_Faq_HeadingInputs */
/** @typedef {{}} Pricing_Faq_Q1Inputs */
/** @typedef {{}} Pricing_Faq_A1Inputs */
/** @typedef {{}} Pricing_Faq_Q2Inputs */
/** @typedef {{}} Pricing_Faq_A2Inputs */
/** @typedef {{}} Pricing_Faq_Q3Inputs */
/** @typedef {{}} Pricing_Faq_A3Inputs */
/** @typedef {{}} Pricing_Faq_Q4Inputs */
/** @typedef {{}} Pricing_Faq_A4Inputs */
/** @typedef {{}} Pricing_Faq_Q5Inputs */
/** @typedef {{}} Pricing_Faq_A5Inputs */
import * as __pt from "./pt.js";
import * as __en from "./en.js";
import * as __es from "./es.js";
import * as __fr from "./fr.js";
import * as __it from "./it.js";
import * as __de from "./de.js";
import * as __ru from "./ru.js";
/**
 * | output |
 * | --- |
 * | "Language" |
 *
 * @param {Language_LabelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const language_label =
  /** @type {((inputs?: Language_LabelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Language_LabelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.language_label(inputs);
      if (locale === "en") return __en.language_label(inputs);
      if (locale === "es") return __es.language_label(inputs);
      if (locale === "fr") return __fr.language_label(inputs);
      if (locale === "it") return __it.language_label(inputs);
      if (locale === "de") return __de.language_label(inputs);
      return __ru.language_label(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Current language: {locale}" |
 *
 * @param {Current_LocaleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const current_locale =
  /** @type {((inputs: Current_LocaleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Current_LocaleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.current_locale(inputs);
      if (locale === "en") return __en.current_locale(inputs);
      if (locale === "es") return __es.current_locale(inputs);
      if (locale === "fr") return __fr.current_locale(inputs);
      if (locale === "it") return __it.current_locale(inputs);
      if (locale === "de") return __de.current_locale(inputs);
      return __ru.current_locale(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Vectora" |
 *
 * @param {Site_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const site_title =
  /** @type {((inputs?: Site_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Site_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.site_title(inputs);
      if (locale === "en") return __en.site_title(inputs);
      if (locale === "es") return __es.site_title(inputs);
      if (locale === "fr") return __fr.site_title(inputs);
      if (locale === "it") return __it.site_title(inputs);
      if (locale === "de") return __de.site_title(inputs);
      return __ru.site_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Self-hosted AI agent with RAG, MCP and multi-user web chat. Your data never leaves your server." |
 *
 * @param {Site_DescriptionInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const site_description =
  /** @type {((inputs?: Site_DescriptionInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Site_DescriptionInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.site_description(inputs);
      if (locale === "en") return __en.site_description(inputs);
      if (locale === "es") return __es.site_description(inputs);
      if (locale === "fr") return __fr.site_description(inputs);
      if (locale === "it") return __it.site_description(inputs);
      if (locale === "de") return __de.site_description(inputs);
      return __ru.site_description(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Pricing" |
 *
 * @param {Nav_PricingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_pricing =
  /** @type {((inputs?: Nav_PricingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_PricingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_pricing(inputs);
      if (locale === "en") return __en.nav_pricing(inputs);
      if (locale === "es") return __es.nav_pricing(inputs);
      if (locale === "fr") return __fr.nav_pricing(inputs);
      if (locale === "it") return __it.nav_pricing(inputs);
      if (locale === "de") return __de.nav_pricing(inputs);
      return __ru.nav_pricing(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Docs" |
 *
 * @param {Nav_DocsInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_docs =
  /** @type {((inputs?: Nav_DocsInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_DocsInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_docs(inputs);
      if (locale === "en") return __en.nav_docs(inputs);
      if (locale === "es") return __es.nav_docs(inputs);
      if (locale === "fr") return __fr.nav_docs(inputs);
      if (locale === "it") return __it.nav_docs(inputs);
      if (locale === "de") return __de.nav_docs(inputs);
      return __ru.nav_docs(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "FAQ" |
 *
 * @param {Nav_FaqInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_faq =
  /** @type {((inputs?: Nav_FaqInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_FaqInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_faq(inputs);
      if (locale === "en") return __en.nav_faq(inputs);
      if (locale === "es") return __es.nav_faq(inputs);
      if (locale === "fr") return __fr.nav_faq(inputs);
      if (locale === "it") return __it.nav_faq(inputs);
      if (locale === "de") return __de.nav_faq(inputs);
      return __ru.nav_faq(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Log in" |
 *
 * @param {Nav_LoginInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_login =
  /** @type {((inputs?: Nav_LoginInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_LoginInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_login(inputs);
      if (locale === "en") return __en.nav_login(inputs);
      if (locale === "es") return __es.nav_login(inputs);
      if (locale === "fr") return __fr.nav_login(inputs);
      if (locale === "it") return __it.nav_login(inputs);
      if (locale === "de") return __de.nav_login(inputs);
      return __ru.nav_login(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Start free" |
 *
 * @param {Nav_SignupInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_signup =
  /** @type {((inputs?: Nav_SignupInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_SignupInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_signup(inputs);
      if (locale === "en") return __en.nav_signup(inputs);
      if (locale === "es") return __es.nav_signup(inputs);
      if (locale === "fr") return __fr.nav_signup(inputs);
      if (locale === "it") return __it.nav_signup(inputs);
      if (locale === "de") return __de.nav_signup(inputs);
      return __ru.nav_signup(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Support" |
 *
 * @param {Nav_SupportInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_support =
  /** @type {((inputs?: Nav_SupportInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_SupportInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_support(inputs);
      if (locale === "en") return __en.nav_support(inputs);
      if (locale === "es") return __es.nav_support(inputs);
      if (locale === "fr") return __fr.nav_support(inputs);
      if (locale === "it") return __it.nav_support(inputs);
      if (locale === "de") return __de.nav_support(inputs);
      return __ru.nav_support(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Self-hosted · Privacy-first · Open core" |
 *
 * @param {Hero_EyebrowInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const hero_eyebrow =
  /** @type {((inputs?: Hero_EyebrowInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Hero_EyebrowInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.hero_eyebrow(inputs);
      if (locale === "en") return __en.hero_eyebrow(inputs);
      if (locale === "es") return __es.hero_eyebrow(inputs);
      if (locale === "fr") return __fr.hero_eyebrow(inputs);
      if (locale === "it") return __it.hero_eyebrow(inputs);
      if (locale === "de") return __de.hero_eyebrow(inputs);
      return __ru.hero_eyebrow(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Your AI. Your Data. Your Server." |
 *
 * @param {Hero_TaglineInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const hero_tagline =
  /** @type {((inputs?: Hero_TaglineInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Hero_TaglineInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.hero_tagline(inputs);
      if (locale === "en") return __en.hero_tagline(inputs);
      if (locale === "es") return __es.hero_tagline(inputs);
      if (locale === "fr") return __fr.hero_tagline(inputs);
      if (locale === "it") return __it.hero_tagline(inputs);
      if (locale === "de") return __de.hero_tagline(inputs);
      return __ru.hero_tagline(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Self-hosted AI agent with RAG, MCP and multi-user web chat. Your data never leaves your server." |
 *
 * @param {Hero_SubtitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const hero_subtitle =
  /** @type {((inputs?: Hero_SubtitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Hero_SubtitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.hero_subtitle(inputs);
      if (locale === "en") return __en.hero_subtitle(inputs);
      if (locale === "es") return __es.hero_subtitle(inputs);
      if (locale === "fr") return __fr.hero_subtitle(inputs);
      if (locale === "it") return __it.hero_subtitle(inputs);
      if (locale === "de") return __de.hero_subtitle(inputs);
      return __ru.hero_subtitle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Vectora AI agent in action" |
 *
 * @param {Hero_Gif_AltInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const hero_gif_alt =
  /** @type {((inputs?: Hero_Gif_AltInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Hero_Gif_AltInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.hero_gif_alt(inputs);
      if (locale === "en") return __en.hero_gif_alt(inputs);
      if (locale === "es") return __es.hero_gif_alt(inputs);
      if (locale === "fr") return __fr.hero_gif_alt(inputs);
      if (locale === "it") return __it.hero_gif_alt(inputs);
      if (locale === "de") return __de.hero_gif_alt(inputs);
      return __ru.hero_gif_alt(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Vectora contextual conversation" |
 *
 * @param {Showcase_Chat_AltInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_chat_alt =
  /** @type {((inputs?: Showcase_Chat_AltInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Chat_AltInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_chat_alt(inputs);
      if (locale === "en") return __en.showcase_chat_alt(inputs);
      if (locale === "es") return __es.showcase_chat_alt(inputs);
      if (locale === "fr") return __fr.showcase_chat_alt(inputs);
      if (locale === "it") return __it.showcase_chat_alt(inputs);
      if (locale === "de") return __de.showcase_chat_alt(inputs);
      return __ru.showcase_chat_alt(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Vectora RAG semantic search" |
 *
 * @param {Showcase_Rag_AltInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_rag_alt =
  /** @type {((inputs?: Showcase_Rag_AltInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Rag_AltInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_rag_alt(inputs);
      if (locale === "en") return __en.showcase_rag_alt(inputs);
      if (locale === "es") return __es.showcase_rag_alt(inputs);
      if (locale === "fr") return __fr.showcase_rag_alt(inputs);
      if (locale === "it") return __it.showcase_rag_alt(inputs);
      if (locale === "de") return __de.showcase_rag_alt(inputs);
      return __ru.showcase_rag_alt(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Vectora coding agent" |
 *
 * @param {Showcase_Code_AltInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_code_alt =
  /** @type {((inputs?: Showcase_Code_AltInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Code_AltInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_code_alt(inputs);
      if (locale === "en") return __en.showcase_code_alt(inputs);
      if (locale === "es") return __es.showcase_code_alt(inputs);
      if (locale === "fr") return __fr.showcase_code_alt(inputs);
      if (locale === "it") return __it.showcase_code_alt(inputs);
      if (locale === "de") return __de.showcase_code_alt(inputs);
      return __ru.showcase_code_alt(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Vectora structured reasoning" |
 *
 * @param {Showcase_Plan_AltInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_plan_alt =
  /** @type {((inputs?: Showcase_Plan_AltInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Plan_AltInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_plan_alt(inputs);
      if (locale === "en") return __en.showcase_plan_alt(inputs);
      if (locale === "es") return __es.showcase_plan_alt(inputs);
      if (locale === "fr") return __fr.showcase_plan_alt(inputs);
      if (locale === "it") return __it.showcase_plan_alt(inputs);
      if (locale === "de") return __de.showcase_plan_alt(inputs);
      return __ru.showcase_plan_alt(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Start free trial — 30 days" |
 *
 * @param {Hero_Cta_TrialInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const hero_cta_trial =
  /** @type {((inputs?: Hero_Cta_TrialInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Hero_Cta_TrialInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.hero_cta_trial(inputs);
      if (locale === "en") return __en.hero_cta_trial(inputs);
      if (locale === "es") return __es.hero_cta_trial(inputs);
      if (locale === "fr") return __fr.hero_cta_trial(inputs);
      if (locale === "it") return __it.hero_cta_trial(inputs);
      if (locale === "de") return __de.hero_cta_trial(inputs);
      return __ru.hero_cta_trial(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "See pricing" |
 *
 * @param {Hero_Cta_PricingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const hero_cta_pricing =
  /** @type {((inputs?: Hero_Cta_PricingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Hero_Cta_PricingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.hero_cta_pricing(inputs);
      if (locale === "en") return __en.hero_cta_pricing(inputs);
      if (locale === "es") return __es.hero_cta_pricing(inputs);
      if (locale === "fr") return __fr.hero_cta_pricing(inputs);
      if (locale === "it") return __it.hero_cta_pricing(inputs);
      if (locale === "de") return __de.hero_cta_pricing(inputs);
      return __ru.hero_cta_pricing(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "See Vectora in action" |
 *
 * @param {Showcase_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_title =
  /** @type {((inputs?: Showcase_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_title(inputs);
      if (locale === "en") return __en.showcase_title(inputs);
      if (locale === "es") return __es.showcase_title(inputs);
      if (locale === "fr") return __fr.showcase_title(inputs);
      if (locale === "it") return __it.showcase_title(inputs);
      if (locale === "de") return __de.showcase_title(inputs);
      return __ru.showcase_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Contextual conversation" |
 *
 * @param {Showcase_Chat_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_chat_title =
  /** @type {((inputs?: Showcase_Chat_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Chat_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_chat_title(inputs);
      if (locale === "en") return __en.showcase_chat_title(inputs);
      if (locale === "es") return __es.showcase_chat_title(inputs);
      if (locale === "fr") return __fr.showcase_chat_title(inputs);
      if (locale === "it") return __it.showcase_chat_title(inputs);
      if (locale === "de") return __de.showcase_chat_title(inputs);
      return __ru.showcase_chat_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Ask in natural language — about code, documents, spreadsheets or any file on your server." |
 *
 * @param {Showcase_Chat_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_chat_desc =
  /** @type {((inputs?: Showcase_Chat_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Chat_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_chat_desc(inputs);
      if (locale === "en") return __en.showcase_chat_desc(inputs);
      if (locale === "es") return __es.showcase_chat_desc(inputs);
      if (locale === "fr") return __fr.showcase_chat_desc(inputs);
      if (locale === "it") return __it.showcase_chat_desc(inputs);
      if (locale === "de") return __de.showcase_chat_desc(inputs);
      return __ru.showcase_chat_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "RAG — semantic search" |
 *
 * @param {Showcase_Rag_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_rag_title =
  /** @type {((inputs?: Showcase_Rag_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Rag_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_rag_title(inputs);
      if (locale === "en") return __en.showcase_rag_title(inputs);
      if (locale === "es") return __es.showcase_rag_title(inputs);
      if (locale === "fr") return __fr.showcase_rag_title(inputs);
      if (locale === "it") return __it.showcase_rag_title(inputs);
      if (locale === "de") return __de.showcase_rag_title(inputs);
      return __ru.showcase_rag_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Index any document. Vectora finds the right information with vector search and relevance reranking." |
 *
 * @param {Showcase_Rag_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_rag_desc =
  /** @type {((inputs?: Showcase_Rag_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Rag_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_rag_desc(inputs);
      if (locale === "en") return __en.showcase_rag_desc(inputs);
      if (locale === "es") return __es.showcase_rag_desc(inputs);
      if (locale === "fr") return __fr.showcase_rag_desc(inputs);
      if (locale === "it") return __it.showcase_rag_desc(inputs);
      if (locale === "de") return __de.showcase_rag_desc(inputs);
      return __ru.showcase_rag_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Coding agent" |
 *
 * @param {Showcase_Code_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_code_title =
  /** @type {((inputs?: Showcase_Code_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Code_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_code_title(inputs);
      if (locale === "en") return __en.showcase_code_title(inputs);
      if (locale === "es") return __es.showcase_code_title(inputs);
      if (locale === "fr") return __fr.showcase_code_title(inputs);
      if (locale === "it") return __it.showcase_code_title(inputs);
      if (locale === "de") return __de.showcase_code_title(inputs);
      return __ru.showcase_code_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "From planning to code. Vectora writes, refactors and explains using your repository context." |
 *
 * @param {Showcase_Code_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_code_desc =
  /** @type {((inputs?: Showcase_Code_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Code_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_code_desc(inputs);
      if (locale === "en") return __en.showcase_code_desc(inputs);
      if (locale === "es") return __es.showcase_code_desc(inputs);
      if (locale === "fr") return __fr.showcase_code_desc(inputs);
      if (locale === "it") return __it.showcase_code_desc(inputs);
      if (locale === "de") return __de.showcase_code_desc(inputs);
      return __ru.showcase_code_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Structured reasoning" |
 *
 * @param {Showcase_Plan_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_plan_title =
  /** @type {((inputs?: Showcase_Plan_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Plan_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_plan_title(inputs);
      if (locale === "en") return __en.showcase_plan_title(inputs);
      if (locale === "es") return __es.showcase_plan_title(inputs);
      if (locale === "fr") return __fr.showcase_plan_title(inputs);
      if (locale === "it") return __it.showcase_plan_title(inputs);
      if (locale === "de") return __de.showcase_plan_title(inputs);
      return __ru.showcase_plan_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Complex tasks broken down automatically. Watch each reasoning step in real time." |
 *
 * @param {Showcase_Plan_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const showcase_plan_desc =
  /** @type {((inputs?: Showcase_Plan_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Showcase_Plan_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.showcase_plan_desc(inputs);
      if (locale === "en") return __en.showcase_plan_desc(inputs);
      if (locale === "es") return __es.showcase_plan_desc(inputs);
      if (locale === "fr") return __fr.showcase_plan_desc(inputs);
      if (locale === "it") return __it.showcase_plan_desc(inputs);
      if (locale === "de") return __de.showcase_plan_desc(inputs);
      return __ru.showcase_plan_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "How Vectora thinks" |
 *
 * @param {Agentic_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const agentic_heading =
  /** @type {((inputs?: Agentic_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Agentic_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.agentic_heading(inputs);
      if (locale === "en") return __en.agentic_heading(inputs);
      if (locale === "es") return __es.agentic_heading(inputs);
      if (locale === "fr") return __fr.agentic_heading(inputs);
      if (locale === "it") return __it.agentic_heading(inputs);
      if (locale === "de") return __de.agentic_heading(inputs);
      return __ru.agentic_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Technical docs →" |
 *
 * @param {Agentic_Docs_LinkInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const agentic_docs_link =
  /** @type {((inputs?: Agentic_Docs_LinkInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Agentic_Docs_LinkInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.agentic_docs_link(inputs);
      if (locale === "en") return __en.agentic_docs_link(inputs);
      if (locale === "es") return __es.agentic_docs_link(inputs);
      if (locale === "fr") return __fr.agentic_docs_link(inputs);
      if (locale === "it") return __it.agentic_docs_link(inputs);
      if (locale === "de") return __de.agentic_docs_link(inputs);
      return __ru.agentic_docs_link(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Orchestrator decides in real time: respond, delegate or parallelize" |
 *
 * @param {Agentic_Bullet_OrchestratorInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const agentic_bullet_orchestrator =
  /** @type {((inputs?: Agentic_Bullet_OrchestratorInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Agentic_Bullet_OrchestratorInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.agentic_bullet_orchestrator(inputs);
      if (locale === "en") return __en.agentic_bullet_orchestrator(inputs);
      if (locale === "es") return __es.agentic_bullet_orchestrator(inputs);
      if (locale === "fr") return __fr.agentic_bullet_orchestrator(inputs);
      if (locale === "it") return __it.agentic_bullet_orchestrator(inputs);
      if (locale === "de") return __de.agentic_bullet_orchestrator(inputs);
      return __ru.agentic_bullet_orchestrator(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Coder Agent: files, terminal, git, code implementation" |
 *
 * @param {Agentic_Bullet_CoderInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const agentic_bullet_coder =
  /** @type {((inputs?: Agentic_Bullet_CoderInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Agentic_Bullet_CoderInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.agentic_bullet_coder(inputs);
      if (locale === "en") return __en.agentic_bullet_coder(inputs);
      if (locale === "es") return __es.agentic_bullet_coder(inputs);
      if (locale === "fr") return __fr.agentic_bullet_coder(inputs);
      if (locale === "it") return __it.agentic_bullet_coder(inputs);
      if (locale === "de") return __de.agentic_bullet_coder(inputs);
      return __ru.agentic_bullet_coder(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Search Agent: real-time web, RAG, knowledge base curation" |
 *
 * @param {Agentic_Bullet_SearchInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const agentic_bullet_search =
  /** @type {((inputs?: Agentic_Bullet_SearchInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Agentic_Bullet_SearchInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.agentic_bullet_search(inputs);
      if (locale === "en") return __en.agentic_bullet_search(inputs);
      if (locale === "es") return __es.agentic_bullet_search(inputs);
      if (locale === "fr") return __fr.agentic_bullet_search(inputs);
      if (locale === "it") return __it.agentic_bullet_search(inputs);
      if (locale === "de") return __de.agentic_bullet_search(inputs);
      return __ru.agentic_bullet_search(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "RAG Subgraph: query expansion, reranking, web fallback" |
 *
 * @param {Agentic_Bullet_RagInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const agentic_bullet_rag =
  /** @type {((inputs?: Agentic_Bullet_RagInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Agentic_Bullet_RagInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.agentic_bullet_rag(inputs);
      if (locale === "en") return __en.agentic_bullet_rag(inputs);
      if (locale === "es") return __es.agentic_bullet_rag(inputs);
      if (locale === "fr") return __fr.agentic_bullet_rag(inputs);
      if (locale === "it") return __it.agentic_bullet_rag(inputs);
      if (locale === "de") return __de.agentic_bullet_rag(inputs);
      return __ru.agentic_bullet_rag(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Parallel mode: independent tasks run at the same time" |
 *
 * @param {Agentic_Bullet_ParallelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const agentic_bullet_parallel =
  /** @type {((inputs?: Agentic_Bullet_ParallelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Agentic_Bullet_ParallelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.agentic_bullet_parallel(inputs);
      if (locale === "en") return __en.agentic_bullet_parallel(inputs);
      if (locale === "es") return __es.agentic_bullet_parallel(inputs);
      if (locale === "fr") return __fr.agentic_bullet_parallel(inputs);
      if (locale === "it") return __it.agentic_bullet_parallel(inputs);
      if (locale === "de") return __de.agentic_bullet_parallel(inputs);
      return __ru.agentic_bullet_parallel(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Your documents, accessible anywhere" |
 *
 * @param {Rag_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const rag_heading =
  /** @type {((inputs?: Rag_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Rag_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.rag_heading(inputs);
      if (locale === "en") return __en.rag_heading(inputs);
      if (locale === "es") return __es.rag_heading(inputs);
      if (locale === "fr") return __fr.rag_heading(inputs);
      if (locale === "it") return __it.rag_heading(inputs);
      if (locale === "de") return __de.rag_heading(inputs);
      return __ru.rag_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "From zero to team in minutes" |
 *
 * @param {Team_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_heading =
  /** @type {((inputs?: Team_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_heading(inputs);
      if (locale === "en") return __en.team_heading(inputs);
      if (locale === "es") return __es.team_heading(inputs);
      if (locale === "fr") return __fr.team_heading(inputs);
      if (locale === "it") return __it.team_heading(inputs);
      if (locale === "de") return __de.team_heading(inputs);
      return __ru.team_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Deploy the stack" |
 *
 * @param {Team_Step1_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_step1_title =
  /** @type {((inputs?: Team_Step1_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_Step1_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_step1_title(inputs);
      if (locale === "en") return __en.team_step1_title(inputs);
      if (locale === "es") return __es.team_step1_title(inputs);
      if (locale === "fr") return __fr.team_step1_title(inputs);
      if (locale === "it") return __it.team_step1_title(inputs);
      if (locale === "de") return __de.team_step1_title(inputs);
      return __ru.team_step1_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "A single file. No external dependencies." |
 *
 * @param {Team_Step1_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_step1_desc =
  /** @type {((inputs?: Team_Step1_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_Step1_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_step1_desc(inputs);
      if (locale === "en") return __en.team_step1_desc(inputs);
      if (locale === "es") return __es.team_step1_desc(inputs);
      if (locale === "fr") return __fr.team_step1_desc(inputs);
      if (locale === "it") return __it.team_step1_desc(inputs);
      if (locale === "de") return __de.team_step1_desc(inputs);
      return __ru.team_step1_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Root account" |
 *
 * @param {Team_Step2_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_step2_title =
  /** @type {((inputs?: Team_Step2_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_Step2_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_step2_title(inputs);
      if (locale === "en") return __en.team_step2_title(inputs);
      if (locale === "es") return __es.team_step2_title(inputs);
      if (locale === "fr") return __fr.team_step2_title(inputs);
      if (locale === "it") return __it.team_step2_title(inputs);
      if (locale === "de") return __de.team_step2_title(inputs);
      return __ru.team_step2_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Full administrative access to your workspace." |
 *
 * @param {Team_Step2_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_step2_desc =
  /** @type {((inputs?: Team_Step2_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_Step2_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_step2_desc(inputs);
      if (locale === "en") return __en.team_step2_desc(inputs);
      if (locale === "es") return __es.team_step2_desc(inputs);
      if (locale === "fr") return __fr.team_step2_desc(inputs);
      if (locale === "it") return __it.team_step2_desc(inputs);
      if (locale === "de") return __de.team_step2_desc(inputs);
      return __ru.team_step2_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Invite team" |
 *
 * @param {Team_Step3_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_step3_title =
  /** @type {((inputs?: Team_Step3_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_Step3_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_step3_title(inputs);
      if (locale === "en") return __en.team_step3_title(inputs);
      if (locale === "es") return __es.team_step3_title(inputs);
      if (locale === "fr") return __fr.team_step3_title(inputs);
      if (locale === "it") return __it.team_step3_title(inputs);
      if (locale === "de") return __de.team_step3_title(inputs);
      return __ru.team_step3_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Permission control per project." |
 *
 * @param {Team_Step3_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_step3_desc =
  /** @type {((inputs?: Team_Step3_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_Step3_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_step3_desc(inputs);
      if (locale === "en") return __en.team_step3_desc(inputs);
      if (locale === "es") return __es.team_step3_desc(inputs);
      if (locale === "fr") return __fr.team_step3_desc(inputs);
      if (locale === "it") return __it.team_step3_desc(inputs);
      if (locale === "de") return __de.team_step3_desc(inputs);
      return __ru.team_step3_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Initialize projects" |
 *
 * @param {Team_Step4_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_step4_title =
  /** @type {((inputs?: Team_Step4_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_Step4_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_step4_title(inputs);
      if (locale === "en") return __en.team_step4_title(inputs);
      if (locale === "es") return __es.team_step4_title(inputs);
      if (locale === "fr") return __fr.team_step4_title(inputs);
      if (locale === "it") return __it.team_step4_title(inputs);
      if (locale === "de") return __de.team_step4_title(inputs);
      return __ru.team_step4_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Each project has its own knowledge base and history." |
 *
 * @param {Team_Step4_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_step4_desc =
  /** @type {((inputs?: Team_Step4_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_Step4_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_step4_desc(inputs);
      if (locale === "en") return __en.team_step4_desc(inputs);
      if (locale === "es") return __es.team_step4_desc(inputs);
      if (locale === "fr") return __fr.team_step4_desc(inputs);
      if (locale === "it") return __it.team_step4_desc(inputs);
      if (locale === "de") return __de.team_step4_desc(inputs);
      return __ru.team_step4_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Compatible with any Linux VPS — AWS, GCP, Hetzner, DigitalOcean" |
 *
 * @param {Team_CompatInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const team_compat =
  /** @type {((inputs?: Team_CompatInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Team_CompatInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.team_compat(inputs);
      if (locale === "en") return __en.team_compat(inputs);
      if (locale === "es") return __es.team_compat(inputs);
      if (locale === "fr") return __fr.team_compat(inputs);
      if (locale === "it") return __it.team_compat(inputs);
      if (locale === "de") return __de.team_compat(inputs);
      return __ru.team_compat(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Why self-hosted?" |
 *
 * @param {Why_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_heading =
  /** @type {((inputs?: Why_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_heading(inputs);
      if (locale === "en") return __en.why_heading(inputs);
      if (locale === "es") return __es.why_heading(inputs);
      if (locale === "fr") return __fr.why_heading(inputs);
      if (locale === "it") return __it.why_heading(inputs);
      if (locale === "de") return __de.why_heading(inputs);
      return __ru.why_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Privacy" |
 *
 * @param {Why_Privacy_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_privacy_title =
  /** @type {((inputs?: Why_Privacy_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_Privacy_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_privacy_title(inputs);
      if (locale === "en") return __en.why_privacy_title(inputs);
      if (locale === "es") return __es.why_privacy_title(inputs);
      if (locale === "fr") return __fr.why_privacy_title(inputs);
      if (locale === "it") return __it.why_privacy_title(inputs);
      if (locale === "de") return __de.why_privacy_title(inputs);
      return __ru.why_privacy_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "No conversation, document or code is sent to third parties. LGPD, GDPR and internal policy compliance." |
 *
 * @param {Why_Privacy_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_privacy_desc =
  /** @type {((inputs?: Why_Privacy_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_Privacy_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_privacy_desc(inputs);
      if (locale === "en") return __en.why_privacy_desc(inputs);
      if (locale === "es") return __es.why_privacy_desc(inputs);
      if (locale === "fr") return __fr.why_privacy_desc(inputs);
      if (locale === "it") return __it.why_privacy_desc(inputs);
      if (locale === "de") return __de.why_privacy_desc(inputs);
      return __ru.why_privacy_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Cost" |
 *
 * @param {Why_Cost_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_cost_title =
  /** @type {((inputs?: Why_Cost_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_Cost_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_cost_title(inputs);
      if (locale === "en") return __en.why_cost_title(inputs);
      if (locale === "es") return __es.why_cost_title(inputs);
      if (locale === "fr") return __fr.why_cost_title(inputs);
      if (locale === "it") return __it.why_cost_title(inputs);
      if (locale === "de") return __de.why_cost_title(inputs);
      return __ru.why_cost_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Fixed price for the Vectora license. LLM costs under your control — use local models for free." |
 *
 * @param {Why_Cost_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_cost_desc =
  /** @type {((inputs?: Why_Cost_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_Cost_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_cost_desc(inputs);
      if (locale === "en") return __en.why_cost_desc(inputs);
      if (locale === "es") return __es.why_cost_desc(inputs);
      if (locale === "fr") return __fr.why_cost_desc(inputs);
      if (locale === "it") return __it.why_cost_desc(inputs);
      if (locale === "de") return __de.why_cost_desc(inputs);
      return __ru.why_cost_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Customization" |
 *
 * @param {Why_Custom_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_custom_title =
  /** @type {((inputs?: Why_Custom_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_Custom_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_custom_title(inputs);
      if (locale === "en") return __en.why_custom_title(inputs);
      if (locale === "es") return __es.why_custom_title(inputs);
      if (locale === "fr") return __fr.why_custom_title(inputs);
      if (locale === "it") return __it.why_custom_title(inputs);
      if (locale === "de") return __de.why_custom_title(inputs);
      return __ru.why_custom_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Configure LLM providers, embedding models, chunk size, system prompts and much more." |
 *
 * @param {Why_Custom_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_custom_desc =
  /** @type {((inputs?: Why_Custom_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_Custom_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_custom_desc(inputs);
      if (locale === "en") return __en.why_custom_desc(inputs);
      if (locale === "es") return __es.why_custom_desc(inputs);
      if (locale === "fr") return __fr.why_custom_desc(inputs);
      if (locale === "it") return __it.why_custom_desc(inputs);
      if (locale === "de") return __de.why_custom_desc(inputs);
      return __ru.why_custom_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Sovereignty" |
 *
 * @param {Why_Sovereign_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_sovereign_title =
  /** @type {((inputs?: Why_Sovereign_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_Sovereign_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_sovereign_title(inputs);
      if (locale === "en") return __en.why_sovereign_title(inputs);
      if (locale === "es") return __es.why_sovereign_title(inputs);
      if (locale === "fr") return __fr.why_sovereign_title(inputs);
      if (locale === "it") return __it.why_sovereign_title(inputs);
      if (locale === "de") return __de.why_sovereign_title(inputs);
      return __ru.why_sovereign_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "No lock-in. No cloud dependency. Run offline if needed. Your server, your rules." |
 *
 * @param {Why_Sovereign_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_sovereign_desc =
  /** @type {((inputs?: Why_Sovereign_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_Sovereign_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_sovereign_desc(inputs);
      if (locale === "en") return __en.why_sovereign_desc(inputs);
      if (locale === "es") return __es.why_sovereign_desc(inputs);
      if (locale === "fr") return __fr.why_sovereign_desc(inputs);
      if (locale === "it") return __it.why_sovereign_desc(inputs);
      if (locale === "de") return __de.why_sovereign_desc(inputs);
      return __ru.why_sovereign_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Simple, transparent pricing" |
 *
 * @param {Pricing_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_heading =
  /** @type {((inputs?: Pricing_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_heading(inputs);
      if (locale === "en") return __en.pricing_heading(inputs);
      if (locale === "es") return __es.pricing_heading(inputs);
      if (locale === "fr") return __fr.pricing_heading(inputs);
      if (locale === "it") return __it.pricing_heading(inputs);
      if (locale === "de") return __de.pricing_heading(inputs);
      return __ru.pricing_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "30-day free trial. No credit card required." |
 *
 * @param {Pricing_SubtitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_subtitle =
  /** @type {((inputs?: Pricing_SubtitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_SubtitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_subtitle(inputs);
      if (locale === "en") return __en.pricing_subtitle(inputs);
      if (locale === "es") return __es.pricing_subtitle(inputs);
      if (locale === "fr") return __fr.pricing_subtitle(inputs);
      if (locale === "it") return __it.pricing_subtitle(inputs);
      if (locale === "de") return __de.pricing_subtitle(inputs);
      return __ru.pricing_subtitle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "For small teams" |
 *
 * @param {Pricing_Plus_BadgeInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_plus_badge =
  /** @type {((inputs?: Pricing_Plus_BadgeInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Plus_BadgeInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_plus_badge(inputs);
      if (locale === "en") return __en.pricing_plus_badge(inputs);
      if (locale === "es") return __es.pricing_plus_badge(inputs);
      if (locale === "fr") return __fr.pricing_plus_badge(inputs);
      if (locale === "it") return __it.pricing_plus_badge(inputs);
      if (locale === "de") return __de.pricing_plus_badge(inputs);
      return __ru.pricing_plus_badge(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "For companies" |
 *
 * @param {Pricing_Pro_BadgeInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_pro_badge =
  /** @type {((inputs?: Pricing_Pro_BadgeInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Pro_BadgeInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_pro_badge(inputs);
      if (locale === "en") return __en.pricing_pro_badge(inputs);
      if (locale === "es") return __es.pricing_pro_badge(inputs);
      if (locale === "fr") return __fr.pricing_pro_badge(inputs);
      if (locale === "it") return __it.pricing_pro_badge(inputs);
      if (locale === "de") return __de.pricing_pro_badge(inputs);
      return __ru.pricing_pro_badge(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Start free trial" |
 *
 * @param {Pricing_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cta =
  /** @type {((inputs?: Pricing_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cta(inputs);
      if (locale === "en") return __en.pricing_cta(inputs);
      if (locale === "es") return __es.pricing_cta(inputs);
      if (locale === "fr") return __fr.pricing_cta(inputs);
      if (locale === "it") return __it.pricing_cta(inputs);
      if (locale === "de") return __de.pricing_cta(inputs);
      return __ru.pricing_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "See full comparison" |
 *
 * @param {Pricing_Compare_ToggleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_compare_toggle =
  /** @type {((inputs?: Pricing_Compare_ToggleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Compare_ToggleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_compare_toggle(inputs);
      if (locale === "en") return __en.pricing_compare_toggle(inputs);
      if (locale === "es") return __es.pricing_compare_toggle(inputs);
      if (locale === "fr") return __fr.pricing_compare_toggle(inputs);
      if (locale === "it") return __it.pricing_compare_toggle(inputs);
      if (locale === "de") return __de.pricing_compare_toggle(inputs);
      return __ru.pricing_compare_toggle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "BRL" |
 *
 * @param {Pricing_Toggle_BrlInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_toggle_brl =
  /** @type {((inputs?: Pricing_Toggle_BrlInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Toggle_BrlInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_toggle_brl(inputs);
      if (locale === "en") return __en.pricing_toggle_brl(inputs);
      if (locale === "es") return __es.pricing_toggle_brl(inputs);
      if (locale === "fr") return __fr.pricing_toggle_brl(inputs);
      if (locale === "it") return __it.pricing_toggle_brl(inputs);
      if (locale === "de") return __de.pricing_toggle_brl(inputs);
      return __ru.pricing_toggle_brl(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "USD" |
 *
 * @param {Pricing_Toggle_UsdInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_toggle_usd =
  /** @type {((inputs?: Pricing_Toggle_UsdInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Toggle_UsdInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_toggle_usd(inputs);
      if (locale === "en") return __en.pricing_toggle_usd(inputs);
      if (locale === "es") return __es.pricing_toggle_usd(inputs);
      if (locale === "fr") return __fr.pricing_toggle_usd(inputs);
      if (locale === "it") return __it.pricing_toggle_usd(inputs);
      if (locale === "de") return __de.pricing_toggle_usd(inputs);
      return __ru.pricing_toggle_usd(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "/month" |
 *
 * @param {Pricing_Per_MonthInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_per_month =
  /** @type {((inputs?: Pricing_Per_MonthInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Per_MonthInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_per_month(inputs);
      if (locale === "en") return __en.pricing_per_month(inputs);
      if (locale === "es") return __es.pricing_per_month(inputs);
      if (locale === "fr") return __fr.pricing_per_month(inputs);
      if (locale === "it") return __it.pricing_per_month(inputs);
      if (locale === "de") return __de.pricing_per_month(inputs);
      return __ru.pricing_per_month(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Be one of the first" |
 *
 * @param {Waitlist_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_heading =
  /** @type {((inputs?: Waitlist_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_heading(inputs);
      if (locale === "en") return __en.waitlist_heading(inputs);
      if (locale === "es") return __es.waitlist_heading(inputs);
      if (locale === "fr") return __fr.waitlist_heading(inputs);
      if (locale === "it") return __it.waitlist_heading(inputs);
      if (locale === "de") return __de.waitlist_heading(inputs);
      return __ru.waitlist_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "30-day free trial for those who join the list now." |
 *
 * @param {Waitlist_SubtitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_subtitle =
  /** @type {((inputs?: Waitlist_SubtitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_SubtitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_subtitle(inputs);
      if (locale === "en") return __en.waitlist_subtitle(inputs);
      if (locale === "es") return __es.waitlist_subtitle(inputs);
      if (locale === "fr") return __fr.waitlist_subtitle(inputs);
      if (locale === "it") return __it.waitlist_subtitle(inputs);
      if (locale === "de") return __de.waitlist_subtitle(inputs);
      return __ru.waitlist_subtitle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "your@email.com" |
 *
 * @param {Waitlist_Email_PlaceholderInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_email_placeholder =
  /** @type {((inputs?: Waitlist_Email_PlaceholderInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_Email_PlaceholderInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_email_placeholder(inputs);
      if (locale === "en") return __en.waitlist_email_placeholder(inputs);
      if (locale === "es") return __es.waitlist_email_placeholder(inputs);
      if (locale === "fr") return __fr.waitlist_email_placeholder(inputs);
      if (locale === "it") return __it.waitlist_email_placeholder(inputs);
      if (locale === "de") return __de.waitlist_email_placeholder(inputs);
      return __ru.waitlist_email_placeholder(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Join the list" |
 *
 * @param {Waitlist_SubmitInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_submit =
  /** @type {((inputs?: Waitlist_SubmitInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_SubmitInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_submit(inputs);
      if (locale === "en") return __en.waitlist_submit(inputs);
      if (locale === "es") return __es.waitlist_submit(inputs);
      if (locale === "fr") return __fr.waitlist_submit(inputs);
      if (locale === "it") return __it.waitlist_submit(inputs);
      if (locale === "de") return __de.waitlist_submit(inputs);
      return __ru.waitlist_submit(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "✓ You're on the list! Check your email." |
 *
 * @param {Waitlist_SuccessInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_success =
  /** @type {((inputs?: Waitlist_SuccessInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_SuccessInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_success(inputs);
      if (locale === "en") return __en.waitlist_success(inputs);
      if (locale === "es") return __es.waitlist_success(inputs);
      if (locale === "fr") return __fr.waitlist_success(inputs);
      if (locale === "it") return __it.waitlist_success(inputs);
      if (locale === "de") return __de.waitlist_success(inputs);
      return __ru.waitlist_success(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "That email is already on the list." |
 *
 * @param {Waitlist_DuplicateInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_duplicate =
  /** @type {((inputs?: Waitlist_DuplicateInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_DuplicateInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_duplicate(inputs);
      if (locale === "en") return __en.waitlist_duplicate(inputs);
      if (locale === "es") return __es.waitlist_duplicate(inputs);
      if (locale === "fr") return __fr.waitlist_duplicate(inputs);
      if (locale === "it") return __it.waitlist_duplicate(inputs);
      if (locale === "de") return __de.waitlist_duplicate(inputs);
      return __ru.waitlist_duplicate(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "No spam. Just the launch announcement." |
 *
 * @param {Waitlist_FooterInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_footer =
  /** @type {((inputs?: Waitlist_FooterInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_FooterInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_footer(inputs);
      if (locale === "en") return __en.waitlist_footer(inputs);
      if (locale === "es") return __es.waitlist_footer(inputs);
      if (locale === "fr") return __fr.waitlist_footer(inputs);
      if (locale === "it") return __it.waitlist_footer(inputs);
      if (locale === "de") return __de.waitlist_footer(inputs);
      return __ru.waitlist_footer(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Made with ❤ in Brazil" |
 *
 * @param {Footer_Made_InInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_made_in =
  /** @type {((inputs?: Footer_Made_InInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_Made_InInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_made_in(inputs);
      if (locale === "en") return __en.footer_made_in(inputs);
      if (locale === "es") return __es.footer_made_in(inputs);
      if (locale === "fr") return __fr.footer_made_in(inputs);
      if (locale === "it") return __it.footer_made_in(inputs);
      if (locale === "de") return __de.footer_made_in(inputs);
      return __ru.footer_made_in(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Product" |
 *
 * @param {Footer_ProductInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_product =
  /** @type {((inputs?: Footer_ProductInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_ProductInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_product(inputs);
      if (locale === "en") return __en.footer_product(inputs);
      if (locale === "es") return __es.footer_product(inputs);
      if (locale === "fr") return __fr.footer_product(inputs);
      if (locale === "it") return __it.footer_product(inputs);
      if (locale === "de") return __de.footer_product(inputs);
      return __ru.footer_product(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Legal" |
 *
 * @param {Footer_LegalInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_legal =
  /** @type {((inputs?: Footer_LegalInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_LegalInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_legal(inputs);
      if (locale === "en") return __en.footer_legal(inputs);
      if (locale === "es") return __es.footer_legal(inputs);
      if (locale === "fr") return __fr.footer_legal(inputs);
      if (locale === "it") return __it.footer_legal(inputs);
      if (locale === "de") return __de.footer_legal(inputs);
      return __ru.footer_legal(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Privacy" |
 *
 * @param {Footer_PrivacyInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_privacy =
  /** @type {((inputs?: Footer_PrivacyInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_PrivacyInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_privacy(inputs);
      if (locale === "en") return __en.footer_privacy(inputs);
      if (locale === "es") return __es.footer_privacy(inputs);
      if (locale === "fr") return __fr.footer_privacy(inputs);
      if (locale === "it") return __it.footer_privacy(inputs);
      if (locale === "de") return __de.footer_privacy(inputs);
      return __ru.footer_privacy(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Terms of Service" |
 *
 * @param {Footer_TermsInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_terms =
  /** @type {((inputs?: Footer_TermsInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_TermsInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_terms(inputs);
      if (locale === "en") return __en.footer_terms(inputs);
      if (locale === "es") return __es.footer_terms(inputs);
      if (locale === "fr") return __fr.footer_terms(inputs);
      if (locale === "it") return __it.footer_terms(inputs);
      if (locale === "de") return __de.footer_terms(inputs);
      return __ru.footer_terms(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Cookies" |
 *
 * @param {Footer_CookiesInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_cookies =
  /** @type {((inputs?: Footer_CookiesInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_CookiesInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_cookies(inputs);
      if (locale === "en") return __en.footer_cookies(inputs);
      if (locale === "es") return __es.footer_cookies(inputs);
      if (locale === "fr") return __fr.footer_cookies(inputs);
      if (locale === "it") return __it.footer_cookies(inputs);
      if (locale === "de") return __de.footer_cookies(inputs);
      return __ru.footer_cookies(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "SLA" |
 *
 * @param {Footer_SlaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_sla =
  /** @type {((inputs?: Footer_SlaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_SlaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_sla(inputs);
      if (locale === "en") return __en.footer_sla(inputs);
      if (locale === "es") return __es.footer_sla(inputs);
      if (locale === "fr") return __fr.footer_sla(inputs);
      if (locale === "it") return __it.footer_sla(inputs);
      if (locale === "de") return __de.footer_sla(inputs);
      return __ru.footer_sla(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "DPA" |
 *
 * @param {Footer_DpaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_dpa =
  /** @type {((inputs?: Footer_DpaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_DpaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_dpa(inputs);
      if (locale === "en") return __en.footer_dpa(inputs);
      if (locale === "es") return __es.footer_dpa(inputs);
      if (locale === "fr") return __fr.footer_dpa(inputs);
      if (locale === "it") return __it.footer_dpa(inputs);
      if (locale === "de") return __de.footer_dpa(inputs);
      return __ru.footer_dpa(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Support" |
 *
 * @param {Footer_SupportInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_support =
  /** @type {((inputs?: Footer_SupportInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_SupportInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_support(inputs);
      if (locale === "en") return __en.footer_support(inputs);
      if (locale === "es") return __es.footer_support(inputs);
      if (locale === "fr") return __fr.footer_support(inputs);
      if (locale === "it") return __it.footer_support(inputs);
      if (locale === "de") return __de.footer_support(inputs);
      return __ru.footer_support(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Documentation" |
 *
 * @param {Footer_DocsInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_docs =
  /** @type {((inputs?: Footer_DocsInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_DocsInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_docs(inputs);
      if (locale === "en") return __en.footer_docs(inputs);
      if (locale === "es") return __es.footer_docs(inputs);
      if (locale === "fr") return __fr.footer_docs(inputs);
      if (locale === "it") return __it.footer_docs(inputs);
      if (locale === "de") return __de.footer_docs(inputs);
      return __ru.footer_docs(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "FAQ" |
 *
 * @param {Footer_FaqInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_faq =
  /** @type {((inputs?: Footer_FaqInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_FaqInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_faq(inputs);
      if (locale === "en") return __en.footer_faq(inputs);
      if (locale === "es") return __es.footer_faq(inputs);
      if (locale === "fr") return __fr.footer_faq(inputs);
      if (locale === "it") return __it.footer_faq(inputs);
      if (locale === "de") return __de.footer_faq(inputs);
      return __ru.footer_faq(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Status" |
 *
 * @param {Footer_StatusInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_status =
  /** @type {((inputs?: Footer_StatusInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_StatusInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_status(inputs);
      if (locale === "en") return __en.footer_status(inputs);
      if (locale === "es") return __es.footer_status(inputs);
      if (locale === "fr") return __fr.footer_status(inputs);
      if (locale === "it") return __it.footer_status(inputs);
      if (locale === "de") return __de.footer_status(inputs);
      return __ru.footer_status(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Create account" |
 *
 * @param {Signup_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const signup_title =
  /** @type {((inputs?: Signup_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Signup_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.signup_title(inputs);
      if (locale === "en") return __en.signup_title(inputs);
      if (locale === "es") return __es.signup_title(inputs);
      if (locale === "fr") return __fr.signup_title(inputs);
      if (locale === "it") return __it.signup_title(inputs);
      if (locale === "de") return __de.signup_title(inputs);
      return __ru.signup_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "30-day free trial, no credit card required." |
 *
 * @param {Signup_SubtitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const signup_subtitle =
  /** @type {((inputs?: Signup_SubtitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Signup_SubtitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.signup_subtitle(inputs);
      if (locale === "en") return __en.signup_subtitle(inputs);
      if (locale === "es") return __es.signup_subtitle(inputs);
      if (locale === "fr") return __fr.signup_subtitle(inputs);
      if (locale === "it") return __it.signup_subtitle(inputs);
      if (locale === "de") return __de.signup_subtitle(inputs);
      return __ru.signup_subtitle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "I already have an account" |
 *
 * @param {Signup_Already_Have_AccountInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const signup_already_have_account =
  /** @type {((inputs?: Signup_Already_Have_AccountInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Signup_Already_Have_AccountInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.signup_already_have_account(inputs);
      if (locale === "en") return __en.signup_already_have_account(inputs);
      if (locale === "es") return __es.signup_already_have_account(inputs);
      if (locale === "fr") return __fr.signup_already_have_account(inputs);
      if (locale === "it") return __it.signup_already_have_account(inputs);
      if (locale === "de") return __de.signup_already_have_account(inputs);
      return __ru.signup_already_have_account(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "View pricing" |
 *
 * @param {Signup_View_PricingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const signup_view_pricing =
  /** @type {((inputs?: Signup_View_PricingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Signup_View_PricingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.signup_view_pricing(inputs);
      if (locale === "en") return __en.signup_view_pricing(inputs);
      if (locale === "es") return __es.signup_view_pricing(inputs);
      if (locale === "fr") return __fr.signup_view_pricing(inputs);
      if (locale === "it") return __it.signup_view_pricing(inputs);
      if (locale === "de") return __de.signup_view_pricing(inputs);
      return __ru.signup_view_pricing(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Log in" |
 *
 * @param {Login_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const login_title =
  /** @type {((inputs?: Login_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Login_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.login_title(inputs);
      if (locale === "en") return __en.login_title(inputs);
      if (locale === "es") return __es.login_title(inputs);
      if (locale === "fr") return __fr.login_title(inputs);
      if (locale === "it") return __it.login_title(inputs);
      if (locale === "de") return __de.login_title(inputs);
      return __ru.login_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Create account" |
 *
 * @param {Login_No_AccountInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const login_no_account =
  /** @type {((inputs?: Login_No_AccountInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Login_No_AccountInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.login_no_account(inputs);
      if (locale === "en") return __en.login_no_account(inputs);
      if (locale === "es") return __es.login_no_account(inputs);
      if (locale === "fr") return __fr.login_no_account(inputs);
      if (locale === "it") return __it.login_no_account(inputs);
      if (locale === "de") return __de.login_no_account(inputs);
      return __ru.login_no_account(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Forgot password" |
 *
 * @param {Login_Forgot_PasswordInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const login_forgot_password =
  /** @type {((inputs?: Login_Forgot_PasswordInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Login_Forgot_PasswordInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.login_forgot_password(inputs);
      if (locale === "en") return __en.login_forgot_password(inputs);
      if (locale === "es") return __es.login_forgot_password(inputs);
      if (locale === "fr") return __fr.login_forgot_password(inputs);
      if (locale === "it") return __it.login_forgot_password(inputs);
      if (locale === "de") return __de.login_forgot_password(inputs);
      return __ru.login_forgot_password(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Link sent! Check your email." |
 *
 * @param {Login_Magic_Link_SentInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const login_magic_link_sent =
  /** @type {((inputs?: Login_Magic_Link_SentInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Login_Magic_Link_SentInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.login_magic_link_sent(inputs);
      if (locale === "en") return __en.login_magic_link_sent(inputs);
      if (locale === "es") return __es.login_magic_link_sent(inputs);
      if (locale === "fr") return __fr.login_magic_link_sent(inputs);
      if (locale === "it") return __it.login_magic_link_sent(inputs);
      if (locale === "de") return __de.login_magic_link_sent(inputs);
      return __ru.login_magic_link_sent(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Full name" |
 *
 * @param {Form_Full_NameInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_full_name =
  /** @type {((inputs?: Form_Full_NameInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_Full_NameInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_full_name(inputs);
      if (locale === "en") return __en.form_full_name(inputs);
      if (locale === "es") return __es.form_full_name(inputs);
      if (locale === "fr") return __fr.form_full_name(inputs);
      if (locale === "it") return __it.form_full_name(inputs);
      if (locale === "de") return __de.form_full_name(inputs);
      return __ru.form_full_name(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Email" |
 *
 * @param {Form_EmailInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_email =
  /** @type {((inputs?: Form_EmailInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_EmailInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_email(inputs);
      if (locale === "en") return __en.form_email(inputs);
      if (locale === "es") return __es.form_email(inputs);
      if (locale === "fr") return __fr.form_email(inputs);
      if (locale === "it") return __it.form_email(inputs);
      if (locale === "de") return __de.form_email(inputs);
      return __ru.form_email(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Password" |
 *
 * @param {Form_PasswordInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_password =
  /** @type {((inputs?: Form_PasswordInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_PasswordInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_password(inputs);
      if (locale === "en") return __en.form_password(inputs);
      if (locale === "es") return __es.form_password(inputs);
      if (locale === "fr") return __fr.form_password(inputs);
      if (locale === "it") return __it.form_password(inputs);
      if (locale === "de") return __de.form_password(inputs);
      return __ru.form_password(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Country" |
 *
 * @param {Form_CountryInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_country =
  /** @type {((inputs?: Form_CountryInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_CountryInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_country(inputs);
      if (locale === "en") return __en.form_country(inputs);
      if (locale === "es") return __es.form_country(inputs);
      if (locale === "fr") return __fr.form_country(inputs);
      if (locale === "it") return __it.form_country(inputs);
      if (locale === "de") return __de.form_country(inputs);
      return __ru.form_country(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Brazil" |
 *
 * @param {Form_Country_BrInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_country_br =
  /** @type {((inputs?: Form_Country_BrInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_Country_BrInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_country_br(inputs);
      if (locale === "en") return __en.form_country_br(inputs);
      if (locale === "es") return __es.form_country_br(inputs);
      if (locale === "fr") return __fr.form_country_br(inputs);
      if (locale === "it") return __it.form_country_br(inputs);
      if (locale === "de") return __de.form_country_br(inputs);
      return __ru.form_country_br(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Other country" |
 *
 * @param {Form_Country_IntlInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_country_intl =
  /** @type {((inputs?: Form_Country_IntlInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_Country_IntlInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_country_intl(inputs);
      if (locale === "en") return __en.form_country_intl(inputs);
      if (locale === "es") return __es.form_country_intl(inputs);
      if (locale === "fr") return __fr.form_country_intl(inputs);
      if (locale === "it") return __it.form_country_intl(inputs);
      if (locale === "de") return __de.form_country_intl(inputs);
      return __ru.form_country_intl(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Create account" |
 *
 * @param {Form_Submit_SignupInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_submit_signup =
  /** @type {((inputs?: Form_Submit_SignupInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_Submit_SignupInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_submit_signup(inputs);
      if (locale === "en") return __en.form_submit_signup(inputs);
      if (locale === "es") return __es.form_submit_signup(inputs);
      if (locale === "fr") return __fr.form_submit_signup(inputs);
      if (locale === "it") return __it.form_submit_signup(inputs);
      if (locale === "de") return __de.form_submit_signup(inputs);
      return __ru.form_submit_signup(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Log in" |
 *
 * @param {Form_Submit_LoginInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_submit_login =
  /** @type {((inputs?: Form_Submit_LoginInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_Submit_LoginInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_submit_login(inputs);
      if (locale === "en") return __en.form_submit_login(inputs);
      if (locale === "es") return __es.form_submit_login(inputs);
      if (locale === "fr") return __fr.form_submit_login(inputs);
      if (locale === "it") return __it.form_submit_login(inputs);
      if (locale === "de") return __de.form_submit_login(inputs);
      return __ru.form_submit_login(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Please wait..." |
 *
 * @param {Form_LoadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_loading =
  /** @type {((inputs?: Form_LoadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_LoadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_loading(inputs);
      if (locale === "en") return __en.form_loading(inputs);
      if (locale === "es") return __es.form_loading(inputs);
      if (locale === "fr") return __fr.form_loading(inputs);
      if (locale === "it") return __it.form_loading(inputs);
      if (locale === "de") return __de.form_loading(inputs);
      return __ru.form_loading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Your VECTORA_TOKEN" |
 *
 * @param {Dashboard_Token_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_token_title =
  /** @type {((inputs?: Dashboard_Token_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Token_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_token_title(inputs);
      if (locale === "en") return __en.dashboard_token_title(inputs);
      if (locale === "es") return __es.dashboard_token_title(inputs);
      if (locale === "fr") return __fr.dashboard_token_title(inputs);
      if (locale === "it") return __it.dashboard_token_title(inputs);
      if (locale === "de") return __de.dashboard_token_title(inputs);
      return __ru.dashboard_token_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Click to reveal" |
 *
 * @param {Dashboard_Token_Reveal_BtnInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_token_reveal_btn =
  /** @type {((inputs?: Dashboard_Token_Reveal_BtnInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Token_Reveal_BtnInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_token_reveal_btn(inputs);
      if (locale === "en") return __en.dashboard_token_reveal_btn(inputs);
      if (locale === "es") return __es.dashboard_token_reveal_btn(inputs);
      if (locale === "fr") return __fr.dashboard_token_reveal_btn(inputs);
      if (locale === "it") return __it.dashboard_token_reveal_btn(inputs);
      if (locale === "de") return __de.dashboard_token_reveal_btn(inputs);
      return __ru.dashboard_token_reveal_btn(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Copy" |
 *
 * @param {Dashboard_Token_Copy_BtnInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_token_copy_btn =
  /** @type {((inputs?: Dashboard_Token_Copy_BtnInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Token_Copy_BtnInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_token_copy_btn(inputs);
      if (locale === "en") return __en.dashboard_token_copy_btn(inputs);
      if (locale === "es") return __es.dashboard_token_copy_btn(inputs);
      if (locale === "fr") return __fr.dashboard_token_copy_btn(inputs);
      if (locale === "it") return __it.dashboard_token_copy_btn(inputs);
      if (locale === "de") return __de.dashboard_token_copy_btn(inputs);
      return __ru.dashboard_token_copy_btn(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Copied!" |
 *
 * @param {Dashboard_Token_CopiedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_token_copied =
  /** @type {((inputs?: Dashboard_Token_CopiedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Token_CopiedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_token_copied(inputs);
      if (locale === "en") return __en.dashboard_token_copied(inputs);
      if (locale === "es") return __es.dashboard_token_copied(inputs);
      if (locale === "fr") return __fr.dashboard_token_copied(inputs);
      if (locale === "it") return __it.dashboard_token_copied(inputs);
      if (locale === "de") return __de.dashboard_token_copied(inputs);
      return __ru.dashboard_token_copied(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Copy and save. It will not be shown again." |
 *
 * @param {Dashboard_Token_WarningInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_token_warning =
  /** @type {((inputs?: Dashboard_Token_WarningInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Token_WarningInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_token_warning(inputs);
      if (locale === "en") return __en.dashboard_token_warning(inputs);
      if (locale === "es") return __es.dashboard_token_warning(inputs);
      if (locale === "fr") return __fr.dashboard_token_warning(inputs);
      if (locale === "it") return __it.dashboard_token_warning(inputs);
      if (locale === "de") return __de.dashboard_token_warning(inputs);
      return __ru.dashboard_token_warning(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Token already revealed. Rotate if you need a new one." |
 *
 * @param {Dashboard_Token_Revealed_BannerInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_token_revealed_banner =
  /** @type {((inputs?: Dashboard_Token_Revealed_BannerInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Token_Revealed_BannerInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_token_revealed_banner(inputs);
      if (locale === "en") return __en.dashboard_token_revealed_banner(inputs);
      if (locale === "es") return __es.dashboard_token_revealed_banner(inputs);
      if (locale === "fr") return __fr.dashboard_token_revealed_banner(inputs);
      if (locale === "it") return __it.dashboard_token_revealed_banner(inputs);
      if (locale === "de") return __de.dashboard_token_revealed_banner(inputs);
      return __ru.dashboard_token_revealed_banner(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Rotate token" |
 *
 * @param {Dashboard_Token_Rotate_BtnInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_token_rotate_btn =
  /** @type {((inputs?: Dashboard_Token_Rotate_BtnInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Token_Rotate_BtnInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_token_rotate_btn(inputs);
      if (locale === "en") return __en.dashboard_token_rotate_btn(inputs);
      if (locale === "es") return __es.dashboard_token_rotate_btn(inputs);
      if (locale === "fr") return __fr.dashboard_token_rotate_btn(inputs);
      if (locale === "it") return __it.dashboard_token_rotate_btn(inputs);
      if (locale === "de") return __de.dashboard_token_rotate_btn(inputs);
      return __ru.dashboard_token_rotate_btn(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Generate new token? The current token will be invalidated." |
 *
 * @param {Dashboard_Token_Rotate_ConfirmInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_token_rotate_confirm =
  /** @type {((inputs?: Dashboard_Token_Rotate_ConfirmInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Token_Rotate_ConfirmInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_token_rotate_confirm(inputs);
      if (locale === "en") return __en.dashboard_token_rotate_confirm(inputs);
      if (locale === "es") return __es.dashboard_token_rotate_confirm(inputs);
      if (locale === "fr") return __fr.dashboard_token_rotate_confirm(inputs);
      if (locale === "it") return __it.dashboard_token_rotate_confirm(inputs);
      if (locale === "de") return __de.dashboard_token_rotate_confirm(inputs);
      return __ru.dashboard_token_rotate_confirm(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Quick start" |
 *
 * @param {Dashboard_Quickstart_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_quickstart_title =
  /** @type {((inputs?: Dashboard_Quickstart_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Quickstart_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_quickstart_title(inputs);
      if (locale === "en") return __en.dashboard_quickstart_title(inputs);
      if (locale === "es") return __es.dashboard_quickstart_title(inputs);
      if (locale === "fr") return __fr.dashboard_quickstart_title(inputs);
      if (locale === "it") return __it.dashboard_quickstart_title(inputs);
      if (locale === "de") return __de.dashboard_quickstart_title(inputs);
      return __ru.dashboard_quickstart_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "License" |
 *
 * @param {Dashboard_License_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_title =
  /** @type {((inputs?: Dashboard_License_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_title(inputs);
      if (locale === "en") return __en.dashboard_license_title(inputs);
      if (locale === "es") return __es.dashboard_license_title(inputs);
      if (locale === "fr") return __fr.dashboard_license_title(inputs);
      if (locale === "it") return __it.dashboard_license_title(inputs);
      if (locale === "de") return __de.dashboard_license_title(inputs);
      return __ru.dashboard_license_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Plan" |
 *
 * @param {Dashboard_License_PlanInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_plan =
  /** @type {((inputs?: Dashboard_License_PlanInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_PlanInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_plan(inputs);
      if (locale === "en") return __en.dashboard_license_plan(inputs);
      if (locale === "es") return __es.dashboard_license_plan(inputs);
      if (locale === "fr") return __fr.dashboard_license_plan(inputs);
      if (locale === "it") return __it.dashboard_license_plan(inputs);
      if (locale === "de") return __de.dashboard_license_plan(inputs);
      return __ru.dashboard_license_plan(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Status" |
 *
 * @param {Dashboard_License_StatusInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_status =
  /** @type {((inputs?: Dashboard_License_StatusInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_StatusInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_status(inputs);
      if (locale === "en") return __en.dashboard_license_status(inputs);
      if (locale === "es") return __es.dashboard_license_status(inputs);
      if (locale === "fr") return __fr.dashboard_license_status(inputs);
      if (locale === "it") return __it.dashboard_license_status(inputs);
      if (locale === "de") return __de.dashboard_license_status(inputs);
      return __ru.dashboard_license_status(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Trial active" |
 *
 * @param {Dashboard_License_Trial_ActiveInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_trial_active =
  /** @type {((inputs?: Dashboard_License_Trial_ActiveInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_Trial_ActiveInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_trial_active(inputs);
      if (locale === "en") return __en.dashboard_license_trial_active(inputs);
      if (locale === "es") return __es.dashboard_license_trial_active(inputs);
      if (locale === "fr") return __fr.dashboard_license_trial_active(inputs);
      if (locale === "it") return __it.dashboard_license_trial_active(inputs);
      if (locale === "de") return __de.dashboard_license_trial_active(inputs);
      return __ru.dashboard_license_trial_active(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Active" |
 *
 * @param {Dashboard_License_ActiveInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_active =
  /** @type {((inputs?: Dashboard_License_ActiveInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_ActiveInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_active(inputs);
      if (locale === "en") return __en.dashboard_license_active(inputs);
      if (locale === "es") return __es.dashboard_license_active(inputs);
      if (locale === "fr") return __fr.dashboard_license_active(inputs);
      if (locale === "it") return __it.dashboard_license_active(inputs);
      if (locale === "de") return __de.dashboard_license_active(inputs);
      return __ru.dashboard_license_active(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Payment pending" |
 *
 * @param {Dashboard_License_Past_DueInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_past_due =
  /** @type {((inputs?: Dashboard_License_Past_DueInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_Past_DueInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_past_due(inputs);
      if (locale === "en") return __en.dashboard_license_past_due(inputs);
      if (locale === "es") return __es.dashboard_license_past_due(inputs);
      if (locale === "fr") return __fr.dashboard_license_past_due(inputs);
      if (locale === "it") return __it.dashboard_license_past_due(inputs);
      if (locale === "de") return __de.dashboard_license_past_due(inputs);
      return __ru.dashboard_license_past_due(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Canceled" |
 *
 * @param {Dashboard_License_CanceledInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_canceled =
  /** @type {((inputs?: Dashboard_License_CanceledInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_CanceledInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_canceled(inputs);
      if (locale === "en") return __en.dashboard_license_canceled(inputs);
      if (locale === "es") return __es.dashboard_license_canceled(inputs);
      if (locale === "fr") return __fr.dashboard_license_canceled(inputs);
      if (locale === "it") return __it.dashboard_license_canceled(inputs);
      if (locale === "de") return __de.dashboard_license_canceled(inputs);
      return __ru.dashboard_license_canceled(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Expired" |
 *
 * @param {Dashboard_License_ExpiredInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_expired =
  /** @type {((inputs?: Dashboard_License_ExpiredInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_ExpiredInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_expired(inputs);
      if (locale === "en") return __en.dashboard_license_expired(inputs);
      if (locale === "es") return __es.dashboard_license_expired(inputs);
      if (locale === "fr") return __fr.dashboard_license_expired(inputs);
      if (locale === "it") return __it.dashboard_license_expired(inputs);
      if (locale === "de") return __de.dashboard_license_expired(inputs);
      return __ru.dashboard_license_expired(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Trial ends in" |
 *
 * @param {Dashboard_License_Trial_EndsInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_trial_ends =
  /** @type {((inputs?: Dashboard_License_Trial_EndsInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_Trial_EndsInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_trial_ends(inputs);
      if (locale === "en") return __en.dashboard_license_trial_ends(inputs);
      if (locale === "es") return __es.dashboard_license_trial_ends(inputs);
      if (locale === "fr") return __fr.dashboard_license_trial_ends(inputs);
      if (locale === "it") return __it.dashboard_license_trial_ends(inputs);
      if (locale === "de") return __de.dashboard_license_trial_ends(inputs);
      return __ru.dashboard_license_trial_ends(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "{days} days" |
 *
 * @param {Dashboard_License_Days_LeftInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_days_left =
  /** @type {((inputs: Dashboard_License_Days_LeftInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_Days_LeftInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_days_left(inputs);
      if (locale === "en") return __en.dashboard_license_days_left(inputs);
      if (locale === "es") return __es.dashboard_license_days_left(inputs);
      if (locale === "fr") return __fr.dashboard_license_days_left(inputs);
      if (locale === "it") return __it.dashboard_license_days_left(inputs);
      if (locale === "de") return __de.dashboard_license_days_left(inputs);
      return __ru.dashboard_license_days_left(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Validation history" |
 *
 * @param {Dashboard_License_History_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_license_history_title =
  /** @type {((inputs?: Dashboard_License_History_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_License_History_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_license_history_title(inputs);
      if (locale === "en") return __en.dashboard_license_history_title(inputs);
      if (locale === "es") return __es.dashboard_license_history_title(inputs);
      if (locale === "fr") return __fr.dashboard_license_history_title(inputs);
      if (locale === "it") return __it.dashboard_license_history_title(inputs);
      if (locale === "de") return __de.dashboard_license_history_title(inputs);
      return __ru.dashboard_license_history_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Billing" |
 *
 * @param {Dashboard_Billing_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_billing_title =
  /** @type {((inputs?: Dashboard_Billing_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Billing_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_billing_title(inputs);
      if (locale === "en") return __en.dashboard_billing_title(inputs);
      if (locale === "es") return __es.dashboard_billing_title(inputs);
      if (locale === "fr") return __fr.dashboard_billing_title(inputs);
      if (locale === "it") return __it.dashboard_billing_title(inputs);
      if (locale === "de") return __de.dashboard_billing_title(inputs);
      return __ru.dashboard_billing_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Subscribe Plus" |
 *
 * @param {Dashboard_Billing_Subscribe_PlusInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_billing_subscribe_plus =
  /** @type {((inputs?: Dashboard_Billing_Subscribe_PlusInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Billing_Subscribe_PlusInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_billing_subscribe_plus(inputs);
      if (locale === "en") return __en.dashboard_billing_subscribe_plus(inputs);
      if (locale === "es") return __es.dashboard_billing_subscribe_plus(inputs);
      if (locale === "fr") return __fr.dashboard_billing_subscribe_plus(inputs);
      if (locale === "it") return __it.dashboard_billing_subscribe_plus(inputs);
      if (locale === "de") return __de.dashboard_billing_subscribe_plus(inputs);
      return __ru.dashboard_billing_subscribe_plus(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Subscribe Pro" |
 *
 * @param {Dashboard_Billing_Subscribe_ProInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_billing_subscribe_pro =
  /** @type {((inputs?: Dashboard_Billing_Subscribe_ProInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Billing_Subscribe_ProInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_billing_subscribe_pro(inputs);
      if (locale === "en") return __en.dashboard_billing_subscribe_pro(inputs);
      if (locale === "es") return __es.dashboard_billing_subscribe_pro(inputs);
      if (locale === "fr") return __fr.dashboard_billing_subscribe_pro(inputs);
      if (locale === "it") return __it.dashboard_billing_subscribe_pro(inputs);
      if (locale === "de") return __de.dashboard_billing_subscribe_pro(inputs);
      return __ru.dashboard_billing_subscribe_pro(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Upgrade to Pro" |
 *
 * @param {Dashboard_Billing_Upgrade_ProInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_billing_upgrade_pro =
  /** @type {((inputs?: Dashboard_Billing_Upgrade_ProInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Billing_Upgrade_ProInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_billing_upgrade_pro(inputs);
      if (locale === "en") return __en.dashboard_billing_upgrade_pro(inputs);
      if (locale === "es") return __es.dashboard_billing_upgrade_pro(inputs);
      if (locale === "fr") return __fr.dashboard_billing_upgrade_pro(inputs);
      if (locale === "it") return __it.dashboard_billing_upgrade_pro(inputs);
      if (locale === "de") return __de.dashboard_billing_upgrade_pro(inputs);
      return __ru.dashboard_billing_upgrade_pro(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Manage subscription" |
 *
 * @param {Dashboard_Billing_ManageInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_billing_manage =
  /** @type {((inputs?: Dashboard_Billing_ManageInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Billing_ManageInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_billing_manage(inputs);
      if (locale === "en") return __en.dashboard_billing_manage(inputs);
      if (locale === "es") return __es.dashboard_billing_manage(inputs);
      if (locale === "fr") return __fr.dashboard_billing_manage(inputs);
      if (locale === "it") return __it.dashboard_billing_manage(inputs);
      if (locale === "de") return __de.dashboard_billing_manage(inputs);
      return __ru.dashboard_billing_manage(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Update payment" |
 *
 * @param {Dashboard_Billing_Update_PaymentInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_billing_update_payment =
  /** @type {((inputs?: Dashboard_Billing_Update_PaymentInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Billing_Update_PaymentInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_billing_update_payment(inputs);
      if (locale === "en") return __en.dashboard_billing_update_payment(inputs);
      if (locale === "es") return __es.dashboard_billing_update_payment(inputs);
      if (locale === "fr") return __fr.dashboard_billing_update_payment(inputs);
      if (locale === "it") return __it.dashboard_billing_update_payment(inputs);
      if (locale === "de") return __de.dashboard_billing_update_payment(inputs);
      return __ru.dashboard_billing_update_payment(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Reactivate" |
 *
 * @param {Dashboard_Billing_ReactivateInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_billing_reactivate =
  /** @type {((inputs?: Dashboard_Billing_ReactivateInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Billing_ReactivateInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_billing_reactivate(inputs);
      if (locale === "en") return __en.dashboard_billing_reactivate(inputs);
      if (locale === "es") return __es.dashboard_billing_reactivate(inputs);
      if (locale === "fr") return __fr.dashboard_billing_reactivate(inputs);
      if (locale === "it") return __it.dashboard_billing_reactivate(inputs);
      if (locale === "de") return __de.dashboard_billing_reactivate(inputs);
      return __ru.dashboard_billing_reactivate(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "API Keys" |
 *
 * @param {Dashboard_Apikeys_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_title =
  /** @type {((inputs?: Dashboard_Apikeys_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_title(inputs);
      if (locale === "en") return __en.dashboard_apikeys_title(inputs);
      if (locale === "es") return __es.dashboard_apikeys_title(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_title(inputs);
      if (locale === "it") return __it.dashboard_apikeys_title(inputs);
      if (locale === "de") return __de.dashboard_apikeys_title(inputs);
      return __ru.dashboard_apikeys_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Create API key" |
 *
 * @param {Dashboard_Apikeys_Create_BtnInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_create_btn =
  /** @type {((inputs?: Dashboard_Apikeys_Create_BtnInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_Create_BtnInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_create_btn(inputs);
      if (locale === "en") return __en.dashboard_apikeys_create_btn(inputs);
      if (locale === "es") return __es.dashboard_apikeys_create_btn(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_create_btn(inputs);
      if (locale === "it") return __it.dashboard_apikeys_create_btn(inputs);
      if (locale === "de") return __de.dashboard_apikeys_create_btn(inputs);
      return __ru.dashboard_apikeys_create_btn(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Name" |
 *
 * @param {Dashboard_Apikeys_NameInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_name =
  /** @type {((inputs?: Dashboard_Apikeys_NameInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_NameInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_name(inputs);
      if (locale === "en") return __en.dashboard_apikeys_name(inputs);
      if (locale === "es") return __es.dashboard_apikeys_name(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_name(inputs);
      if (locale === "it") return __it.dashboard_apikeys_name(inputs);
      if (locale === "de") return __de.dashboard_apikeys_name(inputs);
      return __ru.dashboard_apikeys_name(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Created" |
 *
 * @param {Dashboard_Apikeys_CreatedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_created =
  /** @type {((inputs?: Dashboard_Apikeys_CreatedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_CreatedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_created(inputs);
      if (locale === "en") return __en.dashboard_apikeys_created(inputs);
      if (locale === "es") return __es.dashboard_apikeys_created(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_created(inputs);
      if (locale === "it") return __it.dashboard_apikeys_created(inputs);
      if (locale === "de") return __de.dashboard_apikeys_created(inputs);
      return __ru.dashboard_apikeys_created(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Scopes" |
 *
 * @param {Dashboard_Apikeys_ScopesInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_scopes =
  /** @type {((inputs?: Dashboard_Apikeys_ScopesInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_ScopesInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_scopes(inputs);
      if (locale === "en") return __en.dashboard_apikeys_scopes(inputs);
      if (locale === "es") return __es.dashboard_apikeys_scopes(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_scopes(inputs);
      if (locale === "it") return __it.dashboard_apikeys_scopes(inputs);
      if (locale === "de") return __de.dashboard_apikeys_scopes(inputs);
      return __ru.dashboard_apikeys_scopes(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Last used" |
 *
 * @param {Dashboard_Apikeys_Last_UsedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_last_used =
  /** @type {((inputs?: Dashboard_Apikeys_Last_UsedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_Last_UsedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_last_used(inputs);
      if (locale === "en") return __en.dashboard_apikeys_last_used(inputs);
      if (locale === "es") return __es.dashboard_apikeys_last_used(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_last_used(inputs);
      if (locale === "it") return __it.dashboard_apikeys_last_used(inputs);
      if (locale === "de") return __de.dashboard_apikeys_last_used(inputs);
      return __ru.dashboard_apikeys_last_used(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Revoke" |
 *
 * @param {Dashboard_Apikeys_RevokeInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_revoke =
  /** @type {((inputs?: Dashboard_Apikeys_RevokeInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_RevokeInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_revoke(inputs);
      if (locale === "en") return __en.dashboard_apikeys_revoke(inputs);
      if (locale === "es") return __es.dashboard_apikeys_revoke(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_revoke(inputs);
      if (locale === "it") return __it.dashboard_apikeys_revoke(inputs);
      if (locale === "de") return __de.dashboard_apikeys_revoke(inputs);
      return __ru.dashboard_apikeys_revoke(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Copy the key now. It will not be shown again." |
 *
 * @param {Dashboard_Apikeys_Secret_WarningInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_secret_warning =
  /** @type {((inputs?: Dashboard_Apikeys_Secret_WarningInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_Secret_WarningInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_secret_warning(inputs);
      if (locale === "en") return __en.dashboard_apikeys_secret_warning(inputs);
      if (locale === "es") return __es.dashboard_apikeys_secret_warning(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_secret_warning(inputs);
      if (locale === "it") return __it.dashboard_apikeys_secret_warning(inputs);
      if (locale === "de") return __de.dashboard_apikeys_secret_warning(inputs);
      return __ru.dashboard_apikeys_secret_warning(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Revoke this API key? This action cannot be undone." |
 *
 * @param {Dashboard_Apikeys_Revoke_ConfirmInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_apikeys_revoke_confirm =
  /** @type {((inputs?: Dashboard_Apikeys_Revoke_ConfirmInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Apikeys_Revoke_ConfirmInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_apikeys_revoke_confirm(inputs);
      if (locale === "en") return __en.dashboard_apikeys_revoke_confirm(inputs);
      if (locale === "es") return __es.dashboard_apikeys_revoke_confirm(inputs);
      if (locale === "fr") return __fr.dashboard_apikeys_revoke_confirm(inputs);
      if (locale === "it") return __it.dashboard_apikeys_revoke_confirm(inputs);
      if (locale === "de") return __de.dashboard_apikeys_revoke_confirm(inputs);
      return __ru.dashboard_apikeys_revoke_confirm(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Account" |
 *
 * @param {Dashboard_Account_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_account_title =
  /** @type {((inputs?: Dashboard_Account_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Account_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_account_title(inputs);
      if (locale === "en") return __en.dashboard_account_title(inputs);
      if (locale === "es") return __es.dashboard_account_title(inputs);
      if (locale === "fr") return __fr.dashboard_account_title(inputs);
      if (locale === "it") return __it.dashboard_account_title(inputs);
      if (locale === "de") return __de.dashboard_account_title(inputs);
      return __ru.dashboard_account_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Save" |
 *
 * @param {Dashboard_Account_SaveInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_account_save =
  /** @type {((inputs?: Dashboard_Account_SaveInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Account_SaveInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_account_save(inputs);
      if (locale === "en") return __en.dashboard_account_save(inputs);
      if (locale === "es") return __es.dashboard_account_save(inputs);
      if (locale === "fr") return __fr.dashboard_account_save(inputs);
      if (locale === "it") return __it.dashboard_account_save(inputs);
      if (locale === "de") return __de.dashboard_account_save(inputs);
      return __ru.dashboard_account_save(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Security" |
 *
 * @param {Dashboard_Account_Security_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_account_security_title =
  /** @type {((inputs?: Dashboard_Account_Security_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Account_Security_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_account_security_title(inputs);
      if (locale === "en") return __en.dashboard_account_security_title(inputs);
      if (locale === "es") return __es.dashboard_account_security_title(inputs);
      if (locale === "fr") return __fr.dashboard_account_security_title(inputs);
      if (locale === "it") return __it.dashboard_account_security_title(inputs);
      if (locale === "de") return __de.dashboard_account_security_title(inputs);
      return __ru.dashboard_account_security_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Change password" |
 *
 * @param {Dashboard_Account_Change_PasswordInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_account_change_password =
  /** @type {((inputs?: Dashboard_Account_Change_PasswordInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Account_Change_PasswordInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt")
        return __pt.dashboard_account_change_password(inputs);
      if (locale === "en")
        return __en.dashboard_account_change_password(inputs);
      if (locale === "es")
        return __es.dashboard_account_change_password(inputs);
      if (locale === "fr")
        return __fr.dashboard_account_change_password(inputs);
      if (locale === "it")
        return __it.dashboard_account_change_password(inputs);
      if (locale === "de")
        return __de.dashboard_account_change_password(inputs);
      return __ru.dashboard_account_change_password(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Data & Privacy" |
 *
 * @param {Dashboard_Account_Gdpr_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_account_gdpr_title =
  /** @type {((inputs?: Dashboard_Account_Gdpr_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Account_Gdpr_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_account_gdpr_title(inputs);
      if (locale === "en") return __en.dashboard_account_gdpr_title(inputs);
      if (locale === "es") return __es.dashboard_account_gdpr_title(inputs);
      if (locale === "fr") return __fr.dashboard_account_gdpr_title(inputs);
      if (locale === "it") return __it.dashboard_account_gdpr_title(inputs);
      if (locale === "de") return __de.dashboard_account_gdpr_title(inputs);
      return __ru.dashboard_account_gdpr_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Export my data" |
 *
 * @param {Dashboard_Account_ExportInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_account_export =
  /** @type {((inputs?: Dashboard_Account_ExportInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Account_ExportInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_account_export(inputs);
      if (locale === "en") return __en.dashboard_account_export(inputs);
      if (locale === "es") return __es.dashboard_account_export(inputs);
      if (locale === "fr") return __fr.dashboard_account_export(inputs);
      if (locale === "it") return __it.dashboard_account_export(inputs);
      if (locale === "de") return __de.dashboard_account_export(inputs);
      return __ru.dashboard_account_export(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Delete account" |
 *
 * @param {Dashboard_Account_DeleteInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_account_delete =
  /** @type {((inputs?: Dashboard_Account_DeleteInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Account_DeleteInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_account_delete(inputs);
      if (locale === "en") return __en.dashboard_account_delete(inputs);
      if (locale === "es") return __es.dashboard_account_delete(inputs);
      if (locale === "fr") return __fr.dashboard_account_delete(inputs);
      if (locale === "it") return __it.dashboard_account_delete(inputs);
      if (locale === "de") return __de.dashboard_account_delete(inputs);
      return __ru.dashboard_account_delete(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Type your email to confirm deletion" |
 *
 * @param {Dashboard_Account_Delete_ConfirmInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const dashboard_account_delete_confirm =
  /** @type {((inputs?: Dashboard_Account_Delete_ConfirmInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Dashboard_Account_Delete_ConfirmInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.dashboard_account_delete_confirm(inputs);
      if (locale === "en") return __en.dashboard_account_delete_confirm(inputs);
      if (locale === "es") return __es.dashboard_account_delete_confirm(inputs);
      if (locale === "fr") return __fr.dashboard_account_delete_confirm(inputs);
      if (locale === "it") return __it.dashboard_account_delete_confirm(inputs);
      if (locale === "de") return __de.dashboard_account_delete_confirm(inputs);
      return __ru.dashboard_account_delete_confirm(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Pricing — Vectora" |
 *
 * @param {Pricing_Page_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_page_title =
  /** @type {((inputs?: Pricing_Page_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Page_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_page_title(inputs);
      if (locale === "en") return __en.pricing_page_title(inputs);
      if (locale === "es") return __es.pricing_page_title(inputs);
      if (locale === "fr") return __fr.pricing_page_title(inputs);
      if (locale === "it") return __it.pricing_page_title(inputs);
      if (locale === "de") return __de.pricing_page_title(inputs);
      return __ru.pricing_page_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "FAQ — Vectora" |
 *
 * @param {Faq_Page_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const faq_page_title =
  /** @type {((inputs?: Faq_Page_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Faq_Page_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.faq_page_title(inputs);
      if (locale === "en") return __en.faq_page_title(inputs);
      if (locale === "es") return __es.faq_page_title(inputs);
      if (locale === "fr") return __fr.faq_page_title(inputs);
      if (locale === "it") return __it.faq_page_title(inputs);
      if (locale === "de") return __de.faq_page_title(inputs);
      return __ru.faq_page_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Search questions..." |
 *
 * @param {Faq_Search_PlaceholderInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const faq_search_placeholder =
  /** @type {((inputs?: Faq_Search_PlaceholderInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Faq_Search_PlaceholderInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.faq_search_placeholder(inputs);
      if (locale === "en") return __en.faq_search_placeholder(inputs);
      if (locale === "es") return __es.faq_search_placeholder(inputs);
      if (locale === "fr") return __fr.faq_search_placeholder(inputs);
      if (locale === "it") return __it.faq_search_placeholder(inputs);
      if (locale === "de") return __de.faq_search_placeholder(inputs);
      return __ru.faq_search_placeholder(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Support — Vectora" |
 *
 * @param {Support_Page_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const support_page_title =
  /** @type {((inputs?: Support_Page_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Support_Page_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.support_page_title(inputs);
      if (locale === "en") return __en.support_page_title(inputs);
      if (locale === "es") return __es.support_page_title(inputs);
      if (locale === "fr") return __fr.support_page_title(inputs);
      if (locale === "it") return __it.support_page_title(inputs);
      if (locale === "de") return __de.support_page_title(inputs);
      return __ru.support_page_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Report an issue — Vectora" |
 *
 * @param {Issues_Page_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_page_title =
  /** @type {((inputs?: Issues_Page_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Page_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_page_title(inputs);
      if (locale === "en") return __en.issues_page_title(inputs);
      if (locale === "es") return __es.issues_page_title(inputs);
      if (locale === "fr") return __fr.issues_page_title(inputs);
      if (locale === "it") return __it.issues_page_title(inputs);
      if (locale === "de") return __de.issues_page_title(inputs);
      return __ru.issues_page_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Title" |
 *
 * @param {Issues_Title_LabelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_title_label =
  /** @type {((inputs?: Issues_Title_LabelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Title_LabelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_title_label(inputs);
      if (locale === "en") return __en.issues_title_label(inputs);
      if (locale === "es") return __es.issues_title_label(inputs);
      if (locale === "fr") return __fr.issues_title_label(inputs);
      if (locale === "it") return __it.issues_title_label(inputs);
      if (locale === "de") return __de.issues_title_label(inputs);
      return __ru.issues_title_label(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Category" |
 *
 * @param {Issues_Category_LabelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_category_label =
  /** @type {((inputs?: Issues_Category_LabelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Category_LabelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_category_label(inputs);
      if (locale === "en") return __en.issues_category_label(inputs);
      if (locale === "es") return __es.issues_category_label(inputs);
      if (locale === "fr") return __fr.issues_category_label(inputs);
      if (locale === "it") return __it.issues_category_label(inputs);
      if (locale === "de") return __de.issues_category_label(inputs);
      return __ru.issues_category_label(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Bug" |
 *
 * @param {Issues_Category_BugInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_category_bug =
  /** @type {((inputs?: Issues_Category_BugInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Category_BugInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_category_bug(inputs);
      if (locale === "en") return __en.issues_category_bug(inputs);
      if (locale === "es") return __es.issues_category_bug(inputs);
      if (locale === "fr") return __fr.issues_category_bug(inputs);
      if (locale === "it") return __it.issues_category_bug(inputs);
      if (locale === "de") return __de.issues_category_bug(inputs);
      return __ru.issues_category_bug(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Recent issues" |
 *
 * @param {Issues_List_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_list_title =
  /** @type {((inputs?: Issues_List_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_List_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_list_title(inputs);
      if (locale === "en") return __en.issues_list_title(inputs);
      if (locale === "es") return __es.issues_list_title(inputs);
      if (locale === "fr") return __fr.issues_list_title(inputs);
      if (locale === "it") return __it.issues_list_title(inputs);
      if (locale === "de") return __de.issues_list_title(inputs);
      return __ru.issues_list_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "No issues yet. Be the first to report one." |
 *
 * @param {Issues_List_EmptyInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_list_empty =
  /** @type {((inputs?: Issues_List_EmptyInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_List_EmptyInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_list_empty(inputs);
      if (locale === "en") return __en.issues_list_empty(inputs);
      if (locale === "es") return __es.issues_list_empty(inputs);
      if (locale === "fr") return __fr.issues_list_empty(inputs);
      if (locale === "it") return __it.issues_list_empty(inputs);
      if (locale === "de") return __de.issues_list_empty(inputs);
      return __ru.issues_list_empty(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Feedback" |
 *
 * @param {Issues_Category_FeedbackInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_category_feedback =
  /** @type {((inputs?: Issues_Category_FeedbackInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Category_FeedbackInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_category_feedback(inputs);
      if (locale === "en") return __en.issues_category_feedback(inputs);
      if (locale === "es") return __es.issues_category_feedback(inputs);
      if (locale === "fr") return __fr.issues_category_feedback(inputs);
      if (locale === "it") return __it.issues_category_feedback(inputs);
      if (locale === "de") return __de.issues_category_feedback(inputs);
      return __ru.issues_category_feedback(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Feature request" |
 *
 * @param {Issues_Category_FeatureInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_category_feature =
  /** @type {((inputs?: Issues_Category_FeatureInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Category_FeatureInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_category_feature(inputs);
      if (locale === "en") return __en.issues_category_feature(inputs);
      if (locale === "es") return __es.issues_category_feature(inputs);
      if (locale === "fr") return __fr.issues_category_feature(inputs);
      if (locale === "it") return __it.issues_category_feature(inputs);
      if (locale === "de") return __de.issues_category_feature(inputs);
      return __ru.issues_category_feature(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Description" |
 *
 * @param {Issues_Description_LabelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_description_label =
  /** @type {((inputs?: Issues_Description_LabelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Description_LabelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_description_label(inputs);
      if (locale === "en") return __en.issues_description_label(inputs);
      if (locale === "es") return __es.issues_description_label(inputs);
      if (locale === "fr") return __fr.issues_description_label(inputs);
      if (locale === "it") return __it.issues_description_label(inputs);
      if (locale === "de") return __de.issues_description_label(inputs);
      return __ru.issues_description_label(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Email (optional)" |
 *
 * @param {Issues_Email_LabelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_email_label =
  /** @type {((inputs?: Issues_Email_LabelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Email_LabelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_email_label(inputs);
      if (locale === "en") return __en.issues_email_label(inputs);
      if (locale === "es") return __es.issues_email_label(inputs);
      if (locale === "fr") return __fr.issues_email_label(inputs);
      if (locale === "it") return __it.issues_email_label(inputs);
      if (locale === "de") return __de.issues_email_label(inputs);
      return __ru.issues_email_label(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Submit" |
 *
 * @param {Issues_SubmitInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_submit =
  /** @type {((inputs?: Issues_SubmitInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_SubmitInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_submit(inputs);
      if (locale === "en") return __en.issues_submit(inputs);
      if (locale === "es") return __es.issues_submit(inputs);
      if (locale === "fr") return __fr.issues_submit(inputs);
      if (locale === "it") return __it.issues_submit(inputs);
      if (locale === "de") return __de.issues_submit(inputs);
      return __ru.issues_submit(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Report submitted. Thank you!" |
 *
 * @param {Issues_SuccessInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_success =
  /** @type {((inputs?: Issues_SuccessInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_SuccessInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_success(inputs);
      if (locale === "en") return __en.issues_success(inputs);
      if (locale === "es") return __es.issues_success(inputs);
      if (locale === "fr") return __fr.issues_success(inputs);
      if (locale === "it") return __it.issues_success(inputs);
      if (locale === "de") return __de.issues_success(inputs);
      return __ru.issues_success(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Last updated:" |
 *
 * @param {Legal_Last_UpdatedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const legal_last_updated =
  /** @type {((inputs?: Legal_Last_UpdatedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Legal_Last_UpdatedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.legal_last_updated(inputs);
      if (locale === "en") return __en.legal_last_updated(inputs);
      if (locale === "es") return __es.legal_last_updated(inputs);
      if (locale === "fr") return __fr.legal_last_updated(inputs);
      if (locale === "it") return __it.legal_last_updated(inputs);
      if (locale === "de") return __de.legal_last_updated(inputs);
      return __ru.legal_last_updated(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Something went wrong. Please try again." |
 *
 * @param {Error_GenericInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_generic =
  /** @type {((inputs?: Error_GenericInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_GenericInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_generic(inputs);
      if (locale === "en") return __en.error_generic(inputs);
      if (locale === "es") return __es.error_generic(inputs);
      if (locale === "fr") return __fr.error_generic(inputs);
      if (locale === "it") return __it.error_generic(inputs);
      if (locale === "de") return __de.error_generic(inputs);
      return __ru.error_generic(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "You need to be logged in to access this page." |
 *
 * @param {Error_UnauthorizedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_unauthorized =
  /** @type {((inputs?: Error_UnauthorizedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_UnauthorizedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_unauthorized(inputs);
      if (locale === "en") return __en.error_unauthorized(inputs);
      if (locale === "es") return __es.error_unauthorized(inputs);
      if (locale === "fr") return __fr.error_unauthorized(inputs);
      if (locale === "it") return __it.error_unauthorized(inputs);
      if (locale === "de") return __de.error_unauthorized(inputs);
      return __ru.error_unauthorized(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Invalid email or password." |
 *
 * @param {Error_Invalid_CredentialsInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_invalid_credentials =
  /** @type {((inputs?: Error_Invalid_CredentialsInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_Invalid_CredentialsInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_invalid_credentials(inputs);
      if (locale === "en") return __en.error_invalid_credentials(inputs);
      if (locale === "es") return __es.error_invalid_credentials(inputs);
      if (locale === "fr") return __fr.error_invalid_credentials(inputs);
      if (locale === "it") return __it.error_invalid_credentials(inputs);
      if (locale === "de") return __de.error_invalid_credentials(inputs);
      return __ru.error_invalid_credentials(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "That email already has an account." |
 *
 * @param {Error_Email_Already_UsedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_email_already_used =
  /** @type {((inputs?: Error_Email_Already_UsedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_Email_Already_UsedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_email_already_used(inputs);
      if (locale === "en") return __en.error_email_already_used(inputs);
      if (locale === "es") return __es.error_email_already_used(inputs);
      if (locale === "fr") return __fr.error_email_already_used(inputs);
      if (locale === "it") return __it.error_email_already_used(inputs);
      if (locale === "de") return __de.error_email_already_used(inputs);
      return __ru.error_email_already_used(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Password must be at least 8 characters." |
 *
 * @param {Error_Weak_PasswordInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_weak_password =
  /** @type {((inputs?: Error_Weak_PasswordInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_Weak_PasswordInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_weak_password(inputs);
      if (locale === "en") return __en.error_weak_password(inputs);
      if (locale === "es") return __es.error_weak_password(inputs);
      if (locale === "fr") return __fr.error_weak_password(inputs);
      if (locale === "it") return __it.error_weak_password(inputs);
      if (locale === "de") return __de.error_weak_password(inputs);
      return __ru.error_weak_password(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Security check failed. Please try again." |
 *
 * @param {Error_TurnstileInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_turnstile =
  /** @type {((inputs?: Error_TurnstileInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_TurnstileInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_turnstile(inputs);
      if (locale === "en") return __en.error_turnstile(inputs);
      if (locale === "es") return __es.error_turnstile(inputs);
      if (locale === "fr") return __fr.error_turnstile(inputs);
      if (locale === "it") return __it.error_turnstile(inputs);
      if (locale === "de") return __de.error_turnstile(inputs);
      return __ru.error_turnstile(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "That email is already on the waitlist." |
 *
 * @param {Error_Duplicate_WaitlistInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_duplicate_waitlist =
  /** @type {((inputs?: Error_Duplicate_WaitlistInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_Duplicate_WaitlistInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_duplicate_waitlist(inputs);
      if (locale === "en") return __en.error_duplicate_waitlist(inputs);
      if (locale === "es") return __es.error_duplicate_waitlist(inputs);
      if (locale === "fr") return __fr.error_duplicate_waitlist(inputs);
      if (locale === "it") return __it.error_duplicate_waitlist(inputs);
      if (locale === "de") return __de.error_duplicate_waitlist(inputs);
      return __ru.error_duplicate_waitlist(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Email not confirmed. Check your inbox." |
 *
 * @param {Error_Email_Not_ConfirmedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_email_not_confirmed =
  /** @type {((inputs?: Error_Email_Not_ConfirmedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_Email_Not_ConfirmedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_email_not_confirmed(inputs);
      if (locale === "en") return __en.error_email_not_confirmed(inputs);
      if (locale === "es") return __es.error_email_not_confirmed(inputs);
      if (locale === "fr") return __fr.error_email_not_confirmed(inputs);
      if (locale === "it") return __it.error_email_not_confirmed(inputs);
      if (locale === "de") return __de.error_email_not_confirmed(inputs);
      return __ru.error_email_not_confirmed(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "That email already has an account." |
 *
 * @param {Error_Email_TakenInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_email_taken =
  /** @type {((inputs?: Error_Email_TakenInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_Email_TakenInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_email_taken(inputs);
      if (locale === "en") return __en.error_email_taken(inputs);
      if (locale === "es") return __es.error_email_taken(inputs);
      if (locale === "fr") return __fr.error_email_taken(inputs);
      if (locale === "it") return __it.error_email_taken(inputs);
      if (locale === "de") return __de.error_email_taken(inputs);
      return __ru.error_email_taken(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Password must be at least 8 characters." |
 *
 * @param {Error_Password_WeakInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const error_password_weak =
  /** @type {((inputs?: Error_Password_WeakInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Error_Password_WeakInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.error_password_weak(inputs);
      if (locale === "en") return __en.error_password_weak(inputs);
      if (locale === "es") return __es.error_password_weak(inputs);
      if (locale === "fr") return __fr.error_password_weak(inputs);
      if (locale === "it") return __it.error_password_weak(inputs);
      if (locale === "de") return __de.error_password_weak(inputs);
      return __ru.error_password_weak(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Self-hosting isn't complexity. It's competitive advantage." |
 *
 * @param {Why_SubtitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const why_subtitle =
  /** @type {((inputs?: Why_SubtitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Why_SubtitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.why_subtitle(inputs);
      if (locale === "en") return __en.why_subtitle(inputs);
      if (locale === "es") return __es.why_subtitle(inputs);
      if (locale === "fr") return __fr.why_subtitle(inputs);
      if (locale === "it") return __it.why_subtitle(inputs);
      if (locale === "de") return __de.why_subtitle(inputs);
      return __ru.why_subtitle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "30-day free trial. No credit card required." |
 *
 * @param {Pricing_TrialInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_trial =
  /** @type {((inputs?: Pricing_TrialInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_TrialInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_trial(inputs);
      if (locale === "en") return __en.pricing_trial(inputs);
      if (locale === "es") return __es.pricing_trial(inputs);
      if (locale === "fr") return __fr.pricing_trial(inputs);
      if (locale === "it") return __it.pricing_trial(inputs);
      if (locale === "de") return __de.pricing_trial(inputs);
      return __ru.pricing_trial(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Start free trial" |
 *
 * @param {Pricing_Cta_TrialInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cta_trial =
  /** @type {((inputs?: Pricing_Cta_TrialInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cta_TrialInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cta_trial(inputs);
      if (locale === "en") return __en.pricing_cta_trial(inputs);
      if (locale === "es") return __es.pricing_cta_trial(inputs);
      if (locale === "fr") return __fr.pricing_cta_trial(inputs);
      if (locale === "it") return __it.pricing_cta_trial(inputs);
      if (locale === "de") return __de.pricing_cta_trial(inputs);
      return __ru.pricing_cta_trial(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "See full comparison" |
 *
 * @param {Pricing_CompareInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_compare =
  /** @type {((inputs?: Pricing_CompareInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_CompareInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_compare(inputs);
      if (locale === "en") return __en.pricing_compare(inputs);
      if (locale === "es") return __es.pricing_compare(inputs);
      if (locale === "fr") return __fr.pricing_compare(inputs);
      if (locale === "it") return __it.pricing_compare(inputs);
      if (locale === "de") return __de.pricing_compare(inputs);
      return __ru.pricing_compare(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Join the list" |
 *
 * @param {Waitlist_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_cta =
  /** @type {((inputs?: Waitlist_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_cta(inputs);
      if (locale === "en") return __en.waitlist_cta(inputs);
      if (locale === "es") return __es.waitlist_cta(inputs);
      if (locale === "fr") return __fr.waitlist_cta(inputs);
      if (locale === "it") return __it.waitlist_cta(inputs);
      if (locale === "de") return __de.waitlist_cta(inputs);
      return __ru.waitlist_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "No spam. Just the launch announcement." |
 *
 * @param {Waitlist_No_SpamInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const waitlist_no_spam =
  /** @type {((inputs?: Waitlist_No_SpamInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Waitlist_No_SpamInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.waitlist_no_spam(inputs);
      if (locale === "en") return __en.waitlist_no_spam(inputs);
      if (locale === "es") return __es.waitlist_no_spam(inputs);
      if (locale === "fr") return __fr.waitlist_no_spam(inputs);
      if (locale === "it") return __it.waitlist_no_spam(inputs);
      if (locale === "de") return __de.waitlist_no_spam(inputs);
      return __ru.waitlist_no_spam(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Please wait..." |
 *
 * @param {Form_SubmittingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_submitting =
  /** @type {((inputs?: Form_SubmittingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_SubmittingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_submitting(inputs);
      if (locale === "en") return __en.form_submitting(inputs);
      if (locale === "es") return __es.form_submitting(inputs);
      if (locale === "fr") return __fr.form_submitting(inputs);
      if (locale === "it") return __it.form_submitting(inputs);
      if (locale === "de") return __de.form_submitting(inputs);
      return __ru.form_submitting(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Cancel" |
 *
 * @param {Form_CancelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_cancel =
  /** @type {((inputs?: Form_CancelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_CancelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_cancel(inputs);
      if (locale === "en") return __en.form_cancel(inputs);
      if (locale === "es") return __es.form_cancel(inputs);
      if (locale === "fr") return __fr.form_cancel(inputs);
      if (locale === "it") return __it.form_cancel(inputs);
      if (locale === "de") return __de.form_cancel(inputs);
      return __ru.form_cancel(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Full name" |
 *
 * @param {Form_NameInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_name =
  /** @type {((inputs?: Form_NameInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_NameInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_name(inputs);
      if (locale === "en") return __en.form_name(inputs);
      if (locale === "es") return __es.form_name(inputs);
      if (locale === "fr") return __fr.form_name(inputs);
      if (locale === "it") return __it.form_name(inputs);
      if (locale === "de") return __de.form_name(inputs);
      return __ru.form_name(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Create account" |
 *
 * @param {Signup_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const signup_heading =
  /** @type {((inputs?: Signup_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Signup_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.signup_heading(inputs);
      if (locale === "en") return __en.signup_heading(inputs);
      if (locale === "es") return __es.signup_heading(inputs);
      if (locale === "fr") return __fr.signup_heading(inputs);
      if (locale === "it") return __it.signup_heading(inputs);
      if (locale === "de") return __de.signup_heading(inputs);
      return __ru.signup_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Create account" |
 *
 * @param {Signup_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const signup_cta =
  /** @type {((inputs?: Signup_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Signup_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.signup_cta(inputs);
      if (locale === "en") return __en.signup_cta(inputs);
      if (locale === "es") return __es.signup_cta(inputs);
      if (locale === "fr") return __fr.signup_cta(inputs);
      if (locale === "it") return __it.signup_cta(inputs);
      if (locale === "de") return __de.signup_cta(inputs);
      return __ru.signup_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "I already have an account" |
 *
 * @param {Signup_Have_AccountInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const signup_have_account =
  /** @type {((inputs?: Signup_Have_AccountInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Signup_Have_AccountInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.signup_have_account(inputs);
      if (locale === "en") return __en.signup_have_account(inputs);
      if (locale === "es") return __es.signup_have_account(inputs);
      if (locale === "fr") return __fr.signup_have_account(inputs);
      if (locale === "it") return __it.signup_have_account(inputs);
      if (locale === "de") return __de.signup_have_account(inputs);
      return __ru.signup_have_account(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "View pricing" |
 *
 * @param {Signup_See_PricingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const signup_see_pricing =
  /** @type {((inputs?: Signup_See_PricingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Signup_See_PricingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.signup_see_pricing(inputs);
      if (locale === "en") return __en.signup_see_pricing(inputs);
      if (locale === "es") return __es.signup_see_pricing(inputs);
      if (locale === "fr") return __fr.signup_see_pricing(inputs);
      if (locale === "it") return __it.signup_see_pricing(inputs);
      if (locale === "de") return __de.signup_see_pricing(inputs);
      return __ru.signup_see_pricing(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Log in to your account" |
 *
 * @param {Login_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const login_heading =
  /** @type {((inputs?: Login_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Login_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.login_heading(inputs);
      if (locale === "en") return __en.login_heading(inputs);
      if (locale === "es") return __es.login_heading(inputs);
      if (locale === "fr") return __fr.login_heading(inputs);
      if (locale === "it") return __it.login_heading(inputs);
      if (locale === "de") return __de.login_heading(inputs);
      return __ru.login_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Forgot password" |
 *
 * @param {Login_ForgotInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const login_forgot =
  /** @type {((inputs?: Login_ForgotInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Login_ForgotInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.login_forgot(inputs);
      if (locale === "en") return __en.login_forgot(inputs);
      if (locale === "es") return __es.login_forgot(inputs);
      if (locale === "fr") return __fr.login_forgot(inputs);
      if (locale === "it") return __it.login_forgot(inputs);
      if (locale === "de") return __de.login_forgot(inputs);
      return __ru.login_forgot(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Link sent! Check your email." |
 *
 * @param {Login_Magic_SentInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const login_magic_sent =
  /** @type {((inputs?: Login_Magic_SentInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Login_Magic_SentInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.login_magic_sent(inputs);
      if (locale === "en") return __en.login_magic_sent(inputs);
      if (locale === "es") return __es.login_magic_sent(inputs);
      if (locale === "fr") return __fr.login_magic_sent(inputs);
      if (locale === "it") return __it.login_magic_sent(inputs);
      if (locale === "de") return __de.login_magic_sent(inputs);
      return __ru.login_magic_sent(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Log in" |
 *
 * @param {Login_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const login_cta =
  /** @type {((inputs?: Login_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Login_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.login_cta(inputs);
      if (locale === "en") return __en.login_cta(inputs);
      if (locale === "es") return __es.login_cta(inputs);
      if (locale === "fr") return __fr.login_cta(inputs);
      if (locale === "it") return __it.login_cta(inputs);
      if (locale === "de") return __de.login_cta(inputs);
      return __ru.login_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Token" |
 *
 * @param {Nav_TokenInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_token =
  /** @type {((inputs?: Nav_TokenInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_TokenInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_token(inputs);
      if (locale === "en") return __en.nav_token(inputs);
      if (locale === "es") return __es.nav_token(inputs);
      if (locale === "fr") return __fr.nav_token(inputs);
      if (locale === "it") return __it.nav_token(inputs);
      if (locale === "de") return __de.nav_token(inputs);
      return __ru.nav_token(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "License" |
 *
 * @param {Nav_LicenseInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_license =
  /** @type {((inputs?: Nav_LicenseInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_LicenseInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_license(inputs);
      if (locale === "en") return __en.nav_license(inputs);
      if (locale === "es") return __es.nav_license(inputs);
      if (locale === "fr") return __fr.nav_license(inputs);
      if (locale === "it") return __it.nav_license(inputs);
      if (locale === "de") return __de.nav_license(inputs);
      return __ru.nav_license(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Billing" |
 *
 * @param {Nav_BillingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_billing =
  /** @type {((inputs?: Nav_BillingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_BillingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_billing(inputs);
      if (locale === "en") return __en.nav_billing(inputs);
      if (locale === "es") return __es.nav_billing(inputs);
      if (locale === "fr") return __fr.nav_billing(inputs);
      if (locale === "it") return __it.nav_billing(inputs);
      if (locale === "de") return __de.nav_billing(inputs);
      return __ru.nav_billing(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "API Keys" |
 *
 * @param {Nav_Api_KeysInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_api_keys =
  /** @type {((inputs?: Nav_Api_KeysInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_Api_KeysInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_api_keys(inputs);
      if (locale === "en") return __en.nav_api_keys(inputs);
      if (locale === "es") return __es.nav_api_keys(inputs);
      if (locale === "fr") return __fr.nav_api_keys(inputs);
      if (locale === "it") return __it.nav_api_keys(inputs);
      if (locale === "de") return __de.nav_api_keys(inputs);
      return __ru.nav_api_keys(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Account" |
 *
 * @param {Nav_AccountInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_account =
  /** @type {((inputs?: Nav_AccountInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_AccountInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_account(inputs);
      if (locale === "en") return __en.nav_account(inputs);
      if (locale === "es") return __es.nav_account(inputs);
      if (locale === "fr") return __fr.nav_account(inputs);
      if (locale === "it") return __it.nav_account(inputs);
      if (locale === "de") return __de.nav_account(inputs);
      return __ru.nav_account(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Vectora — Self-hosted AI agent" |
 *
 * @param {Page_Home_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_home_title =
  /** @type {((inputs?: Page_Home_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Home_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_home_title(inputs);
      if (locale === "en") return __en.page_home_title(inputs);
      if (locale === "es") return __es.page_home_title(inputs);
      if (locale === "fr") return __fr.page_home_title(inputs);
      if (locale === "it") return __it.page_home_title(inputs);
      if (locale === "de") return __de.page_home_title(inputs);
      return __ru.page_home_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Self-hosted AI agent with RAG, MCP and multi-user web chat. Your data never leaves your server." |
 *
 * @param {Page_Home_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_home_desc =
  /** @type {((inputs?: Page_Home_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Home_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_home_desc(inputs);
      if (locale === "en") return __en.page_home_desc(inputs);
      if (locale === "es") return __es.page_home_desc(inputs);
      if (locale === "fr") return __fr.page_home_desc(inputs);
      if (locale === "it") return __it.page_home_desc(inputs);
      if (locale === "de") return __de.page_home_desc(inputs);
      return __ru.page_home_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Pricing — Vectora" |
 *
 * @param {Page_Pricing_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_pricing_title =
  /** @type {((inputs?: Page_Pricing_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Pricing_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_pricing_title(inputs);
      if (locale === "en") return __en.page_pricing_title(inputs);
      if (locale === "es") return __es.page_pricing_title(inputs);
      if (locale === "fr") return __fr.page_pricing_title(inputs);
      if (locale === "it") return __it.page_pricing_title(inputs);
      if (locale === "de") return __de.page_pricing_title(inputs);
      return __ru.page_pricing_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Plus and Pro plans with a 30-day free trial. No credit card required." |
 *
 * @param {Page_Pricing_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_pricing_desc =
  /** @type {((inputs?: Page_Pricing_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Pricing_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_pricing_desc(inputs);
      if (locale === "en") return __en.page_pricing_desc(inputs);
      if (locale === "es") return __es.page_pricing_desc(inputs);
      if (locale === "fr") return __fr.page_pricing_desc(inputs);
      if (locale === "it") return __it.page_pricing_desc(inputs);
      if (locale === "de") return __de.page_pricing_desc(inputs);
      return __ru.page_pricing_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "FAQ — Vectora" |
 *
 * @param {Page_Faq_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_faq_title =
  /** @type {((inputs?: Page_Faq_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Faq_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_faq_title(inputs);
      if (locale === "en") return __en.page_faq_title(inputs);
      if (locale === "es") return __es.page_faq_title(inputs);
      if (locale === "fr") return __fr.page_faq_title(inputs);
      if (locale === "it") return __it.page_faq_title(inputs);
      if (locale === "de") return __de.page_faq_title(inputs);
      return __ru.page_faq_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Frequently asked questions about Vectora." |
 *
 * @param {Page_Faq_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_faq_desc =
  /** @type {((inputs?: Page_Faq_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Faq_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_faq_desc(inputs);
      if (locale === "en") return __en.page_faq_desc(inputs);
      if (locale === "es") return __es.page_faq_desc(inputs);
      if (locale === "fr") return __fr.page_faq_desc(inputs);
      if (locale === "it") return __it.page_faq_desc(inputs);
      if (locale === "de") return __de.page_faq_desc(inputs);
      return __ru.page_faq_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Support — Vectora" |
 *
 * @param {Page_Support_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_support_title =
  /** @type {((inputs?: Page_Support_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Support_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_support_title(inputs);
      if (locale === "en") return __en.page_support_title(inputs);
      if (locale === "es") return __es.page_support_title(inputs);
      if (locale === "fr") return __fr.page_support_title(inputs);
      if (locale === "it") return __it.page_support_title(inputs);
      if (locale === "de") return __de.page_support_title(inputs);
      return __ru.page_support_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Log in — Vectora" |
 *
 * @param {Page_Login_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_login_title =
  /** @type {((inputs?: Page_Login_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Login_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_login_title(inputs);
      if (locale === "en") return __en.page_login_title(inputs);
      if (locale === "es") return __es.page_login_title(inputs);
      if (locale === "fr") return __fr.page_login_title(inputs);
      if (locale === "it") return __it.page_login_title(inputs);
      if (locale === "de") return __de.page_login_title(inputs);
      return __ru.page_login_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Create account — Vectora" |
 *
 * @param {Page_Signup_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_signup_title =
  /** @type {((inputs?: Page_Signup_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Signup_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_signup_title(inputs);
      if (locale === "en") return __en.page_signup_title(inputs);
      if (locale === "es") return __es.page_signup_title(inputs);
      if (locale === "fr") return __fr.page_signup_title(inputs);
      if (locale === "it") return __it.page_signup_title(inputs);
      if (locale === "de") return __de.page_signup_title(inputs);
      return __ru.page_signup_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Report an issue — Vectora" |
 *
 * @param {Page_Issues_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_issues_title =
  /** @type {((inputs?: Page_Issues_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Issues_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_issues_title(inputs);
      if (locale === "en") return __en.page_issues_title(inputs);
      if (locale === "es") return __es.page_issues_title(inputs);
      if (locale === "fr") return __fr.page_issues_title(inputs);
      if (locale === "it") return __it.page_issues_title(inputs);
      if (locale === "de") return __de.page_issues_title(inputs);
      return __ru.page_issues_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Choose the most appropriate channel for your question or issue." |
 *
 * @param {Support_SubtitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const support_subtitle =
  /** @type {((inputs?: Support_SubtitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Support_SubtitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.support_subtitle(inputs);
      if (locale === "en") return __en.support_subtitle(inputs);
      if (locale === "es") return __es.support_subtitle(inputs);
      if (locale === "fr") return __fr.support_subtitle(inputs);
      if (locale === "it") return __it.support_subtitle(inputs);
      if (locale === "de") return __de.support_subtitle(inputs);
      return __ru.support_subtitle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Found a bug, want to give feedback or suggest a feature? Let us know." |
 *
 * @param {Issues_SubtitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_subtitle =
  /** @type {((inputs?: Issues_SubtitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_SubtitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_subtitle(inputs);
      if (locale === "en") return __en.issues_subtitle(inputs);
      if (locale === "es") return __es.issues_subtitle(inputs);
      if (locale === "fr") return __fr.issues_subtitle(inputs);
      if (locale === "it") return __it.issues_subtitle(inputs);
      if (locale === "de") return __de.issues_subtitle(inputs);
      return __ru.issues_subtitle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Description" |
 *
 * @param {Issues_Desc_LabelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const issues_desc_label =
  /** @type {((inputs?: Issues_Desc_LabelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Issues_Desc_LabelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.issues_desc_label(inputs);
      if (locale === "en") return __en.issues_desc_label(inputs);
      if (locale === "es") return __es.issues_desc_label(inputs);
      if (locale === "fr") return __fr.issues_desc_label(inputs);
      if (locale === "it") return __it.issues_desc_label(inputs);
      if (locale === "de") return __de.issues_desc_label(inputs);
      return __ru.issues_desc_label(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Your VECTORA_TOKEN" |
 *
 * @param {Token_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_heading =
  /** @type {((inputs?: Token_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_heading(inputs);
      if (locale === "en") return __en.token_heading(inputs);
      if (locale === "es") return __es.token_heading(inputs);
      if (locale === "fr") return __fr.token_heading(inputs);
      if (locale === "it") return __it.token_heading(inputs);
      if (locale === "de") return __de.token_heading(inputs);
      return __ru.token_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "This token authenticates your Vectora instance with your license. Reveal it once and store it securely." |
 *
 * @param {Token_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_desc =
  /** @type {((inputs?: Token_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_desc(inputs);
      if (locale === "en") return __en.token_desc(inputs);
      if (locale === "es") return __es.token_desc(inputs);
      if (locale === "fr") return __fr.token_desc(inputs);
      if (locale === "it") return __it.token_desc(inputs);
      if (locale === "de") return __de.token_desc(inputs);
      return __ru.token_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Quick start" |
 *
 * @param {Token_Quickstart_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_quickstart_heading =
  /** @type {((inputs?: Token_Quickstart_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_Quickstart_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_quickstart_heading(inputs);
      if (locale === "en") return __en.token_quickstart_heading(inputs);
      if (locale === "es") return __es.token_quickstart_heading(inputs);
      if (locale === "fr") return __fr.token_quickstart_heading(inputs);
      if (locale === "it") return __it.token_quickstart_heading(inputs);
      if (locale === "de") return __de.token_quickstart_heading(inputs);
      return __ru.token_quickstart_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Click to reveal" |
 *
 * @param {Token_Reveal_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_reveal_cta =
  /** @type {((inputs?: Token_Reveal_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_Reveal_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_reveal_cta(inputs);
      if (locale === "en") return __en.token_reveal_cta(inputs);
      if (locale === "es") return __es.token_reveal_cta(inputs);
      if (locale === "fr") return __fr.token_reveal_cta(inputs);
      if (locale === "it") return __it.token_reveal_cta(inputs);
      if (locale === "de") return __de.token_reveal_cta(inputs);
      return __ru.token_reveal_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Token copied!" |
 *
 * @param {Token_CopiedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_copied =
  /** @type {((inputs?: Token_CopiedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_CopiedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_copied(inputs);
      if (locale === "en") return __en.token_copied(inputs);
      if (locale === "es") return __es.token_copied(inputs);
      if (locale === "fr") return __fr.token_copied(inputs);
      if (locale === "it") return __it.token_copied(inputs);
      if (locale === "de") return __de.token_copied(inputs);
      return __ru.token_copied(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Copy token" |
 *
 * @param {Token_Copy_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_copy_cta =
  /** @type {((inputs?: Token_Copy_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_Copy_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_copy_cta(inputs);
      if (locale === "en") return __en.token_copy_cta(inputs);
      if (locale === "es") return __es.token_copy_cta(inputs);
      if (locale === "fr") return __fr.token_copy_cta(inputs);
      if (locale === "it") return __it.token_copy_cta(inputs);
      if (locale === "de") return __de.token_copy_cta(inputs);
      return __ru.token_copy_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Copy and save. It will not be shown again." |
 *
 * @param {Token_Show_Once_WarningInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_show_once_warning =
  /** @type {((inputs?: Token_Show_Once_WarningInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_Show_Once_WarningInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_show_once_warning(inputs);
      if (locale === "en") return __en.token_show_once_warning(inputs);
      if (locale === "es") return __es.token_show_once_warning(inputs);
      if (locale === "fr") return __fr.token_show_once_warning(inputs);
      if (locale === "it") return __it.token_show_once_warning(inputs);
      if (locale === "de") return __de.token_show_once_warning(inputs);
      return __ru.token_show_once_warning(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Token already revealed. Rotate below if you need a new one." |
 *
 * @param {Token_Already_RevealedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_already_revealed =
  /** @type {((inputs?: Token_Already_RevealedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_Already_RevealedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_already_revealed(inputs);
      if (locale === "en") return __en.token_already_revealed(inputs);
      if (locale === "es") return __es.token_already_revealed(inputs);
      if (locale === "fr") return __fr.token_already_revealed(inputs);
      if (locale === "it") return __it.token_already_revealed(inputs);
      if (locale === "de") return __de.token_already_revealed(inputs);
      return __ru.token_already_revealed(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Rotate token" |
 *
 * @param {Token_Rotate_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_rotate_cta =
  /** @type {((inputs?: Token_Rotate_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_Rotate_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_rotate_cta(inputs);
      if (locale === "en") return __en.token_rotate_cta(inputs);
      if (locale === "es") return __es.token_rotate_cta(inputs);
      if (locale === "fr") return __fr.token_rotate_cta(inputs);
      if (locale === "it") return __it.token_rotate_cta(inputs);
      if (locale === "de") return __de.token_rotate_cta(inputs);
      return __ru.token_rotate_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "New token generated successfully." |
 *
 * @param {Token_RotatedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const token_rotated =
  /** @type {((inputs?: Token_RotatedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Token_RotatedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.token_rotated(inputs);
      if (locale === "en") return __en.token_rotated(inputs);
      if (locale === "es") return __es.token_rotated(inputs);
      if (locale === "fr") return __fr.token_rotated(inputs);
      if (locale === "it") return __it.token_rotated(inputs);
      if (locale === "de") return __de.token_rotated(inputs);
      return __ru.token_rotated(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Plan" |
 *
 * @param {License_PlanInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_plan =
  /** @type {((inputs?: License_PlanInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_PlanInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_plan(inputs);
      if (locale === "en") return __en.license_plan(inputs);
      if (locale === "es") return __es.license_plan(inputs);
      if (locale === "fr") return __fr.license_plan(inputs);
      if (locale === "it") return __it.license_plan(inputs);
      if (locale === "de") return __de.license_plan(inputs);
      return __ru.license_plan(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Started" |
 *
 * @param {License_StartedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_started =
  /** @type {((inputs?: License_StartedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_StartedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_started(inputs);
      if (locale === "en") return __en.license_started(inputs);
      if (locale === "es") return __es.license_started(inputs);
      if (locale === "fr") return __fr.license_started(inputs);
      if (locale === "it") return __it.license_started(inputs);
      if (locale === "de") return __de.license_started(inputs);
      return __ru.license_started(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Trial ends" |
 *
 * @param {License_Trial_EndsInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_trial_ends =
  /** @type {((inputs?: License_Trial_EndsInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_Trial_EndsInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_trial_ends(inputs);
      if (locale === "en") return __en.license_trial_ends(inputs);
      if (locale === "es") return __es.license_trial_ends(inputs);
      if (locale === "fr") return __fr.license_trial_ends(inputs);
      if (locale === "it") return __it.license_trial_ends(inputs);
      if (locale === "de") return __de.license_trial_ends(inputs);
      return __ru.license_trial_ends(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Subscribe Plus" |
 *
 * @param {License_Cta_Subscribe_PlusInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_cta_subscribe_plus =
  /** @type {((inputs?: License_Cta_Subscribe_PlusInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_Cta_Subscribe_PlusInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_cta_subscribe_plus(inputs);
      if (locale === "en") return __en.license_cta_subscribe_plus(inputs);
      if (locale === "es") return __es.license_cta_subscribe_plus(inputs);
      if (locale === "fr") return __fr.license_cta_subscribe_plus(inputs);
      if (locale === "it") return __it.license_cta_subscribe_plus(inputs);
      if (locale === "de") return __de.license_cta_subscribe_plus(inputs);
      return __ru.license_cta_subscribe_plus(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Upgrade to Pro" |
 *
 * @param {License_Cta_Upgrade_ProInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_cta_upgrade_pro =
  /** @type {((inputs?: License_Cta_Upgrade_ProInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_Cta_Upgrade_ProInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_cta_upgrade_pro(inputs);
      if (locale === "en") return __en.license_cta_upgrade_pro(inputs);
      if (locale === "es") return __es.license_cta_upgrade_pro(inputs);
      if (locale === "fr") return __fr.license_cta_upgrade_pro(inputs);
      if (locale === "it") return __it.license_cta_upgrade_pro(inputs);
      if (locale === "de") return __de.license_cta_upgrade_pro(inputs);
      return __ru.license_cta_upgrade_pro(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Manage subscription" |
 *
 * @param {License_Cta_ManageInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_cta_manage =
  /** @type {((inputs?: License_Cta_ManageInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_Cta_ManageInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_cta_manage(inputs);
      if (locale === "en") return __en.license_cta_manage(inputs);
      if (locale === "es") return __es.license_cta_manage(inputs);
      if (locale === "fr") return __fr.license_cta_manage(inputs);
      if (locale === "it") return __it.license_cta_manage(inputs);
      if (locale === "de") return __de.license_cta_manage(inputs);
      return __ru.license_cta_manage(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Update payment" |
 *
 * @param {License_Cta_Update_PaymentInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_cta_update_payment =
  /** @type {((inputs?: License_Cta_Update_PaymentInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_Cta_Update_PaymentInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_cta_update_payment(inputs);
      if (locale === "en") return __en.license_cta_update_payment(inputs);
      if (locale === "es") return __es.license_cta_update_payment(inputs);
      if (locale === "fr") return __fr.license_cta_update_payment(inputs);
      if (locale === "it") return __it.license_cta_update_payment(inputs);
      if (locale === "de") return __de.license_cta_update_payment(inputs);
      return __ru.license_cta_update_payment(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "No validations recorded yet." |
 *
 * @param {License_No_ChecksInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_no_checks =
  /** @type {((inputs?: License_No_ChecksInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_No_ChecksInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_no_checks(inputs);
      if (locale === "en") return __en.license_no_checks(inputs);
      if (locale === "es") return __es.license_no_checks(inputs);
      if (locale === "fr") return __fr.license_no_checks(inputs);
      if (locale === "it") return __it.license_no_checks(inputs);
      if (locale === "de") return __de.license_no_checks(inputs);
      return __ru.license_no_checks(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Date" |
 *
 * @param {License_Col_DateInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_col_date =
  /** @type {((inputs?: License_Col_DateInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_Col_DateInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_col_date(inputs);
      if (locale === "en") return __en.license_col_date(inputs);
      if (locale === "es") return __es.license_col_date(inputs);
      if (locale === "fr") return __fr.license_col_date(inputs);
      if (locale === "it") return __it.license_col_date(inputs);
      if (locale === "de") return __de.license_col_date(inputs);
      return __ru.license_col_date(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Version" |
 *
 * @param {License_Col_VersionInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_col_version =
  /** @type {((inputs?: License_Col_VersionInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_Col_VersionInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_col_version(inputs);
      if (locale === "en") return __en.license_col_version(inputs);
      if (locale === "es") return __es.license_col_version(inputs);
      if (locale === "fr") return __fr.license_col_version(inputs);
      if (locale === "it") return __it.license_col_version(inputs);
      if (locale === "de") return __de.license_col_version(inputs);
      return __ru.license_col_version(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Result" |
 *
 * @param {License_Col_ResultInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_col_result =
  /** @type {((inputs?: License_Col_ResultInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_Col_ResultInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_col_result(inputs);
      if (locale === "en") return __en.license_col_result(inputs);
      if (locale === "es") return __es.license_col_result(inputs);
      if (locale === "fr") return __fr.license_col_result(inputs);
      if (locale === "it") return __it.license_col_result(inputs);
      if (locale === "de") return __de.license_col_result(inputs);
      return __ru.license_col_result(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Validation history" |
 *
 * @param {License_History_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const license_history_heading =
  /** @type {((inputs?: License_History_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<License_History_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.license_history_heading(inputs);
      if (locale === "en") return __en.license_history_heading(inputs);
      if (locale === "es") return __es.license_history_heading(inputs);
      if (locale === "fr") return __fr.license_history_heading(inputs);
      if (locale === "it") return __it.license_history_heading(inputs);
      if (locale === "de") return __de.license_history_heading(inputs);
      return __ru.license_history_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Your trial has ended. Subscribe to continue using Vectora." |
 *
 * @param {Billing_Inactive_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const billing_inactive_desc =
  /** @type {((inputs?: Billing_Inactive_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Billing_Inactive_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.billing_inactive_desc(inputs);
      if (locale === "en") return __en.billing_inactive_desc(inputs);
      if (locale === "es") return __es.billing_inactive_desc(inputs);
      if (locale === "fr") return __fr.billing_inactive_desc(inputs);
      if (locale === "it") return __it.billing_inactive_desc(inputs);
      if (locale === "de") return __de.billing_inactive_desc(inputs);
      return __ru.billing_inactive_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Upgrade to Pro" |
 *
 * @param {Billing_Upgrade_ProInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const billing_upgrade_pro =
  /** @type {((inputs?: Billing_Upgrade_ProInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Billing_Upgrade_ProInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.billing_upgrade_pro(inputs);
      if (locale === "en") return __en.billing_upgrade_pro(inputs);
      if (locale === "es") return __es.billing_upgrade_pro(inputs);
      if (locale === "fr") return __fr.billing_upgrade_pro(inputs);
      if (locale === "it") return __it.billing_upgrade_pro(inputs);
      if (locale === "de") return __de.billing_upgrade_pro(inputs);
      return __ru.billing_upgrade_pro(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Manage subscription" |
 *
 * @param {Billing_ManageInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const billing_manage =
  /** @type {((inputs?: Billing_ManageInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Billing_ManageInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.billing_manage(inputs);
      if (locale === "en") return __en.billing_manage(inputs);
      if (locale === "es") return __es.billing_manage(inputs);
      if (locale === "fr") return __fr.billing_manage(inputs);
      if (locale === "it") return __it.billing_manage(inputs);
      if (locale === "de") return __de.billing_manage(inputs);
      return __ru.billing_manage(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Payments securely processed via Stripe (INTL) and Asaas (BR)." |
 *
 * @param {Billing_FooterInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const billing_footer =
  /** @type {((inputs?: Billing_FooterInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Billing_FooterInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.billing_footer(inputs);
      if (locale === "en") return __en.billing_footer(inputs);
      if (locale === "es") return __es.billing_footer(inputs);
      if (locale === "fr") return __fr.billing_footer(inputs);
      if (locale === "it") return __it.billing_footer(inputs);
      if (locale === "de") return __de.billing_footer(inputs);
      return __ru.billing_footer(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "New API Key" |
 *
 * @param {Apikeys_Modal_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_modal_heading =
  /** @type {((inputs?: Apikeys_Modal_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Modal_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_modal_heading(inputs);
      if (locale === "en") return __en.apikeys_modal_heading(inputs);
      if (locale === "es") return __es.apikeys_modal_heading(inputs);
      if (locale === "fr") return __fr.apikeys_modal_heading(inputs);
      if (locale === "it") return __it.apikeys_modal_heading(inputs);
      if (locale === "de") return __de.apikeys_modal_heading(inputs);
      return __ru.apikeys_modal_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Your API Key was created" |
 *
 * @param {Apikeys_Modal_Secret_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_modal_secret_heading =
  /** @type {((inputs?: Apikeys_Modal_Secret_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Modal_Secret_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_modal_secret_heading(inputs);
      if (locale === "en") return __en.apikeys_modal_secret_heading(inputs);
      if (locale === "es") return __es.apikeys_modal_secret_heading(inputs);
      if (locale === "fr") return __fr.apikeys_modal_secret_heading(inputs);
      if (locale === "it") return __it.apikeys_modal_secret_heading(inputs);
      if (locale === "de") return __de.apikeys_modal_secret_heading(inputs);
      return __ru.apikeys_modal_secret_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Done" |
 *
 * @param {Apikeys_Modal_DoneInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_modal_done =
  /** @type {((inputs?: Apikeys_Modal_DoneInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Modal_DoneInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_modal_done(inputs);
      if (locale === "en") return __en.apikeys_modal_done(inputs);
      if (locale === "es") return __es.apikeys_modal_done(inputs);
      if (locale === "fr") return __fr.apikeys_modal_done(inputs);
      if (locale === "it") return __it.apikeys_modal_done(inputs);
      if (locale === "de") return __de.apikeys_modal_done(inputs);
      return __ru.apikeys_modal_done(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Name" |
 *
 * @param {Apikeys_Name_LabelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_name_label =
  /** @type {((inputs?: Apikeys_Name_LabelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Name_LabelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_name_label(inputs);
      if (locale === "en") return __en.apikeys_name_label(inputs);
      if (locale === "es") return __es.apikeys_name_label(inputs);
      if (locale === "fr") return __fr.apikeys_name_label(inputs);
      if (locale === "it") return __it.apikeys_name_label(inputs);
      if (locale === "de") return __de.apikeys_name_label(inputs);
      return __ru.apikeys_name_label(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Scopes" |
 *
 * @param {Apikeys_Scopes_LabelInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_scopes_label =
  /** @type {((inputs?: Apikeys_Scopes_LabelInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Scopes_LabelInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_scopes_label(inputs);
      if (locale === "en") return __en.apikeys_scopes_label(inputs);
      if (locale === "es") return __es.apikeys_scopes_label(inputs);
      if (locale === "fr") return __fr.apikeys_scopes_label(inputs);
      if (locale === "it") return __it.apikeys_scopes_label(inputs);
      if (locale === "de") return __de.apikeys_scopes_label(inputs);
      return __ru.apikeys_scopes_label(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Create API key" |
 *
 * @param {Apikeys_Create_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_create_cta =
  /** @type {((inputs?: Apikeys_Create_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Create_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_create_cta(inputs);
      if (locale === "en") return __en.apikeys_create_cta(inputs);
      if (locale === "es") return __es.apikeys_create_cta(inputs);
      if (locale === "fr") return __fr.apikeys_create_cta(inputs);
      if (locale === "it") return __it.apikeys_create_cta(inputs);
      if (locale === "de") return __de.apikeys_create_cta(inputs);
      return __ru.apikeys_create_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "active keys" |
 *
 * @param {Apikeys_CountInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_count =
  /** @type {((inputs?: Apikeys_CountInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_CountInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_count(inputs);
      if (locale === "en") return __en.apikeys_count(inputs);
      if (locale === "es") return __es.apikeys_count(inputs);
      if (locale === "fr") return __fr.apikeys_count(inputs);
      if (locale === "it") return __it.apikeys_count(inputs);
      if (locale === "de") return __de.apikeys_count(inputs);
      return __ru.apikeys_count(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "No API keys created yet." |
 *
 * @param {Apikeys_EmptyInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_empty =
  /** @type {((inputs?: Apikeys_EmptyInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_EmptyInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_empty(inputs);
      if (locale === "en") return __en.apikeys_empty(inputs);
      if (locale === "es") return __es.apikeys_empty(inputs);
      if (locale === "fr") return __fr.apikeys_empty(inputs);
      if (locale === "it") return __it.apikeys_empty(inputs);
      if (locale === "de") return __de.apikeys_empty(inputs);
      return __ru.apikeys_empty(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Name" |
 *
 * @param {Apikeys_Col_NameInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_col_name =
  /** @type {((inputs?: Apikeys_Col_NameInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Col_NameInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_col_name(inputs);
      if (locale === "en") return __en.apikeys_col_name(inputs);
      if (locale === "es") return __es.apikeys_col_name(inputs);
      if (locale === "fr") return __fr.apikeys_col_name(inputs);
      if (locale === "it") return __it.apikeys_col_name(inputs);
      if (locale === "de") return __de.apikeys_col_name(inputs);
      return __ru.apikeys_col_name(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Scopes" |
 *
 * @param {Apikeys_Col_ScopesInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_col_scopes =
  /** @type {((inputs?: Apikeys_Col_ScopesInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Col_ScopesInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_col_scopes(inputs);
      if (locale === "en") return __en.apikeys_col_scopes(inputs);
      if (locale === "es") return __es.apikeys_col_scopes(inputs);
      if (locale === "fr") return __fr.apikeys_col_scopes(inputs);
      if (locale === "it") return __it.apikeys_col_scopes(inputs);
      if (locale === "de") return __de.apikeys_col_scopes(inputs);
      return __ru.apikeys_col_scopes(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Created" |
 *
 * @param {Apikeys_Col_CreatedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_col_created =
  /** @type {((inputs?: Apikeys_Col_CreatedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Col_CreatedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_col_created(inputs);
      if (locale === "en") return __en.apikeys_col_created(inputs);
      if (locale === "es") return __es.apikeys_col_created(inputs);
      if (locale === "fr") return __fr.apikeys_col_created(inputs);
      if (locale === "it") return __it.apikeys_col_created(inputs);
      if (locale === "de") return __de.apikeys_col_created(inputs);
      return __ru.apikeys_col_created(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Last used" |
 *
 * @param {Apikeys_Col_Last_UsedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_col_last_used =
  /** @type {((inputs?: Apikeys_Col_Last_UsedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_Col_Last_UsedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_col_last_used(inputs);
      if (locale === "en") return __en.apikeys_col_last_used(inputs);
      if (locale === "es") return __es.apikeys_col_last_used(inputs);
      if (locale === "fr") return __fr.apikeys_col_last_used(inputs);
      if (locale === "it") return __it.apikeys_col_last_used(inputs);
      if (locale === "de") return __de.apikeys_col_last_used(inputs);
      return __ru.apikeys_col_last_used(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Use API Keys to authenticate integrations with the REST API /v1." |
 *
 * @param {Apikeys_SubtitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const apikeys_subtitle =
  /** @type {((inputs?: Apikeys_SubtitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Apikeys_SubtitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.apikeys_subtitle(inputs);
      if (locale === "en") return __en.apikeys_subtitle(inputs);
      if (locale === "es") return __es.apikeys_subtitle(inputs);
      if (locale === "fr") return __fr.apikeys_subtitle(inputs);
      if (locale === "it") return __it.apikeys_subtitle(inputs);
      if (locale === "de") return __de.apikeys_subtitle(inputs);
      return __ru.apikeys_subtitle(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Profile" |
 *
 * @param {Account_Profile_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_profile_heading =
  /** @type {((inputs?: Account_Profile_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Profile_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_profile_heading(inputs);
      if (locale === "en") return __en.account_profile_heading(inputs);
      if (locale === "es") return __es.account_profile_heading(inputs);
      if (locale === "fr") return __fr.account_profile_heading(inputs);
      if (locale === "it") return __it.account_profile_heading(inputs);
      if (locale === "de") return __de.account_profile_heading(inputs);
      return __ru.account_profile_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Security" |
 *
 * @param {Account_Security_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_security_heading =
  /** @type {((inputs?: Account_Security_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Security_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_security_heading(inputs);
      if (locale === "en") return __en.account_security_heading(inputs);
      if (locale === "es") return __es.account_security_heading(inputs);
      if (locale === "fr") return __fr.account_security_heading(inputs);
      if (locale === "it") return __it.account_security_heading(inputs);
      if (locale === "de") return __de.account_security_heading(inputs);
      return __ru.account_security_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "We'll send an access link to your email to reset your password." |
 *
 * @param {Account_Password_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_password_desc =
  /** @type {((inputs?: Account_Password_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Password_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_password_desc(inputs);
      if (locale === "en") return __en.account_password_desc(inputs);
      if (locale === "es") return __es.account_password_desc(inputs);
      if (locale === "fr") return __fr.account_password_desc(inputs);
      if (locale === "it") return __it.account_password_desc(inputs);
      if (locale === "de") return __de.account_password_desc(inputs);
      return __ru.account_password_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Change password" |
 *
 * @param {Account_Change_PasswordInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_change_password =
  /** @type {((inputs?: Account_Change_PasswordInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Change_PasswordInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_change_password(inputs);
      if (locale === "en") return __en.account_change_password(inputs);
      if (locale === "es") return __es.account_change_password(inputs);
      if (locale === "fr") return __fr.account_change_password(inputs);
      if (locale === "it") return __it.account_change_password(inputs);
      if (locale === "de") return __de.account_change_password(inputs);
      return __ru.account_change_password(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Data & Privacy" |
 *
 * @param {Account_Gdpr_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_gdpr_heading =
  /** @type {((inputs?: Account_Gdpr_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Gdpr_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_gdpr_heading(inputs);
      if (locale === "en") return __en.account_gdpr_heading(inputs);
      if (locale === "es") return __es.account_gdpr_heading(inputs);
      if (locale === "fr") return __fr.account_gdpr_heading(inputs);
      if (locale === "it") return __it.account_gdpr_heading(inputs);
      if (locale === "de") return __de.account_gdpr_heading(inputs);
      return __ru.account_gdpr_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Export all your data in JSON format. The link expires in 5 minutes." |
 *
 * @param {Account_Export_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_export_desc =
  /** @type {((inputs?: Account_Export_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Export_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_export_desc(inputs);
      if (locale === "en") return __en.account_export_desc(inputs);
      if (locale === "es") return __es.account_export_desc(inputs);
      if (locale === "fr") return __fr.account_export_desc(inputs);
      if (locale === "it") return __it.account_export_desc(inputs);
      if (locale === "de") return __de.account_export_desc(inputs);
      return __ru.account_export_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Export my data" |
 *
 * @param {Account_Export_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_export_cta =
  /** @type {((inputs?: Account_Export_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Export_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_export_cta(inputs);
      if (locale === "en") return __en.account_export_cta(inputs);
      if (locale === "es") return __es.account_export_cta(inputs);
      if (locale === "fr") return __fr.account_export_cta(inputs);
      if (locale === "it") return __it.account_export_cta(inputs);
      if (locale === "de") return __de.account_export_cta(inputs);
      return __ru.account_export_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Request permanent deletion of your account. Data is removed within 30 days." |
 *
 * @param {Account_Delete_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_delete_desc =
  /** @type {((inputs?: Account_Delete_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Delete_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_delete_desc(inputs);
      if (locale === "en") return __en.account_delete_desc(inputs);
      if (locale === "es") return __es.account_delete_desc(inputs);
      if (locale === "fr") return __fr.account_delete_desc(inputs);
      if (locale === "it") return __it.account_delete_desc(inputs);
      if (locale === "de") return __de.account_delete_desc(inputs);
      return __ru.account_delete_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Delete account" |
 *
 * @param {Account_Delete_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_delete_cta =
  /** @type {((inputs?: Account_Delete_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Delete_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_delete_cta(inputs);
      if (locale === "en") return __en.account_delete_cta(inputs);
      if (locale === "es") return __es.account_delete_cta(inputs);
      if (locale === "fr") return __fr.account_delete_cta(inputs);
      if (locale === "it") return __it.account_delete_cta(inputs);
      if (locale === "de") return __de.account_delete_cta(inputs);
      return __ru.account_delete_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Type your email to confirm. This action cannot be undone." |
 *
 * @param {Account_Delete_Confirm_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_delete_confirm_desc =
  /** @type {((inputs?: Account_Delete_Confirm_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Delete_Confirm_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_delete_confirm_desc(inputs);
      if (locale === "en") return __en.account_delete_confirm_desc(inputs);
      if (locale === "es") return __es.account_delete_confirm_desc(inputs);
      if (locale === "fr") return __fr.account_delete_confirm_desc(inputs);
      if (locale === "it") return __it.account_delete_confirm_desc(inputs);
      if (locale === "de") return __de.account_delete_confirm_desc(inputs);
      return __ru.account_delete_confirm_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Confirm deletion" |
 *
 * @param {Account_Delete_Confirm_CtaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_delete_confirm_cta =
  /** @type {((inputs?: Account_Delete_Confirm_CtaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Delete_Confirm_CtaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_delete_confirm_cta(inputs);
      if (locale === "en") return __en.account_delete_confirm_cta(inputs);
      if (locale === "es") return __es.account_delete_confirm_cta(inputs);
      if (locale === "fr") return __fr.account_delete_confirm_cta(inputs);
      if (locale === "it") return __it.account_delete_confirm_cta(inputs);
      if (locale === "de") return __de.account_delete_confirm_cta(inputs);
      return __ru.account_delete_confirm_cta(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Roadmap" |
 *
 * @param {Footer_RoadmapInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const footer_roadmap =
  /** @type {((inputs?: Footer_RoadmapInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Footer_RoadmapInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.footer_roadmap(inputs);
      if (locale === "en") return __en.footer_roadmap(inputs);
      if (locale === "es") return __es.footer_roadmap(inputs);
      if (locale === "fr") return __fr.footer_roadmap(inputs);
      if (locale === "it") return __it.footer_roadmap(inputs);
      if (locale === "de") return __de.footer_roadmap(inputs);
      return __ru.footer_roadmap(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Roadmap — Vectora" |
 *
 * @param {Page_Roadmap_TitleInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_roadmap_title =
  /** @type {((inputs?: Page_Roadmap_TitleInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Roadmap_TitleInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_roadmap_title(inputs);
      if (locale === "en") return __en.page_roadmap_title(inputs);
      if (locale === "es") return __es.page_roadmap_title(inputs);
      if (locale === "fr") return __fr.page_roadmap_title(inputs);
      if (locale === "it") return __it.page_roadmap_title(inputs);
      if (locale === "de") return __de.page_roadmap_title(inputs);
      return __ru.page_roadmap_title(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "See what's already shipped, what's being built, and what's coming next." |
 *
 * @param {Page_Roadmap_DescInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const page_roadmap_desc =
  /** @type {((inputs?: Page_Roadmap_DescInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Page_Roadmap_DescInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.page_roadmap_desc(inputs);
      if (locale === "en") return __en.page_roadmap_desc(inputs);
      if (locale === "es") return __es.page_roadmap_desc(inputs);
      if (locale === "fr") return __fr.page_roadmap_desc(inputs);
      if (locale === "it") return __it.page_roadmap_desc(inputs);
      if (locale === "de") return __de.page_roadmap_desc(inputs);
      return __ru.page_roadmap_desc(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Save" |
 *
 * @param {Form_SaveInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const form_save =
  /** @type {((inputs?: Form_SaveInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Form_SaveInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.form_save(inputs);
      if (locale === "en") return __en.form_save(inputs);
      if (locale === "es") return __es.form_save(inputs);
      if (locale === "fr") return __fr.form_save(inputs);
      if (locale === "it") return __it.form_save(inputs);
      if (locale === "de") return __de.form_save(inputs);
      return __ru.form_save(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Preferred language" |
 *
 * @param {Account_LanguageInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_language =
  /** @type {((inputs?: Account_LanguageInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_LanguageInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_language(inputs);
      if (locale === "en") return __en.account_language(inputs);
      if (locale === "es") return __es.account_language(inputs);
      if (locale === "fr") return __fr.account_language(inputs);
      if (locale === "it") return __it.account_language(inputs);
      if (locale === "de") return __de.account_language(inputs);
      return __ru.account_language(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Profile updated." |
 *
 * @param {Account_Profile_SavedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const account_profile_saved =
  /** @type {((inputs?: Account_Profile_SavedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Account_Profile_SavedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.account_profile_saved(inputs);
      if (locale === "en") return __en.account_profile_saved(inputs);
      if (locale === "es") return __es.account_profile_saved(inputs);
      if (locale === "fr") return __fr.account_profile_saved(inputs);
      if (locale === "it") return __it.account_profile_saved(inputs);
      if (locale === "de") return __de.account_profile_saved(inputs);
      return __ru.account_profile_saved(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Switch to light theme" |
 *
 * @param {Theme_LightInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const theme_light =
  /** @type {((inputs?: Theme_LightInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Theme_LightInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.theme_light(inputs);
      if (locale === "en") return __en.theme_light(inputs);
      if (locale === "es") return __es.theme_light(inputs);
      if (locale === "fr") return __fr.theme_light(inputs);
      if (locale === "it") return __it.theme_light(inputs);
      if (locale === "de") return __de.theme_light(inputs);
      return __ru.theme_light(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Switch to dark theme" |
 *
 * @param {Theme_DarkInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const theme_dark =
  /** @type {((inputs?: Theme_DarkInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Theme_DarkInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.theme_dark(inputs);
      if (locale === "en") return __en.theme_dark(inputs);
      if (locale === "es") return __es.theme_dark(inputs);
      if (locale === "fr") return __fr.theme_dark(inputs);
      if (locale === "it") return __it.theme_dark(inputs);
      if (locale === "de") return __de.theme_dark(inputs);
      return __ru.theme_dark(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Open menu" |
 *
 * @param {Nav_MenuInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const nav_menu =
  /** @type {((inputs?: Nav_MenuInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Nav_MenuInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.nav_menu(inputs);
      if (locale === "en") return __en.nav_menu(inputs);
      if (locale === "es") return __es.nav_menu(inputs);
      if (locale === "fr") return __fr.nav_menu(inputs);
      if (locale === "it") return __it.nav_menu(inputs);
      if (locale === "de") return __de.nav_menu(inputs);
      return __ru.nav_menu(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "1 workspace" |
 *
 * @param {Pricing_Feat_Workspace1Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_workspace1 =
  /** @type {((inputs?: Pricing_Feat_Workspace1Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Workspace1Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_workspace1(inputs);
      if (locale === "en") return __en.pricing_feat_workspace1(inputs);
      if (locale === "es") return __es.pricing_feat_workspace1(inputs);
      if (locale === "fr") return __fr.pricing_feat_workspace1(inputs);
      if (locale === "it") return __it.pricing_feat_workspace1(inputs);
      if (locale === "de") return __de.pricing_feat_workspace1(inputs);
      return __ru.pricing_feat_workspace1(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "MCP integrations" |
 *
 * @param {Pricing_Feat_McpInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_mcp =
  /** @type {((inputs?: Pricing_Feat_McpInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_McpInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_mcp(inputs);
      if (locale === "en") return __en.pricing_feat_mcp(inputs);
      if (locale === "es") return __es.pricing_feat_mcp(inputs);
      if (locale === "fr") return __fr.pricing_feat_mcp(inputs);
      if (locale === "it") return __it.pricing_feat_mcp(inputs);
      if (locale === "de") return __de.pricing_feat_mcp(inputs);
      return __ru.pricing_feat_mcp(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "REST API /v1 — 60 req/min" |
 *
 * @param {Pricing_Feat_Api60Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_api60 =
  /** @type {((inputs?: Pricing_Feat_Api60Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Api60Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_api60(inputs);
      if (locale === "en") return __en.pricing_feat_api60(inputs);
      if (locale === "es") return __es.pricing_feat_api60(inputs);
      if (locale === "fr") return __fr.pricing_feat_api60(inputs);
      if (locale === "it") return __it.pricing_feat_api60(inputs);
      if (locale === "de") return __de.pricing_feat_api60(inputs);
      return __ru.pricing_feat_api60(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "REST API /v1 — 600 req/min" |
 *
 * @param {Pricing_Feat_Api600Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_api600 =
  /** @type {((inputs?: Pricing_Feat_Api600Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Api600Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_api600(inputs);
      if (locale === "en") return __en.pricing_feat_api600(inputs);
      if (locale === "es") return __es.pricing_feat_api600(inputs);
      if (locale === "fr") return __fr.pricing_feat_api600(inputs);
      if (locale === "it") return __it.pricing_feat_api600(inputs);
      if (locale === "de") return __de.pricing_feat_api600(inputs);
      return __ru.pricing_feat_api600(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "SDKs Python/TS" |
 *
 * @param {Pricing_Feat_SdksInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_sdks =
  /** @type {((inputs?: Pricing_Feat_SdksInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_SdksInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_sdks(inputs);
      if (locale === "en") return __en.pricing_feat_sdks(inputs);
      if (locale === "es") return __es.pricing_feat_sdks(inputs);
      if (locale === "fr") return __fr.pricing_feat_sdks(inputs);
      if (locale === "it") return __it.pricing_feat_sdks(inputs);
      if (locale === "de") return __de.pricing_feat_sdks(inputs);
      return __ru.pricing_feat_sdks(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Webhooks" |
 *
 * @param {Pricing_Feat_WebhooksInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_webhooks =
  /** @type {((inputs?: Pricing_Feat_WebhooksInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_WebhooksInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_webhooks(inputs);
      if (locale === "en") return __en.pricing_feat_webhooks(inputs);
      if (locale === "es") return __es.pricing_feat_webhooks(inputs);
      if (locale === "fr") return __fr.pricing_feat_webhooks(inputs);
      if (locale === "it") return __it.pricing_feat_webhooks(inputs);
      if (locale === "de") return __de.pricing_feat_webhooks(inputs);
      return __ru.pricing_feat_webhooks(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "ACP server" |
 *
 * @param {Pricing_Feat_AcpInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_acp =
  /** @type {((inputs?: Pricing_Feat_AcpInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_AcpInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_acp(inputs);
      if (locale === "en") return __en.pricing_feat_acp(inputs);
      if (locale === "es") return __es.pricing_feat_acp(inputs);
      if (locale === "fr") return __fr.pricing_feat_acp(inputs);
      if (locale === "it") return __it.pricing_feat_acp(inputs);
      if (locale === "de") return __de.pricing_feat_acp(inputs);
      return __ru.pricing_feat_acp(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "SSO / SAML" |
 *
 * @param {Pricing_Feat_SsoInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_sso =
  /** @type {((inputs?: Pricing_Feat_SsoInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_SsoInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_sso(inputs);
      if (locale === "en") return __en.pricing_feat_sso(inputs);
      if (locale === "es") return __es.pricing_feat_sso(inputs);
      if (locale === "fr") return __fr.pricing_feat_sso(inputs);
      if (locale === "it") return __it.pricing_feat_sso(inputs);
      if (locale === "de") return __de.pricing_feat_sso(inputs);
      return __ru.pricing_feat_sso(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "API Keys" |
 *
 * @param {Pricing_Cmp_Api_KeysInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_api_keys =
  /** @type {((inputs?: Pricing_Cmp_Api_KeysInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_Api_KeysInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_api_keys(inputs);
      if (locale === "en") return __en.pricing_cmp_api_keys(inputs);
      if (locale === "es") return __es.pricing_cmp_api_keys(inputs);
      if (locale === "fr") return __fr.pricing_cmp_api_keys(inputs);
      if (locale === "it") return __it.pricing_cmp_api_keys(inputs);
      if (locale === "de") return __de.pricing_cmp_api_keys(inputs);
      return __ru.pricing_cmp_api_keys(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Audit log" |
 *
 * @param {Pricing_Cmp_AuditInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_audit =
  /** @type {((inputs?: Pricing_Cmp_AuditInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_AuditInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_audit(inputs);
      if (locale === "en") return __en.pricing_cmp_audit(inputs);
      if (locale === "es") return __es.pricing_cmp_audit(inputs);
      if (locale === "fr") return __fr.pricing_cmp_audit(inputs);
      if (locale === "it") return __it.pricing_cmp_audit(inputs);
      if (locale === "de") return __de.pricing_cmp_audit(inputs);
      return __ru.pricing_cmp_audit(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "SLA" |
 *
 * @param {Pricing_Cmp_SlaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_sla =
  /** @type {((inputs?: Pricing_Cmp_SlaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_SlaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_sla(inputs);
      if (locale === "en") return __en.pricing_cmp_sla(inputs);
      if (locale === "es") return __es.pricing_cmp_sla(inputs);
      if (locale === "fr") return __fr.pricing_cmp_sla(inputs);
      if (locale === "it") return __it.pricing_cmp_sla(inputs);
      if (locale === "de") return __de.pricing_cmp_sla(inputs);
      return __ru.pricing_cmp_sla(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Up to 5 members" |
 *
 * @param {Pricing_Feat_Members5Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_members5 =
  /** @type {((inputs?: Pricing_Feat_Members5Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Members5Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_members5(inputs);
      if (locale === "en") return __en.pricing_feat_members5(inputs);
      if (locale === "es") return __es.pricing_feat_members5(inputs);
      if (locale === "fr") return __fr.pricing_feat_members5(inputs);
      if (locale === "it") return __it.pricing_feat_members5(inputs);
      if (locale === "de") return __de.pricing_feat_members5(inputs);
      return __ru.pricing_feat_members5(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Unlimited RAG" |
 *
 * @param {Pricing_Feat_Rag_UnlimitedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_rag_unlimited =
  /** @type {((inputs?: Pricing_Feat_Rag_UnlimitedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Rag_UnlimitedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_rag_unlimited(inputs);
      if (locale === "en") return __en.pricing_feat_rag_unlimited(inputs);
      if (locale === "es") return __es.pricing_feat_rag_unlimited(inputs);
      if (locale === "fr") return __fr.pricing_feat_rag_unlimited(inputs);
      if (locale === "it") return __it.pricing_feat_rag_unlimited(inputs);
      if (locale === "de") return __de.pricing_feat_rag_unlimited(inputs);
      return __ru.pricing_feat_rag_unlimited(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Email support (48h)" |
 *
 * @param {Pricing_Feat_Email_SupportInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_email_support =
  /** @type {((inputs?: Pricing_Feat_Email_SupportInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Email_SupportInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_email_support(inputs);
      if (locale === "en") return __en.pricing_feat_email_support(inputs);
      if (locale === "es") return __es.pricing_feat_email_support(inputs);
      if (locale === "fr") return __fr.pricing_feat_email_support(inputs);
      if (locale === "it") return __it.pricing_feat_email_support(inputs);
      if (locale === "de") return __de.pricing_feat_email_support(inputs);
      return __ru.pricing_feat_email_support(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Priority support" |
 *
 * @param {Pricing_Feat_Priority_SupportInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_priority_support =
  /** @type {((inputs?: Pricing_Feat_Priority_SupportInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Priority_SupportInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_priority_support(inputs);
      if (locale === "en") return __en.pricing_feat_priority_support(inputs);
      if (locale === "es") return __es.pricing_feat_priority_support(inputs);
      if (locale === "fr") return __fr.pricing_feat_priority_support(inputs);
      if (locale === "it") return __it.pricing_feat_priority_support(inputs);
      if (locale === "de") return __de.pricing_feat_priority_support(inputs);
      return __ru.pricing_feat_priority_support(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Priority support (SLA 24h)" |
 *
 * @param {Pricing_Feat_Priority_SlaInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_priority_sla =
  /** @type {((inputs?: Pricing_Feat_Priority_SlaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Priority_SlaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_priority_sla(inputs);
      if (locale === "en") return __en.pricing_feat_priority_sla(inputs);
      if (locale === "es") return __es.pricing_feat_priority_sla(inputs);
      if (locale === "fr") return __fr.pricing_feat_priority_sla(inputs);
      if (locale === "it") return __it.pricing_feat_priority_sla(inputs);
      if (locale === "de") return __de.pricing_feat_priority_sla(inputs);
      return __ru.pricing_feat_priority_sla(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "SSO / SAML (coming soon)" |
 *
 * @param {Pricing_Feat_Sso_SoonInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_sso_soon =
  /** @type {((inputs?: Pricing_Feat_Sso_SoonInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Sso_SoonInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_sso_soon(inputs);
      if (locale === "en") return __en.pricing_feat_sso_soon(inputs);
      if (locale === "es") return __es.pricing_feat_sso_soon(inputs);
      if (locale === "fr") return __fr.pricing_feat_sso_soon(inputs);
      if (locale === "it") return __it.pricing_feat_sso_soon(inputs);
      if (locale === "de") return __de.pricing_feat_sso_soon(inputs);
      return __ru.pricing_feat_sso_soon(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Unlimited workspaces" |
 *
 * @param {Pricing_Feat_Workspaces_UnlimitedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_workspaces_unlimited =
  /** @type {((inputs?: Pricing_Feat_Workspaces_UnlimitedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Workspaces_UnlimitedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt")
        return __pt.pricing_feat_workspaces_unlimited(inputs);
      if (locale === "en")
        return __en.pricing_feat_workspaces_unlimited(inputs);
      if (locale === "es")
        return __es.pricing_feat_workspaces_unlimited(inputs);
      if (locale === "fr")
        return __fr.pricing_feat_workspaces_unlimited(inputs);
      if (locale === "it")
        return __it.pricing_feat_workspaces_unlimited(inputs);
      if (locale === "de")
        return __de.pricing_feat_workspaces_unlimited(inputs);
      return __ru.pricing_feat_workspaces_unlimited(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Unlimited members" |
 *
 * @param {Pricing_Feat_Members_UnlimitedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_feat_members_unlimited =
  /** @type {((inputs?: Pricing_Feat_Members_UnlimitedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Members_UnlimitedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_members_unlimited(inputs);
      if (locale === "en") return __en.pricing_feat_members_unlimited(inputs);
      if (locale === "es") return __es.pricing_feat_members_unlimited(inputs);
      if (locale === "fr") return __fr.pricing_feat_members_unlimited(inputs);
      if (locale === "it") return __it.pricing_feat_members_unlimited(inputs);
      if (locale === "de") return __de.pricing_feat_members_unlimited(inputs);
      return __ru.pricing_feat_members_unlimited(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Feature" |
 *
 * @param {Pricing_Cmp_FeatureInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_feature =
  /** @type {((inputs?: Pricing_Cmp_FeatureInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_FeatureInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_feature(inputs);
      if (locale === "en") return __en.pricing_cmp_feature(inputs);
      if (locale === "es") return __es.pricing_cmp_feature(inputs);
      if (locale === "fr") return __fr.pricing_cmp_feature(inputs);
      if (locale === "it") return __it.pricing_cmp_feature(inputs);
      if (locale === "de") return __de.pricing_cmp_feature(inputs);
      return __ru.pricing_cmp_feature(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Storage" |
 *
 * @param {Pricing_Cmp_StorageInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_storage =
  /** @type {((inputs?: Pricing_Cmp_StorageInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_StorageInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_storage(inputs);
      if (locale === "en") return __en.pricing_cmp_storage(inputs);
      if (locale === "es") return __es.pricing_cmp_storage(inputs);
      if (locale === "fr") return __fr.pricing_cmp_storage(inputs);
      if (locale === "it") return __it.pricing_cmp_storage(inputs);
      if (locale === "de") return __de.pricing_cmp_storage(inputs);
      return __ru.pricing_cmp_storage(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Projects" |
 *
 * @param {Pricing_Cmp_ProjectsInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_projects =
  /** @type {((inputs?: Pricing_Cmp_ProjectsInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_ProjectsInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_projects(inputs);
      if (locale === "en") return __en.pricing_cmp_projects(inputs);
      if (locale === "es") return __es.pricing_cmp_projects(inputs);
      if (locale === "fr") return __fr.pricing_cmp_projects(inputs);
      if (locale === "it") return __it.pricing_cmp_projects(inputs);
      if (locale === "de") return __de.pricing_cmp_projects(inputs);
      return __ru.pricing_cmp_projects(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Unlimited" |
 *
 * @param {Pricing_Cmp_UnlimitedInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_unlimited =
  /** @type {((inputs?: Pricing_Cmp_UnlimitedInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_UnlimitedInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_unlimited(inputs);
      if (locale === "en") return __en.pricing_cmp_unlimited(inputs);
      if (locale === "es") return __es.pricing_cmp_unlimited(inputs);
      if (locale === "fr") return __fr.pricing_cmp_unlimited(inputs);
      if (locale === "it") return __it.pricing_cmp_unlimited(inputs);
      if (locale === "de") return __de.pricing_cmp_unlimited(inputs);
      return __ru.pricing_cmp_unlimited(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "7 days" |
 *
 * @param {Pricing_Cmp_Days7Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_days7 =
  /** @type {((inputs?: Pricing_Cmp_Days7Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_Days7Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_days7(inputs);
      if (locale === "en") return __en.pricing_cmp_days7(inputs);
      if (locale === "es") return __es.pricing_cmp_days7(inputs);
      if (locale === "fr") return __fr.pricing_cmp_days7(inputs);
      if (locale === "it") return __it.pricing_cmp_days7(inputs);
      if (locale === "de") return __de.pricing_cmp_days7(inputs);
      return __ru.pricing_cmp_days7(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "90 days" |
 *
 * @param {Pricing_Cmp_Days90Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_cmp_days90 =
  /** @type {((inputs?: Pricing_Cmp_Days90Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Cmp_Days90Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_cmp_days90(inputs);
      if (locale === "en") return __en.pricing_cmp_days90(inputs);
      if (locale === "es") return __es.pricing_cmp_days90(inputs);
      if (locale === "fr") return __fr.pricing_cmp_days90(inputs);
      if (locale === "it") return __it.pricing_cmp_days90(inputs);
      if (locale === "de") return __de.pricing_cmp_days90(inputs);
      return __ru.pricing_cmp_days90(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Frequently asked questions" |
 *
 * @param {Pricing_Faq_HeadingInputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_heading =
  /** @type {((inputs?: Pricing_Faq_HeadingInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_HeadingInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_heading(inputs);
      if (locale === "en") return __en.pricing_faq_heading(inputs);
      if (locale === "es") return __es.pricing_faq_heading(inputs);
      if (locale === "fr") return __fr.pricing_faq_heading(inputs);
      if (locale === "it") return __it.pricing_faq_heading(inputs);
      if (locale === "de") return __de.pricing_faq_heading(inputs);
      return __ru.pricing_faq_heading(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Does the 30-day trial require a credit card?" |
 *
 * @param {Pricing_Faq_Q1Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_q1 =
  /** @type {((inputs?: Pricing_Faq_Q1Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_Q1Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_q1(inputs);
      if (locale === "en") return __en.pricing_faq_q1(inputs);
      if (locale === "es") return __es.pricing_faq_q1(inputs);
      if (locale === "fr") return __fr.pricing_faq_q1(inputs);
      if (locale === "it") return __it.pricing_faq_q1(inputs);
      if (locale === "de") return __de.pricing_faq_q1(inputs);
      return __ru.pricing_faq_q1(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "No. The trial starts right after you create your account — no card needed." |
 *
 * @param {Pricing_Faq_A1Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_a1 =
  /** @type {((inputs?: Pricing_Faq_A1Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_A1Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_a1(inputs);
      if (locale === "en") return __en.pricing_faq_a1(inputs);
      if (locale === "es") return __es.pricing_faq_a1(inputs);
      if (locale === "fr") return __fr.pricing_faq_a1(inputs);
      if (locale === "it") return __it.pricing_faq_a1(inputs);
      if (locale === "de") return __de.pricing_faq_a1(inputs);
      return __ru.pricing_faq_a1(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Can I switch plans during the trial?" |
 *
 * @param {Pricing_Faq_Q2Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_q2 =
  /** @type {((inputs?: Pricing_Faq_Q2Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_Q2Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_q2(inputs);
      if (locale === "en") return __en.pricing_faq_q2(inputs);
      if (locale === "es") return __es.pricing_faq_q2(inputs);
      if (locale === "fr") return __fr.pricing_faq_q2(inputs);
      if (locale === "it") return __it.pricing_faq_q2(inputs);
      if (locale === "de") return __de.pricing_faq_q2(inputs);
      return __ru.pricing_faq_q2(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Yes. You can upgrade or downgrade at any time before the trial ends." |
 *
 * @param {Pricing_Faq_A2Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_a2 =
  /** @type {((inputs?: Pricing_Faq_A2Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_A2Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_a2(inputs);
      if (locale === "en") return __en.pricing_faq_a2(inputs);
      if (locale === "es") return __es.pricing_faq_a2(inputs);
      if (locale === "fr") return __fr.pricing_faq_a2(inputs);
      if (locale === "it") return __it.pricing_faq_a2(inputs);
      if (locale === "de") return __de.pricing_faq_a2(inputs);
      return __ru.pricing_faq_a2(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Which payment methods are accepted?" |
 *
 * @param {Pricing_Faq_Q3Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_q3 =
  /** @type {((inputs?: Pricing_Faq_Q3Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_Q3Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_q3(inputs);
      if (locale === "en") return __en.pricing_faq_q3(inputs);
      if (locale === "es") return __es.pricing_faq_q3(inputs);
      if (locale === "fr") return __fr.pricing_faq_q3(inputs);
      if (locale === "it") return __it.pricing_faq_q3(inputs);
      if (locale === "de") return __de.pricing_faq_q3(inputs);
      return __ru.pricing_faq_q3(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Brazil: PIX, Boleto and card via Asaas. International: card via Stripe." |
 *
 * @param {Pricing_Faq_A3Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_a3 =
  /** @type {((inputs?: Pricing_Faq_A3Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_A3Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_a3(inputs);
      if (locale === "en") return __en.pricing_faq_a3(inputs);
      if (locale === "es") return __es.pricing_faq_a3(inputs);
      if (locale === "fr") return __fr.pricing_faq_a3(inputs);
      if (locale === "it") return __it.pricing_faq_a3(inputs);
      if (locale === "de") return __de.pricing_faq_a3(inputs);
      return __ru.pricing_faq_a3(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "What happens when the trial ends?" |
 *
 * @param {Pricing_Faq_Q4Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_q4 =
  /** @type {((inputs?: Pricing_Faq_Q4Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_Q4Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_q4(inputs);
      if (locale === "en") return __en.pricing_faq_q4(inputs);
      if (locale === "es") return __es.pricing_faq_q4(inputs);
      if (locale === "fr") return __fr.pricing_faq_q4(inputs);
      if (locale === "it") return __it.pricing_faq_q4(inputs);
      if (locale === "de") return __de.pricing_faq_q4(inputs);
      return __ru.pricing_faq_q4(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Your account becomes inactive. Your data is kept for 30 days so you can subscribe." |
 *
 * @param {Pricing_Faq_A4Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_a4 =
  /** @type {((inputs?: Pricing_Faq_A4Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_A4Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_a4(inputs);
      if (locale === "en") return __en.pricing_faq_a4(inputs);
      if (locale === "es") return __es.pricing_faq_a4(inputs);
      if (locale === "fr") return __fr.pricing_faq_a4(inputs);
      if (locale === "it") return __it.pricing_faq_a4(inputs);
      if (locale === "de") return __de.pricing_faq_a4(inputs);
      return __ru.pricing_faq_a4(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Can I cancel anytime?" |
 *
 * @param {Pricing_Faq_Q5Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_q5 =
  /** @type {((inputs?: Pricing_Faq_Q5Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_Q5Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_q5(inputs);
      if (locale === "en") return __en.pricing_faq_q5(inputs);
      if (locale === "es") return __es.pricing_faq_q5(inputs);
      if (locale === "fr") return __fr.pricing_faq_q5(inputs);
      if (locale === "it") return __it.pricing_faq_q5(inputs);
      if (locale === "de") return __de.pricing_faq_q5(inputs);
      return __ru.pricing_faq_q5(inputs);
    }
  );
/**
 * | output |
 * | --- |
 * | "Yes. No minimum commitment. Cancel from the dashboard and access continues until the end of the paid period." |
 *
 * @param {Pricing_Faq_A5Inputs} inputs
 * @param {{ locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }} options
 * @returns {LocalizedString}
 */
export const pricing_faq_a5 =
  /** @type {((inputs?: Pricing_Faq_A5Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Faq_A5Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_faq_a5(inputs);
      if (locale === "en") return __en.pricing_faq_a5(inputs);
      if (locale === "es") return __es.pricing_faq_a5(inputs);
      if (locale === "fr") return __fr.pricing_faq_a5(inputs);
      if (locale === "it") return __it.pricing_faq_a5(inputs);
      if (locale === "de") return __de.pricing_faq_a5(inputs);
      return __ru.pricing_faq_a5(inputs);
    }
  );

export const pricing_feat_workspace5 =
  /** @type {((inputs?: Pricing_Feat_Workspace5Inputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Workspace5Inputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_workspace5(inputs);
      if (locale === "en") return __en.pricing_feat_workspace5(inputs);
      if (locale === "es") return __es.pricing_feat_workspace5(inputs);
      if (locale === "fr") return __fr.pricing_feat_workspace5(inputs);
      if (locale === "it") return __it.pricing_feat_workspace5(inputs);
      if (locale === "de") return __de.pricing_feat_workspace5(inputs);
      return __ru.pricing_feat_workspace5(inputs);
    }
  );

export const pricing_feat_mcp_acp =
  /** @type {((inputs?: Pricing_Feat_Mcp_AcpInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Mcp_AcpInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_mcp_acp(inputs);
      if (locale === "en") return __en.pricing_feat_mcp_acp(inputs);
      if (locale === "es") return __es.pricing_feat_mcp_acp(inputs);
      if (locale === "fr") return __fr.pricing_feat_mcp_acp(inputs);
      if (locale === "it") return __it.pricing_feat_mcp_acp(inputs);
      if (locale === "de") return __de.pricing_feat_mcp_acp(inputs);
      return __ru.pricing_feat_mcp_acp(inputs);
    }
  );

export const pricing_feat_support_sla =
  /** @type {((inputs?: Pricing_Feat_Support_SlaInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Support_SlaInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_support_sla(inputs);
      if (locale === "en") return __en.pricing_feat_support_sla(inputs);
      if (locale === "es") return __es.pricing_feat_support_sla(inputs);
      if (locale === "fr") return __fr.pricing_feat_support_sla(inputs);
      if (locale === "it") return __it.pricing_feat_support_sla(inputs);
      if (locale === "de") return __de.pricing_feat_support_sla(inputs);
      return __ru.pricing_feat_support_sla(inputs);
    }
  );

export const pricing_feat_everything_plus =
  /** @type {((inputs?: Pricing_Feat_Everything_PlusInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Everything_PlusInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_everything_plus(inputs);
      if (locale === "en") return __en.pricing_feat_everything_plus(inputs);
      if (locale === "es") return __es.pricing_feat_everything_plus(inputs);
      if (locale === "fr") return __fr.pricing_feat_everything_plus(inputs);
      if (locale === "it") return __it.pricing_feat_everything_plus(inputs);
      if (locale === "de") return __de.pricing_feat_everything_plus(inputs);
      return __ru.pricing_feat_everything_plus(inputs);
    }
  );

export const pricing_feat_rest_api =
  /** @type {((inputs?: Pricing_Feat_Rest_ApiInputs, options?: { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }) => LocalizedString) & import('../runtime.js').MessageMetadata<Pricing_Feat_Rest_ApiInputs, { locale?: "pt" | "en" | "es" | "fr" | "it" | "de" | "ru" }, {}>} */ (
    (inputs = {}, options = {}) => {
      const locale = experimentalStaticLocale ?? options.locale ?? getLocale();
      if (locale === "pt") return __pt.pricing_feat_rest_api(inputs);
      if (locale === "en") return __en.pricing_feat_rest_api(inputs);
      if (locale === "es") return __es.pricing_feat_rest_api(inputs);
      if (locale === "fr") return __fr.pricing_feat_rest_api(inputs);
      if (locale === "it") return __it.pricing_feat_rest_api(inputs);
      if (locale === "de") return __de.pricing_feat_rest_api(inputs);
      return __ru.pricing_feat_rest_api(inputs);
    }
  );
