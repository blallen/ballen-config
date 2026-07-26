# SSH transfer

Prefer generating a fresh per-machine key and registering its public key with
each required service. This limits the effect of a lost or retired laptop and
makes later revocation unambiguous.

If an existing key must move, inspect `~/.ssh` first and distinguish private
keys, `.pub` public keys, optional `config`, and expendable `known_hosts`.
Transfer only through an encrypted local medium or a trusted direct connection.
Never use a plaintext cloud folder, unencrypted USB drive, or other unencrypted
removable media.

The bootstrap owns `~/.ssh/config`, where it installs public GitHub and GitLab
defaults and includes `~/.ssh/config.local`. Move private hosts, aliases, jump
hosts, internal usernames, and machine-specific identity paths into
`config.local`; do not add them to the repository template.

On the destination:

- Set `~/.ssh` to mode `0700`.
- Set private keys, `config`, and `config.local` to mode `0600`.
- Set public keys to mode `0644`.
- Load the selected private key into the macOS agent and Keychain with
  `ssh-add --apple-use-keychain <private-key-path>`.
- Test GitHub, GitLab, and every other required host.

For a host not already known, verify its fingerprint out of band through a
trusted source before accepting it. After successful verification, securely
remove the temporary encrypted transfer copy from both ends and from any
transfer medium.

Do not reuse an unverified host entry, and never commit keys, host credentials,
SSH agent state, or remote-login state to this repository. Local bootstrap
state and credential status also remain outside Git.
