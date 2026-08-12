# FAQ — Closed Beta & Release Candidate (P5.1 / P5.2)

## Is DSP giving investment advice?

No. Outputs are research and educational. See the Investment Research Disclaimer.

## Who can access a closed beta deployment?

Only invited identities (approved/activated) and administrators when invitation-only mode is on.

## What if I am invited but still blocked?

Confirm you signed in with the same email/username as the invite. Ask an admin to check Administration → Closed Beta.

## What happens if the API is down in production?

In production closed beta with invitation-only enabled, access fails closed until the beta status API recovers. Administrators can still enter.

## Where do I send feedback?

Use the floating **Feedback** control. Do not paste secrets, holdings, or research envelopes.

## Are screenshots uploaded?

No. Provide an optional note describing visual context.

## How do admins back up beta invites?

Use **Export beta snapshot** on the admin Closed Beta panel, or `GET /api/v1/admin/beta/snapshot`.

## When is commercial launch?

P5.2 recommends **READY WITH MINOR CONDITIONS** for RC. Unrestricted GA waits on soak attestation and durable invite storage for multi-replica deploys.
