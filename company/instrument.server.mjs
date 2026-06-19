import * as Sentry from '@sentry/tanstackstart-react'

const sentryDsn =
  import.meta.env?.VITE_SENTRY_DSN ?? process.env.VITE_SENTRY_DSN

if (!sentryDsn) {
  console.warn('VITE_SENTRY_DSN is not defined. Sentry is not running.')
} else {
  const isProd = process.env.NODE_ENV === 'production'

  Sentry.init({
    dsn: sentryDsn,
    environment: process.env.NODE_ENV ?? 'development',
    sendDefaultPii: true,
    tracesSampleRate: isProd ? 0.2 : 1.0,
    replaysSessionSampleRate: isProd ? 0.05 : 1.0,
    replaysOnErrorSampleRate: 1.0,
  })
}
