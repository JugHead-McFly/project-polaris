# Hosted-alpha error monitoring

Status: the privacy-safe Sentry integration is implemented and locked off by
default. A Sentry project was created and tested on July 26, 2026, but Polaris
removed its staging DSN after Sentry displayed an IP-derived approximate city
despite its IP-scrubbing option being enabled. Polaris now refuses to transmit
from local and staging environments. A repeat test from the eventual production
host remains required before external alpha access.

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
POLARIS_SENTRY_ALLOW_TRANSMISSION=true
```

Both values are effective only when `POLARIS_ENVIRONMENT=production`. This
prevents a developer's home-network location from reaching Sentry during local
or staging tests. In production, the FastAPI host sends the event, so its
network endpoint belongs to the hosting provider rather than the observer.

With an approved production configuration, Polaris initializes Sentry with:

- automatic integrations disabled so Polaris reports only the failures it
  explicitly chooses to report;
- default personally identifiable information disabled;
- local variables excluded from stack frames;
- request bodies disabled;
- performance traces and profiles disabled for the alpha;
- source code excerpts and local variables excluded;
- no browser request, user context, breadcrumbs, hostname, arbitrary extras,
  or automatic contexts retained;
- only the Polaris request ID and HTTP method retained as request context; and
- exception values redacted while retaining a minimal error type, relative code
  location, function, line number, and stack shape.

The Sentry DSN belongs only in ignored local environment configuration or the
future host's protected environment-variable store. Do not commit it.

## Remaining monitoring gate

Before an external tester is invited:

1. deploy the production FastAPI service without enabling Sentry;
2. add the DSN and explicit transmission approval only to the production host;
3. repeat the fake-sensitive-value test from that host;
4. confirm the event has no observer or developer hostname, IP address, city,
   coordinates, request contents, or arbitrary text (a hosting-region label is
   acceptable because it identifies infrastructure, not a person);
5. configure and receive an alert; and
6. document how Doug finds the event using the user's request ID.

Until those steps pass, monitoring is implemented but not operational.
