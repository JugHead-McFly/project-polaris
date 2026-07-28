# Hosted-alpha error monitoring

Status: the privacy-safe Sentry integration is implemented and enabled only on
the production host. The final controlled Render test passed on July 27, 2026.
Sentry received the redacted synthetic error with the expected release,
environment, request ID, and `STARTUP` method while showing a null user IP and
no city, coordinates, observatory name, URL, request contents, or arbitrary
text. Polaris still refuses all monitoring transmission from local and staging
environments.

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
- an explicit non-identifying IP placeholder before transport so Sentry cannot
  derive geography from the production host's outbound network address (the
  server-side scrubber then removes the placeholder);
- only the Polaris request ID and HTTP method retained as request context; and
- exception values redacted while retaining a minimal error type, relative code
  location, function, line number, and stack shape.

The Sentry DSN belongs only in ignored local environment configuration or the
future host's protected environment-variable store. Do not commit it.

## Monitoring verification

The production-host privacy test passed on July 27, 2026:

1. Render deployed commit `e9f7c07`.
2. A one-time startup smoke identifier produced one synthetic Sentry issue.
3. The event retained only the expected operational identifiers and redacted
   error shape.
4. User IP was null and no derived geography or other personal/observatory
   context appeared.
5. The one-time smoke identifier was removed and the synthetic issue deleted.
6. Privacy-safe production transmission remains enabled.

The production alert workflow also passed on July 27, 2026:

1. Sentry accepted a direct test notification.
2. A production-only alert was created for the `python-fastapi` project.
3. The alert notifies Doug when a new production issue is created or an issue
   changes state.
4. A second one-time synthetic issue triggered the saved alert.
5. The one-time smoke identifier and synthetic issue were removed, and Render
   returned to the normal production configuration.

## Finding a failure from a user's request ID

If a tester sees `Internal server error.`, ask only for the short request ID
shown by Polaris and the approximate time the problem happened. Do not ask for
the tester's password, token, exact address, or other private account details.

To find the matching Sentry event:

1. Open Sentry and choose **Issues**.
2. Search for `polaris.request_id:<request-id>`, replacing `<request-id>` with
   the exact value the tester supplied.
3. Open the matching issue and confirm that its environment is `production`.
4. Use the release, time, HTTP method, and redacted stack location to investigate
   the failure. The error value and user details are intentionally unavailable.

If Sentry has no matching event, open the Render service logs and search for the
exact request ID. Polaris writes the ID to its protected server log even when an
event could not be delivered to Sentry. Record the request ID in the support
note so the investigation stays tied to the tester's report.
