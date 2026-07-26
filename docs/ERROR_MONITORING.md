# Hosted-alpha error monitoring

Status: the privacy-safe Sentry integration is implemented and disabled by
default. No event is transmitted until Doug explicitly creates a Sentry
project and adds its DSN to the hosted environment. A real test event and alert
delivery remain required before external alpha access.

Official references:

- https://docs.sentry.io/platforms/python/integrations/fastapi/
- https://docs.sentry.io/platforms/python/configuration/options/

## What users see

An unexpected API failure returns:

- HTTP 500;
- the plain message `Internal server error.`; and
- a short request ID in both the response body and `X-Request-ID` header.

The request ID gives a tester something safe and useful to report without
showing internal exception details.

## What Polaris records locally

Polaris logs:

- request ID;
- HTTP method;
- URL path without query parameters;
- response status;
- elapsed time; and
- exception type.

Hosted logs do not record request bodies, authorization tokens, cookies,
passwords, email addresses, observing coordinates, or exception values that may
include database parameters.

## Optional Sentry boundary

Set the following only after a Sentry project is approved:

```text
POLARIS_SENTRY_DSN=https://<public-dsn>
```

With a DSN configured, Polaris initializes Sentry with:

- automatic integrations disabled so Polaris reports only the failures it
  explicitly chooses to report;
- default personally identifiable information disabled;
- local variables excluded from stack frames;
- request bodies disabled;
- performance traces and profiles disabled for the alpha;
- user context and breadcrumbs removed;
- headers, cookies, query strings, and request environment removed;
- credential, email, address, and coordinate fields filtered; and
- exception values redacted while retaining code locations and stack shape.

The Sentry DSN belongs only in ignored local environment configuration or the
future host's protected environment-variable store. Do not commit it.

## Remaining monitoring gate

Before an external tester is invited:

1. create a dedicated Polaris Sentry project;
2. review Sentry organization and project data-scrubbing settings;
3. enable default server-side scrubbing and IP-address scrubbing;
4. configure the DSN in staging;
5. trigger one synthetic failure that contains fake sensitive values;
6. confirm the event arrives with those values absent;
7. configure and receive an alert; and
8. document how Doug finds the event using the user's request ID.

Until those steps pass, monitoring is implemented but not operational.
