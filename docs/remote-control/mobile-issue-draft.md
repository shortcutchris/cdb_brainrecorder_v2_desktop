# Draft issue for BIK-GmbH/cdb-knowledge-mobile

Approved by the user and submitted: [cdb-knowledge-mobile #63](https://github.com/BIK-GmbH/cdb-knowledge-mobile/issues/63).

**Title:** feat: pair cdbMOBILE with a Pi voice device and control its conversation

## Summary
Allow a signed-in mobile user to pair their Raspberry Pi voice device and control the conversation running on that device.

## Desired Outcome
Select a paired Pi, start or end its conversation, mute its microphone and see confirmed device status. Audio stays on the Pi. Physical Bluetooth remotes are outside this first implementation.

## Acceptance Criteria
- [ ] Pair using a short-lived code and explicit confirmation on the Pi; require the same verified CDB person, tenant and environment.
- [ ] Show and revoke paired devices without granting control to existing display receivers.
- [ ] Start, end and set mute without opening the mobile microphone or a second voice session.
- [ ] Protect recordings, paused recordings and other occupied audio states; show clear busy/offline feedback.
- [ ] Handle duplicate, expired and stale commands, account changes and reconnects without replaying actions.
- [ ] Support German/English, light/dark mode and phone/tablet layouts; separate automated tests, real-device acceptance and beta delivery.

## Technical Notes
A new authenticated CDB control contract is required. The capability remains disabled until supported; creating the issue does not deploy anything.
