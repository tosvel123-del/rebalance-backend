# Scheduled Market Checks

The API does not run an in-process scheduler. This prevents duplicate jobs when
the service scales and lets a serverless service sleep outside market hours.

Configure a Cloud Scheduler HTTP job to call the following endpoint every five
minutes during Korean market hours:

`POST https://YOUR-SERVICE/internal/jobs/market-cycle`

Set the `X-Job-Secret` header to the same value as `JOB_TRIGGER_SECRET`. Keep
the endpoint private where the hosting platform supports authenticated service
invocation. The shared secret is a second safeguard, not a replacement for
platform authentication.

Suggested schedules in the `Asia/Seoul` timezone:

- `*/5 9-15 * * 1-5` for regular market checks
- `*/15 15 * * 1-5` for the post-close alert resolution window

The job endpoint rejects overlapping work. In production set `ENVIRONMENT` to
`production`, set `ALLOW_DEMO_AUTH=false`, and configure all three required
secrets before deploying.
