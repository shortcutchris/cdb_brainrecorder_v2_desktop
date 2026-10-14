# Instructions for this Python Raspberry Pi repository

Read `README.md`, `docs/architecture/README.md`, and
`docs/customer-image/README.md` before changing packaging, installation,
services, dependencies, device management, or deployment.

For every feature/release, assess both existing-device updates and clean SD-image
installation. Document the image impact: included automatically from tracked
allowlisted app files, explicit factory/runtime changes needed, or no impact.
New assets must be tracked and included in the appropriate allowlist. Tests must
cover relevant clean-install paths as well as upgrades. Never claim a recipe is
a built image or a built image is hardware boot-certified without evidence.

Customer images must come from a clean committed source and a dedicated builder,
never a clone of a live customer SD card. Never copy credentials, recordings,
profiles, device identity, SSH/Tailscale keys or the private release-signing key.
Preserve the current Pi configuration unless the user explicitly authorizes a
specific deployment or configuration change. Large images and raw build logs
stay outside Git; commit the recipe, documentation and sanitized acceptance data.
