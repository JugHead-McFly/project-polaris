# Hosted-alpha error monitoring

Status: the privacy-safe Sentry integration is implemented and disabled by
default. A Sentry project was created and tested on July 26, 2026, but Polaris
removed its staging DSN after Sentry displayed an IP-derived approximate city
despite its IP-scrubbing option being enabled. No event is currently
transmitted. A privacy-safe transport and a repeat test remain required before
external alpha access.

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
- the device hostname and all automatic contexts removed, retaining only the
  Polaris request ID, method, and path; and
- headers, cookies, query strings, and request environment removed;
- credential, email, address, and coordinate fields filtered; and
- exception values redacted while retaining code locations and stack shape.

The Sentry DSN belongs only in ignored local environment configuration or the
future host's protected environment-variable store. Do not commit it.

## Remaining monitoring gate

Before an external tester is invited:

1. identify a monitoring transport that does not expose an observer's or
   developer's network-derived location to the monitoring provider;
2. configure that transport and repeat the fake-sensitive-value test;
3. confirm the event has no hostname, IP address, city, or coordinates;
4. configure and receive an alert; and
5. document how Doug finds the event using the user's request ID.

Until those steps pass, monitoring is implemented but not operational.
